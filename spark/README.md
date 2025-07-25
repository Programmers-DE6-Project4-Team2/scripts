# Korean Sentiment Analysis Pipeline

이 프로젝트는 PySpark와 HuggingFace BERT를 활용한 한국어 감성 분석 파이프라인입니다.

## 🛠 구성
- PySpark + HuggingFace Transformers  
- Google BigQuery / GCS 연동  
- BERT 기반 이진 감성 분류 모델  
- Arrow + Pandas UDF 기반 추론  

## 📦 설치 방법 (Ubuntu VM)

```bash
# 1. 레포 클론
git clone https://github.com/your-id/sentiment-pipeline.git
cd sentiment-pipeline

# 2. 환경변수 설정
cp .env.example .env
vi .env  # HF_TOKEN 값 입력

# 3. 전체 환경 세팅
bash setup.sh
source /etc/profile
```

## 🚀 실행 방법

```bash
spark-submit \
  --master local[*] \
  main.py \
  --test_limit 5000 \
  --sample_mode random \
  --arrow_batch 128 \
  --shuffle_partitions 16 \
  --npartitions 16 \
  --write_mode overwrite
```

## 📁 입력 테이블 구조 예시

- review_uid: string  
- content: string  
- star: int  

## ✅ 주요 특징

- PR 기반 협업 지원 (GitHub Actions 가능)  
- 감성 분류 정확도 측정 내장  
- BigQuery → Spark → BERT → BigQuery 전체 자동화  
