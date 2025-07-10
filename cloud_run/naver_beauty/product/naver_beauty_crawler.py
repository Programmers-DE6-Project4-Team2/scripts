import time
import requests
import logging
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional
from fake_useragent import UserAgent
from gcs_uploader import upload_to_gcs
from categories import category_dir

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NaverShoppingCrawler:
    def __init__(self):
        self.session = requests.Session()
        self.ua = UserAgent()
        self.setup_session()
        self.base_api_url = "https://veco-api.shopping.naver.com/window/api/v2/graphql"
        self.operation_name = "getPagedCards"
        self.hash_value = "db693844352af4739286d5394a31659cac8a1643795d5de3bea7064ba7d7fa45"
        self.default_display_category_id = "20006491"
        self.default_sort_type = "DISPLAY_CATEGORY_GENDER_AGE_GROUP_F20"

    def setup_session(self):
        headers = {
            'User-Agent': self.ua.random,
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Origin': 'https://shopping.naver.com',
            'Referer': 'https://shopping.naver.com/',
            'Connection': 'keep-alive',
        }
        self.session.headers.update(headers)
        logger.info("세션 헤더 설정 완료.")

    def _build_graphql_payload(self, page: int, page_size: int, display_category_id: str, sort_type: str) -> Dict:
        return {
            "operationName": self.operation_name,
            "variables": {
                "isIncludeProductBenefit": False,
                "isIncludeProductDetail": True,
                "isIncludeWindowViewCount": False,
                "skip": False,
                "checkPromotionProduct": False,
                "params": {
                    "page": page,
                    "pageSize": page_size,
                    "filterSoldOut": True,
                    "useNonSubVertical": True,
                    "displayCategoryId": display_category_id,
                    "sort": sort_type
                }
            },
            "extensions": {
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": self.hash_value
                }
            }
        }

    def fetch_single_page(self, page: int, page_size: int = 20, display_category_id: Optional[str] = None,
                          sort_type: Optional[str] = None, collection_timestamp: Optional[str] = None) -> List[Dict]:
        display_category_id = display_category_id or self.default_display_category_id
        sort_type = sort_type or self.default_sort_type
        payload = self._build_graphql_payload(page, page_size, display_category_id, sort_type)

        try:
            response = self.session.post(self.base_api_url, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            card_items = data.get('data', {}).get('pagedCards', {}).get('data', [])
            return [self._parse_product_card(card, collection_timestamp) for card in card_items if self._parse_product_card(card, collection_timestamp)]
        except Exception as e:
            logger.error(f"페이지 {page} 수집 실패: {e}", exc_info=True)
            return []

    def fetch_products_api(self, max_pages: int, page_size: int = 20, display_category_id: Optional[str] = None,
                           sort_type: Optional[str] = None, collection_timestamp: Optional[str] = None) -> List[Dict]:
        display_category_id = display_category_id or self.default_display_category_id
        sort_type = sort_type or self.default_sort_type
        all_products = []
        for page in range(1, max_pages + 1):
            products = self.fetch_single_page(page, page_size, display_category_id, sort_type, collection_timestamp)
            if not products:
                logger.info(f"페이지 {page}에서 더 이상 상품 없음. 수집 종료.")
                break
            all_products.extend(products)
            time.sleep(2.0)
        return all_products

    def _parse_product_card(self, card: Dict, collection_timestamp: Optional[str] = None) -> Optional[Dict]:
        product = card.get('data', {}).get('product')
        if not isinstance(product, dict) or not product:
            return None

        product_id = product.get('id')
        brand = (product.get('brand') or {}).get('name', 'N/A')
        price = product.get('salePrice', product.get('originalPrice', 'N/A'))
        image_url = product.get("representativeImageUrl") or next((img.get("imageUrl") for img in product.get("images", []) if img.get("imageUrl")), "N/A")
        categories = self.extract_category_names(product)
        sub_vertical = product.get('channel', {}).get('subVertical')
        product_url = f"https://shopping.naver.com/window-products/{sub_vertical.lower()}/{product_id}" if sub_vertical and product_id else 'N/A'

        parsed = {
            "product_id": product_id,
            "name": product.get('name', 'N/A'),
            "brand": brand,
            "price": price,
            "representativeImageUrl": image_url,
            "reviewCount": product.get('totalReviewCount', 0),
            "avgReviewScore": product.get('averageReviewScore', 0.0),
            "product_url": product_url,
            "categories": categories,
            "channelName": product.get('channel', {}).get('name', 'N/A'),
            "collectionDate": collection_timestamp
        }
        return parsed

    def extract_category_names(self, product: dict) -> List[str]:
        names = [c.get('name') for c in product.get('categories', []) if c.get('name')]
        if not names and product.get('productCategoryName'):
            names = [product.get('productCategoryName')]
        return names

    def save_and_upload(self, data: List[Dict], category_name: str, timestamp: str, bucket_name: str):
        if not data:
            logger.warning(f"'{category_name}' 저장할 데이터가 없습니다.")
            return
        try:
            df = pd.DataFrame(data)
            blob_path = f"raw-data/naver/{category_name}/product/{timestamp}.csv"

            df_bytes = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
            upload_to_gcs(bucket_name, df_bytes, blob_path, content_type="text/csv", from_bytes=True)
            logger.info(f"✅ GCS 업로드 완료: {blob_path}")
        except Exception as e:
            logger.error(f"GCS 업로드 중 오류 발생: {e}", exc_info=True)


# # ✅ CLI 인자 기반으로 실행되는 수집 함수(단일 카테고리 수집(직렬))
def collect_product(bucket_name: str, category_name: str):
    if category_name not in category_dir:
        logger.error(f"❌ 존재하지 않는 카테고리: {category_name}")
        return

    category_id = category_dir[category_name]["id"]
    crawler = NaverShoppingCrawler()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    logger.info(f"\n--- 카테고리 '{category_name}' 수집 시작 ---")
    try:
        products = crawler.fetch_products_api(
            display_category_id=category_id,
            sort_type="DISPLAY_CATEGORY_GENDER_AGE_GROUP_F20",
            max_pages=25,
            page_size=20,
            collection_timestamp=timestamp
        )

        if not products:
            logger.warning(f"⚠️ {category_name} 상품 없음")
        else:
            crawler.save_and_upload(products, category_name, timestamp, bucket_name)
            logger.info(f"\n📦 총 수집된 상품 수: {len(products)}개")
            logger.info(f"\n📌 '{category_name}' 수집 샘플: {products[0]['name']} ({products[0]['price']}원), 리뷰수: {products[0]['reviewCount']}, 평점: {products[0]['avgReviewScore']}")
    except Exception as e:
        logger.error(f"❌ 오류 발생: {e}", exc_info=True)

