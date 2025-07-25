#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Korean Sentiment Analysis Pipeline
---------------------------------
- BigQuery -> PySpark -> BERT inference -> BigQuery
- Supports sample_mode: head | random | balanced
"""

import os
import argparse
import datetime as _dt
from typing import Literal

import pandas as pd
import torch
from pyspark.sql import SparkSession, DataFrame, Window
from pyspark.sql import functions as F
from transformers import BertTokenizer, BertForSequenceClassification

# ──────────────────────────────────────────────
# 하이퍼파라미터
# ──────────────────────────────────────────────
THRESH_POS = float(os.getenv("THRESH_POS", "0.6"))
THRESH_NEG = float(os.getenv("THRESH_NEG", "0.4"))
MAX_LEN    = int(os.getenv("MAX_LEN", "128"))

TOKENIZER: BertTokenizer | None = None
MODEL: BertForSequenceClassification | None = None

# ──────────────────────────────────────────────
# 모델 로딩
# ──────────────────────────────────────────────
def _resolve_model_path() -> str:
    model_path = os.getenv("MODEL_PATH")
    if model_path and os.path.exists(model_path):
        return model_path
    raise FileNotFoundError(f"MODEL_PATH not found: {model_path}")

def _load_model_once() -> tuple[BertTokenizer, BertForSequenceClassification]:
    global TOKENIZER, MODEL
    if TOKENIZER is None or MODEL is None:
        mp = _resolve_model_path()
        print(f"[INFO] Loading model from: {mp}")
        TOKENIZER = BertTokenizer.from_pretrained(mp, local_files_only=True)
        MODEL     = BertForSequenceClassification.from_pretrained(
            mp,
            local_files_only=True,
            num_labels=2,
            id2label={ "0": "negative", "1": "positive" },
            label2id={ "negative": 0, "positive": 1 }
        ).eval()
    return TOKENIZER, MODEL

# ──────────────────────────────────────────────
# 추론 로직
# ──────────────────────────────────────────────
def _run_inference(texts: pd.Series) -> pd.Series:
    tokenizer, model = _load_model_once()
    inputs = tokenizer(
        list(texts),
        padding=True,
        truncation=True,
        return_tensors="pt",
        max_length=MAX_LEN,
    )
    with torch.no_grad():
        logits = model(**inputs).logits
        probs  = torch.softmax(logits, dim=1).cpu().numpy()[:, 1]

    return pd.Series([
        "positive" if p >= THRESH_POS else
        "negative" if p < THRESH_NEG else "neutral"
        for p in probs
    ])

# ──────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────
def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser("Korean review sentiment inference")
    parser.add_argument("--project",         default="de6-2ez")
    parser.add_argument("--dataset",         default="gold")
    parser.add_argument("--input_table",     default="fact_reviews")
    parser.add_argument("--output_table",    default="predicted_reviews")
    parser.add_argument("--temp_gcs_bucket", default="sentiment-pipeline")
    parser.add_argument("--test_limit",      type=int, default=1000)
    parser.add_argument("--sample_mode",     choices=["random", "head", "balanced"], default="random")
    parser.add_argument("--npartitions",        type=int, default=8)
    parser.add_argument("--shuffle_partitions", type=int, default=16)
    parser.add_argument("--read_parallelism",   type=int, default=8)
    parser.add_argument("--arrow_batch",        type=int, default=256)
    parser.add_argument("--thresh_pos", type=float, default=None)
    parser.add_argument("--thresh_neg", type=float, default=None)
    parser.add_argument("--max_len",    type=int,   default=None)
    return parser

def _apply_cli_thresholds(args: argparse.Namespace):
    global THRESH_POS, THRESH_NEG, MAX_LEN
    if args.thresh_pos is not None:
        THRESH_POS = args.thresh_pos
    if args.thresh_neg is not None:
        THRESH_NEG = args.thresh_neg
    if args.max_len is not None:
        MAX_LEN = args.max_len

# ──────────────────────────────────────────────
# 샘플링
# ──────────────────────────────────────────────
def _sample_df(
    df: DataFrame,
    limit: int,
    mode: Literal["head", "random", "balanced"]
) -> DataFrame:
    if limit <= 0:
        return df

    if mode == "head":
        return df.limit(limit)

    if mode == "balanced":
        per_cls = limit // 3
        extra   = limit - per_cls * 3
        target  = {
            "positive": per_cls + extra,
            "neutral" : per_cls + extra,  # neutral 클래스도 동일하게 보충
            "negative": per_cls,
        }
        w = Window.partitionBy("true_label").orderBy(F.rand())
        df_rn = df.withColumn("rn", F.row_number().over(w))
        cond = (
            ((F.col("true_label") == "positive") & (F.col("rn") <= target["positive"])) |
            ((F.col("true_label") == "neutral")  & (F.col("rn") <= target["neutral"]))  |
            ((F.col("true_label") == "negative") & (F.col("rn") <= target["negative"]))
        )
        return df_rn.filter(cond).drop("rn")

    if mode == "random":
        min_each = limit // 2
        remain   = limit - min_each * 2

        if "review_uid" not in df.columns:
            raise ValueError("❌ 'review_uid' 컬럼이 있어야 중복 제거가 가능합니다.")

        df_pos = df.filter(F.col("true_label") == "positive").orderBy(F.rand()).limit(min_each)
        df_neg = df.filter(F.col("true_label") == "negative").orderBy(F.rand()).limit(min_each)

        sampled_ids = df_pos.select("review_uid").union(df_neg.select("review_uid")).distinct()
        df_rest = df.join(sampled_ids, on="review_uid", how="left_anti").orderBy(F.rand()).limit(remain)

        df_final = df_pos.union(df_neg).union(df_rest)

        print(f"[DEBUG] df_pos: {df_pos.count()}, df_neg: {df_neg.count()}, df_rest: {df_rest.count()}, final: {df_final.count()}")
        return df_final

    raise ValueError(f"Unknown sample_mode: {mode}")

# ──────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────
def main() -> None:
    args = _build_parser().parse_args()
    _apply_cli_thresholds(args)

    spark = (
        SparkSession.builder.appName("KoreanSentiment")
        .config("spark.sql.shuffle.partitions", str(args.shuffle_partitions))
        .config("spark.sql.execution.arrow.pyspark.enabled", "true")
        .config("spark.sql.execution.arrow.maxRecordsPerBatch", str(args.arrow_batch))
        .config("spark.python.worker.reuse", "true")
        .config("spark.network.timeout", "600s")
        .config("spark.executor.heartbeatInterval", "60s")
        .config("temporaryGcsBucket", args.temp_gcs_bucket)
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("INFO")

    # 모델 및 토크나이저를 Spark 전체에서 공유
    tokenizer, model = _load_model_once()
    tokenizer_bcast = spark.sparkContext.broadcast(tokenizer)
    model_bcast = spark.sparkContext.broadcast(model)

    @F.pandas_udf("string")
    def predict_sentiment_udf(text_col: pd.Series) -> pd.Series:
        tokenizer = tokenizer_bcast.value
        model = model_bcast.value
        return _run_inference(text_col)

    bq_in  = f"{args.project}.{args.dataset}.{args.input_table}"
    bq_out = f"{args.project}.{args.dataset}.{args.output_table}"

    # 데이터 로드 및 필터링
    df_raw = (
        spark.read.format("bigquery")
        .option("table", bq_in)
        .option("parallelism", str(args.read_parallelism))
        .load()
        .filter(
            F.col("content").isNotNull() &
            (F.col("content") != "") &
            F.col("star").isNotNull() &
            (F.col("star") >= 1)  # ⭐ 별점 0 포함 제거
        )
    )

    # true_label 생성
    df_raw = df_raw.withColumn(
        "true_label",
        F.when(F.col("star") >= 4, "positive")
         .when(F.col("star") <= 2, "negative")
         .otherwise("neutral")
    )

    # 샘플링
    df = _sample_df(df_raw, args.test_limit, args.sample_mode)
    if args.test_limit <= 0 and args.npartitions > 0:
        df = df.repartition(args.npartitions)

    # 추론
    df = df.withColumn(
        "pred_label",
        predict_sentiment_udf(F.col("content"))
    ).withColumn(
        "is_correct",
        (F.col("true_label") == F.col("pred_label"))
    )

    # 정확도 출력
    df_for_acc = df.filter(~(F.col("true_label") == "neutral"))
    acc = df_for_acc.selectExpr("avg(int(is_correct)) AS acc").first().acc
    print(f"[RESULT] Accuracy (excluding neutral): {acc:.4f}")

    # 저장
    run_date_str = _dt.date.today().isoformat()
    (
        df.withColumn("run_date", F.to_date(F.lit(run_date_str)))
          .write.format("bigquery")
          .option("table", bq_out)
          .option("partitionField", "run_date")
          .mode("append")
          .save()
    )

    spark.stop()

# ──────────────────────────────────────────────
if __name__ == "__main__":
    main()
