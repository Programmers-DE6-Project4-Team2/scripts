#!/usr/bin/env python3
"""
네이버 쇼핑 크롤러 메인 실행 스크립트
"""
import os
import sys
from datetime import datetime
from naver_shopping_crawler import NaverShoppingCrawler
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """메인 함수"""
    print("🛒 네이버 쇼핑 크롤러")
    print("=" * 40)
    
    # 데이터 저장 디렉토리 생성
    data_dir = "../data"
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    # 사용자 옵션 선택
    print("실행할 작업을 선택하세요:")
    print("1. 기본 크롤링 (100개 상품)")
    print("2. 전체 크롤링 (1,000개 상품)")
    print("3. 사이트 구조 분석")
    print("4. API 응답 테스트")
    print("5. 정렬 옵션 분석")
    
    choice = input("\n선택 (1-5): ").strip()
    
    if choice == "1":
        basic_crawling(data_dir)
    elif choice == "2":
        full_crawling(data_dir)
    elif choice == "3":
        site_analysis()
    elif choice == "4":
        api_test()
    elif choice == "5":
        sort_analysis()
    else:
        print("잘못된 선택입니다.")

def basic_crawling(data_dir):
    """기본 크롤링 (100개 상품)"""
    print("\n🚀 기본 크롤링 시작 (5페이지, 100개 상품)")
    
    crawler = NaverShoppingCrawler()
    
    try:
        # 5페이지 크롤링
        products = crawler.fetch_products_api(max_pages=5)
        
        if not products:
            logger.error("상품 목록을 가져올 수 없습니다.")
            return
        
        # 타임스탬프 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 데이터 저장
        csv_file = f"{data_dir}/naver_basic_{timestamp}.csv"
        json_file = f"{data_dir}/naver_basic_{timestamp}.json"
        
        crawler.save_to_csv(products, csv_file)
        crawler.save_to_json(products, json_file)
        
        print(f"✅ 크롤링 완료!")
        print(f"📊 수집 상품: {len(products)}개")
        print(f"💾 저장 위치: {csv_file}, {json_file}")
        
        # 상위 3개 상품 미리보기
        print("\n📦 수집된 상품 미리보기:")
        for i, product in enumerate(products[:3], 1):
            print(f"{i}. {product.get('name', 'N/A')[:50]}...")
            print(f"   💰 {product.get('price', 'N/A')}원 ⭐ {product.get('rating', 'N/A')}")
        
    except Exception as e:
        logger.error(f"크롤링 중 오류 발생: {e}")

def full_crawling(data_dir):
    """전체 크롤링 (1,000개 상품)"""
    print("\n🔥 전체 크롤링 시작 (50페이지, 1,000개 상품)")
    print("⏰ 예상 소요시간: 약 5분")
    
    confirm = input("계속하시겠습니까? (y/N): ").strip().lower()
    if confirm != 'y':
        print("취소되었습니다.")
        return
    
    # naver_full_crawler.py 실행
    os.system("python naver_full_crawler.py")

def site_analysis():
    """사이트 구조 분석"""
    print("\n🔍 네이버 쇼핑 사이트 구조 분석")
    print("브라우저가 열리고 페이지를 분석합니다...")
    
    # naver_analysis.py 실행
    os.system("python naver_analysis.py")

def api_test():
    """API 응답 테스트"""
    print("\n🧪 네이버 쇼핑 API 응답 구조 테스트")
    
    # test_naver_api.py 실행
    os.system("python test_naver_api.py")

def sort_analysis():
    """정렬 옵션 분석"""
    print("\n📈 다양한 정렬 옵션 분석")
    print("인기순, 리뷰순, 최신순 등을 테스트합니다...")
    
    # check_sort_options.py 실행
    os.system("python check_sort_options.py")

if __name__ == "__main__":
    main()