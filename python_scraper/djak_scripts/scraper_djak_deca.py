import sys

import os
import time
import requests
import argparse
import re
import json
import signal
import atexit
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import tempfile
from webdriver_manager.chrome import ChromeDriverManager
import uuid
import random
import undetected_chromedriver as uc
import platform

# Argument parsing
parser = argparse.ArgumentParser()
parser.add_argument('--limit', type=int, help='Limit broj proizvoda')
parser.add_argument('--headless', action='store_true', help='Run in headless mode')
parser.add_argument('--output', type=str, help='Output JSON file')
parser.add_argument('--instance', type=int, help='Instance number')
args = parser.parse_args()

# HARDKODOVANA KATEGORIJA - DECA
CATEGORY_URLS = ['https://www.djaksport.com/deca']

if platform.system().lower() == "windows":
    API_URL = "http://127.0.0.1:8000/api/products/batch"
else:
    API_URL = "http://192.168.100.24/api/products/batch"
STORE_ID = 3

# Global driver za cleanup
global_driver = None

def cleanup_driver():
    """Cleanup funkcija za zatvaranje driver-a"""
    global global_driver
    if global_driver:
        try:
            print("[CLEANUP] Zatvaranje Chrome driver-a...")
            global_driver.quit()
            global_driver = None
        except Exception as e:
            print(f"[CLEANUP] Greška pri zatvaranju driver-a: {e}")

def signal_handler(signum, frame):
    """Handler za signale (SIGINT, SIGTERM)"""
    print(f"[SIGNAL] Primljen signal {signum}, zatvaranje...")
    cleanup_driver()
    sys.exit(0)

# Registruj signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
atexit.register(cleanup_driver)

def parse_price(price_text):
    """Parsira cenu iz teksta"""
    if not price_text:
        return None
    try:
        # Prvo ukloni sve sto nije broj, zarez ili tacka
        clean_text = re.sub(r'[^0-9,.]', '', price_text)
        
        # Ako imamo format kao "4.399,00" (evropski)
        if ',' in clean_text and '.' in clean_text:
            # Ukloni tacke (hiljade) i zarez zameju decimalnom tackom
            clean_text = clean_text.replace('.', '').replace(',', '.')
        # Ako imamo samo zarez, to je decimalna tacka
        elif ',' in clean_text and '.' not in clean_text:
            clean_text = clean_text.replace(',', '.')
        
        if not clean_text:
            return None
            
        return float(clean_text)
    except:
        return None

def setup_driver(headless=True):
    """Setup Chrome WebDriver sa stealth opcijama - HYBRID verzija"""
    options = uc.ChromeOptions()
    if headless:
        options.headless = True
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=sr-RS")
    options.add_argument("--accept-language=sr-RS,sr;q=0.9,en-US;q=0.8,en;q=0.7")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")

    tmp_dir = tempfile.gettempdir()
    user_data_dir = os.path.join(tmp_dir, f"chrome_user_data_djak_{uuid.uuid4().hex}")
    import shutil
    if os.path.exists(user_data_dir):
        shutil.rmtree(user_data_dir, ignore_errors=True)
    os.makedirs(user_data_dir, exist_ok=True)
    options.add_argument(f"--user-data-dir={user_data_dir}")

    try:
        # JEDNOSTAVAN SETUP - kao u radnoj verziji
        chromedriver_path = ChromeDriverManager().install()
        os.chmod(chromedriver_path, 0o755)
        patcher_path = os.path.join(tmp_dir, f"undetected_chromedriver_patch_{uuid.uuid4().hex}.exe")
        driver = uc.Chrome(
            options=options,
            driver_executable_path=chromedriver_path,
            patcher_force_close=True,
            patcher_executable_path=patcher_path
        )
        return driver
    except Exception as e:
        print(f"[ERROR]  Error creating WebDriver: {e}")
        return None

def extract_product_code(product_element):
    """Ekstraktuje sifru proizvoda iz razlicitih atributa - robusna verzija za zene sekciju"""
    try:
        # Metod 1: Iz div.product-item-info class atributa (druga klasa je SKU)
        try:
            product_info_div = product_element.find_element(By.CSS_SELECTOR, "div.product-item-info")
            class_attr = product_info_div.get_attribute("class")
            if class_attr:
                parts = class_attr.strip().split()
                # Trazi drugu klasu koja nije 'product-item-info'
                for part in parts:
                    if part != "product-item-info" and len(part) >= 4:
                        # Validacija sifre - prihvati i samo numericke (kao 107952) i alfanumericke
                        if re.match(r'^[A-Za-z0-9\-_]+$', part) and re.search(r'[0-9]', part):
                            return part.upper()
        except:
            pass
        
        # Metod 2: Iz quick-shopping dugmeta (id atribut)
        try:
            quick_shopping = product_element.find_element(By.CSS_SELECTOR, ".quick-shopping-open-btn")
            sku_id = quick_shopping.get_attribute("id")
            if sku_id and len(sku_id) > 3:
                # Ako je dugacka verzija, pokusaj da ekstraktujes kratki SKU sa kraja
                if len(sku_id) > 20:  # Dugacka verzija kao SANDALA-KLOMPA-CLASSIC-PLATFORM-CLOG-ZA-ZENE-211231-6ZW
                    # Pokusaj razlicite regex paterne za SKU ekstraktovanje
                    patterns = [
                        r'([A-Z0-9]+[-_][A-Z0-9]+)$',  # 211231-6ZW format
                        r'([0-9]{5,}-[A-Z0-9]+)$',     # 206750-100 format 
                        r'([A-Z0-9]{3,}[-_][A-Z0-9]{3,})$',  # bar 3 karaktera sa obe strane
                        r'-([A-Z0-9]+[-_][A-Z0-9]+)$'  # sa crticom na pocetku
                    ]
                    
                    for pattern in patterns:
                        match = re.search(pattern, sku_id.upper())
                        if match:
                            short_sku = match.group(1) if match.groups() else match.group(0)
                            # Validacija da je pravilno formatiran SKU
                            if re.search(r'[A-Z0-9]', short_sku) and '-' in short_sku and len(short_sku) > 4:
                                return short_sku
                
                # Validacija SKU formata za kracu verziju
                # Prihvati i samo numericke sifre (kao 107952) i alfanumericke
                if re.match(r'^[A-Za-z0-9\-_]+$', sku_id) and len(sku_id) >= 4:
                    # Prihvati ako ima brojeve (i opciono slova)
                    if re.search(r'[0-9]', sku_id):
                        return sku_id.upper()
        except:
            pass
        
        # Metod 3: Iz URL linka - poslednji segment
        try:
            link_elem = product_element.find_element(By.CSS_SELECTOR, "a.product-item-link")
            href = link_elem.get_attribute("href")
            if href:
                # Izvuci SKU iz URL-a - poslednji deo nakon poslednje crtice
                url_parts = href.rstrip('/').split('/')
                if url_parts:
                    last_segment = url_parts[-1]
                    
                    # Pokusaj razlicite regex paterne za SKU sa kraja URL-a
                    patterns = [
                        r'([A-Z0-9]+[-_][A-Z0-9]+)$',  # 211231-6ZW format
                        r'([0-9]{5,}-[A-Z0-9]+)$',     # 206750-100 format 
                        r'([A-Z0-9]{3,}[-_][A-Z0-9]{3,})$',  # bar 3 karaktera sa obe strane
                        r'-([A-Z0-9]+[-_][A-Z0-9]+)$'  # sa crticom na pocetku
                    ]
                    
                    for pattern in patterns:
                        match = re.search(pattern, last_segment.upper())
                        if match:
                            potential_sku = match.group(1) if match.groups() else match.group(0)
                            # Ignorisi genericke prefikse
                            if potential_sku.startswith(('ZENE-', 'MUSKARCI-', 'DECA-')):
                                continue
                            # Validacija da li izgleda kao SKU
                            if re.search(r'[A-Z0-9]', potential_sku) and '-' in potential_sku and len(potential_sku) > 4:
                                return potential_sku
                    
                    # Fallback 1 - trazi kratak pattern na kraju (max 15 karaktera)
                    match = re.search(r'-([A-Za-z0-9\-_]{4,15})$', last_segment)
                    if match:
                        potential_sku = match.group(1).upper()
                        # Ignorisi genericke pattern-e i ukloni "ZENE-" prefiks
                        if potential_sku.startswith('ZENE-'):
                            potential_sku = potential_sku[5:]  # ukloni "ZENE-"
                        if not any(generic in potential_sku for generic in ['ZA-ZENE', 'CONTAINER', 'IMAGE', 'PRODUCT']):
                            if len(potential_sku) <= 15 and potential_sku.count('-') <= 3:
                                # Validacija da li izgleda kao SKU
                                if re.search(r'[A-Za-z0-9]', potential_sku) and len(potential_sku) >= 4:
                                    return potential_sku
                    
                    # Fallback 2 - izvuci broj sa kraja kao SKU
                    number_match = re.search(r'([0-9]{6,})$', last_segment)
                    if number_match:
                        return number_match.group(1)
        except:
            pass
            
        # Metod 4: Iz data atributa (fallback)
        data_attrs = ['data-product-id', 'data-sku', 'data-code']
        for attr in data_attrs:
            value = product_element.get_attribute(attr)
            if value and len(value) > 3:
                if re.match(r'^[A-Za-z0-9\-_]+$', value) and re.search(r'[A-Za-z]', value):
                    return value.upper()
                    
        # Metod 5: Fallback - trazi bilo koji element sa SKU pattern-om
        try:
            # Trazi sve elemente koji mogu sadrzavati SKU
            potential_elements = product_element.find_elements(By.CSS_SELECTOR, "[id*='-'], [class*='-']")
            for elem in potential_elements[:5]:  # ogranici na prvih 5
                for attr in ['id', 'class']:
                    attr_value = elem.get_attribute(attr)
                    if attr_value:
                        # Trazi SKU pattern u atributu
                        matches = re.findall(r'[A-Za-z][A-Za-z0-9\-_]{4,}', attr_value)
                        for match in matches:
                            if re.search(r'[0-9]', match) and len(match) > 4:
                                return match.upper()
        except:
            pass
            
    except Exception as e:
        print(f"WARNING:   Error extracting product code: {e}")
    
    return None

def scrape_category(category_url, driver, limit=None, all_products=None):
    """Scrape-uje jednu Djak kategoriju"""
    category_name = category_url.split('/')[-1]
    page = 1
    cat_count = 0
    batch = []
    BATCH_SIZE = 50  # Vraćeno na 50 kao u radnoj verziji
    
    while True:
        url = f"{category_url}?p={page}"
        
        try:
            driver.get(url)
            time.sleep(0.3)  # optimized: smanji sa 1 na 0.3
            
            # Cekaj da se proizvodi ucitaju - optimized timeout
            try:
                WebDriverWait(driver, 3).until(  # smanji sa 5 na 3
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.product-item-info"))
                )
            except:
                print("WARNING:   Products didn't load in reasonable time")
                break
            
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.2)  # optimized: smanji sa 0.5 na 0.2
            
            # Pronadi sve proizvode
            products = driver.find_elements(By.CSS_SELECTOR, "div.product-item-info")
            
            if not products:
                break
            
            products_on_page = 0
            for i, product in enumerate(products):
                try:
                    # Sifra proizvoda
                    code = extract_product_code(product)
                    if not code:
                        print(f"[ERROR]  Product {i+1}: No code found")
                        continue
                    
                    # Naziv proizvoda - sacekaj da se ucita i ocisti tekst
                    name = None
                    try:
                        # Sacekaj da se element ucita
                        name_elem = WebDriverWait(product, 2).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "a.product-item-link"))
                        )
                        
                        # Pokusaj razlicite nacine citanja teksta
                        name = name_elem.text.strip()
                        if not name:
                            name = name_elem.get_attribute('textContent').strip()
                        if not name:
                            name = name_elem.get_attribute('innerHTML').strip()
                        if not name:
                            name = name_elem.get_attribute('title')
                            
                        # Dodatno ciscenje - ukloni visestruke razmake
                        if name:
                            import re
                            name = re.sub(r'\s+', ' ', name).strip()
                            
                    except:
                        try:
                            name_elem = product.find_element(By.CSS_SELECTOR, "strong.product-name a")
                            name = name_elem.text.strip()
                            if name:
                                import re
                                name = re.sub(r'\s+', ' ', name).strip()
                        except:
                            try:
                                # Fallback na alt iz slike
                                img_elem = product.find_element(By.CSS_SELECTOR, "img.product-image-photo")
                                name = img_elem.get_attribute('alt')
                            except:
                                print(f"[ERROR]  Product {code}: No name found")
                                continue
                    
                    # Trenutna cena - prioritet na text parsing kao u radnoj verziji
                    current_price = None
                    try:
                        # PRIORITET: span.price text unutar price-wrapper
                        price_wrapper = product.find_element(By.CSS_SELECTOR, "span[data-price-type='finalPrice'].price-wrapper")
                        price_elem = price_wrapper.find_element(By.CSS_SELECTOR, "span.price")
                        price_text = price_elem.text.strip()
                        if price_text:  # Samo ako nije prazan
                            current_price = parse_price(price_text)
                        else:
                            raise Exception("Empty price text")
                    except Exception as e:
                        try:
                            # Fallback na bilo koji span.price
                            price_elem = product.find_element(By.CSS_SELECTOR, "span.price")
                            price_text = price_elem.text.strip()
                            if price_text:  # Samo ako nije prazan
                                current_price = parse_price(price_text)
                            else:
                                raise Exception("Empty price text")
                        except Exception as e:
                            try:
                                # Tek onda data-price-amount (vec u dinarima)
                                price_elem = product.find_element(By.CSS_SELECTOR, "span[data-price-amount][data-price-type='finalPrice']")
                                price_amount = price_elem.get_attribute('data-price-amount')
                                if price_amount:
                                    current_price = float(price_amount)  # vec je u dinarima
                            except Exception as e:
                                try:
                                    # Pokusaj bilo koji element sa price
                                    price_elem = product.find_element(By.CSS_SELECTOR, "[class*='price']")
                                    price_text = price_elem.text.strip()
                                    if price_text:
                                        current_price = parse_price(price_text)
                                    else:
                                        raise Exception("Empty price text")
                                except Exception as e:
                                    print(f"[ERROR]  Product {code}: No price found")
                                    continue
                    
                    # Stara cena - prioritet na text parsing
                    old_price = None
                    try:
                        # Pokusaj text iz span.price (prioritet)
                        old_price_elem = product.find_element(By.CSS_SELECTOR, "span[data-price-type='oldPrice'] span.price")
                        old_price = parse_price(old_price_elem.text)
                    except:
                        try:
                            # Fallback na data-price-amount za staru cenu
                            old_price_elem = product.find_element(By.CSS_SELECTOR, "span[data-price-amount][data-price-type='oldPrice']")
                            old_price_amount = old_price_elem.get_attribute('data-price-amount')
                            if old_price_amount:
                                old_price = float(old_price_amount) / 100  # konvertuj pare u dinare
                        except:
                            pass
                    
                    # Debug output za skipped proizvode
                    if not code:
                        print(f"WARNING:   Skipping product {i+1}: no code")
                        continue
                    elif not name or name.strip() == "":
                        print(f"WARNING:   Skipping product {i+1}: code={code}, name='{name}', price={current_price}")
                        continue  
                    elif current_price is None:
                        print(f"WARNING:   Skipping product {i+1}: code={code}, name={name[:30] if name else 'None'}, price=None")
                        continue
                        
                    # Kreiranje payload-a
                    if code and name and current_price is not None:
                        payload = {
                            'code': code,
                            'naziv': name,
                            'price': float(current_price) if current_price is not None else 0.0,
                            'price_regular': float(old_price) if old_price is not None else None,
                            'price_discount': float(current_price) if old_price and old_price > current_price else None,
                            'price_old': float(old_price) if old_price is not None else None,
                            'store_id': STORE_ID
                        }
                        batch.append(payload)
                        if all_products is not None:
                            all_products.append(payload)
                        cat_count += 1
                        products_on_page += 1

                        # Product added
                        
                        # Batch sending - optimized
                        if len(batch) >= BATCH_SIZE:
                            try:
                                response = requests.post(
                                    API_URL,
                                    json=batch,
                                    headers={"Accept": "application/json"},
                                    timeout=15  # reduced timeout from 30 to 15
                                )
                                if response.status_code != 200:
                                    print(f'[ERROR]  API error: {response.text}')
                                else:
                                    print(f'[SUCCESS] Sent batch of {len(batch)} products')
                            except Exception as e:
                                print(f'[ERROR]  Request error: {e}')
                            
                            # Memory cleanup
                            batch.clear()
                            import gc
                            gc.collect()
                        
                        if limit and cat_count >= limit:
                            break
                    else:
                        print(f"WARNING:   Skipping product {i+1}: code={code}, name={name}, price={current_price}")
                
                except Exception as e:
                    pass  # Product log removed
                    continue
            
            print(f" Page {page}: processed {products_on_page} products")
            
            if limit and cat_count >= limit:
                break
            
            # Check for next page
            try:
                next_btn = driver.find_element(By.CSS_SELECTOR, "a.action.next")
                next_url = next_btn.get_attribute("href")
                if not next_url or not next_btn.is_enabled():
                    print("No next page available")
                    break
            except:
                print("No next page button found")
                break
            
            page += 1
        
        except Exception as e:
            print(f"[ERROR]  Error on page {page}: {e}")
            break
        
        if "You have been blocked" in driver.page_source or "Cloudflare" in driver.page_source:
            print("[ERROR]  Blocked by site protection! Stopping scraper.")
            break
    
    # Send final batch - optimized
    if batch:
        print(f'🔄 Sending final batch of {len(batch)} products...')
        try:
            response = requests.post(
                API_URL,
                json=batch,
                headers={"Accept": "application/json"},
                timeout=15  # reduced timeout from 30 to 15
            )
            print(f'[OK]  Final API response: {response.status_code}')
            if response.status_code != 200:
                print(f'[ERROR]  Final API error: {response.text}')
        except Exception as e:
            print(f'[ERROR]  Final request error: {e}')
    
    print(f" Category {category_name} completed: {cat_count} products")
    return cat_count

def main():
    global global_driver
    print("PYTHON:", sys.executable)
    print("CWD:", os.getcwd())
    print("ARGS:", sys.argv)
    print("ENV DISPLAY:", os.getenv('DISPLAY', 'NOT SET'))
    print("ENV PATH:", os.getenv('PATH', 'NOT SET')[:100] + "..." if os.getenv('PATH') else 'NOT SET')
    print("Djak DECA Scraper Starting...")
    print(f"Total categories: {len(CATEGORY_URLS)}")
    
    # Debug URL-ovi
    for i, url in enumerate(CATEGORY_URLS):
        print(f"   Category {i+1}: {url}")

    categories_to_process = CATEGORY_URLS

    global_driver = setup_driver(headless=args.headless)
    if not global_driver:
        print("[ERROR]  Cannot create WebDriver")
        return

    total_products = 0
    all_products = []

    try:
        # Process only deca category
        category_url = categories_to_process[0]
        print(f"\n Processing category: {category_url}")
        cat_products = scrape_category(category_url, global_driver, args.limit, all_products)
        total_products += cat_products
    except Exception as e:
        print(f"Main error: {e}")

    finally:
        cleanup_driver()

        print(f"\n Djak DECA Scraper COMPLETED!")
        print(f" Total products processed: {total_products}")
        print(f"Categories processed: {len(categories_to_process)}")
        if args.output:
            try:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(all_products, f, ensure_ascii=False, indent=2)
                print(f" Saved {len(all_products)} products to {args.output}")
            except Exception as e:
                print(f"[ERROR]  Error saving to {args.output}: {e}")

if __name__ == "__main__":
    main()