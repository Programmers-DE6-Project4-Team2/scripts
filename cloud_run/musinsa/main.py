#!/usr/bin/env python3
"""
무신사 데이터 수집 Flask 애플리케이션 (GCS 연동 포함)
Docker 환경에서 실행되는 크롤링 서비스
"""

import os
import logging
from datetime import datetime
from flask import Flask, jsonify, request
from dotenv import load_dotenv
import pandas as pd

# 로컬 환경일 경우 dotenv 로드
if os.environ.get("ENV", "").lower() != "production":
    load_dotenv()

from musinsa_crawler import MusinsaCrawler
from gcs_uploader import (
    upload_csv_to_gcs,
    upload_json_to_gcs,
    upload_file_to_gcs,
    list_gcs_files
)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)


class MusinsaDataPipeline:
    """무신사 데이터 수집 파이프라인 (GCS 연동 포함)"""

    def __init__(self):
        self.bucket_name = os.environ.get("GCS_BUCKET_NAME")
        self.project_id = os.environ.get("GCS_PROJECT_ID")
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.gcs_enabled = bool(self.bucket_name and self.bucket_name != "your-bucket-name")

        if self.gcs_enabled:
            logger.info(f"GCS 업로드 활성화: {self.bucket_name}")
        else:
            logger.info("GCS 업로드 비활성화 - 로컬 저장만 수행")

    def _upload_to_gcs(self, data: any, filename: str, file_type: str, folder: str = "") -> bool:
        """GCS 업로드 헬퍼 메서드"""
        if not self.gcs_enabled:
            return False

        try:
            if folder:
                gcs_path = f"raw-data/musinsa/{folder}/{filename}"
            else:
                gcs_path = f"raw-data/musinsa/{filename}"

            if file_type == "csv" and isinstance(data, pd.DataFrame):
                return upload_csv_to_gcs(self.bucket_name, data, gcs_path, self.project_id)
            elif file_type == "json":
                return upload_json_to_gcs(self.bucket_name, data, gcs_path, self.project_id)
            elif file_type == "file":
                return upload_file_to_gcs(self.bucket_name, data, gcs_path, self.project_id)
            else:
                logger.error(f"지원하지 않는 파일 타입: {file_type}")
                return False

        except Exception as e:
            logger.error(f"GCS 업로드 중 오류: {e}")
            return False


        except Exception as e:
            logger.error(f"GCS 업로드 중 오류: {e}")
            return False

    def run_product_collection(self, max_pages: int = 5, size: int = 40) -> dict:
        """상품 데이터 수집 실행"""
        try:
            logger.info(f"무신사 상품 크롤링 시작 - 최대 {max_pages}페이지")

            # 크롤러 초기화
            crawler = MusinsaCrawler(
                section_id="231",
                size=size,
                category_code="104001",
                max_pages=max_pages,
                review_page_size=20,
                review_max_pages=1
            )

            # 상품 데이터 수집
            result = crawler.crawling_musinsa_all()
            products = result.get('products', [])

            if not products:
                return {"status": "error", "message": "수집된 상품 데이터가 없습니다."}

            # 로컬 파일 저장
            csv_filename = f"musinsa_products_{self.timestamp}.csv"
            json_filename = f"musinsa_products_{self.timestamp}.json"

            crawler.save_products_to_csv(csv_filename)
            crawler.save_to_json(json_filename)

            # GCS 업로드
            gcs_upload_success = False
            if self.gcs_enabled:
                df = pd.DataFrame(products)
                csv_success = self._upload_to_gcs(df, csv_filename, "csv", "products")
                json_success = self._upload_to_gcs(products, json_filename, "json", "products")
                gcs_upload_success = csv_success and json_success

            logger.info(f"상품 크롤링 완료 - {len(products)}개 상품 수집")

            return {
                "status": "success",
                "message": f"{len(products)}개 상품 데이터 수집 완료",
                "data": {
                    "product_count": len(products),
                    "csv_file": csv_filename,
                    "json_file": json_filename,
                    "timestamp": self.timestamp,
                    "gcs_uploaded": gcs_upload_success,
                    "gcs_path": f"gs://{self.bucket_name}/raw-data/musinsa/products/" if self.gcs_enabled else None
                }
            }

        except Exception as e:
            logger.error(f"상품 크롤링 중 오류: {e}")
            return {"status": "error", "message": str(e)}

    def run_review_collection(self, max_pages: int = 5, review_max_pages: int = 50) -> dict:
        """리뷰 데이터 수집 실행"""
        try:
            logger.info(f"무신사 리뷰 크롤링 시작 - 상품 {max_pages}페이지, 리뷰 {review_max_pages}페이지")

            # 크롤러 초기화
            crawler = MusinsaCrawler(
                section_id="231",
                size=40,
                category_code="104001",
                max_pages=max_pages,
                review_page_size=20,
                review_max_pages=review_max_pages
            )

            # 전체 데이터 수집
            result = crawler.crawling_musinsa_all()
            reviews = result.get('reviews', {})

            if not reviews:
                return {"status": "error", "message": "수집된 리뷰 데이터가 없습니다."}

            # 로컬 파일 저장
            csv_filename = f"musinsa_reviews_{self.timestamp}.csv"
            json_filename = f"musinsa_reviews_{self.timestamp}.json"

            crawler.save_reviews_to_csv(csv_filename)
            crawler.save_to_json(json_filename)

            # GCS 업로드
            gcs_upload_success = False
            if self.gcs_enabled:
                # 리뷰 데이터를 DataFrame으로 변환
                from musinsa_review_collector import MusinsaReviewCollector
                temp_collector = MusinsaReviewCollector(None, [])
                review_rows = temp_collector.flatten_reviews(reviews)
                df = pd.DataFrame(review_rows)

                csv_success = self._upload_to_gcs(df, csv_filename, "csv", "reviews")
                json_success = self._upload_to_gcs(reviews, json_filename, "json", "reviews")
                gcs_upload_success = csv_success and json_success

            total_reviews = sum(len(review_list) for review_list in reviews.values())
            logger.info(f"리뷰 크롤링 완료 - {total_reviews}개 리뷰 수집")

            return {
                "status": "success",
                "message": f"{total_reviews}개 리뷰 데이터 수집 완료",
                "data": {
                    "product_count": len(reviews),
                    "review_count": total_reviews,
                    "csv_file": csv_filename,
                    "json_file": json_filename,
                    "timestamp": self.timestamp,
                    "gcs_uploaded": gcs_upload_success,
                    "gcs_path": f"gs://{self.bucket_name}/raw-data/musinsa/reviews/" if self.gcs_enabled else None
                }
            }

        except Exception as e:
            logger.error(f"리뷰 크롤링 중 오류: {e}")
            return {"status": "error", "message": str(e)}

    def run_full_pipeline(self, product_pages: int = 5, review_pages: int = 50) -> dict:
        """전체 파이프라인 실행"""
        try:
            logger.info("무신사 전체 데이터 파이프라인 시작")

            # 크롤러 초기화
            crawler = MusinsaCrawler(
                section_id="231",
                size=40,
                category_code="104001",
                max_pages=product_pages,
                review_page_size=20,
                review_max_pages=review_pages
            )

            # 전체 데이터 수집
            result = crawler.crawling_musinsa_all()
            products = result.get('products', [])
            reviews = result.get('reviews', {})

            if not products and not reviews:
                return {"status": "error", "message": "수집된 데이터가 없습니다."}

            # 로컬 파일 저장
            products_csv = f"musinsa_products_{self.timestamp}.csv"
            reviews_csv = f"musinsa_reviews_{self.timestamp}.csv"
            all_json = f"musinsa_all_data_{self.timestamp}.json"

            crawler.save_products_to_csv(products_csv)
            crawler.save_reviews_to_csv(reviews_csv)
            crawler.save_to_json(all_json)

            # GCS 업로드
            gcs_upload_success = False
            if self.gcs_enabled:
                upload_results = []

                # 상품 데이터 업로드
                if products:
                    df_products = pd.DataFrame(products)
                    upload_results.append(self._upload_to_gcs(df_products, products_csv, "csv", "products"))

                # 리뷰 데이터 업로드
                if reviews:
                    from musinsa_review_collector import MusinsaReviewCollector
                    temp_collector = MusinsaReviewCollector(None, [])
                    review_rows = temp_collector.flatten_reviews(reviews)
                    df_reviews = pd.DataFrame(review_rows)
                    upload_results.append(self._upload_to_gcs(df_reviews, reviews_csv, "csv", "reviews"))

                # 전체 데이터 JSON 업로드
                upload_results.append(self._upload_to_gcs(result, all_json, "json", "all"))

                gcs_upload_success = all(upload_results)

            total_reviews = sum(len(review_list) for review_list in reviews.values())
            logger.info(f"전체 파이프라인 완료 - 상품 {len(products)}개, 리뷰 {total_reviews}개")

            return {
                "status": "success",
                "message": "전체 파이프라인 실행 완료",
                "data": {
                    "product_count": len(products),
                    "review_count": total_reviews,
                    "files": {
                        "products_csv": products_csv,
                        "reviews_csv": reviews_csv,
                        "all_json": all_json
                    },
                    "timestamp": self.timestamp,
                    "gcs_uploaded": gcs_upload_success,
                    "gcs_path": f"gs://{self.bucket_name}/raw-data/musinsa/" if self.gcs_enabled else None
                }
            }

        except Exception as e:
            logger.error(f"전체 파이프라인 실행 중 오류: {e}")
            return {"status": "error", "message": str(e)}


# Flask 라우트 정의 (기존과 동일)
@app.route('/', methods=['GET'])
def health_check():
    """헬스 체크 엔드포인트"""
    return jsonify({
        "status": "healthy",
        "service": "musinsa-data-crawler",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "gcs_enabled": bool(os.environ.get("GCS_BUCKET_NAME"))
    })


@app.route('/gcs/files', methods=['GET'])
def list_gcs_files_endpoint():
    """GCS 파일 목록 조회"""
    bucket_name = os.environ.get("GCS_BUCKET_NAME")
    project_id = os.environ.get("GCS_PROJECT_ID")
    prefix = request.args.get('prefix', 'raw-data/musinsa/')

    if not bucket_name:
        return jsonify({"error": "GCS 버킷이 설정되지 않았습니다."}), 400

    try:
        files = list_gcs_files(bucket_name, prefix, project_id)
        return jsonify({
            "bucket": bucket_name,
            "prefix": prefix,
            "files": files,
            "count": len(files)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# 기존 크롤링 엔드포인트들 (동일)
@app.route('/crawl/products', methods=['POST'])
def crawl_products():
    """상품 데이터 크롤링 엔드포인트"""
    try:
        data = request.get_json() or {}
        max_pages = data.get('max_pages', 5)
        size = data.get('size', 40)

        logger.info(f"상품 크롤링 요청 - 페이지: {max_pages}, 크기: {size}")

        pipeline = MusinsaDataPipeline()
        result = pipeline.run_product_collection(max_pages, size)

        status_code = 200 if result["status"] == "success" else 500
        return jsonify(result), status_code

    except Exception as e:
        logger.error(f"상품 크롤링 API 오류: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/crawl/reviews', methods=['POST'])
def crawl_reviews():
    """리뷰 데이터 크롤링 엔드포인트"""
    try:
        data = request.get_json() or {}
        max_pages = data.get('max_pages', 5)
        review_max_pages = data.get('review_max_pages', 50)

        logger.info(f"리뷰 크롤링 요청 - 상품 페이지: {max_pages}, 리뷰 페이지: {review_max_pages}")

        pipeline = MusinsaDataPipeline()
        result = pipeline.run_review_collection(max_pages, review_max_pages)

        status_code = 200 if result["status"] == "success" else 500
        return jsonify(result), status_code

    except Exception as e:
        logger.error(f"리뷰 크롤링 API 오류: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/crawl/full', methods=['POST'])
def crawl_full():
    """전체 파이프라인 실행 엔드포인트"""
    try:
        data = request.get_json() or {}
        product_pages = data.get('product_pages', 5)
        review_pages = data.get('review_pages', 50)

        logger.info(f"전체 크롤링 요청 - 상품 페이지: {product_pages}, 리뷰 페이지: {review_pages}")

        pipeline = MusinsaDataPipeline()
        result = pipeline.run_full_pipeline(product_pages, review_pages)

        status_code = 200 if result["status"] == "success" else 500
        return jsonify(result), status_code

    except Exception as e:
        logger.error(f"전체 파이프라인 API 오류: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/status', methods=['GET'])
def get_status():
    """서비스 상태 조회"""
    return jsonify({
        "service": "musinsa-data-crawler",
        "version": "1.0.0",
        "environment": os.environ.get("ENV", "local"),
        "timestamp": datetime.now().isoformat(),
        "gcs": {
            "enabled": bool(os.environ.get("GCS_BUCKET_NAME")),
            "bucket": os.environ.get("GCS_BUCKET_NAME"),
            "project_id": os.environ.get("GCS_PROJECT_ID")
        },
        "endpoints": [
            "GET /",
            "GET /status",
            "GET /gcs/status",
            "GET /gcs/files",
            "POST /crawl/products",
            "POST /crawl/reviews",
            "POST /crawl/full"
        ]
    })


def main():
    """메인 함수 - 환경변수에 따른 실행 모드 결정"""
    env = os.environ.get("ENV", "local").lower()

    if env == "local":
        # 로컬 개발 환경: 직접 크롤링 실행
        logger.info("로컬 환경에서 크롤링 직접 실행")

        pipeline = MusinsaDataPipeline()

        # 환경변수로 실행 모드 결정
        mode = os.environ.get("CRAWL_MODE", "full").lower()
        max_pages = int(os.environ.get("MAX_PAGES", "5"))
        review_pages = int(os.environ.get("REVIEW_PAGES", "50"))

        if mode == "products":
            result = pipeline.run_product_collection(max_pages)
        elif mode == "reviews":
            result = pipeline.run_review_collection(max_pages, review_pages)
        else:  # full
            result = pipeline.run_full_pipeline(max_pages, review_pages)

        logger.info(f"크롤링 결과: {result}")

    else:
        # 프로덕션 환경: Flask 서버 실행
        logger.info("프로덕션 환경에서 Flask 서버 시작")
        port = int(os.environ.get("PORT", 8080))
        host = os.environ.get("HOST", "0.0.0.0")
        debug = os.environ.get("DEBUG", "false").lower() == "true"

        logger.info(f"Flask 서버 시작 - {host}:{port}")
        app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()
