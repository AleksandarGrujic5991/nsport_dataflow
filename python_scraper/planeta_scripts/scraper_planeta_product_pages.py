from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import requests
import argparse
import re
import os
import platform

parser = argparse.ArgumentParser()
parser.add_argument('--headless', action='store_true', help='Run in headless mode')
parser.add_argument('--limit', type=int, help='Limit broj URL-ova')
parser.add_argument('--input', type=str, default='planeta_proizvodi_bez_sifre.txt', help='Putanja do fajla sa URL-ovima')
args = parser.parse_args()

if platform.system().lower() == "windows":
    API_URL = "http://127.0.0.1:8000/api/products/batch"
else:
    API_URL = "http://192.168.100.24/api/products/batch"

def setup_driver():
    """Setup Chrome WebDriver"""
    options = Options()
    if args.headless:
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        pass  # Running in headless mode
    options.add_argument('--window-size=1920,1080')
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

def parse_price(price_text):
    """Parsira cenu iz teksta"""
    if not price_text:
        return None
    try:
        clean_price = re.sub(r'[^\d,]', '', price_text).replace(',', '.')
        return float(clean_price) if clean_price else None
    except:
        return None

def scrape_product_page(driver, url):
    """Scrape-uje pojedinacnu product stranicu"""
    try:
        # Processing URL
        driver.get(url)
        time.sleep(3)
        
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        
        # Sifra iz div-a (GLAVNO!)
        sku_div = soup.select_one('div.product.attribute.sku div.value')
        sifra = sku_div.text.strip() if sku_div else ''
        
        # Naziv iz h1
        naziv_h1 = soup.select_one('h1.page-title span.base')
        naziv = naziv_h1.text.strip() if naziv_h1 else ''
        
        # Hidden input sa punim nazivom
        hidden_input = soup.select_one('input.cnstr-real-name-pdp')
        if hidden_input and not naziv:
            naziv = hidden_input.get('value', '').strip()
        
        # Cene
        regular_price = None
        special_price = None
        
        # Pronadi sve span.price elemente
        price_spans = soup.select('span.price')
        # print([span.text for span in price_spans])  # Debug - UKLONI ILI KOMENTARISI

        prices = [parse_price(span.text) for span in price_spans if parse_price(span.text)]

        # Akcijska cena je obicno prva, regularna druga (ili obrnuto)
        special_price = prices[1] if len(prices) > 1 else None
        regular_price = prices[0] if prices else None
        
        current_price = special_price if special_price else regular_price
        price_old = regular_price if special_price else None
        
        if sifra and naziv and current_price:
            return {
                'code': sifra,
                'naziv': naziv,
                'price': current_price,
                'price_regular': price_old if price_old else current_price,
                'price_discount': current_price if price_old and price_old > current_price else None,
                'price_old': price_old,
                'store_id': 1,  # Planeta ID
            }
        else:
            print(f"ERROR Missing data: code='{sifra}', name='{naziv}', price={current_price}")
            return None
            
    except Exception as e:
        # print(f"[ERROR]  Error processing {url}: {e}")  # UKLONI ILI KOMENTARISI
        return None

def main():
    folder = os.path.dirname(os.path.abspath(__file__))
    
    # Smart path resolution - handle both relative and absolute paths
    if os.path.isabs(args.input):
        urls_file = args.input
    elif args.input.startswith('python_scraper/'):
        # If input starts with python_scraper/, use it from project root
        project_root = os.path.dirname(os.path.dirname(folder))  # Go up 2 levels
        urls_file = os.path.join(project_root, args.input)
    elif os.path.exists(args.input):
        # File exists in current working directory (for run_ultra_scraper case)
        urls_file = args.input
    else:
        # Relative to current script directory (fallback)
        urls_file = os.path.join(folder, args.input)
    
    urls_to_process = []

    try:
        with open(urls_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if '|' in line:
                    url = line.split('|')[0].strip()
                else:
                    url = line
                if url.startswith('http'):
                    urls_to_process.append(url)
        if args.limit:
            urls_to_process = urls_to_process[:args.limit]
    except FileNotFoundError:
        print(f"[ERROR]  File {urls_file} not found!")
        return

    if not urls_to_process:
        print("[ERROR]  No URLs to process!")
        return
    
    # Setup driver
    driver = setup_driver()
    batch = []
    processed = 0
    
    try:
        for url in urls_to_process:
            product = scrape_product_page(driver, url)
            if product:
                batch.append(product)
                processed += 1
                
                # Send batch every 50 products
                if len(batch) >= 50:
                    try:
                        response = requests.post(API_URL, json=batch, headers={'Accept': 'application/json'})
                        if response.status_code != 200:
                            print(f'[ERROR]  API error: {response.text}')
                    except Exception as e:
                        print(f'[ERROR]  Request error: {e}')
                    batch = []
            
            time.sleep(1)  # Pauza izmedu stranica
        
        # Send final batch
        if batch:
            try:
                response = requests.post(API_URL, json=batch, headers={'Accept': 'application/json'})
                if response.status_code != 200:
                    print(f'[ERROR]  Final API error: {response.text}')
            except Exception as e:
                print(f'[ERROR]  Final request error: {e}')
    
    finally:
        driver.quit()
        print(f"[OK] Processed: {processed}/{len(urls_to_process)} URLs")

if __name__ == "__main__":
    main()