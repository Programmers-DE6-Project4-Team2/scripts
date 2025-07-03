import multiprocessing
from datetime import datetime
from oliveyoung_crawler import OliveYoungCrawler
from categories import get_all_categories
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def crawl_category(category_name: str, category_url: str):
    logger.info(f"[시작] 카테고리: {category_name}")
    crawler = OliveYoungCrawler(headless=True)

    try:
        products = crawler.extract_product_list(category_url)
        if not products:
            logger.warning(f"[실패] 상품 없음: {category_name}")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = category_name.replace("/", "_").replace(" ", "_")

        data_dir = os.path.join("data", "products")
        os.makedirs(data_dir, exist_ok=True)

        csv_file = os.path.join(data_dir, f"products_{safe_name}_{timestamp}.csv")
        json_file = os.path.join(data_dir, f"products_{safe_name}_{timestamp}.json")

        crawler.save_to_csv(products, csv_file)
        crawler.save_to_json(products, json_file)

        logger.info(f"[완료] {category_name} - 총 {len(products)}개 저장")

    except Exception as e:
        logger.error(f"[오류] {category_name} - {e}")
    finally:
        crawler.close()

def main():
    categories = get_all_categories()
    logger.info(f"총 {len(categories)}개 카테고리 병렬 크롤링 시작")

    pool = multiprocessing.Pool(processes=min(4, len(categories)))  # CPU 4개 이하 제한
    tasks = [(name, url) for name, url in categories.items()]
    pool.starmap(crawl_category, tasks)
    pool.close()
    pool.join()

    logger.info("전체 카테고리 크롤링 완료")

if __name__ == '__main__':
    main()
