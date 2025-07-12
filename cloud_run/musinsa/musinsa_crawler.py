#!/usr/bin/env python3

"""
무신사 크롤러 메인 (카테고리별 수집)
"""

import requests
import csv
import json
import logging
import pandas as pd
from datetime import datetime
from typing import Dict, List
from fake_useragent import UserAgent
from musinsa_ranking_collector import MusinsaRankingCollector
from musinsa_review_collector import MusinsaReviewCollector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 카테고리 매핑
CATEGORY_MAPPING = {
    "104000": "전체",
    "104001": "스킨케어",
    "104013": "마스크팩",
    "104014": "베이스메이크업",
    "104015": "립메이크업",
    "104016": "아이메이크업",
    "104017": "네일",
    "104005": "프레그런스",
    "104002": "선케어",
    "104003": "클렌징/필링",
    "104006": "헤어케어",
    "104007": "바디케어",
    "104009": "쉐이빙/제모",
    "104010": "뷰티 디바이스/소품",
    "104011": "미용소품",
    "104012": "헬스/푸드"
}


class MusinsaCrawler:
    def __init__(self, section_id: str = "231", size: int = 40,
                 max_pages: int = 5, review_page_size: int = 20,
                 review_max_pages: int = 50):
        self.session = self._setup_session()
        self.section_id = section_id
        self.size = size
        self.max_pages = max_pages
        self.review_page_size = review_page_size
        self.review_max_pages = review_max_pages

        # 날짜 포맷 설정
        self.date_str = datetime.now().strftime("%Y%m%d")
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 카테고리별 수집된 데이터 저장
        self.all_category_data = {}

    def _setup_session(self) -> requests.Session:
        """세션 설정"""
        ua = UserAgent()
        headers = {
            'User-Agent': ua.random,
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://www.musinsa.com/main/beauty/ranking',
            'Origin': 'https://www.musinsa.com',
        }

        session = requests.Session()
        session.headers.update(headers)
        logger.info("세션 설정 완료")
        return session

    def get_category_folder_name(self, category_code: str) -> str:
        """카테고리 코드를 폴더명으로 변환 (슬래시를 &로 변경)"""
        category_name = CATEGORY_MAPPING.get(category_code, f"category_{category_code}")
        # 슬래시를 앰퍼샌드로 변경
        return category_name.replace("/", "&")

    def crawl_single_category(self, category_code: str) -> Dict:
        """단일 카테고리 크롤링"""
        logger.info(f"카테고리 {category_code} ({CATEGORY_MAPPING.get(category_code, 'Unknown')}) 크롤링 시작")
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 1. 랭킹 데이터 수집
        ranking_collector = MusinsaRankingCollector(
            session=self.session,
            section_id=self.section_id,
            size=self.size,
            category_code=category_code,
            max_pages=self.max_pages,
            created_at=created_at
        )

        # 페이지별로 상품 수집
        all_products = []
        for page in range(1, self.max_pages + 1):
            data = ranking_collector.fetch_products_page(page)
            if not data:
                logger.warning(f"카테고리 {category_code} 페이지 {page}에서 데이터를 가져올 수 없습니다.")
                break

            products = ranking_collector.parse_api_response(data, page)
            if not products:
                logger.info(f"카테고리 {category_code} 페이지 {page}에서 더 이상 상품이 없습니다.")
                break

            all_products.extend(products)
            logger.info(f"카테고리 {category_code} 페이지 {page}: {len(products)}개 상품 수집")

        logger.info(f"카테고리 {category_code} 랭킹 수집 완료 - 총 {len(all_products)}개 상품")

        # 2. product_ids 추출
        product_ids = ranking_collector.extract_product_ids(all_products)
        logger.info(f"카테고리 {category_code} 추출된 product_ids: {len(product_ids)}개")

        # 3. 리뷰 데이터 수집
        reviews = {}
        if product_ids:
            review_collector = MusinsaReviewCollector(
                session=self.session,
                product_ids=product_ids,
                review_page_size=self.review_page_size,
                review_max_pages=self.review_max_pages
            )

            reviews = review_collector.collect_all_reviews()
            logger.info(f"카테고리 {category_code} 리뷰 수집 완료 - {len(reviews)}개 상품의 리뷰")

        return {
            'category_code': category_code,
            'category_name': CATEGORY_MAPPING.get(category_code, 'Unknown'),
            'products': all_products,
            'reviews': reviews
        }

    def crawling_all_categories(self) -> Dict:
        """모든 카테고리 크롤링 실행"""
        logger.info("무신사 뷰티 전체 카테고리 크롤링 시작...")

        for category_code in CATEGORY_MAPPING.keys():
            try:
                category_data = self.crawl_single_category(category_code)
                self.all_category_data[category_code] = category_data

                # 카테고리별 파일 저장
                self.save_category_data(category_code, category_data)

            except Exception as e:
                logger.error(f"카테고리 {category_code} 크롤링 중 오류: {e}")
                continue

        logger.info(f"전체 카테고리 크롤링 완료 - {len(self.all_category_data)}개 카테고리")
        return self.all_category_data

    def save_category_data(self, category_code: str, category_data: Dict):
        """카테고리별 데이터 저장"""
        category_folder = self.get_category_folder_name(category_code)
        category_name = category_data['category_name']

        # 새로운 파일명 생성 규칙
        products_csv = f"product_{category_folder}_{category_code}_{self.timestamp}.csv"
        reviews_csv = f"review_{category_folder}_{category_code}_{self.timestamp}.csv"
        all_json = f"all_{category_folder}_{category_code}_{self.timestamp}.json"

        # 상품 데이터 CSV 저장
        if category_data['products']:
            self.save_products_to_csv(category_data['products'], products_csv)

        # 리뷰 데이터 CSV 저장
        if category_data['reviews']:
            self.save_reviews_to_csv(category_data['reviews'], reviews_csv)

        # 전체 데이터 JSON 저장
        self.save_category_to_json(category_data, all_json)

        logger.info(f"카테고리 {category_code} ({category_name}) 데이터 저장 완료")

    def save_products_to_csv(self, products: List[Dict], filename: str):
        """상품 데이터를 CSV로 저장"""
        if not products:
            logger.warning("저장할 상품 데이터가 없습니다.")
            return

        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['rank', 'name', 'brand', 'price', 'original_price',
                          'discount_rate', 'rating', 'review_count', 'likes',
                          'image_url', 'product_url', 'product_id',
                          'number_of_views', 'sales']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for product in products:
                writer.writerow(product)

        logger.info(f"상품 데이터가 {filename}에 저장되었습니다.")

    def save_reviews_to_csv(self, reviews: Dict, filename: str):
        """리뷰 데이터를 CSV로 저장"""
        if not reviews:
            logger.warning("저장할 리뷰 데이터가 없습니다.")
            return

        review_collector = MusinsaReviewCollector(self.session, [])
        review_rows = review_collector.flatten_reviews(reviews)
        df = pd.DataFrame(review_rows)
        df.to_csv(filename, index=False, encoding='utf-8-sig')

        logger.info(f"리뷰 데이터가 {filename}에 저장되었습니다.")

    def save_category_to_json(self, category_data: Dict, filename: str):
        """카테고리 데이터를 JSON으로 저장"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(category_data, f, ensure_ascii=False, indent=2)

        logger.info(f"카테고리 데이터가 {filename}에 저장되었습니다.")

    def print_summary(self):
        """크롤링 결과 요약 출력"""
        print(f"\n=== 무신사 뷰티 전체 카테고리 크롤링 결과 ===")

        total_products = 0
        total_reviews = 0

        for category_code, data in self.all_category_data.items():
            category_name = data['category_name']
            product_count = len(data['products'])
            review_count = sum(len(reviews) for reviews in data['reviews'].values())

            print(f"카테고리 {category_code} ({category_name}): 상품 {product_count}개, 리뷰 {review_count}개")

            total_products += product_count
            total_reviews += review_count

        print(f"\n총 상품 수: {total_products}개")
        print(f"총 리뷰 수: {total_reviews}개")
        print(f"처리된 카테고리 수: {len(self.all_category_data)}개")


def main():
    """메인 함수"""
    crawler = MusinsaCrawler(
        section_id="231",
        size=40,
        max_pages=5,
        review_page_size=20,
        review_max_pages=50
    )

    try:
        # 전체 카테고리 크롤링 실행
        result = crawler.crawling_all_categories()

        # 결과 출력
        crawler.print_summary()

    except Exception as e:
        logger.error(f"메인 실행 중 오류: {e}")


if __name__ == "__main__":
    main()
