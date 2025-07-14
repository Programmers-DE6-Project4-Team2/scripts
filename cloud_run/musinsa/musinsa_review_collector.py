#!/usr/bin/env python3
"""
무신사 리뷰 수집기
"""
from datetime import datetime, timezone
import os
import requests
import json
import time
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class MusinsaReviewCollector:
    def __init__(
            self, session: requests.Session, product_ids: List[str],
             review_page_size: int = 20, review_max_pages: int = 50,
             sort: str = "up_cnt_desc", my_filter: str = "false",
             has_photo: str = "false", is_experience: str = "false",
             category_code: str = "unknown"
    ):
        self.session = session
        self.product_ids = product_ids
        self.review_page_size = review_page_size
        self.review_max_pages = review_max_pages
        self.sort = sort
        self.my_filter = my_filter
        self.has_photo = has_photo
        self.is_experience = is_experience

        self.category_code = category_code
        from utils import CATEGORY_MAPPING
        self.category_name = CATEGORY_MAPPING.get(category_code, 'Unknown')

        # 환경변수 기반 설정 추가
        self.request_delay = float(os.environ.get("REQUEST_DELAY", "1.0"))
        self.test_mode = os.environ.get("TEST_MODE", "false").lower() == "true"

        # 테스트 모드에서는 제한
        if self.test_mode:
            self.product_ids = self.product_ids[:3]  # 상품 3개만
            self.review_max_pages = min(self.review_max_pages, 3)  # 페이지 3개만
            logger.info(f"테스트 모드: 상품 {len(self.product_ids)}개, 페이지 {self.review_max_pages}개로 제한")

    def collect_all_reviews(self) -> Dict[str, List[Dict]]:
        """모든 상품의 리뷰 수집 - 로깅 강화"""
        all_reviews = {}

        for i, goods_no in enumerate(self.product_ids):
            try:
                logger.info(f"상품 {goods_no} 리뷰 수집 중 ({i + 1}/{len(self.product_ids)})")
                scraped_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

                reviews = self.fetch_product_reviews(goods_no, scraped_at)
                all_reviews[goods_no] = reviews

                logger.info(f"상품 {goods_no} 완료: {len(reviews)}개 리뷰 수집")

                # 상품 간 지연
                if i < len(self.product_ids) - 1:
                    time.sleep(self.request_delay)

            except Exception as e:
                logger.error(f"상품 {goods_no} 리뷰 수집 실패: {e}")
                all_reviews[goods_no] = []
                continue

        total_reviews = sum(len(reviews) for reviews in all_reviews.values())
        logger.info(f"전체 리뷰 수집 완료: {total_reviews}개")

        return all_reviews

    def fetch_product_reviews(self, goods_no: str, scraped_at: str) -> List[Dict]:
        """단일 상품의 모든 리뷰 수집 - 지연 시간 추가"""
        logger.info(f"상품 {goods_no}의 리뷰 수집 시작")
        reviews = []

        for page in range(1, self.review_max_pages + 1):
            url = self.build_review_api_url(page=page, goods_no=goods_no)
            try:
                response = self.session.get(url=url, timeout=10)
                response.raise_for_status()
                data = response.json()

                review_list = data.get("data", {}).get("list", [])
                if not review_list:
                    logger.info(f"상품 {goods_no}의 {page}페이지에서 더 이상 리뷰가 없음")
                    break

                for review in review_list:
                    review['scraped_at'] = scraped_at
                    review['category_code'] = self.category_code
                    review['category_name'] = self.category_name

                reviews.extend(review_list)
                logger.info(f"상품 {goods_no}의 {page}페이지에서 {len(review_list)}개 리뷰 수집")

                # 페이지 간 지연
                if page < self.review_max_pages:
                    time.sleep(self.request_delay * 0.5)

            except requests.exceptions.RequestException as e:
                logger.error(f"상품 {goods_no}의 {page}페이지 요청 실패: {e}")
                break
            except json.JSONDecodeError as e:
                logger.error(f"상품 {goods_no}의 {page}페이지 JSON 파싱 실패: {e}")
                break

        logger.info(f"상품 {goods_no}의 총 {len(reviews)}개 리뷰 수집 완료")
        return reviews

    def build_review_api_url(self, page: int = 0, goods_no: str = "231") -> str:
        """리뷰 API URL 생성"""
        base_url = "https://goods.musinsa.com/api2/review/v1/view/list"
        params = {
            "page": page,
            "pageSize": self.review_page_size,
            "goodsNo": goods_no,
            "sort": self.sort,
            "selectedSimilarNo": goods_no,
            "myFilter": self.my_filter,
            "hasPhoto": self.has_photo,
            "isExperience": self.is_experience
        }
        param_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{base_url}?{param_string}"

    def flatten_reviews(self, reviews: Dict[str, List[Dict]]) -> List[Dict]:
        """리뷰 데이터를 플랫하게 만들어주는 함수"""
        rows = []
        for product_id, review_list in reviews.items():
            for review in review_list:
                flat = {
                    'product_id': product_id
                }

                for k, v in review.items():
                    if isinstance(v, dict):
                        for subk, subv in v.items():
                            column_name = f'{k}_{subk}'.replace('.', '_')
                            flat[column_name] = subv
                    elif isinstance(v, list):
                        column_name = k.replace('.', '_')
                        flat[column_name] = json.dumps(v, ensure_ascii=False)
                    else:
                        column_name = k.replace('.', '_')
                        flat[column_name] = v
                rows.append(flat)
        return rows
