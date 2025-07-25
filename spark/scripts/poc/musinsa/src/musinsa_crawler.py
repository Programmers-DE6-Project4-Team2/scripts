#!/usr/bin/env python3
"""
무신사 크롤러 메인
"""

import requests
import csv
import json
import logging
import pandas as pd
from typing import Dict
from fake_useragent import UserAgent

from musinsa_ranking_collector import MusinsaRankingCollector
from musinsa_review_collector import MusinsaReviewCollector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MusinsaCrawler:
    def __init__(self, section_id: str = "231", size: int = 40,
                 category_code: str = "104001", max_pages: int = 5,
                 review_page_size: int = 20, review_max_pages: int = 50):
        self.session = self._setup_session()
        self.section_id = section_id
        self.size = size
        self.category_code = category_code
        self.max_pages = max_pages
        self.review_page_size = review_page_size
        self.review_max_pages = review_max_pages

        # 수집된 데이터 저장
        self.products = []
        self.reviews = {}

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

    def crawling_musinsa_all(self) -> Dict:
        """무신사 전체 크롤링 실행"""
        logger.info("무신사 뷰티 랭킹 크롤링 시작...")

        # 1. 랭킹 데이터 수집
        ranking_collector = MusinsaRankingCollector(
            session=self.session,
            section_id=self.section_id,
            size=self.size,
            category_code=self.category_code,
            max_pages=self.max_pages
        )

        # 페이지별로 상품 수집
        all_products = []
        for page in range(1, self.max_pages + 1):
            data = ranking_collector.fetch_products_page(page)
            if not data:
                logger.warning(f"페이지 {page}에서 데이터를 가져올 수 없습니다.")
                break

            products = ranking_collector.parse_api_response(data, page)
            if not products:
                logger.info(f"페이지 {page}에서 더 이상 상품이 없습니다.")
                break

            all_products.extend(products)
            logger.info(f"페이지 {page}: {len(products)}개 상품 수집")

        self.products = all_products
        logger.info(f"랭킹 수집 완료 - 총 {len(self.products)}개 상품")

        # 2. product_ids 추출
        product_ids = ranking_collector.extract_product_ids(self.products)
        logger.info(f"추출된 product_ids: {len(product_ids)}개")

        # 3. 리뷰 데이터 수집
        if product_ids:
            review_collector = MusinsaReviewCollector(
                session=self.session,
                product_ids=product_ids,
                review_page_size=self.review_page_size,
                review_max_pages=self.review_max_pages
            )

            self.reviews = review_collector.collect_all_reviews()
            logger.info(f"리뷰 수집 완료 - {len(self.reviews)}개 상품의 리뷰")

        return {
            'products': self.products,
            'reviews': self.reviews
        }

    def save_products_to_csv(self, filename: str = 'musinsa_beauty_products.csv'):
        """상품 데이터를 CSV로 저장"""
        if not self.products:
            logger.warning("저장할 상품 데이터가 없습니다.")
            return

        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['rank', 'name', 'brand', 'price', 'original_price',
                          'discount_rate', 'rating', 'review_count', 'likes',
                          'image_url', 'product_url', 'product_id']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for product in self.products:
                writer.writerow(product)
        logger.info(f"상품 데이터가 {filename}에 저장되었습니다.")

    def save_reviews_to_csv(self, filename: str = 'musinsa_beauty_reviews.csv'):
        """리뷰 데이터를 CSV로 저장"""
        if not self.reviews:
            logger.warning("저장할 리뷰 데이터가 없습니다.")
            return

        review_collector = MusinsaReviewCollector(self.session, [])
        review_rows = review_collector.flatten_reviews(self.reviews)
        df = pd.DataFrame(review_rows)
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        logger.info(f"리뷰 데이터가 {filename}에 저장되었습니다.")

    def save_to_json(self, filename: str = 'musinsa_beauty_all_data.json'):
        """전체 데이터를 JSON으로 저장"""
        data = {
            'products': self.products,
            'reviews': self.reviews
        }
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"전체 데이터가 {filename}에 저장되었습니다.")

    def print_summary(self):
        """크롤링 결과 요약 출력"""
        print(f"\n=== 무신사 뷰티 크롤링 결과 ===")
        print(f"총 상품 수: {len(self.products)}개")
        print(f"리뷰 수집 상품 수: {len(self.reviews)}개")

        total_reviews = sum(len(reviews) for reviews in self.reviews.values())
        print(f"총 리뷰 수: {total_reviews}개")


def main():
    """메인 함수"""
    crawler = MusinsaCrawler(
        section_id="231",
        size=3, #40,
        category_code="104001",
        max_pages=1, #5,
        review_page_size=3, #20,
        review_max_pages=1 #50
    )

    try:
        # 전체 크롤링 실행
        result = crawler.crawling_musinsa_all()

        # 결과 출력
        crawler.print_summary()

        # 파일 저장
        crawler.save_products_to_csv()
        crawler.save_reviews_to_csv()
        crawler.save_to_json()

    except Exception as e:
        logger.error(f"메인 실행 중 오류: {e}")


if __name__ == "__main__":
    main()
