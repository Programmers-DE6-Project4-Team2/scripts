#!/usr/bin/env python3
"""
무신사 API 응답 구조 디버깅 스크립트
"""
import requests
import json
from fake_useragent import UserAgent

def debug_musinsa_api():
    """무신사 API 응답 구조 분석"""
    ua = UserAgent()
    
    headers = {
        'User-Agent': ua.random,
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Referer': 'https://www.musinsa.com/main/beauty/ranking',
        'Origin': 'https://www.musinsa.com',
    }
    
    url = "https://api.musinsa.com/api2/hm/web/v5/pans/ranking/sections/231?storeCode=beauty&categoryCode=104001&contentsId=&gf=A&ageBand=AGE_BAND_ALL&period=REALTIME&page=1&size=40"
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # MULTICOLUMN 모듈 찾기
        modules = data['data']['modules']
        for module in modules:
            if module.get('type') == 'MULTICOLUMN' and 'items' in module:
                # 첫 번째 상품 아이템 분석
                first_item = module['items'][0]
                
                print("=== 첫 번째 상품 아이템 구조 분석 ===")
                print(json.dumps(first_item, indent=2, ensure_ascii=False))
                
                print("\n=== 주요 필드 추출 ===")
                print(f"ID: {first_item.get('id')}")
                print(f"Type: {first_item.get('type')}")
                
                info = first_item.get('info', {})
                print(f"Brand: {info.get('brandName')}")
                print(f"Product: {info.get('productName')}")
                print(f"Price: {info.get('finalPrice')}")
                print(f"Discount: {info.get('discountRatio')}")
                
                # Additional Information 분석
                additional_info = info.get('additionalInformation', [])
                print(f"\nAdditional Information ({len(additional_info)} items):")
                for i, item in enumerate(additional_info):
                    print(f"  {i+1}: {item}")
                
                # 이미지 정보 분석
                images = first_item.get('images', {})
                print(f"\nImages: {list(images.keys())}")
                for key, value in images.items():
                    print(f"  {key}: {value}")
                
                # onClick 정보 분석
                onclick = first_item.get('onClick', {})
                print(f"\nonClick URL: {onclick.get('url')}")
                
                # 전체 키 구조 출력
                print(f"\n=== 전체 아이템 키 구조 ===")
                def print_keys(obj, prefix=""):
                    if isinstance(obj, dict):
                        for key, value in obj.items():
                            if isinstance(value, dict):
                                print(f"{prefix}{key}/ (dict)")
                                print_keys(value, prefix + "  ")
                            elif isinstance(value, list):
                                print(f"{prefix}{key}[] (list, {len(value)} items)")
                                if value and isinstance(value[0], dict):
                                    print_keys(value[0], prefix + "  [0].")
                            else:
                                print(f"{prefix}{key}: {type(value).__name__}")
                
                print_keys(first_item)
                break
        
    except Exception as e:
        print(f"오류: {e}")

if __name__ == "__main__":
    debug_musinsa_api()