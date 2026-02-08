import requests
from bs4 import BeautifulSoup
import json
import sys
import platform

if platform.system().lower() == "windows":
    API_URL = "http://127.0.0.1:8000/api/products/batch"
else:
    API_URL = "http://127.0.0.1/api/products/batch"

# Različiti store_id za svaku prodavnicu
STORE_IDS = {
    "nsport": 7,      # NSport glavna (bez sufiksa)
    "nfashion": 8,    # NSport Fashion (&fashion=1)
    "lacoste": 9      # NSport Lacoste (&lacoste=1)
}

BATCH_SIZE = 50

FASHION_SUFFIX = "&fashion=1"
LACOSTE_SUFFIX = "&lacoste=1"

def build_category_urls(suffix):
    # Svi URL-ovi koriste normalne karaktere - server automatski enkodira
    return [
        f"https://www.n-sport.net/patike?filter_submited=1&show_filters=1&filters[Pol][]=Muškarci{suffix}",
        f"https://www.n-sport.net/obuca?filter_submited=1&show_filters=1&filters[Pol][]=Muškarci{suffix}",
        f"https://www.n-sport.net/odeca?filter_submited=1&show_filters=1&filters[Pol][]=Muškarci{suffix}",
        f"https://www.n-sport.net/aksesoari?filter_submited=1&show_filters=1&filters[Pol][]=Muškarci{suffix}",
        f"https://www.n-sport.net/sportska-oprema?filter_submited=1&show_filters=1&filters[Pol][]=Muškarci{suffix}",
        f"https://www.n-sport.net/patike?filter_submited=1&show_filters=1&filters[Pol][]=Žene{suffix}",
        f"https://www.n-sport.net/obuca?filter_submited=1&show_filters=1&filters[Pol][]=Žene{suffix}",
        f"https://www.n-sport.net/odeca?filter_submited=1&show_filters=1&filters[Pol][]=Žene{suffix}",
        f"https://www.n-sport.net/aksesoari?filter_submited=1&show_filters=1&filters[Pol][]=Žene{suffix}",
        f"https://www.n-sport.net/sportska-oprema?filter_submited=1&show_filters=1&filters[Pol][]=Žene{suffix}",
        f"https://www.n-sport.net/patike?filter_submited=1&show_filters=1&filters[Pol][]=Deca{suffix}",
        f"https://www.n-sport.net/obuca?filter_submited=1&show_filters=1&filters[Pol][]=Deca{suffix}",
        f"https://www.n-sport.net/odeca?filter_submited=1&show_filters=1&filters[Pol][]=Deca{suffix}",
        f"https://www.n-sport.net/aksesoari?filter_submited=1&show_filters=1&filters[Pol][]=Deca{suffix}",
        f"https://www.n-sport.net/sportska-oprema?filter_submited=1&show_filters=1&filters[Pol][]=Deca{suffix}"
    ]

import sys
if '--category' in sys.argv:
    idx = sys.argv.index('--category')
    CATEGORY_URLS = [sys.argv[idx + 1]]
else:
    CATEGORY_URLS = (
        build_category_urls("") +
        build_category_urls(FASHION_SUFFIX) +
        build_category_urls(LACOSTE_SUFFIX)
    )

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

def get_total_pages(soup, suffix=""):
    # Prvo probaj paginationTGNF (za fashion), pa paginationTG (za ostale)
    pager = soup.select_one("div.paginationTGNF ul") or soup.select_one("div.paginationTG ul")
    if not pager:
        return 1
    if suffix == FASHION_SUFFIX:
        pages = []
        for a in pager.find_all("a"):
            txt = a.text.strip()
            if txt.startswith("..."):
                num = ''.join(filter(str.isdigit, txt))
                if num:
                    pages.append(int(num))
            elif txt.isdigit():
                pages.append(int(txt))
        return max(pages) if pages else 1
    elif suffix == LACOSTE_SUFFIX:
        last_page_link = pager.find("a", string=">>")
        if last_page_link and last_page_link.has_attr("href"):
            import re
            match = re.search(r'/(\d+)\?', last_page_link["href"])
            if match:
                return int(match.group(1))
        pages = [int(a.text) for a in pager.find_all("a") if a.text.isdigit()]
        return max(pages) if pages else 1
    else:
        last_page_link = pager.find("a", string=">>")
        if last_page_link and last_page_link.has_attr("href"):
            import re
            match = re.search(r'/(\d+)\?', last_page_link["href"])
            if match:
                return int(match.group(1))
        pages = [int(a.text) for a in pager.find_all("a") if a.text.isdigit()]
        return max(pages) if pages else 1

def get_fashion_code(prod):
    # Šifra je u atributu data-product-id na <a> ili <img>
    a = prod.select_one("a[data-product-id]")
    if a and a.has_attr("data-product-id"):
        return a["data-product-id"].strip()
    # fallback: probaj na img
    img = prod.select_one("img[data-product-id]")
    if img and img.has_attr("data-product-id"):
        return img["data-product-id"].strip()
    return None

def scrape_nsport():
    all_codes_by_store = {}  # Separate code tracking per store_id
    batch = []
    total_count = 0

    for category_url in CATEGORY_URLS:
        print(f"[NSport] Processing category {category_url}")
        suffix = ""
        store_name = "nsport"  # Default
        
        if FASHION_SUFFIX in category_url:
            suffix = FASHION_SUFFIX
            store_name = "nfashion"
        elif LACOSTE_SUFFIX in category_url:
            suffix = LACOSTE_SUFFIX
            store_name = "lacoste"
        
        current_store_id = STORE_IDS[store_name]
        print(f"[NSport] Using store_id={current_store_id} for {store_name}")
        resp = requests.get(category_url)
        soup = BeautifulSoup(resp.text, "html.parser")
        products = soup.select("div.product[itemtype='http://schema.org/Product']")
        total_pages = get_total_pages(soup, suffix=suffix)
        print(f"{category_url} - total pages: {total_pages}")

        # --- Prikupi sve page URL-ove iz paginacije ---
        page_urls = [category_url]
        if suffix == FASHION_SUFFIX and total_pages > 1:
            # Za NFashion koristimo href-ove direktno iz paginacije
            pager = soup.select_one("div.paginationTGNF ul") or soup.select_one("div.paginationTG ul")
            if pager:
                for a in pager.find_all("a"):
                    href = a.get("href")
                    if href and href not in page_urls:
                        if not href.startswith("http"):
                            href = "https://www.n-sport.net" + href
                        page_urls.append(href)
            # Ako nema sve stranice u paginaciji, generiši ih
            if len(page_urls) < total_pages:
                for page in range(2, total_pages + 1):
                    # Koristi pg parametar za NFashion
                    if '?' in category_url:
                        page_url = category_url + f"&pg={page}"
                    else:
                        page_url = category_url + f"?pg={page}"
                    if page_url not in page_urls:
                        page_urls.append(page_url)
        else:
            # Standardni NSport i Lacoste pagination
            for page in range(2, total_pages + 1):
                base, sep, query = category_url.partition('?')
                url = f"{base}/{page}?{query}" if sep else f"{base}/{page}"
                page_urls.append(url)

        # --- Kraj izmene ---

        for idx, url in enumerate(page_urls, 1):
            resp = requests.get(url)
            soup = BeautifulSoup(resp.text, "html.parser")
            products = soup.select("div.product[itemtype='http://schema.org/Product']")
            print(f"{url} - page {idx}: {len(products)} products")
            for prod in products:
                if suffix == FASHION_SUFFIX or suffix == LACOSTE_SUFFIX:
                    # Za NFashion i Lacoste: šifra iz <h5 class="product-code"> elementa
                    code = prod.select_one("h5.product-code")
                    code_val = code.text.strip() if code else None
                else:
                    # Standardni N-Sport: takođe šifra iz <h5 class="product-code">
                    code = prod.select_one("h5.product-code")
                    code_val = code.text.strip() if code else None

                # Brend iz meta taga
                brand = prod.select_one("meta[itemprop='brand']")
                brand_val = brand["content"].strip() if brand and brand.has_attr("content") else None

                name = prod.select_one("h3.product-name a")
                price = prod.select_one("span.product-price")
                old_price = prod.select_one("span.product-old-price")
                link = name["href"] if name else None
                
                # Initialize store-specific code set if not exists
                if current_store_id not in all_codes_by_store:
                    all_codes_by_store[current_store_id] = set()
                
                # Check for duplicates only within the same store_id
                if not code_val or code_val in all_codes_by_store[current_store_id]:
                    continue
                all_codes_by_store[current_store_id].add(code_val)
                price_val = parse_price(price.text) if price else None
                price_old_val = parse_price(old_price.text) if old_price else None
                # Ako je prazno i suffix je Lacoste, zakucaj na "Lacoste"
                if not brand_val and suffix == LACOSTE_SUFFIX:
                    brand_val = "Lacoste"
                payload = {
                    "code": code_val,
                    "naziv": name.text.strip() if name else None,
                    "brand": brand_val,
                    "price": price_val if price_val is not None else 0.0,
                    "price_regular": price_old_val if price_old_val is not None else None,
                    "price_discount": price_val if price_old_val and price_val < price_old_val else None,
                    "price_old": price_old_val if price_old_val else None,
                    "store_id": current_store_id
                }
                batch.append(payload)
                total_count += 1
                if len(batch) >= BATCH_SIZE:
                    response = requests.post(
                        API_URL ,
                        json=batch,
                        headers={"Accept": "application/json"}
                    )
                    print(f'[OK] N-Sport batch: {len(batch)} products sent, API response: {response.status_code}')
                    batch = []
    if batch:
        response = requests.post(
            API_URL ,
            json=batch,
            headers={"Accept": "application/json"}
        )
        print(f'[OK] N-Sport final batch: {len(batch)} products sent, API response: {response.status_code}')

    print(f"[NSport] COMPLETED: Total {total_count} products processed")

if __name__ == "__main__":
    scrape_nsport()