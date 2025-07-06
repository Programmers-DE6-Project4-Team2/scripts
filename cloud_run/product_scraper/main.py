from flask import Flask, request, jsonify
from oliveyoung_scraper_module import OliveYoungCrawler
from google.cloud import storage
import pandas as pd
import os
import logging
from datetime import datetime
from dotenv import load_dotenv


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()

app = Flask(__name__)

def upload_csv_to_gcs(bucket_name: str, dataframe: pd.DataFrame, destination_blob_name: str):
    logger.info("🔄 [GCS] 업로드 시작...")
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    csv_data = dataframe.to_csv(index=False, encoding="utf-8-sig")
    logger.info(f"🔄 [GCS] CSV 변환 완료, 크기: {len(csv_data)} bytes")
    blob.upload_from_string(csv_data, content_type="text/csv")
    logger.info(f"✅ [GCS] 업로드 완료: gs://{bucket_name}/{destination_blob_name}")
    return f"gs://{bucket_name}/{destination_blob_name}"


@app.route("/scrape", methods=["POST"])
def scrape():
    data = request.get_json()
    category_url = data.get("category_url")
    category_name = data.get("category_name", "default")
    max_pages = int(data.get("max_pages", 1))

    if not category_url:
        return jsonify({"status": "error", "message": "category_url is required"}), 400

    logger.info(f"[START] category={category_name} max_pages={max_pages}")
    crawler = OliveYoungCrawler(headless=True)

    try:
        # 1. 크롤링
        products = crawler.extract_product_list(category_url, max_pages=max_pages)
        df = pd.DataFrame(products)

        # 2. GCS 업로드
        bucket_name = "de6-ez2"
        now = datetime.utcnow()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        year = now.strftime("%Y")
        month = now.strftime("%m")
        day = now.strftime("%d")
        filename = f"raw-data/olive-young/{category_name}/{year}/{month}/{day}/{category_name}_{timestamp}.csv"
        gcs_path = upload_csv_to_gcs(bucket_name, df, filename)

        # 3. 응답
        return jsonify({
            "status": "completed",
            "category_name": category_name,
            "products_count": len(products),
            "gcs_path": gcs_path
        })

    except Exception as e:
        logger.exception("크롤링 도중 에러 발생")
        return jsonify({
            "status": "error",
            "message": str(e),
        }), 500

    finally:
        crawler.close()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
