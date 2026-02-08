#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import time
import requests
import argparse
import re
import json
import signal
import atexit
import gc
import psutil
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
import pickle

# Argument parsing
parser = argparse.ArgumentParser()
parser.add_argument('--limit', type=int, help='Limit broj proizvoda')
parser.add_argument('--headless', action='store_true', help='Run in headless mode')
parser.add_argument('--category', type=str, help='Category URL')
parser.add_argument('--output', type=str, help='Output JSON file')
args = parser.parse_args()

# API konfiguracija
if platform.system().lower() == "windows":
    API_URL = "http://127.0.0.1:8000/api/products/batch"
else:
    API_URL = "http://192.168.100.24/api/products/batch"
STORE_ID = 3

def save_cookies(driver, filename="djak_cookies.pkl"):
    """Save cookies za održavanje sesije"""
    try:
        cookies = driver.get_cookies()
        cookie_file = os.path.join(tempfile.gettempdir(), filename)
        with open(cookie_file, "wb") as f:
            pickle.dump(cookies, f)
        print(f"   Cookies saved to {cookie_file}")
    except Exception as e:
        print(f"   Failed to save cookies: {e}")

def load_cookies(driver, filename="djak_cookies.pkl"):
    """Load cookies za održavanje sesije"""
    try:
        cookie_file = os.path.join(tempfile.gettempdir(), filename)
        if os.path.exists(cookie_file):
            with open(cookie_file, "rb") as f:
                cookies = pickle.load(f)
            for cookie in cookies:
                try:
                    driver.add_cookie(cookie)
                except:
                    pass  # Ignoriši nevalidne cookies
            print(f"   Cookies loaded from {cookie_file}")
            return True
    except Exception as e:
        print(f"   Failed to load cookies: {e}")
    return False

def cleanup_chrome_processes():
    """Kill hanging Chrome processes"""
    try:
        import subprocess
        # Windows command to kill Chrome
        subprocess.run("taskkill /f /im chrome.exe 2>nul", shell=True, capture_output=True)
        subprocess.run("taskkill /f /im chromedriver.exe 2>nul", shell=True, capture_output=True)
    except:
        pass

# Default kategorije ako nije prosleđena
DEFAULT_CATEGORIES = [
    'https://www.djaksport.com/deca',
    'https://www.djaksport.com/muskarci',
    'https://www.djaksport.com/zene'
]

# Global driver za cleanup
global_driver = None

def cleanup_driver():
    """Cleanup WebDriver and all chrome processes"""
    global global_driver
    
    if global_driver:
        try:
            global_driver.quit()
        except:
            pass
        finally:
            global_driver = None
    
    # Kill any remaining chrome processes
    cleanup_chrome_processes()
    
    # Force garbage collection
    gc.collect()

def aggressive_cleanup():
    """Ultra agresivno čišćenje system resources"""
    print("🧹 Performing aggressive cleanup...")
    
    # Cleanup driver
    cleanup_driver()
    
    # Kill all Chrome processes
    cleanup_chrome_processes()
    
    # Clear Python garbage
    collected = gc.collect()
    print(f"   Garbage collected: {collected} objects")
    
    # Show memory usage
    mem_usage = get_memory_usage()
    print(f"   Memory usage after cleanup: {mem_usage:.1f}MB")

def signal_handler(signum, frame):
    """Handler za signale (SIGINT, SIGTERM)"""
    print(f"[SIGNAL] Primljen signal {signum}, zatvaranje...")
    cleanup_driver()
    sys.exit(0)

# Registruj signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
atexit.register(cleanup_driver)

def setup_driver(headless=True):
    """Setup Chrome WebDriver sa persistent session i enhanced stealth opcijama"""
    options = uc.ChromeOptions()
    if headless:
        options.headless = True
    
    # Basic stealth options
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=sr-RS")
    options.add_argument("--accept-language=sr-RS,sr;q=0.9,en-US;q=0.8,en;q=0.7")
    
    # Enhanced stealth - template inspired
    options.add_argument("--start-maximized")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-plugins-discovery")
    options.add_argument("--disable-web-security")
    options.add_argument("--allow-running-insecure-content")
    
    # Real user-agent rotation
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ]
    selected_ua = random.choice(user_agents)
    options.add_argument(f"--user-agent={selected_ua}")
    print(f"   Using User-Agent: {selected_ua[:50]}...")

    # Persistent user data directory
    tmp_dir = tempfile.gettempdir()
    # Koristi FIKSNI user-data dir umesto random UUID - KLJUČNO za cookie persistence!
    user_data_dir = os.path.join(tmp_dir, "djak_chrome_persistent")
    
    if not os.path.exists(user_data_dir):
        os.makedirs(user_data_dir, exist_ok=True)
        print(f"   Created persistent user data dir: {user_data_dir}")
    else:
        print(f"   Using existing user data dir: {user_data_dir}")
        
    options.add_argument(f"--user-data-dir={user_data_dir}")

    try:
        chromedriver_path = ChromeDriverManager().install()
        if platform.system().lower() != "windows":
            os.chmod(chromedriver_path, 0o755)
        
        patcher_path = os.path.join(tmp_dir, f"undetected_chromedriver_patch_{uuid.uuid4().hex}")
        if platform.system().lower() == "windows":
            patcher_path += ".exe"
            
        driver = uc.Chrome(
            options=options,
            driver_executable_path=chromedriver_path,
            patcher_force_close=True,
            patcher_executable_path=patcher_path
        )
        
        # Initial load to establish session
        print(f"   Establishing initial session...")
        driver.get("https://www.djaksport.com")
        time.sleep(2)
        
        # Load existing cookies ako postoje
        load_cookies(driver)
        
        return driver
    except Exception as e:
        print(f"[ERROR] Error creating WebDriver: {e}")
        return None

def random_sleep(min_sec=0.5, max_sec=2.5):
    """Random delay za simulaciju human behavior"""
    delay = random.uniform(min_sec, max_sec)
    time.sleep(delay)
    return delay

def parse_price(price_text):
    """Parsira cenu iz teksta (npr. '4.949,55 RSD')"""
    if not price_text:
        return None
    try:
        # Ukloni sve što nije broj, zarez ili tacka
        clean_text = re.sub(r'[^0-9,.]', '', price_text)
        
        # Ako imamo format kao "4.949,55" (evropski)
        if ',' in clean_text and '.' in clean_text:
            # Ukloni tacke (hiljade) i zarez zameni decimalnom tackom
            clean_text = clean_text.replace('.', '').replace(',', '.')
        # Ako imamo samo zarez, to je decimalna tacka
        elif ',' in clean_text and '.' not in clean_text:
            clean_text = clean_text.replace(',', '.')
        
        if not clean_text:
            return None
            
        return float(clean_text)
    except:
        return None

def extract_product_code(product_element):
    """Ekstraktuje šifru proizvoda iz class atributa div.product-item-info"""
    try:
        class_attr = product_element.get_attribute("class")
        if class_attr:
            parts = class_attr.strip().split()
            # Traži drugi deo klase koji nije 'product-item-info'
            for part in parts:
                if part != "product-item-info" and len(part) >= 4:
                    # Validacija šifre - mora imati brojeve ili crtice
                    if re.match(r'^[A-Za-z0-9\-_]+$', part) and (re.search(r'[0-9]', part) or '-' in part):
                        return part.upper()
        return None
    except Exception as e:
        print(f"WARNING: Error extracting product code: {e}")
        return None

def extract_product_data(product_element):
    """Ekstraktuje podatke o proizvodu iz DOM elementa"""
    try:        
        # Naziv proizvoda
        try:
            name_elem = product_element.find_element(By.CSS_SELECTOR, "strong.product-item-name .product-item-link")
            naziv = name_elem.text.strip()
        except:
            naziv = None
            
        # Šifra proizvoda
        code = extract_product_code(product_element)
        
        # Trenutna cena
        try:
            price_elem = product_element.find_element(By.CSS_SELECTOR, "span[data-price-type='finalPrice'] span.price")
            current_price = parse_price(price_elem.text)
        except:
            current_price = None
            
        # Stara cena (ako postoji)
        try:
            old_price_elem = product_element.find_element(By.CSS_SELECTOR, "span[data-price-type='oldPrice'] span.price")
            old_price = parse_price(old_price_elem.text)
        except:
            old_price = None
            
        # Proverava da li su svi potrebni podaci pronađeni
        if not naziv or not code or current_price is None:
            return None
            
        product_data = {
            'code': code,
            'naziv': naziv,
            'price': float(current_price),
            'price_regular': float(old_price) if old_price else None,
            'price_discount': float(current_price) if old_price and old_price > current_price else None,
            'price_old': float(old_price) if old_price else None,
            'store_id': STORE_ID
        }
        
        return product_data
        
    except Exception as e:
        print(f"ERROR extracting product data: {e}")
        return None

def send_products_to_api(products):
    """Šalje proizvode u Laravel API"""
    if not products:
        return False
        
    try:
        response = requests.post(
            API_URL,
            json=products,
            headers={"Accept": "application/json"},
            timeout=15
        )
        
        if response.status_code == 200:
            print(f"[SUCCESS] Sent batch of {len(products)} products")
            return True
        else:
            print(f"[ERROR] API responded with status {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print(f"[ERROR] Failed to send products to API: {e}")
        return False

def restart_driver_if_needed(current_count, restart_interval=8000):
    """Restartuje driver samo kad je STVARNO potrebno - mnogo ređe"""
    global global_driver
    
    # Samo za ekstremne slučajeve memory leak-a
    if current_count > 0 and current_count % restart_interval == 0:
        print(f"\n🔄 RESTARTING driver at {current_count} products (extreme memory protection)...")
        
        # Save cookies pre restart-a
        save_cookies(global_driver)
        
        # Cleanup trenutni driver
        cleanup_driver()
        
        # Force garbage collection
        gc.collect()
        
        # Kratka pauza za cleanup
        time.sleep(3)
        
        # Kreiraj novi driver
        global_driver = setup_driver(headless=args.headless)
        
        if global_driver:
            print(f" Driver restarted successfully!")
            # Load cookies nazad
            load_cookies(global_driver)
        else:
            print(f" Failed to restart driver!")
            return False
    
    return True

def get_memory_usage():
    """Vraća trenutnu memory usage"""
    try:
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024  # MB
    except:
        return 0

def scrape_category(driver, category_url, limit=None):
    """Scrape-uje jednu DJAK kategoriju"""
    global global_driver
    
    category_name = category_url.split('/')[-1]
    page = 1
    total_count = 0
    batch = []
    BATCH_SIZE = 50
    MAX_PAGES_PER_CATEGORY = 200  # Limit da se spreči beskonačno skrejpovanje
    
    print(f"\n Processing category: {category_name}")
    
    while True:
        url = f"{category_url}?p={page}"
        
        try:
            print(f" Page {page}: ", end="", flush=True)
            driver.get(url)
            
            # Dodaj human-like delay
            delay = random_sleep(1.0, 3.0)
            
            # Čekaj da se proizvodi učitaju
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.product-item-info"))
                )
            except:
                print("no products found - end of category")
                break
            
            # Scroll da se učitaju svi proizvodi
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.5)
            
            # Pronađi sve proizvode na stranici
            products = driver.find_elements(By.CSS_SELECTOR, "div.product-item-info")
            
            if not products:
                print("no products found")
                break
            
            products_on_page = 0
            
            for i, product in enumerate(products):
                if limit and total_count >= limit:
                    break
                
                # Restart driver samo ako je baš potrebno (svakih 5000)
                if not restart_driver_if_needed(total_count):
                    print("   Driver restart failed - stopping scraper")
                    return total_count
                    
                product_data = extract_product_data(product)
                if product_data:
                    batch.append(product_data)
                    total_count += 1
                    products_on_page += 1
                    
                    # Memory usage check - mnogo ređe
                    if total_count % 1000 == 0:
                        mem_usage = get_memory_usage()
                        print(f"\n   Memory usage at {total_count} products: {mem_usage:.1f}MB")
                        
                        # Samo basic garbage collection, bez refresh-a koji može pokvariti session
                        if mem_usage > 1200:  # Povećan threshold
                            print("   Basic cleanup for stability...")
                            gc.collect()
                            random_sleep(1, 2)
                    
                    # Pošalji batch kada dostigne BATCH_SIZE
                    if len(batch) >= BATCH_SIZE:
                        send_products_to_api(batch)
                        batch.clear()
                        # Force garbage collection nakon batch-a
                        gc.collect()
                        
            print(f"processed {products_on_page} products (total: {total_count})")
            
            if limit and total_count >= limit:
                break
                
            # Check max pages limit
            if page >= MAX_PAGES_PER_CATEGORY:
                print(f" Reached max pages limit ({MAX_PAGES_PER_CATEGORY}) for category")
                break
            
            # Proveri da li postoji sledeća stranica
            try:
                next_btn = driver.find_element(By.CSS_SELECTOR, "a.action.next")
                if not next_btn.is_enabled():
                    print("No next page available")
                    break
            except:
                print("No next page button found")
                break
            
            page += 1
            
            # Minimalno čišćenje svakih 50 stranica 
            if page % 50 == 0:
                print("   Minimal cleanup...")
                gc.collect()
            
        except Exception as e:
            print(f"Error on page {page}: {e}")
            
            # Pokušaj oporavak
            try:
                print(" Attempting recovery...")
                
                # Save cookies pre refresh
                save_cookies(driver)
                
                driver.refresh()
                random_sleep(2, 4)
                
                # Reload cookies
                load_cookies(driver)
                
                # Ako i dalje ne radi, restart driver
                if "chrome" not in driver.current_url.lower():
                    print("⚠️ Driver seems broken, restarting...")
                    if restart_driver_if_needed(total_count, restart_interval=1):
                        continue
                    else:
                        break
            except:
                print(" Recovery failed")
                break
    
    # Pošalji finalni batch
    if batch:
        print(f" Sending final batch of {len(batch)} products...")
        send_products_to_api(batch)
    
    # Save cookies na kraju kategorije
    save_cookies(driver)
    
    print(f" Category {category_name} completed: {total_count} products")
    return total_count

def main():
    global global_driver
    
    print(" DJAK Nova Scraper Starting...")
    print(f"PYTHON: {sys.executable}")
    print(f"CWD: {os.getcwd()}")
    print(f"ARGS: {sys.argv}")
    
    # Određi kategorije za obradu
    if args.category:
        categories_to_process = [args.category]
    else:
        categories_to_process = DEFAULT_CATEGORIES
    
    print(f" Total categories: {len(categories_to_process)}")
    for i, url in enumerate(categories_to_process):
        print(f"   {i+1}. {url}")

    # Setup Chrome driver
    global_driver = setup_driver(headless=args.headless)
    if not global_driver:
        print("[ERROR] Cannot create WebDriver")
        return

    total_products = 0

    try:
        for i, category_url in enumerate(categories_to_process):
            print(f"\n Processing category {i+1}/{len(categories_to_process)}")
            
            cat_products = scrape_category(global_driver, category_url, args.limit)
            total_products += cat_products
            
            # Blaga pauza između kategorija (bez restart-a driver-a)
            if i < len(categories_to_process) - 1:  # Ne za poslednju kategoriju
                print(f"Brief pause between categories...")
                save_cookies(global_driver)  # Save cookies za sigurnost
                time.sleep(2)
                gc.collect()  # Basic cleanup
            
            
    except Exception as e:
        print(f"Main error: {e}")
    finally:
        aggressive_cleanup()

    print(f"\n DJAK Nova Scraper COMPLETED!")
    print(f" Total products processed: {total_products}")
    print(f" Categories processed: {len(categories_to_process)}")

if __name__ == "__main__":
    main()