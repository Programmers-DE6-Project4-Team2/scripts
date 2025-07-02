# 올리브영 크롤러 PoC

올리브영 웹사이트에서 뷰티 상품과 리뷰를 크롤링하는 Python 스크립트입니다.

## 기능

- 상품 목록 크롤링 (이름, 브랜드, 가격, 평점, 리뷰 수)
- 상품 상세 정보 크롤링 (설명, 성분, 사용법, 이미지)
- 리뷰 데이터 크롤링 (평점, 내용, 작성자, 날짜)
- CSV 및 JSON 형태로 데이터 저장

## 설치

```bash
pip install -r requirements.txt
```

## 사용법

```bash
python main.py
```

## 주의사항

1. **CSS 선택자 수정 필요**: 현재 코드의 CSS 선택자들은 가상의 것입니다. 실제 올리브영 사이트의 HTML 구조를 분석한 후 수정해야 합니다.

2. **로봇 차단 대응**: 
   - User-Agent 랜덤화 적용
   - 요청 간 딜레이 설정
   - robots.txt 확인 권장

3. **법적 준수**: 
   - 크롤링 전 해당 사이트의 이용약관 확인
   - robots.txt 준수
   - 적절한 요청 빈도 유지

## 파일 구조

- `oliveyoung_crawler.py`: 메인 크롤러 클래스
- `main.py`: 실행 스크립트
- `requirements.txt`: 필요한 라이브러리 목록
- `data/`: 크롤링된 데이터 저장 폴더

## 결과 파일

- `products_YYYYMMDD_HHMMSS.csv/json`: 상품 목록
- `detailed_products_YYYYMMDD_HHMMSS.csv/json`: 상세 정보가 포함된 상품 데이터
- `reviews_YYYYMMDD_HHMMSS.csv/json`: 리뷰 데이터

## 커스터마이징

실제 사용 전에 다음 사항들을 수정해야 합니다:

1. **CSS 선택자 업데이트**: 올리브영 사이트의 실제 HTML 구조에 맞게 선택자 수정
2. **URL 검증**: 카테고리 URL이 올바른지 확인
3. **딜레이 조정**: 사이트 부하를 고려하여 요청 간격 조정
4. **에러 처리**: 더 견고한 에러 처리 로직 추가