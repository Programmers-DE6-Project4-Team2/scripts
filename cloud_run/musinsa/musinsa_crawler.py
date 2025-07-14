#!/usr/bin/env python3

"""
무신사 크롤러 메인 (카테고리별 수집)
"""

import requests
import logging
from datetime import datetime, timezone
from typing import Dict, List
from fake_useragent import UserAgent

from utils import CATEGORY_MAPPING
from musinsa_ranking_collector import MusinsaRankingCollector
from musinsa_review_collector import MusinsaReviewCollector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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

    def crawl_single_category_ranking(self, category_code: str) -> Dict:
        """단일 카테고리 랭킹만 크롤링 (Airflow Dynamic Task Mapping용)"""
        logger.info(f"카테고리 {category_code} 랭킹 크롤링 시작")

        try:
            scraped_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

            ranking_collector = MusinsaRankingCollector(
                session=self.session,
                section_id=self.section_id,
                size=self.size,
                category_code=category_code,
                max_pages=self.max_pages,
                scraped_at=scraped_at
            )

            all_products = []
            for page in range(1, self.max_pages + 1):
                data = ranking_collector.fetch_products_page(page)
                if not data:
                    break
                products = ranking_collector.parse_api_response(data, page)
                if not products:
                    break
                all_products.extend(products)

            # product_ids 추출 (Airflow XCom용)
            product_ids = [p['product_id'] for p in all_products if p.get('product_id')]

            return {
                'status': 'success',
                'category_code': category_code,
                'category_name': CATEGORY_MAPPING.get(category_code, 'Unknown'),
                'products': all_products,
                'product_ids': product_ids,  # Airflow 전달용
                'product_count': len(all_products),
                'scraped_at': scraped_at
            }

        except Exception as e:
            logger.error(f"카테고리 {category_code} 랭킹 크롤링 실패: {e}")
            return {
                'status': 'error',
                'category_code': category_code,
                'products': [],
                'product_ids': [],
                'product_count': 0,
                'error_message': str(e)
            }

    def crawl_review_batch(self, product_ids: List[str], batch_info: Dict = None) -> Dict:
        """상품 ID 배치별 리뷰 크롤링 (Airflow 배치 처리용)"""
        batch_index = batch_info.get('batch_index', 0) if batch_info else 0
        category_code = batch_info.get('category_code', 'unknown') if batch_info else 'unknown'

        logger.info(f"배치 {batch_index} 리뷰 크롤링 시작 - {len(product_ids)}개 상품")

        try:
            if not product_ids:
                return {
                    'status': 'success',
                    'batch_index': batch_index,
                    'category_code': category_code,
                    'category_name': CATEGORY_MAPPING.get(category_code, 'Unknown'),
                    'reviews': {},
                    'review_count': 0
                }

            review_collector = MusinsaReviewCollector(
                session=self.session,
                product_ids=product_ids,
                review_page_size=self.review_page_size,
                review_max_pages=self.review_max_pages
            )

            reviews = review_collector.collect_all_reviews()
            total_reviews = sum(len(review_list) for review_list in reviews.values())

            logger.info(f"배치 {batch_index} 리뷰 크롤링 완료 - {total_reviews}개 리뷰")

            return {
                'status': 'success',
                'batch_index': batch_index,
                'category_code': category_code,
                'category_name': CATEGORY_MAPPING.get(category_code, 'Unknown'),
                'reviews': reviews,
                'review_count': total_reviews,
                'product_count': len(product_ids)
            }

        except Exception as e:
            logger.error(f"배치 {batch_index} 리뷰 크롤링 실패: {e}")
            return {
                'status': 'error',
                'batch_index': batch_index,
                'category_code': category_code,
                'reviews': {},
                'review_count': 0,
                'error_message': str(e)
            }

    def get_product_ids_from_category(self, category_code: str) -> List[str]:
        """카테고리에서 product_ids만 추출 (중간 데이터 전달용)"""
        logger.info(f"카테고리 {category_code}에서 product_ids 추출")

        ranking_data = self.crawl_single_category_ranking(category_code)
        products = ranking_data.get('products', [])

        product_ids = [product['product_id'] for product in products if product.get('product_id')]
        logger.info(f"카테고리 {category_code}에서 {len(product_ids)}개 product_ids 추출")

        return product_ids

    @staticmethod
    def create_review_batches(product_ids: List[str], batch_size: int = 30) -> List[Dict]:
        """product_ids를 배치로 나누기"""
        batches = []
        for i in range(0, len(product_ids), batch_size):
            batch = {
                'batch_index': i // batch_size,
                'product_ids': product_ids[i:i + batch_size],
                'batch_size': len(product_ids[i:i + batch_size]),
                'start_index': i,
                'end_index': min(i + batch_size, len(product_ids))
            }
            batches.append(batch)

        return batches
