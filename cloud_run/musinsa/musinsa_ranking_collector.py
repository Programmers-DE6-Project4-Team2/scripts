#!/usr/bin/env python3

"""
무신사 랭킹 수집기
"""
from datetime import datetime

import requests
import json
import time
import logging
import re
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class MusinsaRankingCollector:
    def __init__(
            self, session: requests.Session, section_id: str = "231", size: int = 40,
            category_code: str = "104001", max_pages: int = 5, created_at: str = None
    ):
        self.session = session
        self.size = size
        self.section_id = section_id
        self.category_code = category_code
        self.max_pages = max_pages
        self.created_at = created_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def build_api_url(self, page: int = 1) -> str:
        """API URL 생성"""
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
        url = self.build_api_url(page)
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
                product['created_at'] = self.created_at
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
                'number_of_views': 0,  # 새로 추가
                'sales': 0  # 새로 추가
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

            # ===== 새로 추가된 부분 =====

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

            # ===== 새로 추가된 부분 끝 =====

            if product['name'] and product['brand']:
                return product

        except Exception as e:
            logger.warning(f"상품 파싱 중 오류: {e}")
            return None
