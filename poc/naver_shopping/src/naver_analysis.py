#!/usr/bin/env python3
"""
네이버 쇼핑 사이트 구조 분석 스크립트
"""
import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from fake_useragent import UserAgent
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NaverShoppingAnalyzer:
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.driver = None
        self.wait = None
        self.ua = UserAgent()
        self.setup_driver()
        
    def setup_driver(self):
        """Chrome WebDriver 설정"""
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument('--headless')
        
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument(f'--user-agent={self.ua.random}')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
        except Exception as e:
            logger.error(f"Chrome WebDriver 초기화 실패: {e}")
            self.driver = webdriver.Chrome(options=chrome_options)
            
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.wait = WebDriverWait(self.driver, 10)
        logger.info("Chrome WebDriver 초기화 완료")
    
    def analyze_naver_shopping(self, url: str):
        """네이버 쇼핑 페이지 분석"""
        logger.info("네이버 쇼핑 페이지 로딩 중...")
        
        try:
            self.driver.get(url)
            time.sleep(5)  # 페이지 로딩 대기
            
            # 페이지 제목 확인
            print(f"페이지 제목: {self.driver.title}")
            
            # 현재 URL 확인 (리다이렉트 여부)
            current_url = self.driver.current_url
            print(f"현재 URL: {current_url}")
            
            # HTML 저장
            with open('naver_shopping_html.html', 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            print("HTML이 naver_shopping_html.html에 저장되었습니다.")
            
            # 상품 관련 요소 찾기
            self.find_product_elements()
            
            # 무한 스크롤 테스트
            self.test_infinite_scroll()
            
            # Network 요청 모니터링 (JavaScript로)
            self.monitor_network_requests()
            
        except Exception as e:
            logger.error(f"분석 중 오류 발생: {e}")
        
        finally:
            # 10초 대기 후 종료
            print("10초 후 브라우저를 종료합니다...")
            time.sleep(10)
    
    def find_product_elements(self):
        """상품 관련 HTML 요소 찾기"""
        print("\n=== 상품 관련 요소 분석 ===")
        
        # 일반적인 상품 관련 선택자들
        possible_selectors = [
            'div[class*="product"]',
            'div[class*="item"]',
            'li[class*="product"]',
            'li[class*="item"]',
            'article[class*="product"]',
            '[data-testid*="product"]',
            '[class*="card"]',
            '[class*="goods"]'
        ]
        
        for selector in possible_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements and len(elements) > 5:  # 5개 이상이면 상품 리스트일 가능성
                    print(f"발견: {selector} - {len(elements)}개")
                    if elements:
                        first_element = elements[0]
                        print(f"  첫번째 요소 클래스: {first_element.get_attribute('class')}")
                        print(f"  텍스트 일부: {first_element.text[:100]}...")
            except Exception as e:
                continue
    
    def test_infinite_scroll(self):
        """무한 스크롤 테스트"""
        print("\n=== 무한 스크롤 테스트 ===")
        
        # 초기 페이지 높이
        initial_height = self.driver.execute_script("return document.body.scrollHeight")
        print(f"초기 페이지 높이: {initial_height}")
        
        # 스크롤 다운
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        
        # 새로운 페이지 높이
        new_height = self.driver.execute_script("return document.body.scrollHeight")
        print(f"스크롤 후 페이지 높이: {new_height}")
        
        if new_height > initial_height:
            print("✅ 무한 스크롤 동작 확인!")
        else:
            print("❌ 무한 스크롤 동작 안함")
    
    def monitor_network_requests(self):
        """Network 요청 모니터링"""
        print("\n=== Network 요청 모니터링 ===")
        
        # JavaScript로 fetch 및 XMLHttpRequest 모니터링
        monitor_script = """
        window.networkRequests = [];
        
        // fetch 모니터링
        const originalFetch = window.fetch;
        window.fetch = function(...args) {
            window.networkRequests.push({
                type: 'fetch',
                url: args[0],
                method: args[1] ? args[1].method || 'GET' : 'GET',
                timestamp: new Date().toISOString()
            });
            return originalFetch.apply(this, args);
        };
        
        // XMLHttpRequest 모니터링
        const originalXHR = window.XMLHttpRequest;
        window.XMLHttpRequest = function() {
            const xhr = new originalXHR();
            const originalOpen = xhr.open;
            xhr.open = function(method, url) {
                window.networkRequests.push({
                    type: 'xhr',
                    url: url,
                    method: method,
                    timestamp: new Date().toISOString()
                });
                return originalOpen.apply(this, arguments);
            };
            return xhr;
        };
        """
        
        self.driver.execute_script(monitor_script)
        
        # 스크롤하여 추가 요청 발생시키기
        for i in range(3):
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
        
        # 캡처된 요청들 확인
        requests = self.driver.execute_script("return window.networkRequests || [];")
        
        print(f"캡처된 네트워크 요청: {len(requests)}개")
        
        # API 요청으로 보이는 것들 필터링
        api_requests = []
        for req in requests:
            url = req.get('url', '')
            if any(keyword in url.lower() for keyword in ['api', 'ajax', 'json', 'search', 'category', 'product']):
                api_requests.append(req)
        
        print(f"API 관련 요청: {len(api_requests)}개")
        
        # 중요한 API 요청들 출력
        for req in api_requests[:10]:  # 상위 10개만
            print(f"  - {req['method']} {req['url']}")
        
        # 요청 데이터를 JSON으로 저장
        with open('naver_network_requests.json', 'w', encoding='utf-8') as f:
            json.dump(requests, f, ensure_ascii=False, indent=2)
        print("네트워크 요청이 naver_network_requests.json에 저장되었습니다.")
    
    def close(self):
        """브라우저 종료"""
        if self.driver:
            self.driver.quit()
            logger.info("브라우저가 종료되었습니다.")

def main():
    """메인 함수"""
    analyzer = NaverShoppingAnalyzer(headless=False)
    
    try:
        # 네이버 쇼핑 뷰티-스킨케어 카테고리
        url = "https://shopping.naver.com/window/beauty/category?filterSoldOut=true&menu=20032470"
        analyzer.analyze_naver_shopping(url)
        
    except Exception as e:
        print(f"오류 발생: {e}")
        
    finally:
        analyzer.close()

if __name__ == "__main__":
    main()