# 네이버 쇼핑 API 분석 문서

## 🔍 발견된 GraphQL API

### 기본 정보
- **엔드포인트**: `https://veco-api.shopping.naver.com/window/api/v2/graphql`
- **방식**: HTTP GET
- **데이터 형식**: GraphQL (Query String 방식)

### API 구조

#### Operation Name
```
getPagedCards
```

#### Required Headers
```http
User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)...
Accept: application/json, text/plain, */*
Accept-Language: ko-KR,ko;q=0.9,en;q=0.8
Origin: https://shopping.naver.com
Referer: https://shopping.naver.com/
```

#### Variables 구조
```json
{
  "isIncludeProductBenefit": false,
  "isIncludeProductDetail": false, 
  "isIncludeWindowViewCount": false,
  "skip": false,
  "checkPromotionProduct": false,
  "params": {
    "page": 1,                    // 페이지 번호 (1-50)
    "pageSize": 20,               // 페이지당 상품 수 (고정)
    "sort": "POPULARITY",         // 정렬 방식
    "subVertical": "BEAUTY",      // 대분류 (뷰티)
    "filterSoldOut": true,        // 품절 제외
    "menuId": "20032470"          // 소분류 (스킨케어)
  }
}
```

#### Extensions (GraphQL Persisted Query)
```json
{
  "persistedQuery": {
    "version": 1,
    "sha256Hash": "db693844352af4739286d5394a31659cac8a1643795d5de3bea7064ba7d7fa45"
  }
}
```

## 📊 응답 구조

### 성공 응답 (200 OK)
```json
{
  "data": {
    "pagedCards": {
      "data": [                   // 상품 배열
        {
          "cardId": "7789123756_PRODUCT",
          "data": {
            "product": {
              "id": "7789123756",
              "name": "상품명",
              "pcDiscountedSalePrice": 24750,  // 할인가
              "salePrice": 33000,              // 정가
              "pcDiscountedRatio": 25,         // 할인율
              "averageReviewScore": 4.88,      // 평점
              "totalReviewCount": 28542,       // 리뷰수
              "images": [...]                  // 이미지 배열
            }
          }
        }
      ],
      "page": 1,                  // 현재 페이지
      "hasMore": true,            // 다음 페이지 존재 여부
      "cursor": null,
      "__typename": "PagedCards"
    }
  }
}
```

## 🎛️ 지원하는 정렬 방식

| Sort 값 | 설명 | 지원 여부 |
|---------|------|-----------|
| `POPULARITY` | 인기순 | ✅ |
| `REVIEW` | 리뷰 많은순 | ✅ |
| `RECENT` | 최신순 | ✅ |
| `PRICE_LOW` | 낮은 가격순 | ❌ (400 에러) |
| `PRICE_HIGH` | 높은 가격순 | ❌ (400 에러) |
| `SALE` | 할인순 | ❌ (400 에러) |
| `RATING` | 평점순 | ❌ (400 에러) |

## 🏷️ 카테고리 구조

### 뷰티 카테고리 (subVertical: "BEAUTY")

| menuId | 카테고리명 | 상태 |
|--------|------------|------|
| `20032470` | 스킨케어 | ✅ 확인됨 |
| `20032480` | 메이크업 | ❓ 추정 |
| `20032490` | 바디케어 | ❓ 추정 |
| `20032500` | 헤어케어 | ❓ 추정 |

## 📈 데이터 제한사항

### 페이지 제한
- **최대 페이지**: 50페이지
- **페이지당 상품**: 20개 (고정)
- **총 상품 수**: 1,000개 (각 정렬별)

### API 제한
- **요청 빈도**: 초당 1-2회 권장
- **동시 연결**: 제한 있음 (정확한 수치 불명)
- **사용자 에이전트**: 필수 (봇 차단)

## 🛡️ 봇 탐지 우회 방법

### 1. 헤더 설정
```python
headers = {
    'User-Agent': 'Mozilla/5.0...',  # 실제 브라우저 UA
    'Accept': 'application/json',
    'Origin': 'https://shopping.naver.com',
    'Referer': 'https://shopping.naver.com/'
}
```

### 2. 요청 빈도 제어
```python
import time
time.sleep(1)  # 요청 간 1초 딜레이
```

### 3. User-Agent 로테이션
```python
from fake_useragent import UserAgent
ua = UserAgent()
headers['User-Agent'] = ua.random
```

## 🚨 에러 처리

### 400 Bad Request
- **원인**: 잘못된 정렬 옵션, 파라미터 오류
- **해결**: 지원되는 정렬 옵션만 사용

### 403 Forbidden
- **원인**: 봇 탐지, 과도한 요청
- **해결**: User-Agent 변경, 딜레이 증가

### 429 Too Many Requests
- **원인**: 요청 빈도 초과
- **해결**: 요청 간격 늘리기

## 📝 개발 팁

### URL 인코딩
```python
from urllib.parse import quote
variables_encoded = quote(json.dumps(variables))
```

### 세션 재사용
```python
session = requests.Session()
session.headers.update(headers)
```

### 응답 검증
```python
if 'data' in response and 'pagedCards' in response['data']:
    products = response['data']['pagedCards']['data']
```

## 🔄 API 버전 변화 대응

GraphQL Hash 값이 변경될 수 있으므로, 정기적으로 브라우저 네트워크 탭에서 최신 요청을 확인하는 것이 필요합니다.

현재 Hash: `db693844352af4739286d5394a31659cac8a1643795d5de3bea7064ba7d7fa45`