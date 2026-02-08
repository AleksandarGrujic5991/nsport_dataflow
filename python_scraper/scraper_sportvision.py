import sys
import os
import requests
from bs4 import BeautifulSoup
import time
import platform

# Podesi encoding za print na Windowsu
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

if platform.system().lower() == "windows":
    API_URL = "http://127.0.0.1:8000/api/products/batch"
else:
    API_URL = "http://192.168.100.24/api/products/batch"
STORE_ID = 2

headers = {
    'User-Agent': 'Mozilla/5.0',
    'Accept-Language': 'sr-RS,sr;q=0.9,en-US;q=0.8,en;q=0.7',
    'Referer': 'https://www.sportvision.rs/'
}

def parse_price(cena):
    import re
    digits = re.sub(r'[^0-9]', '', cena) if cena else ''
    if not digits:
        return None
    if len(digits) > 2:
        value = f"{digits[:-2]}.{digits[-2:]}"
    elif len(digits) == 2:
        value = f"0.{digits}"
    else:
        value = f"0.0{digits}"
    try:
        return float(value)
    except:
        return None

def main():
    print("SportVision scraper starting...")

    # KATEGORIJE - ULTRA MODE
    if '--category' in sys.argv:
        idx = sys.argv.index('--category')
        CATEGORY_URLS = [sys.argv[idx + 1]]
    else:
        CATEGORY_URLS = [
            'https://www.sportvision.rs/obuca/za-muskarce+unisex/za-odrasle/',
            'https://www.sportvision.rs/odeca/za-muskarce+unisex/za-odrasle/',
            'https://www.sportvision.rs/oprema/za-muskarce+unisex/za-odrasle/',
            'https://www.sportvision.rs/obuca/za-zene/',
            'https://www.sportvision.rs/odeca/za-zene/za-odrasle/',
            'https://www.sportvision.rs/oprema/za-zene/za-odrasle/',
            'https://www.sportvision.rs/obuca/za-tinejdzere+za-malu-decu+za-bebe/',
            'https://www.sportvision.rs/odeca/za-tinejdzere+za-malu-decu+za-bebe/',
            'https://www.sportvision.rs/oprema/za-tinejdzere+za-malu-decu+za-bebe/'
        ]

    # Categories loaded

    # Parsiranje --limit argumenta - OPCIONALNO ZA TEST MODOVE
    limit = None
    if '--limit' in sys.argv:
        idx = sys.argv.index('--limit')
        try:
            limit = int(sys.argv[idx + 1])
            pass  # Using limit
        except (IndexError, ValueError):
            limit = None

    # (Opcionalno) Log folder
    log_dir = 'logs'
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f'log_{os.path.basename(__file__)}.txt')

    BATCH_SIZE = 50
    total_count = 0
    category_results = {}  # Track po kategorijama

    for category_idx, base_url in enumerate(CATEGORY_URLS, 1):
        # Processing category
        cat_start_time = time.time()
        page = 1
        cat_count = 0
        batch = []
        
        while True:
            url = base_url.rstrip('/') + f'/page-{page}' if page > 1 else base_url
            # Processing page
            
            try:
                response = requests.get(url, headers=headers, timeout=10)
                soup = BeautifulSoup(response.text, 'html.parser')
            except Exception as e:
                print(f"   WARNING:   Request error on page {page}: {e}")
                break

            products_on_page = 0
            product_elements = soup.select('div.text-wrapper')
            # Products found
            
            for product in product_elements:
                # Koristi data attributes koji su pouzdaniji
                sifra = product.get('data-productcode') or product.get('data-product-item-id')
                naziv = product.get('data-productname')
                brend = product.get('data-productbrand')
                cena = product.get('data-productprice')
                
                # Fallback na CSS selektore ako data attributes ne postoje
                if not sifra:
                    sifra_tag = product.select_one('div.category-wrapper span.code')
                    sifra = sifra_tag.text.strip() if sifra_tag else None
                if not naziv:
                    naziv_tag = product.select_one('div.title a')
                    naziv = naziv_tag.text.strip() if naziv_tag else None
                if not brend:
                    # Fallback za brend iz HTML strukture
                    brend_tag = product.select_one('div.brand a')
                    brend = brend_tag.text.strip() if brend_tag else None
                if not cena:
                    cena_tag = product.select_one('div.current-price.price-with-discount span.value')
                    cena = cena_tag.text.strip() if cena_tag else None
                    if not cena:
                        cena_tag = product.select_one('div.current-price span.value')
                        cena = cena_tag.text.strip() if cena_tag else None
                
                # Link iz CSS selektora
                naziv_tag = product.select_one('div.title a')
                link = naziv_tag['href'] if naziv_tag else None
                
                # Stara cena iz data attributes ili CSS selektor
                stara_cena = product.get('data-productprevprice')
                if not stara_cena:
                    stara_cena_tag = product.select_one('div.prev-price')
                    if stara_cena_tag:
                        import re
                        match = re.search(r'([\d.,]+)', stara_cena_tag.text)
                        if match:
                            stara_cena = match.group(1)

                # Popust iz data attributes ili CSS selektor
                popust_str = product.get('data-productdiscount')
                popust = None
                if popust_str:
                    try:
                        popust = int(popust_str)
                    except:
                        popust = None
                
                if not popust:
                    popust_tag = product.select_one('div.price-discount')
                    if popust_tag:
                        import re
                        match = re.search(r'(\d+)', popust_tag.text)
                        if match:
                            popust = int(match.group(1))

                price = parse_price(cena)
                price_regular = parse_price(stara_cena)
                price_discount = price if popust and popust > 0 else None
                price_old = price_regular

                # Progress tracking
                if total_count % 100 == 0 and total_count > 0:
                    pass  # Progress update

                if sifra and naziv and price is not None:
                    payload = {
                        'code': sifra,
                        'naziv': naziv,
                        'brand': brend if brend else None,
                        'price': float(price) if price is not None else 0.0,
                        'price_regular': float(price_regular) if price_regular is not None else None,
                        'price_discount': float(price_discount) if price_discount is not None else None,
                        'price_old': float(price_old) if price_old is not None else None,
                        'store_id': STORE_ID
                    }
                    batch.append(payload)
                    cat_count += 1
                    total_count += 1
                    products_on_page += 1
                    
                    # OPCIONALNA LIMIT PROVERA SAMO AKO JE EKSPLICITNO ZADATO
                    if limit and total_count >= limit:
                        pass  # Limit reached
                        break
                    
                    if len(batch) >= BATCH_SIZE:
                        resp = requests.post(
                            API_URL,
                            json=batch,
                            headers={'Accept': 'application/json'}
                        )
                        pass  # Batch sent
                        batch = []
                        
                else:
                    continue

            # IMPROVED NEXT BUTTON LOGIC SA DEBUGGING
            # Page processed
            
            # Break iz inner loop ako je dostignut limit
            if limit and total_count >= limit:
                pass  # Limit reached
                break

            next_btn = soup.select_one('a[rel="next"]')
            
            if not next_btn:
                pass  # No next page
                break  # Prekini samo ovu kategoriju
            elif products_on_page == 0:
                pass  # No products
                break  # Prekini samo ovu kategoriju
                
            page += 1

        # CATEGORY SUMMARY
        cat_duration = time.time() - cat_start_time
        category_results[base_url] = {
            'products': cat_count,
            'duration': cat_duration,
            'pages': page - 1
        }
        # Category completed

        # BREAK IZ GLAVNE PETLJE AKO JE DOSTIGNUT EKSPLICITNI LIMIT    
        if limit and total_count >= limit:
            print(f"🏁 SportVision: Global limit reached, stopping all categories")
            break

    # Upisi preostale proizvode iz batcha
    if batch:
        resp = requests.post(
            API_URL,
            json=batch,
            headers={'Accept': 'application/json'}
        )
        print(f'[OK]  SportVision final batch: {len(batch)} products sent, API response: {resp.status_code}')

    # FINAL SUMMARY
    print(f"\n SportVision FINAL SUMMARY:")
    print(f"   Total products: {total_count}")
    print(f"   Categories processed: {len(category_results)}/{len(CATEGORY_URLS)}")
    
    for idx, (url, result) in enumerate(category_results.items(), 1):
        short_name = url.split('/')[-3] if url.split('/')[-3] else url.split('/')[-2]
        print(f"   Cat {idx} ({short_name}): {result['products']} products, {result['pages']} pages ({result['duration']/60:.1f}min)")

if __name__ == '__main__':
    main()