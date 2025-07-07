import time
import json
import requests
from datetime import datetime
from typing import List, Dict, Optional
import pandas as pd
from urllib.parse import quote
from fake_useragent import UserAgent
import logging
import os

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NaverShoppingCrawler:
    """
    네이버 쇼핑의 GraphQL API를 이용하여 상품 데이터를 수집하는 클래스
    """
    def __init__(self):
        self.session = requests.Session()
        self.ua = UserAgent() # User-Agent 로테이션을 위한 객체
        self.setup_session()
        
        # 네이버 쇼핑 GraphQL API 기본 정보
        self.base_api_url = "https://veco-api.shopping.naver.com/window/api/v2/graphql"
        self.operation_name = "getPagedCards"
        # "인기순" 정렬에 해당하는 GraphQL Persisted Query Hash 값
        self.hash_value = "db693844352af4739286d5394a31659cac8a1643795d5de3bea7064ba7d7fa45"
        
        # 기본 카테고리 및 정렬 설정 (이 설정은 fetch_products_api 호출 시 오버라이드 가능)
        self.default_display_category_id = "20006491" # 네이버 뷰티 전체 카테고리
        self.default_sort_type = "DISPLAY_CATEGORY_GENDER_AGE_GROUP_F20" # 인기순 (20대 여성 기준)

    def setup_session(self):
        """HTTP 세션의 기본 헤더를 설정합니다."""
        headers = {
            'User-Agent': self.ua.random, # 매 요청마다 다른 User-Agent 사용 가능 (fake_useragent 라이브러리 사용 시)
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Origin': 'https://shopping.naver.com',
            'Referer': 'https://shopping.naver.com/',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="124", "Google Chrome";v="124"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'Connection': 'keep-alive',
            # POST 요청 시 Content-Type은 requests 라이브러리가 json 파라미터 사용 시 자동으로 설정해줍니다.
            # 'Content-Type': 'application/json',
        }
        self.session.headers.update(headers)
        logger.info("세션 헤더 설정 완료.")

    def _build_graphql_payload(self, page: int, page_size: int, display_category_id: str, sort_type: str) -> Dict:
        """
        GraphQL POST 요청에 필요한 JSON 페이로드 딕셔너리를 생성합니다.
        variables와 extensions는 딕셔너리 형태 그대로 반환합니다.
        """
        variables = {
            "isIncludeProductBenefit": False,
            "isIncludeProductDetail": False,
            "isIncludeWindowViewCount": False,
            "skip": False,
            "checkPromotionProduct": False,
            "params": {
                "page": page,
                "pageSize": page_size,
                "filterSoldOut": True, # 품절 상품 필터링
                "useNonSubVertical": True,
                "displayCategoryId": display_category_id,
                "sort": sort_type
            }
        }
        
        extensions = {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": self.hash_value
            }
        }
        
        return {
            "operationName": self.operation_name,
            "variables": variables, # 딕셔너리 형태로 전달
            "extensions": extensions # 딕셔너리 형태로 전달
        }

    def fetch_single_page(self, page: int, page_size: int = 20, 
                          display_category_id: Optional[str] = None, 
                          sort_type: Optional[str] = None,
                          collection_timestamp: Optional[str] = None) -> List[Dict]:
        """
        단일 페이지의 상품 정보를 GraphQL API를 통해 수집합니다.
        """
        # 기본값 사용 또는 인자값 오버라이드
        if display_category_id is None:
            display_category_id = self.default_display_category_id
        if sort_type is None:
            sort_type = self.default_sort_type

        # POST 요청에 필요한 페이로드 생성
        payload = self._build_graphql_payload(page, page_size, display_category_id, sort_type)
        
        try:
            # POST 요청으로 GraphQL API 호출, json=payload 사용
            response = self.session.post(self.base_api_url, json=payload, timeout=30)
            response.raise_for_status() # HTTP 오류(4xx, 5xx) 발생 시 예외 발생
            
            data = response.json()
            
            # --- 디버깅 추가: 응답 데이터가 딕셔너리인지 확인 ---
            if not isinstance(data, dict):
                logger.error(f"페이지 {page} 응답이 유효한 JSON 딕셔너리가 아닙니다. 수집 실패. 응답 텍스트: {response.text[:500]}...") # 부분 출력
                return []
            # --- 디버깅 추가 끝 ---

            card_items = data.get('data', {}).get('pagedCards', {}).get('data', [])
            
            products = []
            for card in card_items:
                # _parse_product_card 메서드에 수집 날짜 전달
                product = self._parse_product_card(card, collection_timestamp)
                if product:
                    products.append(product)
            
            # 디버깅 로그 추가: API 응답에서 파싱된 상품 카드 개수와 최종 추출된 상품 개수 확인
            logger.info(f"  페이지 {page}: API 응답에서 {len(card_items)}개 상품 카드 확인, 최종 {len(products)}개 상품 추출됨.")
            return products
        
        except requests.exceptions.RequestException as e:
            logger.error(f"페이지 {page} API 요청 중 네트워크/HTTP 오류 발생: {e}. 응답 상태 코드: {response.status_code if 'response' in locals() else 'N/A'}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"페이지 {page} JSON 응답 디코딩 중 오류 발생: {e}. 응답 텍스트 (부분): {response.text[:500] if 'response' in locals() else 'N/A'}")
            return []
        except KeyError as e:
            logger.error(f"페이지 {page} 응답 데이터 구조 오류: 필수 키 없음 - {e}. 응답: {data if 'data' in locals() else 'N/A'}")
            return []
        except Exception as e:
            logger.error(f"페이지 {page} 처리 중 알 수 없는 오류 발생: {e}", exc_info=True)
            return []

    def fetch_products_api(self, max_pages: int, page_size: int = 20, 
                           display_category_id: Optional[str] = None, 
                           sort_type: Optional[str] = None,
                           collection_timestamp: Optional[str] = None) -> List[Dict]:
        """
        GraphQL API를 사용하여 지정된 카테고리에서 여러 페이지의 상품 정보를 수집합니다.
        """
        if display_category_id is None:
            display_category_id = self.default_display_category_id
        if sort_type is None:
            sort_type = self.default_sort_type

        all_products = []
        for page in range(1, max_pages + 1):
            logger.info(f"✨ 카테고리 '{display_category_id}' - {page}페이지 상품 수집 중...")
            # fetch_single_page 메서드에 수집 날짜 전달
            products_on_page = self.fetch_single_page(page, page_size, display_category_id, sort_type, collection_timestamp)
            
            if not products_on_page:
                logger.info(f"페이지 {page}에서 더 이상 상품을 찾을 수 없습니다. (빈 응답 또는 오류 발생). 수집을 종료합니다.")
                break # 더 이상 상품이 없거나 오류 발생 시 루프 종료
            
            all_products.extend(products_on_page)
            time.sleep(2.0) # 서버 부하 방지를 위한 대기 시간 (2.0초)

        return all_products

    def _parse_product_card(self, card: Dict, collection_timestamp: Optional[str] = None) -> Optional[Dict]:
        """
        단일 상품 카드 딕셔너리에서 필요한 정보를 추출하고 수집 날짜를 추가합니다.
        'product' 필드가 유효하지 않거나 None인 경우를 방어적으로 처리합니다.
        """
        product_data_from_card = card.get('data', {}) # 'data' 키가 없으면 빈 딕셔너리
        
        # 'data' 필드가 딕셔너리가 아니면 유효하지 않은 카드이므로 건너뜀
        if not isinstance(product_data_from_card, dict):
            logger.warning(f"카드 'data' 필드가 딕셔너리가 아님: {type(product_data_from_card)} for card {card.get('cardId', 'N/A')}. 스킵.")
            return None

        product = product_data_from_card.get('product', None) 

        # 'product'가 None이거나 딕셔너리 형태가 아니면 유효하지 않다고 판단
        if product is None or not isinstance(product, dict):
            logger.warning(f"유효하지 않은 'product' 데이터 구조 발견 (유형: {type(product)} 또는 None) for card {card.get('cardId', 'N/A')}. 스킵.")
            return None
        
        # product 딕셔너리가 비어있는 경우 ({}인 경우)
        if not product: 
            logger.warning("상품 데이터 딕셔너리가 비어있음 for card: %s. 스킵.", card.get('cardId', 'N/A'))
            return None
        
        # 여기까지 도달했다면 product는 유효한 (비어있지 않은) 딕셔너리임이 보장됩니다.
        # 기존 파싱 로직 계속.
        # 가격 정보: salePrice(할인 가격) 우선, 없으면 originalPrice(정가) 사용
        price = product.get('salePrice', product.get('originalPrice', 'N/A'))
        
        # 카테고리 정보 추출 로직
        category_names = []
        categories_list_from_product = product.get('categories', []) # 'categories' 키에서 리스트를 시도
        
        if categories_list_from_product:
            # 'categories' 리스트가 존재하고 비어있지 않으면 거기서 이름 추출
            category_names = [cat.get('name') for cat in categories_list_from_product if cat.get('name')]
            if not category_names: # 리스트는 있었으나 이름이 모두 None/비어있었던 경우
                logger.warning(f"상품 ID {product.get('id', 'N/A')}의 'categories' 리스트는 존재하지만 유효한 이름이 없습니다. 원본: {categories_list_from_product}")
        
        # 'categories' 리스트에서 유효한 이름을 얻지 못했고, 'productCategoryName'이 존재하면 그걸 사용
        if not category_names and product.get('productCategoryName'):
            category_names = [product.get('productCategoryName')]
            # logger.info(f"상품 ID {product.get('id', 'N/A')}에 대해 'productCategoryName' 사용: {category_names[0]}") # 너무 많은 로그 방지
        
        # 두 가지 모두 없는 경우
        if not category_names:
            logger.warning(f"상품 ID {product.get('id', 'N/A')}에 대한 카테고리 데이터(categories 또는 productCategoryName)가 모두 누락되었습니다.")
       
        # 브랜드 정보 추출
        brand = (product.get('brand') or {}).get('name', 'N/A')
        
        # 상품 상세 URL 생성
        sub_vertical = product.get('channel', {}).get('subVertical')
        product_id = product.get('id')

        if sub_vertical and product_id:
            product_url = f"https://shopping.naver.com/window-products/{sub_vertical.lower()}/{product_id}"
        else:
            logger.warning(f"URL 생성 실패: id={product_id}, subVertical={sub_vertical}")
            product_url = 'N/A'

        # 리뷰 수와 평점 필드명 변경
        review_count = product.get('totalReviewCount', 0) # 필드명 변경
        avg_review_score = product.get('averageReviewScore', 0.0) # 필드명 변경

        # 디버깅 추가: 리뷰/평점 데이터가 기본값으로 사용될 경우 원본 product 데이터 로깅
        if (review_count == 0 and avg_review_score == 0.0) and \
           (product.get('totalReviewCount') is None or product.get('averageReviewScore') is None):
             logger.warning(f"상품 ID {product.get('id', 'N/A')}에 대한 리뷰/평점 데이터가 누락되어 기본값 사용. 원본 product 데이터 (일부): {json.dumps(product, ensure_ascii=False, indent=2)[:500]}...") # 로그 길이 제한
        
        parsed_data = {
            "product_id": product_id,
            "name": product.get('name', 'N/A'),
            "brand": brand,
            "price": price,
            "originalPrice": product.get('originalPrice', 'N/A'),
            "representativeImageUrl": product.get('representativeImageUrl', 'N/A'),
            "reviewCount": review_count, # 추출된 변수 사용
            "avgReviewScore": avg_review_score, # 추출된 변수 사용
            "product_url": product_url,
            "categories": category_names, # 수정된 category_names 변수 사용
            "detailContent": product.get('detailContent', 'N/A'), # 상품 상세 설명 (HTML/텍스트 등)
            "channelName": product.get('channel', {}).get('name', 'N/A'), # 판매 채널명
        }
        
        # 수집 날짜 필드 추가
        if collection_timestamp:
            parsed_data["collectionDate"] = collection_timestamp
            
        return parsed_data

    def save_to_csv(self, data: List[Dict], filename: str):
        """리스트 데이터를 CSV 파일로 저장"""
        if not data:
            logger.warning(f"'{filename}'에 저장할 데이터가 없습니다.")
            return

        try:
            df = pd.DataFrame(data)
            df.to_csv(filename, index=False, encoding='utf-8-sig') # 한글 깨짐 방지를 위해 'utf-8-sig' 사용
            logger.info(f"데이터가 '{filename}'에 CSV 형식으로 저장되었습니다. (총 {len(data)}개)")
        except Exception as e:
            logger.error(f"CSV 저장 중 오류 발생: {e}", exc_info=True)

    def save_to_json(self, data: List[Dict], filename: str):
        """리스트 데이터를 JSON 파일로 저장"""
        if not data:
            logger.warning(f"'{filename}'에 저장할 데이터가 없습니다.")
            return

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4) # 한글 인코딩 및 가독성을 위해 ensure_ascii=False, indent=4
            logger.info(f"데이터가 '{filename}'에 JSON 형식으로 저장되었습니다. (총 {len(data)}개)")
        except Exception as e:
            logger.error(f"JSON 저장 중 오류 발생: {e}", exc_info=True)

def main_collect_products_by_categories():
    """
    지정된 카테고리들의 상품을 수집하고 저장하는 메인 함수
    """
    
    # 데이터 저장 디렉토리 생성
    data_dir = "collected_data"
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    # 크롤러 인스턴스 생성
    crawler = NaverShoppingCrawler()
    
    # --- 수집하고자 하는 네이버 뷰티 카테고리 ID 리스트 ---
    # 예시: 네이버 뷰티 전체(20006491), 스킨케어(20006492), 클렌징(20006509)
    target_category_ids = {
        "뷰티_전체": "20006491",
        "스킨케어": "20006492",
        "선케어": "20006505",
        "마스크_팩": "20006513", # 파일명에 사용될 수 있도록 슬래시 대신 언더스코어
        "클렌징": "20006522",
        "메이크업": "20006536",
        "네일케어": "20006567",
        "바디케어": "20006585",
        "헤어케어": "20006612",
        "뷰티소품": "20006651",
        "향수": "20006681",
        "남성화장품": "20006688",
        "뷰티디바이스": "20006713",
        "유아동화장품": "20006719"
    }
    # ----------------------------------------------------

    # 수집 목표: 각 카테고리별로 인기순 500개 데이터
    items_per_category = 500
    page_size = 20 # 한 페이지에 20개 상품씩 가져옴 (API 기본)
    max_pages_to_fetch = (items_per_category + page_size - 1) // page_size 

    logger.info(f"🚀 총 {len(target_category_ids)}개의 카테고리에서 각각 약 {items_per_category}개 상품 수집 시작 (페이지당 {page_size}개, 최대 {max_pages_to_fetch}페이지).")

    # 수집 시작 시간 기록 (파일 이름 및 데이터 내 필드에 사용)
    current_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_dir = os.path.join(data_dir, current_timestamp)
    os.makedirs(save_dir, exist_ok=True)

    for category_name, category_id in target_category_ids.items():
        try:
            logger.info(f"\n--- 카테고리 '{category_name}' (ID: {category_id}) 상품 수집 시작 ---")
            
            products_for_category = crawler.fetch_products_api(
                display_category_id=category_id,
                sort_type="DISPLAY_CATEGORY_GENDER_AGE_GROUP_F20", # 인기순 정렬 고정
                max_pages=max_pages_to_fetch, 
                page_size=page_size,
                collection_timestamp=current_timestamp # 수집 날짜/시간 전달
            )

            if not products_for_category:
                logger.warning(f"카테고리 '{category_name}'에서 상품을 가져오지 못했습니다. 다음 카테고리로 이동합니다.")
                continue 
            
            # 수집된 상품 개수 확인 (정확히 500개가 아닐 수 있음, API 응답에 따라 달라짐)
            actual_items_collected = len(products_for_category)
            logger.info(f"✅ 카테고리 '{category_name}' 크롤링 완료! 총 {actual_items_collected}개 상품 수집.")
            
            # 파일 이름 구성
            csv_file = os.path.join(save_dir, f"{category_name}_{category_id}.csv")
            json_file = os.path.join(save_dir, f"{category_name}_{category_id}.json")

            crawler.save_to_csv(products_for_category, csv_file)
            crawler.save_to_json(products_for_category, json_file)
            
            # 수집된 상품 샘플 출력 (1개만 출력)
            print(f"\n=== 카테고리 '{category_name}' 수집 상품 샘플 (상위 1개) ===")
            for i, product in enumerate(products_for_category[:1], 1):
                print(f"\n{i}. {product.get('name', 'N/A')}")
                print(f"   브랜드: {product.get('brand', 'N/A')}")
                print(f"   가격: {product.get('price', 'N/A')}원")
                print(f"   리뷰 수: {product.get('reviewCount', 0)} (평점: {product.get('avgReviewScore', 0.0)})")
                print(f"   URL: {product.get('product_url', 'N/A')}")
                print(f"   카테고리: {', '.join(product.get('categories', []))}")
                print(f"   수집일: {product.get('collectionDate', 'N/A')}") # 추가된 필드 출력
            
            time.sleep(3) # 각 카테고리 수집 후 충분한 대기 시간
            
        except Exception as e:
            logger.error(f"카테고리 '{category_name}' 수집 중 예상치 못한 오류 발생: {e}", exc_info=True)

    logger.info("모든 지정 카테고리 상품 수집 완료!")


# 메인 실행 부분
if __name__ == "__main__":
    main_collect_products_by_categories()