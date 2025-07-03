#!/usr/bin/env python3
"""
올리브영 크롤러 메인 실행 스크립트
"""
import os
from datetime import datetime
from oliveyoung_crawler import OliveYoungCrawler
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    # 데이터 저장 디렉토리 생성
    data_dir = "data"
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    # 크롤러 초기화
    crawler = OliveYoungCrawler(headless=True)
    
    try:
        # 올리브영 스킨/토너 카테고리 URL (실제 URL로 수정 필요)
        category_url = "https://www.oliveyoung.co.kr/store/display/getMCategoryList.do?dispCatNo=1000001000100130001"
        
        logger.info("상품 목록 크롤링 시작...")
        products = crawler.extract_product_list(category_url, max_pages=3)
        
        if not products:
            logger.error("상품 목록을 가져올 수 없습니다.")
            return
        
        # 타임스탬프 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 상품 목록 저장
        products_file = f"{data_dir}/products_{timestamp}.csv"
        crawler.save_to_csv(products, products_file)
        
        products_json_file = f"{data_dir}/products_{timestamp}.json"
        crawler.save_to_json(products, products_json_file)
        
        # 간단한 테스트를 위해 리뷰 크롤링 부분은 주석 처리
        logger.info("상품 목록 크롤링 완료. 리뷰 크롤링은 별도 테스트에서...")
        detailed_products = []
        all_reviews = []
        
        # 상세 정보가 포함된 상품 저장
        if detailed_products:
            detailed_file = f"{data_dir}/detailed_products_{timestamp}.csv"
            crawler.save_to_csv(detailed_products, detailed_file)
            
            detailed_json_file = f"{data_dir}/detailed_products_{timestamp}.json"
            crawler.save_to_json(detailed_products, detailed_json_file)
        
        # 리뷰 저장
        if all_reviews:
            reviews_file = f"{data_dir}/reviews_{timestamp}.csv"
            crawler.save_to_csv(all_reviews, reviews_file)
            
            reviews_json_file = f"{data_dir}/reviews_{timestamp}.json"
            crawler.save_to_json(all_reviews, reviews_json_file)
        
        logger.info("크롤링 완료!")
        logger.info(f"총 상품 수: {len(products)}")
        logger.info(f"상세 정보 수집 상품 수: {len(detailed_products)}")
        logger.info(f"총 리뷰 수: {len(all_reviews)}")
        
    except Exception as e:
        logger.error(f"크롤링 중 오류 발생: {e}")
        
    finally:
        # 브라우저 종료
        crawler.close()

if __name__ == "__main__":
    main()