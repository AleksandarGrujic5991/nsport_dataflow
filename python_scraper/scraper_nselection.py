import requests
from bs4 import BeautifulSoup
import json
import sys
import platform

if platform.system().lower() == "windows":
    API_URL = "http://127.0.0.1:8000/api/products/batch"
else:
    API_URL = "http://127.0.0.1/api/products/batch"
STORE_ID = 10  # NSelection - samostalan ID
BATCH_SIZE = 50

def build_category_urls():
    return [
        f"https://www.nselection.rs/patike?filter_submited=1&show_filters=1&filters[Pol][]=Muškarci",
        f"https://www.nselection.rs/obuca?filter_submited=1&show_filters=1&filters[Pol][]=Muškarci",
        f"https://www.nselection.rs/odeca?filter_submited=1&show_filters=1&filters[Pol][]=Muškarci",
        f"https://www.nselection.rs/aksesoari?filter_submited=1&show_filters=1&filters[Pol][]=Muškarci",
        f"https://www.nselection.rs/sportska-oprema?filter_submited=1&show_filters=1&filters[Pol][]=Muškarci",
        f"https://www.nselection.rs/patike?filter_submited=1&show_filters=1&filters[Pol][]=Žene",
        f"https://www.nselection.rs/obuca?filter_submited=1&show_filters=1&filters[Pol][]=Žene",
        f"https://www.nselection.rs/odeca?filter_submited=1&show_filters=1&filters[Pol][]=Žene",
        f"https://www.nselection.rs/aksesoari?filter_submited=1&show_filters=1&filters[Pol][]=Žene",
        f"https://www.nselection.rs/sportska-oprema?filter_submited=1&show_filters=1&filters[Pol][]=Žene",
        f"https://www.nselection.rs/patike?filter_submited=1&show_filters=1&filters[Pol][]=Deca",
        f"https://www.nselection.rs/obuca?filter_submited=1&show_filters=1&filters[Pol][]=Deca",
        f"https://www.nselection.rs/odeca?filter_submited=1&show_filters=1&filters[Pol][]=Deca",
        f"https://www.nselection.rs/aksesoari?filter_submited=1&show_filters=1&filters[Pol][]=Deca",
        f"https://www.nselection.rs/sportska-oprema?filter_submited=1&show_filters=1&filters[Pol][]=Deca"
    ]

import sys
if '--category' in sys.argv:
    idx = sys.argv.index('--category')
    CATEGORY_URLS = [sys.argv[idx + 1]]
else:
    CATEGORY_URLS = build_category_urls()

def parse_price(price_str):
    import re
    clean = re.sub(r'[^\d.]', '', price_str)
    if '.' in clean and len(clean.split('.')[-1]) == 3:
        clean = clean.replace('.', '')
    try:
        return float(clean)
    except ValueError:
        digits = re.sub(r'[^\d]', '', price_str)
        return float(digits) if digits else 0.0

def get_total_pages(soup):
    pager = soup.select_one("div.paginationTG ul")
    if not pager:
        return 1
    # Prvo probaj da nađeš poslednji <a> koji NIJE << ili <, i NIJE >>
    page_numbers = []
    for a in pager.find_all("a"):
        if a.text.isdigit():
            page_numbers.append(int(a.text))
        # Ako je tekst >>, koristi href da izvučeš broj strane
        elif ">>" in a.text and a.has_attr("href"):
            import re
            match = re.search(r'/(\d+)\?', a['href'])
            if match:
                page_numbers.append(int(match.group(1)))
    return max(page_numbers) if page_numbers else 1

def scrape_nselection():
    all_codes = set()
    batch = []
    total_count = 0

    for category_url in CATEGORY_URLS:
        print(f"[NSelection] Processing category {category_url}")
        resp = requests.get(category_url)
        soup = BeautifulSoup(resp.text, "html.parser")
        products = soup.select("div.product[itemtype='http://schema.org/Product']")
        total_pages = get_total_pages(soup)
        print(f"{category_url} - total pages: {total_pages}")

        # GENERIŠI SVE PAGE URL-ove
        page_urls = []
        for page in range(1, total_pages + 1):
            if page == 1:
                page_urls.append(category_url)
            else:
                # Dodaj /{page} pre znaka ?
                base, sep, query = category_url.partition('?')
                url = f"{base}/{page}?{query}" if sep else f"{base}/{page}"
                page_urls.append(url)

        for idx, url in enumerate(page_urls, 1):
            resp = requests.get(url)
            soup = BeautifulSoup(resp.text, "html.parser")
            products = soup.select("div.product[itemtype='http://schema.org/Product']")
            print(f"{url} - page {idx}: {len(products)} products")
            for prod in products:
                # Šifra je u <h5 class="product-code">
                code = prod.select_one("h5.product-code")
                code_val = code.text.strip() if code else None
                name = prod.select_one("h3.product-name a")
                price = prod.select_one("span.product-price")
                old_price = prod.select_one("span.product-old-price")
                link = name["href"] if name else None
                brand = prod.select_one("meta[itemprop='brand']")
                brand_val = brand["content"].strip() if brand and brand.has_attr("content") else None
                if not code_val or code_val in all_codes:
                    continue
                all_codes.add(code_val)
                price_val = parse_price(price.text) if price else None
                price_old_val = parse_price(old_price.text) if old_price else None
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
                    print(f'[OK] NSelection batch: {len(batch)} products sent, API response: {response.status_code}')
                    batch = []
    if batch:
        response = requests.post(
            API_URL ,
            json=batch,
            headers={"Accept": "application/json"}
        )
        print(f'[OK] NSelection final batch: {len(batch)} products sent, API response: {response.status_code}')

    print(f"[NSelection] COMPLETED: Total {total_count} products processed")

if __name__ == "__main__":
    scrape_nselection()