#!/usr/bin/env python3
"""
업데이트된 올리브영 크롤러 테스트
"""
from oliveyoung_crawler import OliveYoungCrawler
import json

def test_updated_crawler():
    """업데이트된 크롤러 테스트"""
    crawler = OliveYoungCrawler(headless=True)
    
    try:
        # 올리브영 스킨/토너 카테고리 URL (1페이지만 테스트)
        category_url = "https://www.oliveyoung.co.kr/store/display/getMCategoryList.do?dispCatNo=1000001000100130001"
        
        print("상품 목록 크롤링 테스트 시작...")
        products = crawler.extract_product_list(category_url, max_pages=1)
        
        print(f"\n크롤링 결과: {len(products)}개 상품")
        
        # 첫 3개 상품 출력
        for i, product in enumerate(products[:3], 1):
            print(f"\n=== 상품 {i} ===")
            print(f"브랜드: {product.get('brand', 'N/A')}")
            print(f"이름: {product.get('name', 'N/A')}")
            print(f"가격: {product.get('price', 'N/A')}원")
            print(f"평점: {product.get('rating', 'N/A')}/5.0")
            print(f"리뷰수: {product.get('review_count', 'N/A')}")
            print(f"URL: {product.get('url', 'N/A')[:80]}...")
        
        # JSON으로 저장
        if products:
            with open('test_products.json', 'w', encoding='utf-8') as f:
                json.dump(products[:5], f, ensure_ascii=False, indent=2)
            print(f"\n상위 5개 상품이 test_products.json에 저장되었습니다.")
        
    except Exception as e:
        print(f"오류 발생: {e}")
        
    finally:
        crawler.close()

if __name__ == "__main__":
    test_updated_crawler()