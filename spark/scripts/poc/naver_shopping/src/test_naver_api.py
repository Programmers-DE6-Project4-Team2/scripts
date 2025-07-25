#!/usr/bin/env python3
"""
네이버 쇼핑 API 응답 구조 테스트
"""
import json
import requests
from urllib.parse import quote
from fake_useragent import UserAgent

def test_naver_api():
    """네이버 쇼핑 API 테스트"""
    
    # 세션 설정
    session = requests.Session()
    ua = UserAgent()
    
    headers = {
        'User-Agent': ua.random,
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Origin': 'https://shopping.naver.com',
        'Referer': 'https://shopping.naver.com/',
    }
    session.headers.update(headers)
    
    # API URL 구성 (실제 분석에서 얻은 것)
    base_url = "https://veco-api.shopping.naver.com/window/api/v2/graphql"
    
    variables = {
        "isIncludeProductBenefit": False,
        "isIncludeProductDetail": False,
        "isIncludeWindowViewCount": False,
        "skip": False,
        "checkPromotionProduct": False,
        "params": {
            "page": 1,
            "pageSize": 20,
            "sort": "POPULARITY",
            "subVertical": "BEAUTY",
            "filterSoldOut": True,
            "menuId": "20032470"
        }
    }
    
    extensions = {
        "persistedQuery": {
            "version": 1,
            "sha256Hash": "db693844352af4739286d5394a31659cac8a1643795d5de3bea7064ba7d7fa45"
        }
    }
    
    variables_encoded = quote(json.dumps(variables, separators=(',', ':')))
    extensions_encoded = quote(json.dumps(extensions, separators=(',', ':')))
    
    url = f"{base_url}?operationName=getPagedCards&variables={variables_encoded}&extensions={extensions_encoded}"
    
    print("API URL 생성 완료")
    print(f"URL 길이: {len(url)}")
    
    try:
        print("API 호출 중...")
        response = session.get(url, timeout=30)
        
        print(f"응답 상태 코드: {response.status_code}")
        print(f"응답 헤더: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            
            # 응답 구조 저장
            with open('naver_api_response.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print("API 응답이 naver_api_response.json에 저장되었습니다.")
            
            # 응답 구조 분석
            print("\n=== 응답 구조 분석 ===")
            print(f"최상위 키들: {list(data.keys())}")
            
            if 'data' in data:
                print(f"data 키들: {list(data['data'].keys())}")
                
                # 가능한 경로들 탐색
                possible_paths = [
                    ['data', 'category', 'cards'],
                    ['data', 'window', 'cards'],
                    ['data', 'products'],
                    ['data', 'items'],
                    ['data', 'results']
                ]
                
                for path in possible_paths:
                    try:
                        current = data
                        for key in path:
                            current = current[key]
                        print(f"✅ 경로 발견: {' -> '.join(path)} ({len(current)}개 항목)")
                        
                        # 첫 번째 항목 구조 확인
                        if current and isinstance(current, list):
                            first_item = current[0]
                            print(f"   첫 번째 항목 키들: {list(first_item.keys()) if isinstance(first_item, dict) else type(first_item)}")
                        break
                    except (KeyError, TypeError):
                        continue
                else:
                    print("❌ 알려진 경로에서 상품 데이터를 찾을 수 없습니다.")
            
        else:
            print(f"API 호출 실패: {response.status_code}")
            print(f"응답 내용: {response.text[:500]}")
            
    except Exception as e:
        print(f"오류 발생: {e}")

if __name__ == "__main__":
    test_naver_api()