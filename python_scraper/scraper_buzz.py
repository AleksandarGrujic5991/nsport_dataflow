import sys
import os
import platform
import requests
from bs4 import BeautifulSoup
import argparse
import time

# Argument parsing
parser = argparse.ArgumentParser()
parser.add_argument('--limit', type=int, help='Limit broj proizvoda')
parser.add_argument('--headless', action='store_true', help='Run in headless mode (not used but for consistency)')
parser.add_argument('--category', type=str, required=True)
parser.add_argument('--output', type=str, default=None)
args = parser.parse_args()

category_url = args.category
output_file = args.output

# Podesi encoding za print na Windowsu
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

if platform.system().lower() == "windows":
    API_URL = "http://127.0.0.1:8000/api/products/batch"
else:
    API_URL = "http://192.168.100.24/api/products/batch"  # FIX: Dodao /batch
STORE_ID = 4  # Buzz ID

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def parse_price(cena):
    """Parsira cenu iz teksta, radi za srpske formate (npr. 9.899,10)"""
    if not cena:
        return None
    try:
        import re
        digits = re.sub(r'[^\d.,]', '', str(cena))
        if ',' in digits:
            digits = digits.replace('.', '').replace(',', '.')
        else:
            digits = digits.replace('.', '')
        return float(digits)
    except Exception:
        return None

def main():
    print("🚀 Buzz Sneakers Scraper Starting...")
    import sys
    if '--category' in sys.argv:
        idx = sys.argv.index('--category')
        CATEGORY_URLS = [sys.argv[idx + 1]]
    else:
        CATEGORY_URLS = [
            "https://www.buzzsneakers.rs/obuca/za-muskarce",
            "https://www.buzzsneakers.rs/odeca/za-muskarce", 
            "https://www.buzzsneakers.rs/oprema/za-muskarce",
            "https://www.buzzsneakers.rs/obuca/za-zene",
            "https://www.buzzsneakers.rs/odeca/za-zene",
            "https://www.buzzsneakers.rs/oprema/za-zene",
            "https://www.buzzsneakers.rs/odeca/za-decake+za-devojcice+kids/",
            "https://www.buzzsneakers.rs/obuca/za-decake+za-devojcice+kids/",
            "https://www.buzzsneakers.rs/oprema/za-decake+za-devojcice+kids/",
        ]

    print(f"📂 Total categories: {len(CATEGORY_URLS)}")
    if args.limit:
        print(f" Using limit: {args.limit}")

    BATCH_SIZE = 50
    total_count = 0

    for cat_idx, base_url in enumerate(CATEGORY_URLS, 1):
        category_name = base_url.split('/')[-1] if base_url.split('/')[-1] else base_url.split('/')[-2]
        print(f"\n Processing category {cat_idx}/{len(CATEGORY_URLS)}: {category_name}")
        print(f"📂 URL: {base_url}")
        
        page = 1
        cat_count = 0
        batch = []
        
        while True:
            if args.limit and total_count >= args.limit:
                print(f" Global limit {args.limit} reached!")
                break
                
            url = base_url if page == 1 else f"{base_url}/page-{page}"
            try:
                resp = requests.get(url, headers=headers, timeout=15)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")
            except Exception as e:
                print(f"[ERROR]  Error accessing {url}: {e}")
                break

            products = soup.find_all("div", class_="wrapper-grid-view")
            
            if not products:
                break
                
            products_on_page = 0
            
            for product in products:
                try:
                    code = product.get("data-productcode")
                    name = None
                    title_div = product.find("div", class_="title")
                    if title_div:
                        name_a = title_div.find("a")
                        if name_a:
                            name = name_a.text.strip()
                    brand = None
                    brand_div = product.find("div", class_="caption-brand")
                    if brand_div:
                        brand_a = brand_div.find("a", title=True)
                        if brand_a:
                            brand = brand_a["title"].strip()
                    if not brand:
                        brand = product.get("data-productbrand")
                    
                    price = None
                    price_div = product.find("div", class_="current-price")
                    if price_div:
                        value_span = price_div.find("span", class_="value")
                        if value_span:
                            price = parse_price(value_span.text)
                    if price is None:
                        price_attr = product.get("data-productprice")
                        if price_attr:
                            price = parse_price(price_attr)

                    price_regular = None
                    prev_price_div = product.find("div", class_="prev-price")
                    if prev_price_div:
                        prev_price_text = prev_price_div.text.strip().split()[0]
                        price_regular = parse_price(prev_price_text)

                    price_old = None
                    prev_old_div = product.find("div", class_="prev-old-price")
                    if prev_old_div:
                        prev_old_text = prev_old_div.text.strip().split()[0]
                        price_old = parse_price(prev_old_text)

                    price_discount = None
                    discount_div = product.find("div", class_="product-discount")
                    if discount_div:
                        discount_span = discount_div.find("span", class_="text-discount")
                        if discount_span:
                            discount_text = discount_span.text.strip().replace('%', '')
                            price_discount = price if discount_text and discount_text != "0" else None

                    if code and name and price is not None:
                        payload = {
                            "code": str(code),
                            "naziv": str(name),
                            "brand": str(brand) if brand else None,
                            "price": float(price),
                            "price_regular": float(price_regular) if price_regular else float(price),
                            "price_discount": float(price_discount) if price_discount else None,
                            "price_old": float(price_old) if price_old else None,
                            "store_id": STORE_ID
                        }
                        batch.append(payload)
                        cat_count += 1
                        total_count += 1
                        products_on_page += 1
                        # Product added successfully
                        
                        if len(batch) >= BATCH_SIZE:
                            try:
                                response = requests.post(
                                    API_URL,
                                    json=batch,
                                    headers={"Accept": "application/json"},
                                    timeout=30
                                )
                                pass  # API response handled
                            except Exception as e:
                                pass  # Request error
                            batch = []
                except Exception:
                    continue
            
            if args.limit and total_count >= args.limit:
                break
            
            if products_on_page == 0:
                break
            
            next_page_url = f"{base_url}/page-{page + 1}"
            try:
                test_resp = requests.get(next_page_url, headers=headers, timeout=10)
                test_soup = BeautifulSoup(test_resp.text, "html.parser")
                test_products = test_soup.find_all("div", class_="wrapper-grid-view")
                
                if len(test_products) > 0:
                    page += 1
                    time.sleep(1)
                    continue
                else:
                    break
            except Exception:
                break
        
        if batch:
            try:
                response = requests.post(
                    API_URL,
                    json=batch,
                    headers={"Accept": "application/json"},
                    timeout=30
                )
                pass  # Final API response processed
            except Exception as e:
                print(f'[ERROR]  Final request error: {e}')
            batch = []

    print(f"\n Buzz Scraper COMPLETED!")
    print(f" Total products processed: {total_count}")
    print(f"📂 Categories processed: {cat_idx if 'cat_idx' in locals() else len(CATEGORY_URLS)}")

if __name__ == "__main__":
    main()