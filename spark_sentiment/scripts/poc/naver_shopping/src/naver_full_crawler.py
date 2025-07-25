#!/usr/bin/env python3
"""
네이버 쇼핑 스킨케어 전체 데이터 수집
"""
from naver_shopping_crawler import NaverShoppingCrawler
from datetime import datetime
import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def collect_all_skincare_products():
    """스킨케어 전체 상품 수집"""
    
    # 데이터 저장 디렉토리 생성
    data_dir = "data"
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    # 크롤러 초기화
    crawler = NaverShoppingCrawler()
    
    try:
        logger.info("🚀 네이버 쇼핑 스킨케어 전체 데이터 수집 시작...")
        
        # 최대 50페이지까지 수집 (약 1,000개 상품)
        all_products = []
        batch_size = 10  # 10페이지씩 배치 처리
        
        for start_page in range(1, 51, batch_size):
            end_page = min(start_page + batch_size - 1, 50)
            
            logger.info(f"📦 배치 수집: {start_page}페이지 ~ {end_page}페이지")
            
            # 배치별 상품 수집
            batch_products = []
            for page in range(start_page, end_page + 1):
                try:
                    page_products = crawler.fetch_single_page(page)
                    if page_products:
                        batch_products.extend(page_products)
                        logger.info(f"  ✅ 페이지 {page}: {len(page_products)}개 상품")
                    else:
                        logger.warning(f"  ❌ 페이지 {page}: 데이터 없음 (수집 종료)")
                        break
                        
                except Exception as e:
                    logger.error(f"  ❌ 페이지 {page} 오류: {e}")
                    break
            
            if not batch_products:
                logger.info("더 이상 수집할 데이터가 없습니다.")
                break
            
            # 배치 결과를 전체 리스트에 추가
            all_products.extend(batch_products)
            
            # 중간 저장 (데이터 유실 방지)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            temp_file = f"{data_dir}/naver_skincare_temp_{timestamp}.json"
            crawler.save_to_json(all_products, temp_file)
            
            logger.info(f"📊 현재까지 수집: {len(all_products)}개 상품 (중간저장: {temp_file})")
            
            # 너무 빠른 요청 방지를 위한 딜레이
            import time
            time.sleep(2)
        
        if not all_products:
            logger.error("수집된 데이터가 없습니다.")
            return
        
        # 최종 저장
        final_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # CSV 저장
        csv_file = f"{data_dir}/naver_skincare_all_{final_timestamp}.csv"
        crawler.save_to_csv(all_products, csv_file)
        
        # JSON 저장
        json_file = f"{data_dir}/naver_skincare_all_{final_timestamp}.json"
        crawler.save_to_json(all_products, json_file)
        
        # 결과 통계
        logger.info("🎉 전체 데이터 수집 완료!")
        logger.info(f"📈 총 수집 상품: {len(all_products):,}개")
        logger.info(f"💾 저장 파일: {csv_file}, {json_file}")
        
        # 브랜드별 통계
        brands = {}
        price_ranges = {"1만원 미만": 0, "1-3만원": 0, "3-5만원": 0, "5만원 이상": 0}
        
        for product in all_products:
            # 브랜드 통계
            brand = product.get('brand', 'Unknown')
            brands[brand] = brands.get(brand, 0) + 1
            
            # 가격대 통계
            try:
                price = int(product.get('price', 0))
                if price < 10000:
                    price_ranges["1만원 미만"] += 1
                elif price < 30000:
                    price_ranges["1-3만원"] += 1
                elif price < 50000:
                    price_ranges["3-5만원"] += 1
                else:
                    price_ranges["5만원 이상"] += 1
            except:
                pass
        
        # 상위 브랜드 출력
        top_brands = sorted(brands.items(), key=lambda x: x[1], reverse=True)[:10]
        
        print("\n" + "="*50)
        print("📊 수집 결과 통계")
        print("="*50)
        print(f"총 상품 수: {len(all_products):,}개")
        print(f"브랜드 수: {len(brands)}개")
        
        print("\n🏆 상위 브랜드 (상품 수):")
        for brand, count in top_brands:
            print(f"  {brand}: {count}개")
        
        print("\n💰 가격대별 분포:")
        for price_range, count in price_ranges.items():
            percentage = (count / len(all_products)) * 100
            print(f"  {price_range}: {count}개 ({percentage:.1f}%)")
        
    except Exception as e:
        logger.error(f"수집 중 오류 발생: {e}")

# NaverShoppingCrawler 클래스에 단일 페이지 수집 메서드 추가
def fetch_single_page(self, page: int) -> list:
    """단일 페이지 상품 수집"""
    try:
        url = self.build_api_url(page)
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        if 'data' in data and 'pagedCards' in data['data']:
            cards = data['data']['pagedCards'].get('data', [])
            
            products = []
            for card in cards:
                product = self.parse_product_card(card)
                if product:
                    products.append(product)
            
            return products
        return []
        
    except Exception as e:
        logging.getLogger(__name__).error(f"페이지 {page} 수집 오류: {e}")
        return []

# 메서드를 클래스에 동적으로 추가
NaverShoppingCrawler.fetch_single_page = fetch_single_page

if __name__ == "__main__":
    collect_all_skincare_products()