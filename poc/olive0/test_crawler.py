#!/usr/bin/env python3
"""
올리브영 사이트 구조 분석용 테스트 스크립트
"""
from oliveyoung_crawler import OliveYoungCrawler
from bs4 import BeautifulSoup
import time

def test_oliveyoung_structure():
    """올리브영 사이트 구조 분석"""
    crawler = OliveYoungCrawler(headless=False)  # 브라우저 보이게 설정
    
    try:
        # 올리브영 스킨/토너 카테고리 URL
        test_url = "https://www.oliveyoung.co.kr/store/display/getMCategoryList.do?dispCatNo=1000001000100130001"
        
        print("올리브영 페이지 로딩 중...")
        if crawler.get_page(test_url, wait_time=5):
            print("페이지 로딩 성공")
            
            # HTML 구조 저장
            with open('oliveyoung_html.html', 'w', encoding='utf-8') as f:
                f.write(crawler.driver.page_source)
            print("HTML 구조가 oliveyoung_html.html에 저장되었습니다.")
            
            # BeautifulSoup으로 파싱
            soup = BeautifulSoup(crawler.driver.page_source, 'html.parser')
            
            # 상품 관련 클래스 찾기
            print("\n=== 상품 관련 클래스 분석 ===")
            
            # 일반적인 상품 컨테이너 클래스명들 검색
            possible_selectors = [
                'div[class*="item"]',
                'div[class*="product"]', 
                'div[class*="prd"]',
                'li[class*="item"]',
                'li[class*="product"]',
                'li[class*="prd"]'
            ]
            
            for selector in possible_selectors:
                elements = soup.select(selector)
                if elements and len(elements) > 5:  # 5개 이상 발견되면 상품 리스트일 가능성
                    print(f"발견: {selector} - {len(elements)}개")
                    if elements:
                        print(f"첫번째 요소 클래스: {elements[0].get('class')}")
            
            print("\n페이지 제목:", soup.title.string if soup.title else "제목 없음")
            
            # 5초 대기 (수동으로 페이지 확인 가능)
            print("\n5초 후 브라우저를 종료합니다...")
            time.sleep(5)
            
        else:
            print("페이지 로딩 실패")
            
    except Exception as e:
        print(f"오류 발생: {e}")
        
    finally:
        crawler.close()

if __name__ == "__main__":
    test_oliveyoung_structure()