#!/usr/bin/env python3
"""
무신사 리뷰 수집기
"""

import requests
import json
import time
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class MusinsaReviewCollector:
    def __init__(self, session: requests.Session, product_ids: List[str],
                 review_page_size: int = 20, review_max_pages: int = 50,
                 sort: str = "up_cnt_desc", my_filter: str = "false",
                 has_photo: str = "false", is_experience: str = "false"):
        self.session = session
        self.product_ids = product_ids
        self.review_page_size = review_page_size
        self.review_max_pages = review_max_pages
        self.sort = sort
        self.my_filter = my_filter
        self.has_photo = has_photo
        self.is_experience = is_experience

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

    def fetch_product_reviews(self, goods_no: str) -> List[Dict]:
        """단일 상품의 모든 리뷰 수집"""
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

                reviews.extend(review_list)
                logger.info(f"상품 {goods_no}의 {page}페이지에서 {len(review_list)}개 리뷰 수집")

            except requests.exceptions.RequestException as e:
                logger.error(f"상품 {goods_no}의 {page}페이지 요청 실패: {e}")
                break
            except json.JSONDecodeError as e:
                logger.error(f"상품 {goods_no}의 {page}페이지 JSON 파싱 실패: {e}")
                break

            time.sleep(1)

        logger.info(f"상품 {goods_no}의 총 {len(reviews)}개 리뷰 수집 완료")
        return reviews

    def collect_all_reviews(self) -> Dict[str, List[Dict]]:
        """모든 상품의 리뷰 수집"""
        all_reviews = {}
        for goods_no in self.product_ids:
            reviews = self.fetch_product_reviews(goods_no)
            all_reviews[goods_no] = reviews
        return all_reviews

    def flatten_reviews(self, reviews: Dict[str, List[Dict]]) -> List[Dict]:
        """리뷰 데이터를 플랫하게 만들어주는 함수"""
        rows = []
        for product_id, review_list in reviews.items():
            for review in review_list:
                flat = {'product_id': product_id}
                for k, v in review.items():
                    if isinstance(v, dict):
                        for subk, subv in v.items():
                            flat[f'{k}.{subk}'] = subv
                    elif isinstance(v, list):
                        flat[k] = json.dumps(v, ensure_ascii=False)
                    else:
                        flat[k] = v
                rows.append(flat)
        return rows
