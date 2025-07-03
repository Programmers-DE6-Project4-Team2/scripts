#!/usr/bin/env python3
"""
무신사 뷰티 랭킹 API 크롤러
웹 API 기반 크롤러 - 네이버 쇼핑과 유사한 방식
"""
import requests
import json
import csv
import time
from typing import List, Dict, Optional
from fake_useragent import UserAgent
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MusinsaApiCrawler:
    def __init__(self):
        self.ua = UserAgent()
        self.session = requests.Session()
        self.products = []
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
    
    def build_api_url(self, page: int = 1, size: int = 40, section_id: str = "231", category_code: str = "104001") -> str:
        """API URL 생성"""
        # 올바른 sections API 엔드포인트 사용
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
        url = self.build_api_url(page, size)
        
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
    
    def crawl_all_products(self, max_pages: int = 5) -> List[Dict]:
        """모든 상품 데이터 수집"""
        logger.info("무신사 뷰티 랭킹 API 크롤링 시작...")
        
        page = 1
        total_products = 0
        
        while page <= max_pages:
            # API 호출
            data = self.fetch_products_api(page)
            
            if not data:
                logger.warning(f"페이지 {page}에서 데이터를 가져올 수 없습니다.")
                break
            
            # 상품 데이터 추출
            products = self.parse_api_response(data, page)
            
            if not products:
                logger.info(f"페이지 {page}에서 더 이상 상품이 없습니다.")
                break
            
            self.products.extend(products)
            total_products += len(products)
            
            logger.info(f"페이지 {page}: {len(products)}개 상품 수집 (누적: {total_products}개)")
            
            # API 호출 간격 조절
            time.sleep(1)
            page += 1
        
        logger.info(f"크롤링 완료 - 총 {len(self.products)}개 상품 수집")
        return self.products
    
    def parse_api_response(self, data: Dict, page: int) -> List[Dict]:
        """API 응답 데이터 파싱"""
        products = []
        
        try:
            # 무신사 API 응답 구조: data.modules에서 MULTICOLUMN 타입 찾기
            if 'data' not in data or 'modules' not in data['data']:
                logger.warning(f"페이지 {page}: 예상된 API 응답 구조가 아닙니다.")
                return products
            
            modules = data['data']['modules']
            product_items = []
            
            # MULTICOLUMN 모듈에서 상품 아이템 추출
            for module in modules:
                if module.get('type') == 'MULTICOLUMN' and 'items' in module:
                    for item in module['items']:
                        if item.get('type') == 'PRODUCT_COLUMN':
                            product_items.append(item)
            
            if not product_items:
                logger.info(f"페이지 {page}: 상품 데이터가 없습니다.")
                return products
            
            logger.info(f"페이지 {page}: {len(product_items)}개 상품 아이템 발견")
            
            # 각 상품 파싱
            for idx, item in enumerate(product_items):
                product = self.parse_product_item(item, (page - 1) * 40 + idx + 1)
                if product:
                    products.append(product)
                    
        except Exception as e:
            logger.error(f"페이지 {page} API 응답 파싱 중 오류: {e}")
            
        return products
    
    def parse_product_item(self, item: Dict, rank: int) -> Optional[Dict]:
        """개별 상품 아이템 파싱 - 무신사 API 구조에 맞춰 수정"""
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
                'product_id': ''
            }
            
            # 무신사 API 구조: item.id가 상품 ID, item.info에 상품 정보
            product['product_id'] = str(item.get('id', ''))
            
            info = item.get('info', {})
            if not info:
                return None
            
            # 상품명과 브랜드명
            product['name'] = info.get('productName', '')
            product['brand'] = info.get('brandName', '')
            
            # 가격 정보
            product['price'] = str(info.get('finalPrice', ''))
            product['discount_rate'] = str(info.get('discountRatio', ''))
            
            # 할인율이 있는 경우 원가 계산
            if product['discount_rate'] and product['price']:
                try:
                    final_price = int(product['price'])
                    discount_ratio = int(product['discount_rate'])
                    if discount_ratio > 0:
                        original_price = int(final_price * 100 / (100 - discount_ratio))
                        product['original_price'] = str(original_price)
                except:
                    pass
            
            # 이미지 정보 - 실제 API 구조에 맞춰 수정
            image_info = item.get('image', {})
            if image_info and 'url' in image_info:
                product['image_url'] = image_info['url']
            
            # 상품 URL
            if product['product_id']:
                product['product_url'] = f"https://www.musinsa.com/goods/{product['product_id']}"
            
            # onClick 정보에서 추가 데이터 추출
            onclick_info = item.get('onClick', {})
            if onclick_info and 'url' in onclick_info:
                product['product_url'] = onclick_info['url']
            
            # 평점과 리뷰 수 정보 - eventLog에서 추출
            # onClick eventLog에서 추출 시도
            onclick_event = item.get('onClick', {}).get('eventLog', {}).get('amplitude', {}).get('payload', {})
            if onclick_event:
                product['review_count'] = onclick_event.get('reviewCount', '')
                product['rating'] = onclick_event.get('reviewScore', '')
            
            # image onClickLike eventLog에서도 추출 시도 (더 정확한 데이터일 수 있음)
            image_event = item.get('image', {}).get('onClickLike', {}).get('eventLog', {}).get('amplitude', {}).get('payload', {})
            if image_event:
                if not product['review_count']:
                    product['review_count'] = image_event.get('reviewCount', '')
                if not product['rating']:
                    product['rating'] = image_event.get('reviewScore', '')
            
            # 추가 정보에서 실시간 조회 수 등 추출
            additional_info = info.get('additionalInformation', [])
            if additional_info:
                import re
                for info_item in additional_info:
                    text = info_item.get('text', '')
                    
                    # "N명이 보는 중" 정보 추출
                    if '명이 보는 중' in text:
                        numbers = re.findall(r'\d+', text)
                        if numbers:
                            product['likes'] = numbers[0]  # 실시간 조회자 수를 likes 필드에 저장
            
            # 필수 정보가 있는 경우만 반환
            if product['name'] and product['brand']:
                return product
                
        except Exception as e:
            logger.warning(f"상품 파싱 중 오류: {e}")
            logger.warning(f"아이템 구조: {item}")
            
        return None
    
    def save_to_csv(self, filename: str = 'musinsa_beauty_api_products.csv'):
        """CSV 파일로 저장"""
        if not self.products:
            logger.warning("저장할 데이터가 없습니다.")
            return
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['rank', 'name', 'brand', 'price', 'original_price', 
                         'discount_rate', 'rating', 'review_count', 'likes', 
                         'image_url', 'product_url', 'product_id']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for product in self.products:
                writer.writerow(product)
        
        logger.info(f"데이터가 {filename}에 저장되었습니다.")
    
    def save_to_json(self, filename: str = 'musinsa_beauty_api_products.json'):
        """JSON 파일로 저장"""
        if not self.products:
            logger.warning("저장할 데이터가 없습니다.")
            return
        
        with open(filename, 'w', encoding='utf-8') as jsonfile:
            json.dump(self.products, jsonfile, ensure_ascii=False, indent=2)
        
        logger.info(f"데이터가 {filename}에 저장되었습니다.")
    
    def print_summary(self):
        """크롤링 결과 요약 출력"""
        if not self.products:
            print("수집된 데이터가 없습니다.")
            return
        
        print(f"\n=== 무신사 뷰티 랭킹 API 크롤링 결과 ===")
        print(f"총 상품 수: {len(self.products)}개")
        
        # 브랜드별 통계
        brands = {}
        prices = []
        
        for product in self.products:
            brand = product.get('brand', '알 수 없음')
            brands[brand] = brands.get(brand, 0) + 1
            
            # 가격 정보 수집
            price = product.get('price', '')
            if price and price.replace(',', '').replace('원', '').isdigit():
                prices.append(int(price.replace(',', '').replace('원', '')))
        
        print(f"\n브랜드별 상품 수 (상위 10개):")
        for brand, count in sorted(brands.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {brand}: {count}개")
        
        if prices:
            print(f"\n가격 통계:")
            print(f"  평균 가격: {sum(prices) // len(prices):,}원")
            print(f"  최고 가격: {max(prices):,}원")
            print(f"  최저 가격: {min(prices):,}원")
        
        print(f"\n상위 10개 상품:")
        for i, product in enumerate(self.products[:10]):
            print(f"  {i+1}. {product.get('name', 'N/A')} - {product.get('brand', 'N/A')} - {product.get('price', 'N/A')}")

def main():
    """메인 함수"""
    crawler = MusinsaApiCrawler()
    
    try:
        # API 크롤링 실행 (테스트용 5페이지)
        products = crawler.crawl_all_products(max_pages=5)
        
        if products:
            # 결과 출력
            crawler.print_summary()
            
            # 파일 저장
            crawler.save_to_csv()
            crawler.save_to_json()
        else:
            print("크롤링된 데이터가 없습니다.")
        
    except Exception as e:
        logger.error(f"메인 실행 중 오류: {e}")

if __name__ == "__main__":
    main()