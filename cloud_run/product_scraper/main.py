from flask import Flask, request, jsonify
from oliveyoung_scraper_module import OliveYoungCrawler
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route("/scrape", methods=["POST"])
def scrape():
    data = request.get_json()
    category_url = data.get("category_url")
    category_name = data.get("category_name", "default")
    max_pages = int(data.get("max_pages", 1))

    if not category_url:
        return jsonify({"status": "error", "message": "category_url is required"}), 400

    logger.info(f"[START] category={category_name} max_pages={max_pages}")
    crawler = OliveYoungCrawler(headless=True)

    try:
        products = crawler.extract_product_list(category_url, max_pages=max_pages)
        return jsonify({
            "status": "completed",
            "category_name": category_name,
            "products_count": len(products),
            "products": products
        })

    except Exception as e:
        logger.exception("크롤링 도중 에러 발생")
        return jsonify({
            "status": "error",
            "message": str(e),
        }), 500

    finally:
        crawler.close()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
