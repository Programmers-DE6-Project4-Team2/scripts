# 네이버 쇼핑 크롤러 PoC

네이버 쇼핑에서 뷰티/스킨케어 상품 데이터를 수집하는 Python 크롤러입니다.

## 🎯 주요 특징

- **API 직접 호출**: Selenium 없이 GraphQL API 사용으로 빠른 크롤링
- **무한 스크롤 해결**: 페이지네이션 방식으로 대량 데이터 수집
- **다양한 정렬 지원**: 인기순, 리뷰순, 최신순
- **구조화된 데이터**: JSON 형태의 깔끔한 상품 정보

## 📁 프로젝트 구조

```
naver_shopping_poc/
├── src/                          # 소스 코드
│   ├── naver_shopping_crawler.py # 메인 크롤러 클래스
│   ├── naver_full_crawler.py     # 전체 데이터 수집
│   ├── naver_analysis.py         # 사이트 구조 분석
│   ├── test_naver_api.py         # API 응답 테스트
│   ├── check_total_count.py      # 전체 데이터 개수 확인
│   └── check_sort_options.py     # 정렬 옵션 분석
├── data/                         # 수집된 데이터
│   ├── naver_skincare_all_*.csv  # 전체 상품 데이터 (CSV)
│   ├── naver_skincare_all_*.json # 전체 상품 데이터 (JSON)
│   └── analysis_files/           # 분석용 HTML/JSON 파일들
├── docs/                         # 문서
├── tests/                        # 테스트 코드
├── requirements.txt              # 의존성 패키지
└── README.md                     # 프로젝트 설명
```

## 🚀 빠른 시작

### 1. 환경 설정
```bash
pip install -r requirements.txt
```

### 2. 기본 사용법

#### 소량 테스트 (100개 상품)
```bash
cd src
python naver_shopping_crawler.py
```

#### 전체 데이터 수집 (1,000개 상품)
```bash
cd src
python naver_full_crawler.py
```

#### 사이트 구조 분석
```bash
cd src
python naver_analysis.py
```

## 📊 수집 데이터 예시

```json
{
  "product_id": "7789123756",
  "name": "라네즈 크림스킨 단품기획세트 170ml",
  "brand": "라네즈",
  "price": "24750",
  "original_price": "33000", 
  "discount_rate": "25",
  "rating": "4.88",
  "review_count": "28542",
  "url": "https://shopping.naver.com/window/products/7789123756",
  "image_url": "https://shop-phinf.pstatic.net/...",
  "scraped_at": "2025-07-02T16:03:50.748588"
}
```

## 🔍 API 분석 결과

### 발견된 GraphQL API
- **엔드포인트**: `https://veco-api.shopping.naver.com/window/api/v2/graphql`
- **오퍼레이션**: `getPagedCards`
- **페이지네이션**: `page` 파라미터 (1-50)

### 지원하는 정렬 방식
- ✅ `POPULARITY` - 인기순
- ✅ `REVIEW` - 리뷰 많은순  
- ✅ `RECENT` - 최신순
- ❌ `PRICE_LOW/HIGH` - 가격순 (미지원)
- ❌ `SALE` - 할인순 (미지원)

### 데이터 제한
- **페이지 제한**: 각 정렬별 최대 50페이지 (1,000개)
- **카테고리**: 뷰티 > 스킨케어 (`menuId: 20032470`)

## 📈 수집 성과 (2025-07-02 기준)

- **총 상품 수**: 1,000개
- **브랜드 수**: 525개
- **수집 시간**: 약 5분
- **데이터 품질**: 99% 이상

### 주요 브랜드 Top 5
1. [1+1] - 19개
2. 더페이스샵 - 16개  
3. 빌리프 - 14개
4. [본사직영] - 13개
5. 원씽 - 12개

### 가격대 분포
- 1-3만원: 62.7% (주력 가격대)
- 3-5만원: 21.5%
- 1만원 미만: 8.6%
- 5만원 이상: 7.2%

## ⚡ 성능 비교

| 구분 | 올리브영 | 네이버 쇼핑 |
|------|----------|-------------|
| **방식** | Selenium + HTML | API 직접 호출 |
| **속도** | 느림 (~10분/100개) | 빠름 (~1분/100개) |
| **안정성** | 보통 | 높음 |
| **데이터 품질** | HTML 파싱 의존 | 구조화된 JSON |
| **확장성** | 제한적 | 높음 |

## 🔧 고급 사용법

### 다른 정렬 방식으로 수집
```python
from src.naver_shopping_crawler import NaverShoppingCrawler

crawler = NaverShoppingCrawler()

# 리뷰순으로 수집
products = crawler.fetch_products_with_sort("REVIEW", max_pages=10)

# 최신순으로 수집  
products = crawler.fetch_products_with_sort("RECENT", max_pages=10)
```

### 데이터 분석
```python
import pandas as pd

# 데이터 로드
df = pd.read_csv('data/naver_skincare_all_*.csv')

# 브랜드별 평균 가격
brand_avg_price = df.groupby('brand')['price'].mean().sort_values(ascending=False)

# 평점 높은 상품 Top 10
top_rated = df.nlargest(10, 'rating')[['name', 'brand', 'rating', 'review_count']]
```

## 🚨 주의사항

1. **API 사용 정책**: 네이버 쇼핑 API 이용약관 준수
2. **요청 빈도**: 과도한 요청으로 인한 차단 방지를 위해 딜레이 유지
3. **데이터 제한**: 현재는 스킨케어 카테고리만 지원
4. **법적 준수**: 데이터 사용 시 개인정보보호법 및 관련 법령 준수

## 🛠️ 확장 계획

- [ ] 다른 뷰티 카테고리 지원 (메이크업, 헤어케어 등)
- [ ] 실시간 가격 모니터링
- [ ] 상품 리뷰 상세 수집
- [ ] 브랜드별 특화 분석
- [ ] 대시보드 구축

## 📞 문의

이 프로젝트에 대한 질문이나 제안사항이 있으시면 이슈를 등록해주세요.