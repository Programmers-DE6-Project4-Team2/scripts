#!/usr/bin/env python3

"""
무신사 크롤러 메인 (카테고리별 수집)
"""
import json
import re

import requests
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from fake_useragent import UserAgent

from utils import CATEGORY_MAPPING

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MusinsaProductCrawler:
    def __init__(self, section_id: str = "231", size: int = 40,
                 max_pages: int = 5, category_code: str = "104001"):
        self.session = self._setup_session()
        self.section_id = section_id
        self.size = size
        self.max_pages = max_pages
        self.scraped_at = None
        self.category_code = category_code


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

    def _build_api_url(self, page: int = 1) -> str:
        """API URL 생성"""
        if not self.category_code:
            raise ValueError("category_code가 설정되지 않았습니다.")
        base_url = f"https://api.musinsa.com/api2/hm/web/v5/pans/ranking/sections/{self.section_id}"
        params = {
            'storeCode': 'beauty',
            'categoryCode': self.category_code,
            'contentsId': '',
            'gf': 'A',
            'ageBand': 'AGE_BAND_ALL',
            'period': 'REALTIME',
            'page': page,
            'size': self.size
        }

        param_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{base_url}?{param_string}"

    def fetch_products_page(self, page: int = 1) -> Optional[Dict]:
        """단일 페이지 상품 데이터 수집"""
        url = self._build_api_url(page)
        try:
            logger.info(f"API 요청: {url}")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            logger.info(f"페이지 {page} API 응답 성공")
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"페이지 {page} API 요청 실패: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"페이지 {page} JSON 파싱 실패: {e}")
            return None

    def parse_api_response(self, data: Dict, page: int) -> List[Dict]:
        """API 응답 데이터 파싱"""
        products = []
        try:
            if 'data' not in data or 'modules' not in data['data']:
                logger.warning(f"페이지 {page}: 예상된 API 응답 구조가 아닙니다.")
                return products

            modules = data['data']['modules']
            product_items = []

            for module in modules:
                if module.get('type') == 'MULTICOLUMN' and 'items' in module:
                    for item in module['items']:
                        if item.get('type') == 'PRODUCT_COLUMN':
                            product_items.append(item)

            if not product_items:
                logger.info(f"페이지 {page}: 상품 데이터가 없습니다.")
                return products

            logger.info(f"페이지 {page}: {len(product_items)}개 상품 아이템 발견")

            for idx, item in enumerate(product_items):
                product = self.parse_product_item(item, (page - 1) * self.size + idx + 1)
                product['scraped_at'] = self.scraped_at
                product['category_name'] = CATEGORY_MAPPING.get(self.category_code, f"category_{self.category_code}")
                product['category_code'] = self.category_code
                if product:
                    products.append(product)

        except Exception as e:
            logger.error(f"페이지 {page} API 응답 파싱 중 오류: {e}")

        return products

    def parse_product_item(self, item: Dict, rank: int) -> Optional[Dict]:
        """개별 상품 아이템 파싱"""
        try:
            product = {
                'rank': rank,
                'name': '',
                'brand': '',
                'price': '',
                'original_price': '',
                'discount_rate': '',
                'rating': '',
                'review_count': '',
                'likes': '',
                'image_url': '',
                'product_url': '',
                'product_id': '',
                'number_of_views': 0,
                'sales': 0
            }

            # 기본 상품 정보 추출
            product['product_id'] = str(item.get('id', ''))

            info = item.get('info', {})
            if not info:
                return None

            product['name'] = info.get('productName', '')
            product['brand'] = info.get('brandName', '')
            product['price'] = str(info.get('finalPrice', ''))
            product['discount_rate'] = str(info.get('discountRatio', ''))

            # 원가 계산
            if product['discount_rate'] and product['price']:
                try:
                    final_price = int(product['price'])
                    discount_ratio = int(product['discount_rate'])
                    if discount_ratio > 0:
                        original_price = int(final_price * 100 / (100 - discount_ratio))
                        product['original_price'] = str(original_price)
                except:
                    pass

            # 이미지 정보 추출
            image_info = item.get('image', {})
            if image_info and 'url' in image_info:
                product['image_url'] = image_info['url']

            # 상품 URL 생성
            if product['product_id']:
                product['product_url'] = f"https://www.musinsa.com/goods/{product['product_id']}"

            onclick_info = item.get('onClick', {})
            if onclick_info and 'url' in onclick_info:
                product['product_url'] = onclick_info['url']

            # 리뷰 정보 추출
            onclick_event = item.get('onClick', {}).get('eventLog', {}).get('amplitude', {}).get('payload', {})
            if onclick_event:
                product['review_count'] = onclick_event.get('reviewCount', '')
                product['rating'] = onclick_event.get('reviewScore', '')

            image_event = item.get('image', {}).get('onClickLike', {}).get('eventLog', {}).get('amplitude', {}).get(
                'payload', {})
            if image_event:
                if not product['review_count']:
                    product['review_count'] = image_event.get('reviewCount', '')
                if not product['rating']:
                    product['rating'] = image_event.get('reviewScore', '')

            # 1. number_of_views 추출 (info.additionalInformation에서)
            additional_info = info.get('additionalInformation', [])
            if additional_info:
                for info_item in additional_info:
                    text = info_item.get('text', '')

                    # "{number}명이 보는 중" 패턴 찾기
                    views_match = re.search(r'(\d+)명이 보는 중', text)
                    if views_match:
                        product['number_of_views'] = int(views_match.group(1))

                    # 기존 likes 로직도 유지
                    if '명이 보는 중' in text:
                        numbers = re.findall(r'\d+', text)
                        if numbers and not product.get('likes'):
                            product['likes'] = numbers[0]

            # 2. sales 추출 (image.labels에서)
            image_labels = image_info.get('labels', [])
            if image_labels:
                for label in image_labels:
                    text = label.get('text', '')

                    # "판매 {float}천개" 패턴 찾기
                    sales_match = re.search(r'판매 ([\d.]+)천개', text)
                    if sales_match:
                        float_value = float(sales_match.group(1))
                        product['sales'] = int(float_value * 1000)  # float * 1000
                        break

            if product['name'] and product['brand']:
                return product

        except Exception as e:
            logger.warning(f"상품 파싱 중 오류: {e}")
            return None

    def crawl_single_category_ranking(self) -> Dict:
        """단일 카테고리 랭킹만 크롤링 (Airflow Dynamic Task Mapping용)"""
        logger.info(f"카테고리 {self.category_code} 랭킹 크롤링 시작")

        try:
            self.scraped_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

            all_products = []
            for page in range(1, self.max_pages + 1):
                data = self.fetch_products_page(page)
                if not data:
                    break
                products = self.parse_api_response(data, page)
                if not products:
                    break
                all_products.extend(products)

            return {
                'status': 'success',
                'category_code': self.category_code,
                'category_name': CATEGORY_MAPPING.get(self.category_code, 'Unknown'),
                'products': all_products,
                'product_count': len(all_products),
                'scraped_at': self.scraped_at
            }

        except Exception as e:
            logger.error(f"카테고리 {self.category_code} 랭킹 크롤링 실패: {e}")
            return {
                'status': 'error',
                'category_code': self.category_code,
                'products': [],
                'product_ids': [],
                'product_count': 0,
                'error_message': str(e)
            }
