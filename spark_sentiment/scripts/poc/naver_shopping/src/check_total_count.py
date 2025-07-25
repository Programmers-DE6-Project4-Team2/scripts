#!/usr/bin/env python3
"""
네이버 쇼핑 스킨케어 전체 데이터 개수 확인
"""
import json
import requests
from urllib.parse import quote
from fake_useragent import UserAgent

def check_total_products():
    """전체 상품 개수 확인"""
    
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
    
    # API URL 구성
    base_url = "https://veco-api.shopping.naver.com/window/api/v2/graphql"
    
    # 첫 페이지만 요청하여 전체 개수 확인
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
    
    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # 응답에서 전체 개수 정보 찾기
        print("=== API 응답 구조 분석 ===")
        
        if 'data' in data and 'pagedCards' in data['data']:
            paged_cards = data['data']['pagedCards']
            print(f"pagedCards 키들: {list(paged_cards.keys())}")
            
            # 전체 개수 정보 찾기
            total_count = None
            page_info = None
            
            # 가능한 키들 확인
            for key in paged_cards.keys():
                print(f"{key}: {paged_cards[key] if not isinstance(paged_cards[key], list) else f'리스트 ({len(paged_cards[key])}개)'}")
                
                if 'total' in key.lower() or 'count' in key.lower():
                    total_count = paged_cards[key]
                    print(f"🎯 전체 개수 발견: {key} = {total_count}")
                
                if 'page' in key.lower() or 'info' in key.lower():
                    page_info = paged_cards[key]
                    print(f"📄 페이지 정보: {key} = {page_info}")
            
            # 현재 페이지 데이터 개수
            current_data = paged_cards.get('data', [])
            print(f"현재 페이지 상품 수: {len(current_data)}")
            
            # 전체 응답을 JSON으로 저장하여 수동 분석
            with open('total_count_response.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print("전체 응답이 total_count_response.json에 저장되었습니다.")
            
            return total_count, len(current_data)
        
    except Exception as e:
        print(f"오류 발생: {e}")
        return None, None

def estimate_total_by_testing():
    """페이지를 증가시켜가며 전체 개수 추정"""
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
    
    base_url = "https://veco-api.shopping.naver.com/window/api/v2/graphql"
    
    print("\n=== 페이지별 테스트로 전체 개수 추정 ===")
    
    # 점진적으로 페이지를 늘려가며 테스트
    test_pages = [1, 10, 50, 100, 200, 500, 1000]
    last_valid_page = 1
    
    for page in test_pages:
        variables = {
            "isIncludeProductBenefit": False,
            "isIncludeProductDetail": False,
            "isIncludeWindowViewCount": False,
            "skip": False,
            "checkPromotionProduct": False,
            "params": {
                "page": page,
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
        
        try:
            response = session.get(url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'data' in data and 'pagedCards' in data['data']:
                    cards = data['data']['pagedCards'].get('data', [])
                    if cards:
                        print(f"페이지 {page}: ✅ 데이터 있음 ({len(cards)}개)")
                        last_valid_page = page
                    else:
                        print(f"페이지 {page}: ❌ 데이터 없음")
                        break
                else:
                    print(f"페이지 {page}: ❌ 응답 구조 오류")
                    break
            else:
                print(f"페이지 {page}: ❌ HTTP {response.status_code}")
                break
                
        except Exception as e:
            print(f"페이지 {page}: ❌ 오류 - {e}")
            break
    
    estimated_total = last_valid_page * 20
    print(f"\n🎯 추정 전체 상품 수: 약 {estimated_total:,}개 (최소 {last_valid_page}페이지 × 20개)")
    
    return last_valid_page, estimated_total

if __name__ == "__main__":
    print("네이버 쇼핑 스킨케어 전체 데이터 개수 확인 중...")
    
    # 방법 1: API 응답에서 전체 개수 정보 찾기
    total_count, current_count = check_total_products()
    
    # 방법 2: 페이지 테스트로 추정
    max_page, estimated_total = estimate_total_by_testing()
    
    print(f"\n=== 최종 결과 ===")
    if total_count:
        print(f"API에서 제공하는 전체 개수: {total_count:,}개")
    print(f"테스트 기반 추정 개수: 약 {estimated_total:,}개")
    print(f"최대 유효 페이지: {max_page}페이지")