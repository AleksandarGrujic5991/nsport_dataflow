import sys
import os
import requests
from bs4 import BeautifulSoup
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
STORE_NAME = "Extra Sport"

headers = {
    "User-Agent": "Mozilla/5.0"
}

def parse_price(cena):
    import re
    if not cena:
        return 0.0
    
    # Srpski format: 12.399,19 (tačka za hiljade, zarez za decimale)
    # Prvo ukloni sve razmake
    cena = cena.strip()
    
    # Ako ima zarez, to je decimalna tačka u srpskom formatu
    if ',' in cena:
        # Podeli na deo pre zareza (hiljade) i posle zareza (decimale)
        parts = cena.split(',')
        if len(parts) == 2:
            # Ukloni tačke iz dela za hiljade (12.399 -> 12399)
            hiljade = re.sub(r'[^0-9]', '', parts[0])
            # Uzmi samo cifre iz decimalnog dela
            decimale = re.sub(r'[^0-9]', '', parts[1])
            # Ograniči decimale na 2 cifre
            if len(decimale) > 2:
                decimale = decimale[:2]
            elif len(decimale) == 1:
                decimale = decimale + '0'
            try:
                return float(f"{hiljade}.{decimale}")
            except:
                return 0.0
    
    # Ako nema zarez, pokušaj sa standardnim formatom (samo cifre)
    digits = re.sub(r'[^0-9]', '', cena)
    if not digits:
        return 0.0
    if len(digits) > 2:
        value = f"{digits[:-2]}.{digits[-2:]}"
    elif len(digits) == 2:
        value = f"0.{digits}"
    else:
        value = f"0.0{digits}"
    try:
        return float(value)
    except:
        return 0.0

def main():
    # KATEGORIJE - ULTRA MODE
    if '--category' in sys.argv:
        idx = sys.argv.index('--category')
        CATEGORY_URLS = [sys.argv[idx + 1]]
    else:
        CATEGORY_URLS = [
            "https://www.extrasports.com/SRB_rs/obuca/za-muskarce+unisex/",
            "https://www.extrasports.com/SRB_rs/odeca/za-muskarce+unisex/",
            "https://www.extrasports.com/SRB_rs/oprema/za-muskarce+unisex/",
            "https://www.extrasports.com/SRB_rs/obuca/unisex+za-zene/",
            "https://www.extrasports.com/SRB_rs/odeca/unisex+za-zene/",
            "https://www.extrasports.com/SRB_rs/oprema/za-zene+unisex/",
            "https://www.extrasports.com/SRB_rs/obuca/kids-boys+kids-girls+kids-other/",
            "https://www.extrasports.com/SRB_rs/odeca/kids-boys+kids-girls+kids-other/",
            "https://www.extrasports.com/SRB_rs/oprema/kids-boys+kids-girls+kids-other/"
        ]

    # Parsiranje --limit argumenta
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

    for base_url in CATEGORY_URLS:
        page = 1
        cat_count = 0
        batch = []
        
        # Processing category
        
        while True:
            url = base_url if page == 1 else f"{base_url}page-{page}/"
            # Processing page
            resp = requests.get(url, headers=headers)
            soup = BeautifulSoup(resp.text, "html.parser")

            products = soup.find_all("div", class_="wrapper-grid-view")
            products_on_page = 0

            for product in products:
                code = product.get("data-productcode")
                name = product.get("data-productname")
                price_str = product.get("data-productprice")
                price_old_str = product.get("data-productprevprice")
                discount_str = product.get("data-productdiscount")

                # Parsiranje brenda iz HTML-a
                brand = ""
                brand_div = product.find("div", class_="brand")
                if brand_div:
                    brand_link = brand_div.find("a")
                    if brand_link:
                        brand = brand_link.get_text().strip()

                price = parse_price(price_str) if price_str else None
                price_regular = parse_price(price_old_str) if price_old_str else None
                price_discount = price if discount_str and discount_str != "0" else None
                price_old = price_regular

                # DODANO: Progress tracking
                if total_count % 50 == 0 and total_count > 0:
                    pass  # Progress update

                if code and name and price:
                    payload = {
                        "code": code,
                        "naziv": name,
                        "brand": brand,  # Dodano polje za brend
                        "price": float(price) if price is not None else 0.0,
                        "price_regular": float(price_regular) if price_regular is not None else None,
                        "price_discount": float(price_discount) if price_discount is not None else None,
                        "price_old": float(price_old) if price_old is not None else None,
                        "store_id": 5
                    }
                    batch.append(payload)
                    cat_count += 1
                    total_count += 1
                    products_on_page += 1
                    
                    if len(batch) >= BATCH_SIZE:
                        response = requests.post(
                            API_URL,
                            json=batch,
                            headers={"Accept": "application/json"}
                        )
                        pass  # Batch sent
                        batch = []
                else:
                    pass  # Skipping invalid product

            # Provera za next dugme
            next_btn = soup.find("a", rel="next")
            if not next_btn or products_on_page == 0:
                break
            page += 1
            
    # Upisi preostale proizvode iz batcha
    if batch:
        response = requests.post(
            API_URL ,
            json=batch,
            headers={"Accept": "application/json"}
        )
        pass  # Final batch processed

    print(f"ExtraSport COMPLETED: {total_count} products")

if __name__ == "__main__":
    main()