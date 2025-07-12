#!/usr/bin/env python3

"""
무신사 데이터 수집 Cloud Run Job 애플리케이션 (GCS 연동 포함)
Docker 환경에서 실행되는 크롤링 서비스
"""

import os
import logging
from datetime import datetime
from dotenv import load_dotenv
import pandas as pd

# 로컬 환경일 경우 dotenv 로드
if os.environ.get("ENV", "").lower() != "production":
    load_dotenv()

from musinsa_crawler import MusinsaCrawler, CATEGORY_MAPPING
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


class MusinsaDataPipeline:
    """무신사 데이터 수집 파이프라인 (카테고리별 GCS 연동 포함)"""

    def __init__(self):
        self.bucket_name = os.environ.get("GCS_BUCKET_NAME")
        self.project_id = os.environ.get("GCS_PROJECT_ID")
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.date_str = datetime.now().strftime("%Y%m%d")
        self.gcs_enabled = bool(self.bucket_name and self.bucket_name != "your-bucket-name")

        if self.gcs_enabled:
            logger.info(f"GCS 업로드 활성화: {self.bucket_name}")
        else:
            logger.info("GCS 업로드 비활성화 - 로컬 저장만 수행")

    def get_category_folder_name(self, category_code: str) -> str:
        """카테고리 코드를 폴더명으로 변환 (슬래시를 &로 변경)"""
        category_name = CATEGORY_MAPPING.get(category_code, f"category_{category_code}")
        return category_name.replace("/", "&")

    def _upload_to_gcs_with_category(self, data: any, filename: str, file_type: str,
                                     category_code: str, data_type: str) -> bool:
        """카테고리별 GCS 업로드 헬퍼 메서드"""
        if not self.gcs_enabled:
            return False
        try:
            category_folder = self.get_category_folder_name(category_code)
            # 새로운 경로 구조: musinsa/{data_type}/{category_folder}/{date}/
            gcs_path = f"raw-data/musinsa/{data_type}/{category_folder}/{self.date_str}/{filename}"

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

    def _upload_to_gcs(self, data: any, filename: str, file_type: str, folder: str = "",
                       category_code: str = None) -> bool:
        """GCS 업로드 헬퍼 메서드 (카테고리별 폴더 구조 지원)"""
        if not self.gcs_enabled:
            return False
        try:
            if category_code:
                # 카테고리별 폴더 구조 생성
                category_folder = self.get_category_folder_name(category_code)
                gcs_path = f"raw-data/musinsa/{folder}/{category_folder}/{self.date_str}/{filename}"
            elif folder:
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

    def run_all_categories_collection(self, max_pages: int = 8, review_max_pages: int = 25) -> dict:
        """모든 카테고리 데이터 수집 실행"""
        try:
            logger.info(f"무신사 전체 카테고리 크롤링 시작 - 최대 {max_pages}페이지 (카테고리당 300개 상품)")
            # 크롤러 초기화 - 상품 300개, 리뷰 500개 설정
            crawler = MusinsaCrawler(
                section_id="231",
                size=40,  # 페이지당 40개
                max_pages=max_pages,  # 8페이지 = 320개 (300개 이상 확보)
                review_page_size=20,  # 페이지당 20개 리뷰
                review_max_pages=review_max_pages  # 25페이지 = 500개 리뷰
            )

            # 전체 카테고리 데이터 수집
            all_category_data = crawler.crawling_all_categories()

            if not all_category_data:
                return {"status": "error", "message": "수집된 카테고리 데이터가 없습니다."}

            # 카테고리별 GCS 업로드
            upload_results = []
            category_summary = {}

            for category_code, category_data in all_category_data.items():
                category_name = category_data['category_name']
                category_folder = self.get_category_folder_name(category_code)
                products = category_data['products']
                reviews = category_data['reviews']

                # 새로운 파일명 생성 규칙
                products_csv = f"product_{category_folder}_{category_code}_{self.timestamp}.csv"
                reviews_csv = f"review_{category_folder}_{category_code}_{self.timestamp}.csv"

                category_upload_success = True

                if self.gcs_enabled:
                    # 상품 데이터 업로드 (products 폴더)
                    if products:
                        df_products = pd.DataFrame(products)
                        products_success = self._upload_to_gcs_with_category(
                            df_products, products_csv, "csv", category_code, "products"
                        )
                        category_upload_success = category_upload_success and products_success

                    # 리뷰 데이터 업로드 (reviews 폴더)
                    if reviews:
                        from musinsa_review_collector import MusinsaReviewCollector
                        temp_collector = MusinsaReviewCollector(None, [])
                        review_rows = temp_collector.flatten_reviews(reviews)
                        df_reviews = pd.DataFrame(review_rows)
                        reviews_success = self._upload_to_gcs_with_category(
                            df_reviews, reviews_csv, "csv", category_code, "reviews"
                        )
                        category_upload_success = category_upload_success and reviews_success

                upload_results.append(category_upload_success)

                # 카테고리 요약 정보
                category_summary[category_code] = {
                    "category_name": category_name,
                    "category_folder": category_folder,
                    "product_count": len(products),
                    "review_count": sum(len(review_list) for review_list in reviews.values()),
                    "gcs_uploaded": category_upload_success,
                    "files": {
                        "products": products_csv,
                        "reviews": reviews_csv
                    }
                }

            total_products = sum(info["product_count"] for info in category_summary.values())
            total_reviews = sum(info["review_count"] for info in category_summary.values())

            logger.info(f"전체 카테고리 크롤링 완료 - {len(all_category_data)}개 카테고리, 상품 {total_products}개, 리뷰 {total_reviews}개")

            return {
                "status": "success",
                "message": f"전체 카테고리 데이터 수집 완료",
                "data": {
                    "category_count": len(all_category_data),
                    "total_products": total_products,
                    "total_reviews": total_reviews,
                    "categories": category_summary,
                    "timestamp": self.timestamp,
                    "date": self.date_str,
                    "gcs_uploaded": all(upload_results),
                    "folder_structure": {
                        "products": f"gs://{self.bucket_name}/raw-data/musinsa/products/{{category}}/{self.date_str}/",
                        "reviews": f"gs://{self.bucket_name}/raw-data/musinsa/reviews/{{category}}/{self.date_str}/"
                    } if self.gcs_enabled else None
                }
            }

        except Exception as e:
            logger.error(f"전체 카테고리 크롤링 중 오류: {e}")
            return {"status": "error", "message": str(e)}

    def run_product_collection(self, max_pages: int = 8, size: int = 40) -> dict:
        """상품 데이터 수집 실행"""
        try:
            logger.info(f"무신사 상품 크롤링 시작 - 최대 {max_pages}페이지 (카테고리당 300개 상품)")
            # 크롤러 초기화
            crawler = MusinsaCrawler(
                section_id="231",
                size=size,
                max_pages=max_pages,
                review_page_size=20,
                review_max_pages=1
            )

            # 상품 데이터 수집
            result = crawler.crawling_all_categories()

            # GCS 업로드 (카테고리별)
            gcs_upload_success = True
            upload_results = []

            if self.gcs_enabled:
                for category_code, category_data in result.items():
                    products = category_data.get('products', [])
                    if products:
                        category_folder = self.get_category_folder_name(category_code)
                        csv_filename = f"product_{category_folder}_{category_code}_{self.timestamp}.csv"
                        json_filename = f"product_{category_folder}_{category_code}_{self.timestamp}.json"

                        df = pd.DataFrame(products)
                        csv_success = self._upload_to_gcs(df, csv_filename, "csv", "products", category_code)
                        json_success = self._upload_to_gcs(products, json_filename, "json", "products", category_code)
                        upload_results.append(csv_success and json_success)

            gcs_upload_success = all(upload_results)

            # 전체 상품 수 계산
            all_products = []
            for category_data in result.values():
                all_products.extend(category_data.get('products', []))

            logger.info(f"상품 크롤링 완료 - {len(all_products)}개 상품 수집")

            return {
                "status": "success",
                "message": f"{len(all_products)}개 상품 데이터 수집 완료",
                "data": {
                    "product_count": len(all_products),
                    "category_count": len(result),
                    "timestamp": self.timestamp,
                    "gcs_uploaded": gcs_upload_success,
                    "folder_structure": f"gs://{self.bucket_name}/raw-data/musinsa/products/{{category}}/{self.date_str}/" if self.gcs_enabled else None
                }
            }

        except Exception as e:
            logger.error(f"상품 크롤링 중 오류: {e}")
            return {"status": "error", "message": str(e)}

    def run_review_collection(self, max_pages: int = 8, review_max_pages: int = 25) -> dict:
        """리뷰 데이터 수집 실행"""
        try:
            logger.info(f"무신사 리뷰 크롤링 시작 - 상품 {max_pages}페이지, 리뷰 {review_max_pages}페이지 (상품당 500개 리뷰)")
            # 크롤러 초기화
            crawler = MusinsaCrawler(
                section_id="231",
                size=40,
                max_pages=max_pages,
                review_page_size=20,
                review_max_pages=review_max_pages
            )

            # 전체 데이터 수집
            result = crawler.crawling_all_categories()

            # GCS 업로드 (카테고리별)
            gcs_upload_success = True
            upload_results = []

            if self.gcs_enabled:
                for category_code, category_data in result.items():
                    reviews = category_data.get('reviews', {})
                    if reviews:
                        category_folder = self.get_category_folder_name(category_code)
                        csv_filename = f"review_{category_folder}_{category_code}_{self.timestamp}.csv"
                        json_filename = f"review_{category_folder}_{category_code}_{self.timestamp}.json"

                        # 리뷰 데이터를 DataFrame으로 변환
                        from musinsa_review_collector import MusinsaReviewCollector
                        temp_collector = MusinsaReviewCollector(None, [])
                        review_rows = temp_collector.flatten_reviews(reviews)
                        df = pd.DataFrame(review_rows)

                        csv_success = self._upload_to_gcs(df, csv_filename, "csv", "reviews", category_code)
                        json_success = self._upload_to_gcs(reviews, json_filename, "json", "reviews", category_code)
                        upload_results.append(csv_success and json_success)

            gcs_upload_success = all(upload_results)

            # 전체 리뷰 수 계산
            all_reviews = {}
            for category_data in result.values():
                all_reviews.update(category_data.get('reviews', {}))
            total_reviews = sum(len(review_list) for review_list in all_reviews.values())

            logger.info(f"리뷰 크롤링 완료 - {total_reviews}개 리뷰 수집")

            return {
                "status": "success",
                "message": f"{total_reviews}개 리뷰 데이터 수집 완료",
                "data": {
                    "product_count": len(all_reviews),
                    "review_count": total_reviews,
                    "category_count": len(result),
                    "timestamp": self.timestamp,
                    "gcs_uploaded": gcs_upload_success,
                    "folder_structure": f"gs://{self.bucket_name}/raw-data/musinsa/reviews/{{category}}/{self.date_str}/" if self.gcs_enabled else None
                }
            }

        except Exception as e:
            logger.error(f"리뷰 크롤링 중 오류: {e}")
            return {"status": "error", "message": str(e)}

    def run_full_pipeline(self, product_pages: int = 8, review_pages: int = 25) -> dict:
        """전체 파이프라인 실행 (products, reviews 폴더에만 업로드)"""
        try:
            logger.info("무신사 전체 데이터 파이프라인 시작 - 카테고리당 300개 상품, 상품당 500개 리뷰")
            # 크롤러 초기화
            crawler = MusinsaCrawler(
                section_id="231",
                size=40,
                max_pages=product_pages,
                review_page_size=20,
                review_max_pages=review_pages
            )

            # 전체 데이터 수집
            result = crawler.crawling_all_categories()

            # GCS 업로드 (카테고리별)
            gcs_upload_success = True
            upload_results = []

            if self.gcs_enabled:
                for category_code, category_data in result.items():
                    category_folder = self.get_category_folder_name(category_code)

                    # 상품 데이터 업로드
                    products = category_data.get('products', [])
                    if products:
                        products_csv = f"product_{category_folder}_{category_code}_{self.timestamp}.csv"
                        df_products = pd.DataFrame(products)
                        upload_results.append(
                            self._upload_to_gcs(df_products, products_csv, "csv", "products", category_code))

                    # 리뷰 데이터 업로드
                    reviews = category_data.get('reviews', {})
                    if reviews:
                        reviews_csv = f"review_{category_folder}_{category_code}_{self.timestamp}.csv"
                        from musinsa_review_collector import MusinsaReviewCollector
                        temp_collector = MusinsaReviewCollector(None, [])
                        review_rows = temp_collector.flatten_reviews(reviews)
                        df_reviews = pd.DataFrame(review_rows)
                        upload_results.append(
                            self._upload_to_gcs(df_reviews, reviews_csv, "csv", "reviews", category_code))

            gcs_upload_success = all(upload_results)

            # 전체 통계 계산
            all_products = []
            all_reviews = {}
            for category_data in result.values():
                all_products.extend(category_data.get('products', []))
                all_reviews.update(category_data.get('reviews', {}))
            total_reviews = sum(len(review_list) for review_list in all_reviews.values())

            logger.info(f"전체 파이프라인 완료 - 상품 {len(all_products)}개, 리뷰 {total_reviews}개")

            return {
                "status": "success",
                "message": "전체 파이프라인 실행 완료",
                "data": {
                    "product_count": len(all_products),
                    "review_count": total_reviews,
                    "category_count": len(result),
                    "timestamp": self.timestamp,
                    "gcs_uploaded": gcs_upload_success,
                    "folder_structure": {
                        "products": f"gs://{self.bucket_name}/raw-data/musinsa/products/{{category}}/{self.date_str}/",
                        "reviews": f"gs://{self.bucket_name}/raw-data/musinsa/reviews/{{category}}/{self.date_str}/"
                    } if self.gcs_enabled else None
                }
            }

        except Exception as e:
            logger.error(f"전체 파이프라인 실행 중 오류: {e}")
            return {"status": "error", "message": str(e)}


def main():
    """메인 함수 - 환경변수에 따른 실행 모드 결정"""
    logger.info("무신사 데이터 크롤링 서비스 시작")

    pipeline = MusinsaDataPipeline()

    # 환경변수로 실행 모드 결정 (기본값을 새로운 설정으로 변경)
    mode = os.environ.get("CRAWL_MODE", "all-categories").lower()
    max_pages = int(os.environ.get("MAX_PAGES", "8"))  # 8페이지 = 320개 상품
    review_pages = int(os.environ.get("REVIEW_PAGES", "25"))  # 25페이지 = 500개 리뷰

    logger.info(f"실행 모드: {mode}, 최대 페이지: {max_pages} (카테고리당 ~300개 상품), 리뷰 페이지: {review_pages} (상품당 ~500개 리뷰)")

    if mode == "products":
        result = pipeline.run_product_collection(max_pages)
    elif mode == "reviews":
        result = pipeline.run_review_collection(max_pages, review_pages)
    elif mode == "full":
        result = pipeline.run_full_pipeline(max_pages, review_pages)
    else:  # all-categories
        result = pipeline.run_all_categories_collection(max_pages, review_pages)

    logger.info(f"크롤링 결과: {result}")

    # 결과에 따라 exit code 설정
    if result.get("status") == "success":
        logger.info("크롤링 작업이 성공적으로 완료되었습니다.")
        exit(0)
    else:
        logger.error("크롤링 작업이 실패했습니다.")
        exit(1)


if __name__ == "__main__":
    main()
