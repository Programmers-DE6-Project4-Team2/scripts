#!/usr/bin/env python3
"""
네이버 쇼핑 정렬 옵션별 데이터 확인
"""
import json
import requests
from urllib.parse import quote
from fake_useragent import UserAgent
import time

def test_sort_options():
    """다양한 정렬 옵션으로 데이터 확인"""
    
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
    
    # 다양한 정렬 옵션 테스트
    sort_options = [
        "POPULARITY",      # 인기순 (현재 사용)
        "PRICE_LOW",       # 낮은 가격순
        "PRICE_HIGH",      # 높은 가격순
        "REVIEW",          # 리뷰 많은순
        "RECENT",          # 최신순
        "SALE",            # 할인률순
        "RATING"           # 평점순
    ]
    
    results = {}
    
    for sort_option in sort_options:
        print(f"\n=== {sort_option} 정렬 테스트 ===")
        
        variables = {
            "isIncludeProductBenefit": False,
            "isIncludeProductDetail": False,
            "isIncludeWindowViewCount": False,
            "skip": False,
            "checkPromotionProduct": False,
            "params": {
                "page": 1,
                "pageSize": 20,
                "sort": sort_option,
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
                    paged_cards = data['data']['pagedCards']
                    cards = paged_cards.get('data', [])
                    has_more = paged_cards.get('hasMore', False)
                    
                    print(f"  ✅ {sort_option}: {len(cards)}개 상품, hasMore: {has_more}")
                    
                    # 상위 3개 상품명 출력
                    for i, card in enumerate(cards[:3], 1):
                        if 'data' in card and 'product' in card['data']:
                            product = card['data']['product']
                            name = product.get('name', 'N/A')
                            price = product.get('pcDiscountedSalePrice', product.get('salePrice', 'N/A'))
                            print(f"    {i}. {name[:50]}... ({price}원)")
                    
                    # 끝 페이지 테스트 (100페이지로)
                    if has_more:
                        max_page = test_max_page(session, base_url, sort_option)
                        results[sort_option] = {
                            'max_page': max_page,
                            'estimated_total': max_page * 20,
                            'has_more': has_more
                        }
                    else:
                        results[sort_option] = {
                            'max_page': 1,
                            'estimated_total': len(cards),
                            'has_more': False
                        }
                        
                else:
                    print(f"  ❌ {sort_option}: 응답 구조 오류")
                    results[sort_option] = {'error': '응답 구조 오류'}
            else:
                print(f"  ❌ {sort_option}: HTTP {response.status_code}")
                results[sort_option] = {'error': f'HTTP {response.status_code}'}
                
        except Exception as e:
            print(f"  ❌ {sort_option}: 오류 - {e}")
            results[sort_option] = {'error': str(e)}
        
        time.sleep(1)  # API 호출 간격
    
    return results

def test_max_page(session, base_url, sort_option, test_pages=[50, 100, 200, 500]):
    """특정 정렬 옵션의 최대 페이지 테스트"""
    print(f"    📄 {sort_option} 최대 페이지 테스트...")
    
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
                "sort": sort_option,
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
                        print(f"      페이지 {page}: ✅ ({len(cards)}개)")
                        last_valid_page = page
                    else:
                        print(f"      페이지 {page}: ❌ 데이터 없음")
                        break
                else:
                    print(f"      페이지 {page}: ❌ 구조 오류")
                    break
            else:
                print(f"      페이지 {page}: ❌ HTTP {response.status_code}")
                break
                
        except Exception as e:
            print(f"      페이지 {page}: ❌ {e}")
            break
        
        time.sleep(0.5)
    
    print(f"    📊 {sort_option} 최대 유효 페이지: {last_valid_page}")
    return last_valid_page

def check_different_categories():
    """다른 뷰티 하위 카테고리도 확인"""
    print("\n" + "="*60)
    print("🔍 다른 뷰티 하위 카테고리 확인")
    print("="*60)
    
    # 추정되는 다른 카테고리 ID들
    beauty_categories = {
        "20032470": "스킨케어 (현재)",
        "20032480": "메이크업 (추정)",
        "20032490": "바디케어 (추정)",
        "20032500": "헤어케어 (추정)",
        "20032510": "향수/디퓨저 (추정)"
    }
    
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
    
    for menu_id, category_name in beauty_categories.items():
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
                "menuId": menu_id
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
                        print(f"✅ {category_name}: {len(cards)}개 상품 발견")
                        # 첫 번째 상품명 출력
                        if cards and 'data' in cards[0] and 'product' in cards[0]['data']:
                            first_product = cards[0]['data']['product'].get('name', '')
                            print(f"   예시: {first_product[:40]}...")
                    else:
                        print(f"❌ {category_name}: 데이터 없음")
                else:
                    print(f"❌ {category_name}: 응답 구조 오류")
            else:
                print(f"❌ {category_name}: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"❌ {category_name}: 오류 - {e}")
        
        time.sleep(0.5)

if __name__ == "__main__":
    print("🔍 네이버 쇼핑 정렬 옵션별 데이터 분석")
    
    # 1. 정렬 옵션별 테스트
    results = test_sort_options()
    
    # 2. 다른 카테고리 확인
    check_different_categories()
    
    # 3. 최종 결과 요약
    print("\n" + "="*60)
    print("📊 최종 분석 결과")
    print("="*60)
    
    total_unique_products = 0
    
    for sort_option, result in results.items():
        if 'estimated_total' in result:
            estimated = result['estimated_total']
            print(f"{sort_option:12}: 최대 약 {estimated:,}개 상품")
            
            # 각 정렬의 최대값 중 최대값을 전체 추정치로 사용
            if estimated > total_unique_products:
                total_unique_products = estimated
    
    print(f"\n🎯 전체 추정 상품 수: 약 {total_unique_products:,}개")
    print("💡 결론: 네이버는 정렬별로 일정 개수만 제공하는 것으로 보임")