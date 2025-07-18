#!/usr/bin/env python3
"""
무신사 크롤러 메인
"""
import time

import requests
import csv
import json
import logging
import pandas as pd
from typing import Dict, List, Optional
from fake_useragent import UserAgent
from datetime import datetime, timezone

from utils import CATEGORY_MAPPING


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MusinsaReviewCrawler:
    def __init__(
            self, product_id: str,
            section_id: str = "231", size: int = 40,
            category_code: str = "104001", request_delay: float = 1.0,
            review_page_size: int = 20, review_max_pages: int = 50,
            sort: str = "up_cnt_desc", my_filter: str = "false",
            has_photo: str = "false", is_experience: str = "false",
    ):
        self.session = self._setup_session()
        self.product_id = product_id
        self.section_id = section_id
        self.size = size
        self.category_code = category_code
        self.category_name = CATEGORY_MAPPING.get(category_code, 'Unknown')
        self.request_delay = request_delay
        self.review_page_size = review_page_size
        self.review_max_pages = review_max_pages
        self.sort = sort
        self.my_filter = my_filter
        self.has_photo = has_photo
        self.is_experience = is_experience

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

    def _build_review_api_url(self, page: int = 0) -> str:
        """리뷰 API URL 생성"""
        base_url = "https://goods.musinsa.com/api2/review/v1/view/list"
        params = {
            "page": page,
            "pageSize": self.review_page_size,
            "goodsNo": self.product_id,
            "sort": self.sort,
            "selectedSimilarNo": self.product_id,
            "myFilter": self.my_filter,
            "hasPhoto": self.has_photo,
            "isExperience": self.is_experience
        }
        param_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{base_url}?{param_string}"

    def crawl_reviews(self) -> Dict:
        """단일 상품의 모든 리뷰 수집"""
        logger.info(f"상품 {self.product_id}의 리뷰 수집 시작")

        reviews = []
        scraped_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        for page in range(1, self.review_max_pages + 1):
            url = self._build_review_api_url(page=page)

            try:
                response = self.session.get(url=url, timeout=10)
                response.raise_for_status()
                data = response.json()

                review_list = data.get("data", {}).get("list", [])

                if not review_list:
                    logger.info(f"상품 {self.product_id}의 {page}페이지에서 더 이상 리뷰가 없음")
                    break

                # 각 리뷰에 메타데이터 추가
                for review in review_list:
                    review['scraped_at'] = scraped_at
                    review['category_code'] = self.category_code
                    review['category_name'] = self.category_name
                    review['product_id'] = self.product_id

                reviews.extend(review_list)
                logger.info(f"상품 {self.product_id}의 {page}페이지에서 {len(review_list)}개 리뷰 수집")

                # 페이지 간 지연
                if page < self.review_max_pages:
                    time.sleep(self.request_delay * 0.5)

            except requests.exceptions.RequestException as e:
                logger.error(f"상품 {self.product_id}의 {page}페이지 요청 실패: {e}")
                break
            except json.JSONDecodeError as e:
                logger.error(f"상품 {self.product_id}의 {page}페이지 JSON 파싱 실패: {e}")
                break

        logger.info(f"상품 {self.product_id}의 총 {len(reviews)}개 리뷰 수집 완료")

        return {
            'product_id': self.product_id,
            'category_code': self.category_code,
            'category_name': self.category_name,
            'reviews': reviews,
            'review_count': len(reviews),
            'scraped_at': scraped_at
        }

    def flatten_reviews(self, reviews: List[Dict]) -> List[Dict]:
        """리뷰 데이터를 플랫하게 만들어주는 함수"""
        rows = []

        for review in reviews:
            flat = {
                'product_id': self.product_id,
                'category_code': self.category_code,
                'category_name': self.category_name
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

    def save_reviews_to_csv(self, reviews: List[Dict], filename: Optional[str] = None) -> str:
        """리뷰 데이터를 CSV로 저장"""
        if not reviews:
            logger.warning("저장할 리뷰 데이터가 없습니다.")
            return ""

        # 파일명 생성
        if not filename:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = f"{self.product_id}_{timestamp}.csv"

        review_rows = self.flatten_reviews(reviews)
        df = pd.DataFrame(review_rows)
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        logger.info(f"리뷰 데이터가 {filename}에 저장되었습니다.")

        return filename
