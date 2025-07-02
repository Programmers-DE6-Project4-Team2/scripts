import time
import json
import requests
from datetime import datetime
from typing import List, Dict, Optional
import pandas as pd
from urllib.parse import quote, unquote
from fake_useragent import UserAgent
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NaverShoppingCrawler:
    def __init__(self):
        self.session = requests.Session()
        self.ua = UserAgent()
        self.setup_session()
        
        # 네이버 쇼핑 API 정보
        self.base_api_url = "https://veco-api.shopping.naver.com/window/api/v2/graphql"
        self.operation_name = "getPagedCards"
        self.hash_value = "db693844352af4739286d5394a31659cac8a1643795d5de3bea7064ba7d7fa45"
        
    def setup_session(self):
        """세션 설정"""
        headers = {
            'User-Agent': self.ua.random,
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Origin': 'https://shopping.naver.com',
            'Referer': 'https://shopping.naver.com/',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"macOS"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
        }
        self.session.headers.update(headers)
        logger.info("세션 설정 완료")
    
    def build_api_url(self, page: int, page_size: int = 20, menu_id: str = "20032470") -> str:
        """API URL 생성"""
        variables = {
            "isIncludeProductBenefit": False,
            "isIncludeProductDetail": False,
            "isIncludeWindowViewCount": False,
            "skip": False,
            "checkPromotionProduct": False,
            "params": {
                "page": page,
                "pageSize": page_size,
                "sort": "POPULARITY",
                "subVertical": "BEAUTY",
                "filterSoldOut": True,
                "menuId": menu_id
            }
        }
        
        extensions = {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": self.hash_value
            }
        }
        
        variables_encoded = quote(json.dumps(variables, separators=(',', ':')))
        extensions_encoded = quote(json.dumps(extensions, separators=(',', ':')))
        
        url = f"{self.base_api_url}?operationName={self.operation_name}&variables={variables_encoded}&extensions={extensions_encoded}"
        return url
    
    def fetch_products_api(self, max_pages: int = 10) -> List[Dict]:
        """API 직접 호출로 상품 목록 수집"""
        products = []
        
        for page in range(1, max_pages + 1):
            logger.info(f"페이지 {page} API 호출 중...")
            
            try:
                url = self.build_api_url(page)
                
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                
                # GraphQL 응답 구조 파싱 (실제 구조)
                if 'data' in data and 'pagedCards' in data['data']:
                    cards = data['data']['pagedCards'].get('data', [])
                    
                    if not cards:
                        logger.warning(f"페이지 {page}에서 상품을 찾을 수 없습니다.")
                        break
                    
                    for card in cards:
                        try:
                            product = self.parse_product_card(card)
                            if product:
                                products.append(product)
                        except Exception as e:
                            logger.error(f"상품 파싱 오류: {e}")
                            continue
                            
                    logger.info(f"페이지 {page}에서 {len(cards)}개 상품 수집")
                    
                else:
                    logger.error(f"페이지 {page} 응답 구조 오류")
                    break
                    
            except Exception as e:
                logger.error(f"페이지 {page} API 호출 오류: {e}")
                break
                
            # 요청 간 딜레이
            time.sleep(1)
        
        logger.info(f"총 {len(products)}개 상품 수집 완료")
        return products
    
    def parse_product_card(self, card: Dict) -> Optional[Dict]:
        """상품 카드 데이터 파싱 (실제 네이버 API 구조)"""
        try:
            # 기본 상품 정보
            product_info = {
                'product_id': '',
                'name': '',
                'brand': '',
                'price': '',
                'original_price': '',
                'discount_rate': '',
                'rating': '',
                'review_count': '',
                'url': '',
                'image_url': '',
                'mall_name': '',
                'shipping_info': '',
                'scraped_at': datetime.now().isoformat()
            }
            
            # 네이버 API 실제 구조: card -> data -> product
            if 'data' not in card or 'product' not in card['data']:
                return None
                
            product = card['data']['product']
            
            # 상품 ID
            if 'id' in product:
                product_info['product_id'] = str(product['id'])
            
            # 상품명
            if 'name' in product:
                product_info['name'] = product['name']
            
            # 브랜드 (네이버 API에서는 별도 필드가 없을 수 있음)
            # 상품명에서 브랜드 추출 시도
            name = product.get('name', '')
            if name:
                # 첫 번째 단어를 브랜드로 추정
                brand_candidate = name.split()[0] if name.split() else ''
                product_info['brand'] = brand_candidate
            
            # 가격 정보
            if 'pcDiscountedSalePrice' in product:
                product_info['price'] = str(product['pcDiscountedSalePrice'])
            
            if 'salePrice' in product:
                product_info['original_price'] = str(product['salePrice'])
            
            if 'pcDiscountedRatio' in product:
                product_info['discount_rate'] = str(product['pcDiscountedRatio'])
            
            # 평점 및 리뷰
            if 'averageReviewScore' in product:
                product_info['rating'] = str(product['averageReviewScore'])
            
            if 'totalReviewCount' in product:
                product_info['review_count'] = str(product['totalReviewCount'])
            
            # 상품 URL (상품 ID로 구성)
            if 'id' in product:
                product_info['url'] = f"https://shopping.naver.com/window/products/{product['id']}"
            
            # 이미지 URL (첫 번째 대표 이미지)
            if 'images' in product and product['images']:
                for img in product['images']:
                    if img.get('representativeImage', False):
                        product_info['image_url'] = img.get('imageUrl', '')
                        break
                # 대표 이미지가 없으면 첫 번째 이미지 사용
                if not product_info['image_url'] and product['images']:
                    product_info['image_url'] = product['images'][0].get('imageUrl', '')
            
            return product_info
            
        except Exception as e:
            logger.error(f"상품 카드 파싱 오류: {e}")
            return None
    
    def save_to_csv(self, data: List[Dict], filename: str):
        """CSV로 데이터 저장"""
        if not data:
            logger.warning("저장할 데이터가 없습니다.")
            return
            
        df = pd.DataFrame(data)
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        logger.info(f"데이터가 {filename}에 저장되었습니다.")
    
    def save_to_json(self, data: List[Dict], filename: str):
        """JSON으로 데이터 저장"""
        if not data:
            logger.warning("저장할 데이터가 없습니다.")
            return
            
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"데이터가 {filename}에 저장되었습니다.")

def main():
    """메인 함수"""
    import os
    
    # 데이터 저장 디렉토리 생성
    data_dir = "data"
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    # 크롤러 초기화
    crawler = NaverShoppingCrawler()
    
    try:
        logger.info("네이버 쇼핑 뷰티 카테고리 크롤링 시작...")
        
        # API 방식으로 상품 수집 (5페이지, 100개 상품)
        products = crawler.fetch_products_api(max_pages=5)
        
        if not products:
            logger.error("상품 목록을 가져올 수 없습니다.")
            return
        
        # 타임스탬프 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 데이터 저장
        csv_file = f"{data_dir}/naver_beauty_products_{timestamp}.csv"
        crawler.save_to_csv(products, csv_file)
        
        json_file = f"{data_dir}/naver_beauty_products_{timestamp}.json"
        crawler.save_to_json(products, json_file)
        
        logger.info("크롤링 완료!")
        logger.info(f"총 상품 수: {len(products)}")
        
        # 상위 5개 상품 정보 출력
        print("\n=== 수집된 상품 샘플 (상위 5개) ===")
        for i, product in enumerate(products[:5], 1):
            print(f"\n{i}. {product.get('name', 'N/A')}")
            print(f"   브랜드: {product.get('brand', 'N/A')}")
            print(f"   가격: {product.get('price', 'N/A')}원")
            print(f"   평점: {product.get('rating', 'N/A')}")
            print(f"   리뷰수: {product.get('review_count', 'N/A')}")
            print(f"   판매자: {product.get('mall_name', 'N/A')}")
        
    except Exception as e:
        logger.error(f"크롤링 중 오류 발생: {e}")

if __name__ == "__main__":
    main()