import requests
from bs4 import BeautifulSoup
import json
import sys
import platform

if platform.system().lower() == "windows":
    API_URL = "http://127.0.0.1:8000/api/products/batch"
else:
    API_URL = "http://127.0.0.1/api/products/batch"
STORE_ID = 11  # Intersport
BATCH_SIZE = 50

def build_category_urls():
    return [
        "https://www.intersport.rs/patike?filter_submited=1&show_filters=1&filters[Pol][]=Muškarci",
        "https://www.intersport.rs/obuca?filter_submited=1&show_filters=1&filters[Pol][]=Muškarci",
        "https://www.intersport.rs/odeca?filter_submited=1&show_filters=1&filters[Pol][]=Muškarci",
        "https://www.intersport.rs/aksesoari?filter_submited=1&show_filters=1&filters[Pol][]=Muškarci",
        "https://www.intersport.rs/sportska-oprema?filter_submited=1&show_filters=1&filters[Pol][]=Muškarci",
        "https://www.intersport.rs/patike?filter_submited=1&show_filters=1&filters[Pol][]=Žene",
        "https://www.intersport.rs/obuca?filter_submited=1&show_filters=1&filters[Pol][]=Žene",
        "https://www.intersport.rs/odeca?filter_submited=1&show_filters=1&filters[Pol][]=Žene",
        "https://www.intersport.rs/aksesoari?filter_submited=1&show_filters=1&filters[Pol][]=Žene",
        "https://www.intersport.rs/sportska-oprema?filter_submited=1&show_filters=1&filters[Pol][]=Žene",
        "https://www.intersport.rs/patike?filter_submited=1&show_filters=1&filters[Pol][]=Deca",
        "https://www.intersport.rs/obuca?filter_submited=1&show_filters=1&filters[Pol][]=Deca",
        "https://www.intersport.rs/odeca?filter_submited=1&show_filters=1&filters[Pol][]=Deca",
        "https://www.intersport.rs/aksesoari?filter_submited=1&show_filters=1&filters[Pol][]=Deca",
        "https://www.intersport.rs/sportska-oprema?filter_submited=1&show_filters=1&filters[Pol][]=Deca"
    ]

import sys
if '--category' in sys.argv:
    idx = sys.argv.index('--category')
    CATEGORY_URLS = [sys.argv[idx + 1]]
else:
    CATEGORY_URLS = build_category_urls()

def parse_price(price_str):
    import re
    if not price_str:
        return 0.0
    
    # Remove RSD and extra spaces
    clean = price_str.replace('RSD', '').strip()
    
    # Extract numbers and dots - Serbian format uses dots as thousands separator
    clean = re.sub(r'[^\d.]', '', clean)
    
    # If we have format like "8.999" (Serbian thousands separator)
    if '.' in clean:
        parts = clean.split('.')
        if len(parts) == 2 and len(parts[1]) == 3:
            # This is thousands separator, remove it
            clean = parts[0] + parts[1]
        elif len(parts) > 2:
            # Multiple dots, join all but keep last as decimal if it's 1-2 digits
            if len(parts[-1]) <= 2:
                # Last part is decimal
                clean = ''.join(parts[:-1]) + '.' + parts[-1]
            else:
                # All are thousands separators
                clean = ''.join(parts)
    
    try:
        return float(clean)
    except:
        return 0.0

def get_total_pages(soup):
    try:
        pager = soup.select_one("div.paginationTG ul") or soup.select_one("div.pagination ul")
        if pager:
            links = pager.find_all("a")
            if links:
                last_link = links[-1]
                if last_link.get("href"):
                    href = last_link["href"]
                    import re
                    match = re.search(r'/(\d+)\?', href)
                    if match:
                        return int(match.group(1))
        return 1
    except Exception as e:
        print(f"[ERROR] Error getting total pages: {e}")
        return 1

def get_product_code(prod):
    # First try product code from h5.product-code (Intersport specific)
    code_elem = prod.select_one("h5.product-code")
    if code_elem and code_elem.text.strip():
        return code_elem.text.strip()
    
    # Fallback to data-product-id on img
    img = prod.select_one("img")
    if img and img.has_attr("data-product-id"):
        return img["data-product-id"].strip()
    
    return None

def scrape_intersport():
    all_codes = set()
    batch = []
    total_count = 0

    for category_url in CATEGORY_URLS:
        print(f"[Intersport] Processing category {category_url}")
        resp = requests.get(category_url)
        soup = BeautifulSoup(resp.text, "html.parser")
        products = soup.select("div.product[itemtype='http://schema.org/Product']")
        total_pages = get_total_pages(soup)
        print(f"{category_url} - total pages: {total_pages}")

        page_urls = [category_url]
        for page in range(2, total_pages + 1):
            base, sep, query = category_url.partition('?')
            url = f"{base}/{page}?{query}" if sep else f"{base}/{page}"
            page_urls.append(url)

        for idx, url in enumerate(page_urls, 1):
            resp = requests.get(url)
            soup = BeautifulSoup(resp.text, "html.parser")
            products = soup.select("div.product[itemtype='http://schema.org/Product']")
            print(f"{url} - page {idx}: {len(products)} products")
            
            for prod in products:
                code_val = get_product_code(prod)
                if not code_val or code_val in all_codes:
                    continue
                all_codes.add(code_val)

                name = prod.select_one("h3.product-name a") or prod.select_one("[itemprop='name']")
                brand_elem = prod.select_one("meta[itemprop='brand']") or prod.select_one("[itemprop='brand']")
                
                # Intersport specific price selectors (same as Trendmaker)
                price_elem = prod.select_one(".product-price") or prod.select_one("span[itemprop='price']")
                price_old_elem = prod.select_one(".product-old-price")

                # Get brand from meta content or default to "Unknown"
                brand_val = "Unknown"
                if brand_elem and brand_elem.has_attr('content'):
                    brand_val = brand_elem['content'].strip()
                elif brand_elem and brand_elem.text:
                    brand_val = brand_elem.text.strip()
                
                price_val = None
                price_old_val = None

                if price_elem:
                    price_text = price_elem.text.strip()
                    price_val = parse_price(price_text)
                
                if price_old_elem:
                    price_old_text = price_old_elem.text.strip()
                    price_old_val = parse_price(price_old_text)

                payload = {
                    "code": code_val,
                    "naziv": name.text.strip() if name else None,
                    "brand": brand_val,
                    "price": price_val if price_val is not None else 0.0,
                    "price_regular": price_old_val if price_old_val is not None else None,
                    "price_discount": price_val if price_old_val and price_val < price_old_val else None,
                    "price_old": price_old_val if price_old_val else None,
                    "store_id": STORE_ID
                }
                batch.append(payload)
                total_count += 1
                
                if len(batch) >= BATCH_SIZE:
                    response = requests.post(
                        API_URL,
                        json=batch,
                        headers={"Accept": "application/json"}
                    )
                    print(f'[OK] Intersport batch: {len(batch)} products sent, API response: {response.status_code}')
                    batch = []

    if batch:
        response = requests.post(
            API_URL,
            json=batch,
            headers={"Accept": "application/json"}
        )
        print(f'[OK] Intersport final batch: {len(batch)} products sent, API response: {response.status_code}')

    print(f"[Intersport] COMPLETED: Total {total_count} products processed")

if __name__ == "__main__":
    scrape_intersport()