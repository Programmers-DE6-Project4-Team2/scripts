#!/usr/bin/env python3
"""
무신사 뷰티 랭킹 API 크롤러
웹 API 기반 크롤러 - 네이버 쇼핑과 유사한 방식
"""
import requests
import json
import csv
import time
import logging
import pandas as pd
from typing import List, Dict, Optional
from fake_useragent import UserAgent


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MusinsaReviewApiCrawler:
    def __init__(self):
        self.ua = UserAgent()
        self.session = requests.Session()
        self.products = None
        self.setup_session()

    def setup_session(self):
        """세션 설정"""
        headers = {
            'User-Agent': self.ua.random,
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://www.musinsa.com/main/beauty/ranking',
            'Origin': 'https://www.musinsa.com',
        }
        self.session.headers.update(headers)
        logger.info("세션 설정 완료")

    def build_product_api_url(
            self, page: int = 1, size: int = 40, section_id: str = "231", category_code: str = "104001"
    ) -> str:
        """랭킹 페이지 API URL 생성"""
        base_url = f"https://api.musinsa.com/api2/hm/web/v5/pans/ranking/sections/{section_id}"

        params = {
            'storeCode': 'beauty',
            'categoryCode': category_code,
            'contentsId': '',
            'gf': 'A',  # 성별 필터 (All)
            'ageBand': 'AGE_BAND_ALL',  # 연령 필터
            'period': 'REALTIME',  # 실시간
            'page': page,
            'size': size
        }

        # URL 파라미터 생성
        param_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{base_url}?{param_string}"

    def fetch_products_api(self, page: int = 1, size: int = 40) -> Optional[Dict]:
        """API를 통한 상품 데이터 수집"""
        url = self.build_product_api_url(page, size)

        try:
            logger.info(f"Ranking page API 요청: {url}")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            products = response.json()
            logger.info(f"페이지 {page} API 응답 성공")
            return products
        except requests.exceptions.RequestException as e:
            logger.error(f"페이지 {page} API 요청 실패: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"페이지 {page} JSON 파싱 실패: {e}")
            return None

    def extract_product_ids(self, products: dict) -> list:
        product_ids = []

        def recurse(obj):
            if isinstance(obj, dict):
                if obj.get('type') == 'PRODUCT_COLUMN' and 'id' in obj:
                    product_ids.append(obj['id'])
                for v in obj.values():
                    recurse(v)
            elif isinstance(obj, list):
                for item in obj:
                    recurse(item)

        recurse(products)
        product_ids = list(dict.fromkeys(product_ids))
        logger.info(f"추출된 product_ids: {product_ids}")
        return product_ids

    def build_review_api_url(
            self, page: int = 0, page_size: int = 20, sort: str = "up_cnt_desc",  goods_no: str = "231",
            my_filter: str = "false", has_photo: str = "false", is_experience: str = "false"
    ) -> str:
        """리뷰 API URL 생성"""
        base_url = "https://goods.musinsa.com/api2/review/v1/view/list"
        params = {
            "page": page,
            "pageSize": page_size,
            "goodsNo": goods_no,
            "sort": sort,
            "selectedSimilarNo": goods_no,
            "myFilter": my_filter,
            "hasPhoto": has_photo,
            "isExperience": is_experience
        }

        # URL 파라미터 생성
        param_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{base_url}?{param_string}"

    def get_reviews(self, product_ids: list[str], max_pages: int = 50) -> Optional[Dict]:
        """Review 수집"""
        all_reviews = {}

        for goods_no in product_ids:
            logger.info(f"상품 {goods_no}의 리뷰 수집 시작")
            reviews = []

            for page in range(1, max_pages + 1):  # 페이지는 1부터 시작
                url = self.build_review_api_url(
                    page=page, page_size=20, sort="up_cnt_desc", goods_no=goods_no,
                    my_filter="false", has_photo="false", is_experience="false"
                )
                try:
                    response = self.session.get(url=url, timeout=10)
                    response.raise_for_status()
                    data = response.json()
                    review_list = data.get("data", {}).get("list", [])

                    if not review_list:
                        logger.info(f"상품 {goods_no}의 {page}페이지에서 더 이상 리뷰가 없음")
                        break  # 더 이상 리뷰가 없으면 중단

                    reviews.extend(review_list)
                    logger.info(f"상품 {goods_no}의 {page}페이지에서 {len(review_list)}개 리뷰 수집")

                except requests.exceptions.RequestException as e:
                    logger.error(f"상품 {goods_no}의 {page}페이지 요청 실패: {e}")
                    break
                except json.JSONDecodeError as e:
                    logger.error(f"상품 {goods_no}의 {page}페이지 JSON 파싱 실패: {e}")
                    break

                time.sleep(1)  # 서버 부하 방지용 딜레이

            all_reviews[goods_no] = reviews
            logger.info(f"상품 {goods_no}의 총 {len(reviews)}개 리뷰 수집 완료")
        return all_reviews

    def flatten_reviews(self, reviews):
        """리뷰 데이터를 플랫하게 만들어주는 함수"""
        rows = []
        for product_id, reviews in reviews.items():
            for review in reviews:
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

    def convert_to_csv(self, rows: list[dict], filename='reviews.csv'):
        """리스트 데이터를 CSV로 변환하는 함수"""
        df = pd.DataFrame(rows)
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        logger.info(f"CSV 파일이 '{filename}'으로 저장되었습니다.")
        logger.info(f"총 {len(df)} 개의 리뷰가 처리되었습니다.")
        logger.info(f"컬럼 수: {len(df.columns)}")
        return df

    @staticmethod
    def save_to_json(reviews, filename: str = 'musinsa_beauty_reviews.json'):
        """JSON 파일로 저장"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(reviews, f, ensure_ascii=False, indent=2)
        logger.info(f"데이터가 {filename}에 저장되었습니다.")

def main():
    """메인 함수"""
    review_crawler = MusinsaReviewApiCrawler()
    try:
        products = review_crawler.fetch_products_api(1, 40)
        product_ids = review_crawler.extract_product_ids(products)
        reviews = review_crawler.get_reviews(product_ids, 1)

        review_rows = review_crawler.flatten_reviews(reviews)

        review_crawler.convert_to_csv(review_rows)
        review_crawler.save_to_json(reviews)
    except Exception as e:
        logger.error(f"메인 실행 중 오류: {e}")


if __name__ == "__main__":
    main()
