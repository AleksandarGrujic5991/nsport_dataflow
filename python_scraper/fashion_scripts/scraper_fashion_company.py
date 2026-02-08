import pandas as pd
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.keys import Keys
import time
import json
import platform
import re
import os
import sys  # DODANO ZA ORCHESTRATOR
import math
import subprocess  # DODANO ZA ORCHESTRATOR
import tempfile
import uuid

# DODAJ OVO ODMAH POSLE IMPORTA!
input_excel = None
for i, arg in enumerate(sys.argv):
    if arg == "--input" and i + 1 < len(sys.argv):
        input_excel = sys.argv[i + 1]

if input_excel:
    EXCEL_FILE = os.path.abspath(input_excel)
else:
    EXCEL_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "fc_nsport_mapping.xlsx"))

mode_choice = None
for i, arg in enumerate(sys.argv):
    if arg == "--mode" and i + 1 < len(sys.argv):
        mode_choice = sys.argv[i + 1]

# Konfiguracija
if platform.system().lower() == "windows":
    API_URL = "http://127.0.0.1:8000/api/products/batch"
else:
    API_URL = "http://192.168.100.24/api/products/batch"
FC_BASE_URL = "https://www.fashionandfriends.com"
STORE_ID = 6

# DODANO ZA ORCHESTRATOR
def run_fashion_scraper():
    """Entry point za orchestrator"""
    print("🚀 Fashion & Friends Scraper Started")
    
    try:
        create_store()
        scrape_fixed()
        print("[OK]  Fashion scraper completed successfully")
        return True
    except Exception as e:
        print(f"[ERROR]  Fashion scraper failed: {e}")
        return False

def setup_driver_fixed(headless=True, instance_num=1):
    options = ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-logging")
    options.add_argument("--log-level=3")
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    # Dodaj jedinstveni user-data-dir za svaku instancu
    import tempfile, uuid, shutil, time
    tmp_dir = tempfile.gettempdir()
    user_data_dir = os.path.join(tmp_dir, f"user_data_fashion_{instance_num}_{uuid.uuid4().hex}_{int(time.time()*1000)}")
    if os.path.exists(user_data_dir):
        shutil.rmtree(user_data_dir, ignore_errors=True)
    options.add_argument(f"--user-data-dir={user_data_dir}")
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(3)
    driver.set_page_load_timeout(12)
    return driver

def search_fixed(driver, fc_code):
    """Ispravljena pretraga koja radi"""
    try:
        # 1. Homepage prvo za cookies
        driver.get(FC_BASE_URL)
        time.sleep(1)
        
        # 2. Handle cookies
        handle_cookies_fast(driver)
        
        # 3. Search input
        search_input = None
        for selector in ["input[name='q']", "input[type='search']"]:
            try:
                search_input = driver.find_element(By.CSS_SELECTOR, selector)
                if search_input.is_displayed():
                    break
            except:
                continue
        
        if not search_input:
            return {'found': False}
        
        # 4. Search
        search_input.clear()
        search_input.send_keys(fc_code)
        search_input.send_keys(Keys.RETURN)
        time.sleep(2)
        
        # 5. Check results
        current_url = driver.current_url.lower()
        
        if '/rs/' in current_url and 'catalogsearch' not in current_url:
            # Product page
            return extract_fixed(driver)
        else:
            # Search results
            try:
                # Wait for products to load
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".product-item"))
                )
                
                first_link = driver.find_element(By.CSS_SELECTOR, ".product-item a")
                driver.get(first_link.get_attribute("href"))
                time.sleep(2)
                
                return extract_fixed(driver)
            except:
                return {'found': False}
        
    except:
        return {'found': False}

def handle_cookies_fast(driver):
    """Brzo cookies handling"""
    try:
        time.sleep(0.5)
        
        # JavaScript cleanup
        driver.execute_script("""
            var popup = document.querySelector('#cmpbox, .cmpbox');
            if (popup) popup.remove();
        """)
        
        # Click accept if visible
        try:
            btn = driver.find_element(By.CSS_SELECTOR, ".cmpboxbtnyes, #cmpwelcomebtnyes")
            if btn.is_displayed():
                btn.click()
                time.sleep(0.5)
        except:
            pass
    except:
        pass

def extract_fixed(driver, debug=False):
    """Ispravljena ekstrakcija - BEZ DEBUG LOGOVA za brzinu"""
    try:
        # Wait for page to load
        time.sleep(1)
        
        # Naziv
        naziv = ""
        for selector in ["h1", ".page-title"]:
            try:
                element = driver.find_element(By.CSS_SELECTOR, selector)
                naziv = element.text.strip()
                if naziv and len(naziv) > 5:
                    break
            except:
                continue
        
        if not naziv:
            return {'found': False}
        
        # Cena - pokusaj sa wait
        price = None
        price_selectors = [
            ".price-container.price-final_price .price",
            ".price-final_price .price", 
            ".price-container .price",
            ".price"
        ]
        
        for selector in price_selectors:
            try:
                # Wait for price element
                price_el = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                
                price_text = price_el.text.strip()
                
                if debug:
                    print(f"Debug price text: '{price_text}'")
                
                if price_text and any(char.isdigit() for char in price_text):
                    # Parse Serbian format
                    price_match = re.search(r'(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)', price_text)
                    if price_match:
                        price_str = price_match.group(1)
                        
                        if '.' in price_str and ',' in price_str:
                            price = float(price_str.replace('.', '').replace(',', '.'))
                        elif ',' in price_str:
                            price = float(price_str.replace(',', '.'))
                        else:
                            price = float(price_str.replace('.', ''))
                        
                        if price > 50:
                            break
                            
            except:
                continue
        
        if debug:
            print(f"Debug extracted: naziv='{naziv}' price={price}")
        
        if naziv and price and price > 50:
            return {
                'naziv': naziv,
                'price': price,
                'found': True
            }
        
        return {'found': False}
        
    except:
        return {'found': False}

def test_debug():
    """Debug test sa GUI"""
    print("🔍 DEBUG TEST SA GUI")
    
    driver = setup_driver_fixed(headless=False)
    
    try:
        fc_code = "SDM1110439A-2DI"
        print(f"Testing: {fc_code}")
        
        # Extract sa debug = True
        driver.get(FC_BASE_URL)
        handle_cookies_fast(driver)
        search_input = driver.find_element(By.CSS_SELECTOR, "input[name='q']")
        search_input.send_keys(fc_code)
        search_input.send_keys(Keys.RETURN)
        time.sleep(3)
        
        result = extract_fixed(driver, debug=True)  # SA DEBUG
        
        print(f"Result: {result}")
        input("Press Enter to close...")
        
    finally:
        driver.quit()

def test_fixed_speed():
    """Test ispravljene brzine - BEZ DEBUG-a"""
    print("🔧 FIXED SPEED TEST")
    
    test_codes = ['SDM1110439A-2DI', 'SDM1011245A-G8R', 'SDM1012078A-01C']
    
    driver = setup_driver_fixed(headless=True)
    start_time = time.time()
    
    results = 0
    
    try:
        for i, fc_code in enumerate(test_codes, 1):
            print(f"[{i}] {fc_code}", end=" -> ")
            
            result = search_fixed(driver, fc_code)  # BEZ DEBUG-a
            
            if result['found']:
                print(f"[OK]  {result['naziv'][:30]} - {result['price']}")
                results += 1
            else:
                print("[ERROR] ")
            
    finally:
        driver.quit()
        elapsed = time.time() - start_time
        rate = len(test_codes) / elapsed
        print(f"\n🔧 {elapsed:.1f}s | {rate:.2f}/s | {results}/{len(test_codes)} found")
        print(f" Procenjena brzina za 470 proizvoda: {470/rate/60:.1f} minuta")

def scrape_fixed():
    """Scraper sa ispravkama - PRODUKCIJSKA VERZIJA"""
    print("🚀 Fashion and Friends - PRODUKCIJSKA VERZIJA")
    
    mapping = load_excel_mapping()
    if not mapping:
        print("[ERROR]  Nema mapiranja")
        return
    
    # PODELA PO INSTANCAMA
    instance_num = 1
    total_instances = 1
    if "--instance" in sys.argv:
        idx = sys.argv.index("--instance")
        instance_arg = sys.argv[idx + 1].strip().replace("\\", "")
        instance_num = int(instance_arg)
        total_instances = 8  # ili koliko pokreces

    fc_codes = list(mapping.keys())
    chunk_size = math.ceil(len(fc_codes) / total_instances)
    start = (instance_num - 1) * chunk_size
    end = start + chunk_size
    fc_codes = fc_codes[start:end]
    print(f" Instance {instance_num}/{total_instances} radi {len(fc_codes)} proizvoda")

    driver = setup_driver_fixed(headless=True, instance_num=instance_num)
    
    products_batch = []
    processed = 0
    found_count = 0
    start_time = time.time()
    
    try:
        for fc_code in fc_codes:
            nsport_code = mapping[fc_code]
            processed += 1
            
            # Kratki progress
            print(f"[{processed}/{len(mapping)}] {fc_code[:12]}", end="->", flush=True)
            
            product_data = search_fixed(driver, fc_code)
            
            if product_data['found']:
                found_count += 1
                print(f"[OK]  {product_data['price']}")
                
                products_batch.append({
                    'code': nsport_code,
                    'naziv': product_data['naziv'],
                    'price': product_data['price'],
                    'store_id': STORE_ID
                })
                
                if len(products_batch) >= 10:
                    send_ultra_fast(products_batch)
                    products_batch = []
            else:
                print("[ERROR] ")
            
            # Stats svakih 25
            if processed % 25 == 0:
                elapsed = time.time() - start_time
                rate = processed / elapsed * 60
                success = (found_count / processed) * 100
                remaining = (len(mapping) - processed) / (processed / elapsed) / 60 if processed > 0 else 0
                print(f"\n {processed}/{len(mapping)} | {found_count} found | {success:.0f}% | {rate:.0f}/min | ETA: {remaining:.0f}min\n")
            
            time.sleep(0.5)  # Kratka pauza
    
    except KeyboardInterrupt:
        print("\nWARNING:  Prekinuto")
    
    finally:
        if products_batch:
            send_ultra_fast(products_batch)
        
        driver.quit()
        
        elapsed = time.time() - start_time
        success_rate = (found_count / processed) * 100 if processed > 0 else 0
        print(f"\n🎉 ZAVRSENO!")
        print(f"⏱️ Vreme: {elapsed/60:.1f} minuta")
        print(f" Ukupno: {processed} | Pronadeno: {found_count} | Uspesnost: {success_rate:.1f}%")
        print(f"Total products processed: {found_count}")

def send_ultra_fast(products_batch):
    """Ultra brzo slanje"""
    try:
        print(f"{len(products_batch)}", end="", flush=True)
        response = requests.post(API_URL, json=products_batch, timeout=10)
        print("[OK] " if response.status_code == 200 else f"[ERROR] {response.status_code}")
    except Exception as e:
        with open(f"backup_{int(time.time())}.json", 'w') as f:
            json.dump(products_batch, f)
        print("")

def load_excel_mapping():
    """Ucitaj Excel mapiranje"""
    if not os.path.exists(EXCEL_FILE):
        print("Excel fajl ne postoji!")
        return {
            'SDM1110439A-2DI': 'M1110439A-2DI',
            'SDM1011245A-G8R': 'M1011245A-G8R',
            'SDM1012078A-01C': 'M1012078A-01C'
        }
    
    try:
        df = pd.read_excel(EXCEL_FILE)
        print("Kolone:", df.columns)
        print("Broj redova:", len(df))
        mapping = {}
        for _, row in df.iterrows():
            fc_code = str(row['FC SIFRA']).strip()
            nsport_code = str(row['N SPORT SIFRA']).strip()
            if fc_code and nsport_code and fc_code != 'nan' and nsport_code != 'nan':
                mapping[fc_code] = nsport_code
        print("Broj mapiranih:", len(mapping))
        return mapping
    except Exception as e:
        print("Greska pri ucitavanju Excel fajla:", e)
        return {}

def create_store():
    try:
        requests.post(
            "http://192.168.100.24/api/stores", 
            json={"id": STORE_ID, "naziv": "Fashion and Friends", "url": FC_BASE_URL},
            timeout=5
        )
    except:
        pass

# IZMENJENO ZA ORCHESTRATOR
if __name__ == "__main__":
    # Proveri da li je pokrenut od orchestrator-a
    if len(sys.argv) > 1 and sys.argv[1] == "--orchestrator":
        os.chdir("/var/www/dataFlow")  # <-- PROMENI PUTANJU
        success = run_fashion_scraper()
        sys.exit(0 if success else 1)
    else:
        os.chdir("/var/www/dataFlow")  # <-- PROMENI PUTANJU

        print("🚀 Fashion and Friends - FINALNA OPTIMIZOVANA VERZIJA")
        print("=" * 55)

        create_store()

        print("1. 🚀 PRODUKCIJSKI scraper - SVI PROIZVODI")
        print("2. 🔧 Speed test - 3 proizvoda") 
        print("3. 🔍 Debug test (GUI)")

        if mode_choice is None:
            choice = input("Izbor (1/2/3): ").strip()
        else:
            choice = mode_choice

        if choice == "2":
            test_fixed_speed()
        elif choice == "3":
            test_debug()
        else:
            scrape_fixed()

        # DODANO ZA ORCHESTRATOR
        # Pokretanje vise instanci
        # for i in range(1, 9):  # ili koliko zelis
        #     subprocess.Popen([
        #         "python", "python_scraper/fashion_scripts/scraper_fashion_company.py",
        #         "--orchestrator", "--instance", str(i)
        #     ])