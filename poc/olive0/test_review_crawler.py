#!/usr/bin/env python3
"""
리뷰 크롤링 테스트
"""
from oliveyoung_crawler import OliveYoungCrawler
from bs4 import BeautifulSoup
import time

def test_review_structure():
    """상품 상세 페이지 및 리뷰 구조 분석"""
    crawler = OliveYoungCrawler(headless=False)  # 브라우저 보이게 설정
    
    try:
        # 테스트할 상품 URL (위에서 크롤링한 첫 번째 상품)
        product_url = "https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo=A000000170266&dispCatNo=1000001000100130001"
        
        print("상품 상세 페이지 로딩 중...")
        if crawler.get_page(product_url, wait_time=5):
            print("페이지 로딩 성공")
            
            # 페이지 제목 확인
            soup = BeautifulSoup(crawler.driver.page_source, 'html.parser')
            print("페이지 제목:", soup.title.string if soup.title else "제목 없음")
            
            # 리뷰 관련 요소 찾기
            print("\n=== 리뷰 관련 요소 분석 ===")
            
            # 리뷰 탭 또는 버튼 찾기
            review_selectors = [
                'a[href*="review"]',
                'button[class*="review"]',
                'div[class*="review"]',
                'tab[class*="review"]',
                '.review',
                '#review'
            ]
            
            for selector in review_selectors:
                elements = soup.select(selector)
                if elements:
                    print(f"발견: {selector} - {len(elements)}개")
                    for elem in elements[:3]:  # 처음 3개만 출력
                        print(f"  - {elem.name}: {elem.get('class', [])} | {elem.get_text()[:50]}...")
            
            # 리뷰 탭 클릭 시도
            try:
                # 여러 가능한 선택자 시도
                review_tab_selectors = [
                    "a[href*='review']",
                    "button[onclick*='review']",
                    ".tabItem[data-tab='review']",
                    "#review-tab",
                    "a[data-tab='review']"
                ]
                
                for selector in review_tab_selectors:
                    try:
                        review_tab = crawler.driver.find_element("css selector", selector)
                        print(f"\n리뷰 탭 발견: {selector}")
                        print(f"탭 텍스트: {review_tab.text}")
                        
                        # 탭 클릭
                        crawler.driver.execute_script("arguments[0].click();", review_tab)
                        time.sleep(3)
                        print("리뷰 탭 클릭 성공")
                        break
                    except:
                        continue
                
            except Exception as e:
                print(f"리뷰 탭 클릭 실패: {e}")
            
            # 현재 페이지의 리뷰 관련 클래스 저장
            with open('product_detail_html.html', 'w', encoding='utf-8') as f:
                f.write(crawler.driver.page_source)
            print("\n상품 상세 페이지 HTML이 product_detail_html.html에 저장되었습니다.")
            
            # 10초 대기 (수동으로 페이지 확인 가능)
            print("\n10초 후 브라우저를 종료합니다...")
            time.sleep(10)
            
        else:
            print("페이지 로딩 실패")
            
    except Exception as e:
        print(f"오류 발생: {e}")
        
    finally:
        crawler.close()

if __name__ == "__main__":
    test_review_structure()