import sys
import os
import platform
import requests
from bs4 import BeautifulSoup
import argparse
import time
import json

# Argument parsing
parser = argparse.ArgumentParser()
parser.add_argument('--limit', type=int, help='Limit broj proizvoda')
parser.add_argument('--headless', action='store_true', help='Run in headless mode (not used but for consistency)')
parser.add_argument('--category', type=str, required=False)
parser.add_argument('--output', type=str, default=None)
args = parser.parse_args()

category_url = args.category if args.category else None
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
    API_URL = "http://127.0.0.1/api/products/batch"

STORE_ID = 13  # ETSport ID (novi store)
BATCH_SIZE = 50

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def build_category_urls():
    """Vraća sve kategorije za scraping ETSport sajta"""
    base_categories = [
        # Muškarci
        "https://www.etsport.rs/obuca/muskarci/",
        "https://www.etsport.rs/odeca/muskarci/",
        "https://www.etsport.rs/aksesoari/muskarci/",
        
        # Žene
        "https://www.etsport.rs/obuca/zene/",
        "https://www.etsport.rs/odeca/zene/",
        "https://www.etsport.rs/aksesoari/zene/",
        
        # Deca
        "https://www.etsport.rs/obuca/deca/",
        "https://www.etsport.rs/odeca/deca/",
        "https://www.etsport.rs/aksesoari/deca/"
    ]
    return base_categories

# Koristi specifičnu kategoriju ili sve
if category_url:
    CATEGORY_URLS = [category_url]
else:
    CATEGORY_URLS = build_category_urls()

def parse_price(price_str):
    """Parsira cenu iz RSD formata (npr. '5.455,45' ili '7.793,50')"""
    if not price_str:
        return 0.0
    
    try:
        import re
        # Ukloni sve što nije cifra, tačka ili zarez
        clean = re.sub(r'[^\d.,]', '', str(price_str))
        
        # Srpski format: 5.455,45 -> 5455.45
        if ',' in clean:
            # Sepija pre zareza su hiljade, posle su decimale
            parts = clean.rsplit(',', 1)  # Podeli po poslednjem zarez
            if len(parts) == 2:
                thousands_part = parts[0].replace('.', '')  # Ukloni tačke iz hiljada
                decimal_part = parts[1]
                clean = thousands_part + '.' + decimal_part
            else:
                clean = clean.replace(',', '.')
        else:
            # Samo tačke - ukloni ih jer su hiljade separatori
            clean = clean.replace('.', '')
        
        return float(clean)
    except Exception as e:
        print(f"[ERROR] Parsing price '{price_str}': {e}")
        return 0.0

def get_total_pages(soup, base_url):
    """ETSport koristi page-X format za paginaciju"""
    try:
        # Traži poslednju stranicu u paginaciji
        pagination = soup.find_all('a', href=True)
        max_page = 1
        
        for link in pagination:
            href = link.get('href', '')
            if 'page-' in href:
                try:
                    page_num = int(href.split('page-')[1].split('/')[0])
                    max_page = max(max_page, page_num)
                except:
                    continue
        
        # Ako nije našao stranice u linkovima, probaj da pronađeš brojeve stranica
        page_numbers = soup.find_all(lambda tag: tag.name and tag.string and tag.string.strip().isdigit())
        for num_tag in page_numbers:
            try:
                num = int(num_tag.string.strip())
                if num > max_page and num < 100:  # Razumna granica
                    max_page = num
            except:
                continue
        
        print(f"[INFO] Pronašao {max_page} stranica za {base_url}")
        return max_page
        
    except Exception as e:
        print(f"[ERROR] Error getting total pages: {e}")
        return 1

def extract_product_data(product_div):
    """Ekstraktuje podatke o proizvodu iz HTML div-a"""
    try:
        # Osnovni podaci iz data atributa
        product_id = product_div.get('data-productid')
        product_name = product_div.get('data-productname')
        product_code = product_div.get('data-productcode')
        product_brand = product_div.get('data-productbrand')
        product_category = product_div.get('data-productcat')
        product_price = product_div.get('data-productprice')  # Aktuelna cena
        product_old_price = product_div.get('data-productprevprice')  # Stara cena
        product_discount = product_div.get('data-productdiscount')
        
        if not product_name or not product_price:
            return None
        
        # URL proizvoda
        product_link = product_div.select_one('a[href]')
        product_url = product_link.get('href') if product_link else ''
        if product_url and not product_url.startswith('http'):
            product_url = 'https://www.etsport.rs' + product_url
        
        # Slika proizvoda
        img_elem = product_div.select_one('img')
        image_url = img_elem.get('src') if img_elem else ''
        if image_url and not image_url.startswith('http'):
            image_url = 'https://www.etsport.rs' + image_url
        
        # Parseovane cene
        current_price = parse_price(product_price)
        old_price = parse_price(product_old_price) if product_old_price else current_price
        
        # Proveri da li je na akciji
        discount_percent = 0
        if product_discount:
            try:
                discount_percent = int(product_discount)
            except:
                discount_percent = 0
        
        # Kreiraj objekat proizvoda - samo neophodna polja kao ExtraSport
        product = {
            'code': product_code or product_id,
            'naziv': product_name.strip() if product_name else '',
            'brand': product_brand.strip() if product_brand else '',
            'price': float(current_price) if current_price is not None else 0.0,
            'price_regular': float(old_price) if old_price is not None else None,
            'price_discount': float(current_price) if discount_percent > 0 else None,
            'price_old': float(old_price) if old_price is not None else None,
            'store_id': STORE_ID
        }
        
        return product
        
    except Exception as e:
        print(f"[ERROR] Extracting product data: {e}")
        return None

def scrape_page(url, page_num=None):
    """Scrape jednu stranicu proizvoda"""
    try:
        # Konstruiši URL za specifičnu stranicu
        if page_num and page_num > 1:
            if not url.endswith('/'):
                url += '/'
            page_url = f"{url}page-{page_num}"
        else:
            page_url = url
        
        print(f"[INFO] Scraping: {page_url}")
        
        response = requests.get(page_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        products = []
        
        # Pronađi sve proizvode - ETSport koristi specific class struktura
        product_cards = soup.select('div.nb-component.nb-product-card-19')
        
        if not product_cards:
            # Probaj alternativni selektor
            product_cards = soup.select('div[data-productid]')
        
        print(f"[INFO] Nađeno {len(product_cards)} proizvoda na stranici")
        
        for card in product_cards:
            product = extract_product_data(card)
            if product:
                products.append(product)
                print(f"[PRODUCT] {product['naziv']} - {product['price']} RSD")
            
            # Limit check
            if args.limit and len(products) >= args.limit:
                break
        
        return products, soup
        
    except Exception as e:
        print(f"[ERROR] Scraping page {page_url}: {e}")
        return [], None

def send_to_api(products):
    """Šalje proizvode u API po batch-evima"""
    if not products:
        print("[INFO] Nema proizvoda za slanje")
        return
    
    print(f"[DEBUG] API URL: {API_URL}")
    print(f"[DEBUG] Ukupno proizvoda za slanje: {len(products)}")
    print(f"[DEBUG] Batch size: {BATCH_SIZE}")
    
    # Ispis prvog proizvoda za proveru strukture
    if products:
        print(f"[DEBUG] Primer proizvoda: {json.dumps(products[0], ensure_ascii=False, indent=2)}")
    
    try:
        for i in range(0, len(products), BATCH_SIZE):
            batch = products[i:i + BATCH_SIZE]
            
            print(f"[API] Šaljem batch {i//BATCH_SIZE + 1} sa {len(batch)} proizvoda...")
            print(f"[DEBUG] Batch data size: {len(json.dumps(batch))} bytes")
            
            response = requests.post(
                API_URL, 
                json=batch,
                headers={"Accept": "application/json"}, 
                timeout=30
            )
            
            print(f"[DEBUG] Response status: {response.status_code}")
            print(f"[DEBUG] Response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                print(f"[API] Uspešno poslano {len(batch)} proizvoda")
                print(f"[DEBUG] Response: {response.text[:200]}")
            else:
                print(f"[ERROR] API error {response.status_code}: {response.text[:500]}")
            
            # Kratka pauza između batch-eva
            time.sleep(0.5)
            
    except Exception as e:
        print(f"[ERROR] Sending to API: {e}")
        import traceback
        traceback.print_exc()

def save_to_json(products, filename):
    """Sačuva proizvode u JSON fajl"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
        print(f"[INFO] Sačuvano {len(products)} proizvoda u {filename}")
    except Exception as e:
        print(f"[ERROR] Saving to JSON: {e}")

def main():
    """Glavna funkcija"""
    print(f"[INFO] ============= ETSport Scraper Start =============")
    print(f"[INFO] Platform: {platform.system()}")
    print(f"[INFO] Python version: {sys.version}")
    print(f"[INFO] Working directory: {os.getcwd()}")
    print(f"[INFO] Store ID: {STORE_ID}")
    print(f"[INFO] API URL: {API_URL}")
    print(f"[INFO] Kategorije: {len(CATEGORY_URLS)}")
    print(f"[INFO] Limit: {args.limit if args.limit else 'None'}")
    print(f"[INFO] Output file: {output_file if output_file else 'API'}")
    print(f"[INFO] ================================================\n")
    
    all_products = []
    
    for category_url in CATEGORY_URLS:
        print(f"\n[CATEGORY] Processing: {category_url}")
        
        # Scrape prvu stranicu da dobijemo ukupan broj stranica
        products, soup = scrape_page(category_url, 1)
        if products:
            all_products.extend(products)
        
        if not soup:
            print(f"[ERROR] Couldn't load first page for {category_url}")
            continue
        
        # Dobij ukupan broj stranica
        total_pages = get_total_pages(soup, category_url)
        
        # Scrape preostale stranice
        for page in range(2, total_pages + 1):
            if args.limit and len(all_products) >= args.limit:
                break
                
            products, _ = scrape_page(category_url, page)
            if products:
                all_products.extend(products)
            
            # Pauza između stranica
            time.sleep(1)
        
        print(f"[INFO] Kategorija završena. Ukupno proizvoda: {len(all_products)}")
        
        if args.limit and len(all_products) >= args.limit:
            break
    
    print(f"\n[SUMMARY] Ukupno pronađeno {len(all_products)} proizvoda")
    print(f"[DEBUG] Collected products from {len(set([p.get('category', 'Unknown') for p in all_products]))} categories")
    
    if output_file:
        print(f"[INFO] Čuvam u fajl: {output_file}")
        save_to_json(all_products, output_file)
    else:
        print(f"[INFO] Šaljem u API...")
        # Pošalji u API
        send_to_api(all_products)
    
    print("[INFO] ============= ETSport scraper završen! =============\n")

if __name__ == "__main__":
    main()