"""
올리브영 카테고리 딕셔너리
각 카테고리명과 해당 URL을 매핑
"""

from datetime import datetime
from typing import Dict, List

# 올리브영 메인 카테고리 딕셔너리
OLIVEYOUNG_CATEGORIES = {
    # 스킨케어
    "스킨케어_스킨/토너": "https://www.oliveyoung.co.kr/store/display/getMCategoryList.do?dispCatNo=1000001000100130001&fltDispCatNo=&prdSort=01&pageIdx=1&rowsPerPage=24&searchTypeSort=btn_thumb&plusButtonFlag=N&isLoginCnt=1&aShowCnt=0&bShowCnt=0&cShowCnt=0&trackingCd=Cat1000001000100130001_Small&amplitudePageGubun=&t_page=%EC%B9%B4%ED%85%8C%EA%B3%A0%EB%A6%AC%EA%B4%80&t_click=%EC%B9%B4%ED%85%8C%EA%B3%A0%EB%A6%AC%EC%83%81%EC%84%B8_%EC%86%8C%EC%B9%B4%ED%85%8C%EA%B3%A0%EB%A6%AC&midCategory=%EC%8A%A4%ED%82%A8%2F%ED%86%A0%EB%84%88&smallCategory=%EC%A0%84%EC%B2%B4&checkBrnds=&lastChkBrnd=&t_1st_category_type=%EB%8C%80_%EC%8A%A4%ED%82%A8%EC%BC%80%EC%96%B4&t_2nd_category_type=%EC%A4%91_%EC%8A%A4%ED%82%A8%2F%ED%86%A0%EB%84%88&t_3rd_category_type=%EC%86%8C_%EC%A0%84%EC%B2%B4",
    "스킨케어_에센스/세럼/앰플": "https://www.oliveyoung.co.kr/store/display/getMCategoryList.do?dispCatNo=100000100010014&isLoginCnt=0&aShowCnt=0&bShowCnt=0&cShowCnt=0&t_page=%EB%A1%9C%EC%BC%80%EC%9D%B4%EC%85%98_%EC%B9%B4%ED%85%8C%EA%B3%A0%EB%A6%AC%EA%B4%80&t_click=%EC%B9%B4%ED%85%8C%EA%B3%A0%EB%A6%AC%ED%83%AD_%EC%A4%91%EC%B9%B4%ED%85%8C%EA%B3%A0%EB%A6%AC&t_1st_category_type=%EB%8C%80_%EC%8A%A4%ED%82%A8%EC%BC%80%EC%96%B4&t_2nd_category_type=%EC%A4%91_%EC%97%90%EC%84%BC%EC%8A%A4/%EC%84%B8%EB%9F%BC/%EC%95%B0%ED%94%8C",
    "스킨케어_크림": "https://www.oliveyoung.co.kr/store/display/getMCategoryList.do?dispCatNo=100000100010015&isLoginCnt=0&aShowCnt=0&bShowCnt=0&cShowCnt=0&t_page=%EB%A1%9C%EC%BC%80%EC%9D%B4%EC%85%98_%EC%B9%B4%ED%85%8C%EA%B3%A0%EB%A6%AC%EA%B4%80&t_click=%EC%B9%B4%ED%85%8C%EA%B3%A0%EB%A6%AC%ED%83%AD_%EC%A4%91%EC%B9%B4%ED%85%8C%EA%B3%A0%EB%A6%AC&t_1st_category_type=%EB%8C%80_%EC%8A%A4%ED%82%A8%EC%BC%80%EC%96%B4&t_2nd_category_type=%EC%A4%91_%ED%81%AC%EB%A6%BC",
    "스킨케어_로션": "https://www.oliveyoung.co.kr/store/display/getMCategoryList.do?dispCatNo=100000100010016&isLoginCnt=0&aShowCnt=0&bShowCnt=0&cShowCnt=0&t_page=%EB%A1%9C%EC%BC%80%EC%9D%B4%EC%85%98_%EC%B9%B4%ED%85%8C%EA%B3%A0%EB%A6%AC%EA%B4%80&t_click=%EC%B9%B4%ED%85%8C%EA%B3%A0%EB%A6%AC%ED%83%AD_%EC%A4%91%EC%B9%B4%ED%85%8C%EA%B3%A0%EB%A6%AC&t_1st_category_type=%EB%8C%80_%EC%8A%A4%ED%82%A8%EC%BC%80%EC%96%B4&t_2nd_category_type=%EC%A4%91_%EB%A1%9C%EC%85%98",
    "스킨케어_미스트/오일": "https://www.oliveyoung.co.kr/store/display/getMCategoryList.do?dispCatNo=100000100010010&isLoginCnt=0&aShowCnt=0&bShowCnt=0&cShowCnt=0&t_page=%EB%A1%9C%EC%BC%80%EC%9D%B4%EC%85%98_%EC%B9%B4%ED%85%8C%EA%B3%A0%EB%A6%AC%EA%B4%80&t_click=%EC%B9%B4%ED%85%8C%EA%B3%A0%EB%A6%AC%ED%83%AD_%EC%A4%91%EC%B9%B4%ED%85%8C%EA%B3%A0%EB%A6%AC&t_1st_category_type=%EB%8C%80_%EC%8A%A4%ED%82%A8%EC%BC%80%EC%96%B4&t_2nd_category_type=%EC%A4%91_%EB%AF%B8%EC%8A%A4%ED%8A%B8/%EC%98%A4%EC%9D%BC",
    "스킨케어_스킨케어세트": "https://www.oliveyoung.co.kr/store/display/getMCategoryList.do?dispCatNo=100000100010017&isLoginCnt=0&aShowCnt=0&bShowCnt=0&cShowCnt=0&t_page=%EB%A1%9C%EC%BC%80%EC%9D%B4%EC%85%98_%EC%B9%B4%ED%85%8C%EA%B3%A0%EB%A6%AC%EA%B4%80&t_click=%EC%B9%B4%ED%85%8C%EA%B3%A0%EB%A6%AC%ED%83%AD_%EC%A4%91%EC%B9%B4%ED%85%8C%EA%B3%A0%EB%A6%AC&t_1st_category_type=%EB%8C%80_%EC%8A%A4%ED%82%A8%EC%BC%80%EC%96%B4&t_2nd_category_type=%EC%A4%91_%EC%8A%A4%ED%82%A8%EC%BC%80%EC%96%B4%EC%84%B8%ED%8A%B8",
}

def get_all_categories() -> Dict[str, str]:
    """모든 카테고리 딕셔너리 반환"""
    return OLIVEYOUNG_CATEGORIES.copy()

def get_category_url(category_name: str) -> str:
    """특정 카테고리의 URL 반환"""
    return OLIVEYOUNG_CATEGORIES.get(category_name, "")

def get_category_names() -> List[str]:
    """모든 카테고리명 리스트 반환"""
    return list(OLIVEYOUNG_CATEGORIES.keys())

def get_categories_by_type(category_type: str) -> Dict[str, str]:
    """특정 타입의 카테고리들만 반환 (예: 스킨케어, 메이크업)"""
    filtered_categories = {
        name: url for name, url in OLIVEYOUNG_CATEGORIES.items() 
        if name.startswith(category_type)
    }
    return filtered_categories

def create_category_metadata(category_name: str) -> Dict:
    """카테고리 메타데이터 생성 (크롤링 시점 포함)"""
    return {
        "category_name": category_name,
        "category_url": get_category_url(category_name),
        "crawling_timestamp": datetime.now().isoformat(),
        "crawling_date": datetime.now().strftime("%Y-%m-%d"),
        "crawling_time": datetime.now().strftime("%H:%M:%S"),
        "source": "oliveyoung",
        "data_type": "products"
    }

# 실제 올리브영 URL은 다음과 같은 형식입니다:
# https://www.oliveyoung.co.kr/store/display/getMCategoryList.do?dispCatNo={카테고리번호}&fltDispCatNo=&prdSort=01&pageIdx=1&rowsPerPage=24

# 참고: 실제 사용 시 위의 URL들은 올리브영 사이트 구조에 맞게 수정이 필요할 수 있습니다.
