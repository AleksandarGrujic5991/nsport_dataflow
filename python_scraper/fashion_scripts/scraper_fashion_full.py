import requests
from bs4 import BeautifulSoup
import time
import pandas as pd
import sys
import os
import platform
from datetime import datetime

# FASHION LOG SETUP with error handling
try:
    fashion_logfile = open("FASHION_LOG.txt", "a", encoding="utf-8")
    log_file_available = True
except Exception as e:
    print(f"Warning: Could not open log file: {e}")
    fashion_logfile = None
    log_file_available = False

def fashion_log(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    # Safely handle encoding issues in message
    try:
        safe_message = str(message).encode('utf-8', errors='replace').decode('utf-8')
    except:
        safe_message = repr(message)  # Fallback to repr for problematic strings
    
    log_msg = f"[{timestamp}] {safe_message}"
    
    try:
        print(log_msg, flush=True)
    except UnicodeEncodeError:
        # If print fails, use ASCII-safe version
        safe_log = log_msg.encode('ascii', errors='replace').decode('ascii')
        print(safe_log, flush=True)
    
    if log_file_available and fashion_logfile:
        try:
            fashion_logfile.write(log_msg + "\n")
            fashion_logfile.flush()
        except Exception as e:
            print(f"Log write error: {e}", flush=True)

fashion_log("=== FASHION SCRAPER STARTED ===")
fashion_log(f"[DEBUG] sys.argv: {sys.argv}")

# Parse arguments
CATEGORIES = []
OUTPUT_FILE = None
HEADLESS_MODE = False

# Parse --category argument
if "--category" in sys.argv:
    category_index = sys.argv.index("--category")
    if category_index + 1 < len(sys.argv):
        CATEGORIES = [sys.argv[category_index + 1]]
        fashion_log(f"[DEBUG] Using category from args: {CATEGORIES[0]}")

# Parse --output argument  
if "--output" in sys.argv:
    output_index = sys.argv.index("--output")
    if output_index + 1 < len(sys.argv):
        OUTPUT_FILE = sys.argv[output_index + 1]
        fashion_log(f"[DEBUG] Output file: {OUTPUT_FILE}")

# Parse --headless argument
if "--headless" in sys.argv:
    HEADLESS_MODE = True
    fashion_log(f"[DEBUG] Headless mode: {HEADLESS_MODE}")

if not CATEGORIES:
    # fallback: koristi sve kategorije
    fashion_log("[DEBUG] Using fallback categories")
    CATEGORIES = [
    # Zene
    "https://www.fashionandfriends.com/rs/zene/odeca/",
    "https://www.fashionandfriends.com/rs/zene/obuca/",
    "https://www.fashionandfriends.com/rs/zene/torbe/",
    "https://www.fashionandfriends.com/rs/zene/aksesoari/",
    "https://www.fashionandfriends.com/rs/zene/cosmetics/",
    # Muskarci
    "https://www.fashionandfriends.com/rs/muskarci/odeca/",
    "https://www.fashionandfriends.com/rs/muskarci/obuca/",
    "https://www.fashionandfriends.com/rs/muskarci/aksesoari/",
    "https://www.fashionandfriends.com/rs/muskarci/cosmetics/",
    # Deca - devojcice
    "https://www.fashionandfriends.com/rs/deca/devojcice/odeca/",
    "https://www.fashionandfriends.com/rs/deca/devojcice/obuca/",
    "https://www.fashionandfriends.com/rs/deca/devojcice/aksesoari/",
    # Deca - decaci
    "https://www.fashionandfriends.com/rs/deca/decaci/odeca/",
    "https://www.fashionandfriends.com/rs/deca/decaci/obuca/",
    "https://www.fashionandfriends.com/rs/deca/decaci/aksesoari/",
]

if platform.system().lower() == "windows":
    API_URL = "http://127.0.0.1:8000/api/products/batch"
else:
    API_URL = "http://192.168.100.24/api/products/batch"

# Ucitaj mapping iz Excel-a i normalizuj FC sifre
if platform.system().lower() == "windows":
    mapping_path = r"C:\laragon\www\testexp\python_scraper\fc_nsport_mapping.xlsx"
else:
    mapping_path = "/var/www/dataFlow/python_scraper/fc_nsport_mapping.xlsx"  # Correct path

try:
    fashion_log(f"[DEBUG] Attempting to load mapping from: {mapping_path}")
    mapping_df = pd.read_excel(mapping_path)
    fashion_log(f"[DEBUG] Loaded mapping with columns: {mapping_df.columns.tolist()}")
    mapping_df['FC ŠIFRA'] = mapping_df['FC ŠIFRA'].astype(str).str.strip().str.upper()
    fc2nsport_map = {fc: nsport for fc, nsport in zip(mapping_df['FC ŠIFRA'], mapping_df['N SPORT ŠIFRA'])}
    fashion_log(f"[DEBUG] Successfully loaded {len(fc2nsport_map)} mappings from {mapping_path}")
except Exception as e:
    error_msg = f"[ERROR] Failed to load mapping file {mapping_path}: {e}"
    fashion_log(error_msg)
    print(f"CRITICAL: {error_msg}", flush=True)
    # Don't continue with empty mapping - this causes issues
    sys.exit(1)

def parse_price(price_str):
    """Parsira cenu iz teksta, radi za srpske formate (npr. 6.990,00 RSD)"""
    if not price_str:
        return None
    try:
        import re
        # Ukloni "RSD" i ostale ne-cifre osim ,.
        digits = re.sub(r'[^\d.,]', '', str(price_str))
        
        # Ako ima zapetu, to je decimalni separator
        if ',' in digits:
            # Ukloni sve tačke (hiljade separator) i zameni zarez sa tačkom
            digits = digits.replace('.', '').replace(',', '.')
        else:
            # Ako nema zapetu, poslednje 2 cifre su centi (kao Sportvision)
            digits = digits.replace('.', '')
            if len(digits) > 2:
                digits = f"{digits[:-2]}.{digits[-2:]}"
            elif len(digits) == 2:
                digits = f"0.{digits}"
            else:
                digits = f"0.0{digits}"
        
        return float(digits)
    except Exception:
        return None

def extract_products_from_html(html):
    soup = BeautifulSoup(html, "html.parser")
    products = []
    
    # Debug: Proveravaj razlicite selektore
    product_elements = soup.select("li.item.product")
    fashion_log(f"[DEBUG] Found {len(product_elements)} li.item.product elements")
    
    if len(product_elements) == 0:
        # Pokusaj sa drugim selectorima
        alt_selectors = [".product-item", ".item", "[data-element-sku]", ".product"]
        for selector in alt_selectors:
            alt_elements = soup.select(selector)
            if len(alt_elements) > 0:
                fashion_log(f"[DEBUG] Alternative selector '{selector}' found {len(alt_elements)} elements")
                product_elements = alt_elements[:10]  # Uzmi prvih 10 za test
                break
    
    for item in product_elements:
        try:
            fc_sku = item.get("data-element-sku", "")
            # Safely handle encoding in SKU
            fc_sku = str(fc_sku).encode('ascii', errors='ignore').decode('ascii')
            fc_sku_norm = fc_sku.strip().upper()
            
            fashion_log(f"[DEBUG] Checking product with SKU: '{fc_sku}' (normalized: '{fc_sku_norm}')")
            
            nsport_sifra = fc2nsport_map.get(fc_sku_norm)
            if not nsport_sifra:
                continue  # preskoci ako nije u mappingu
        except Exception as e:
            fashion_log(f"[ERROR] Product processing failed: {e}")
            continue
        
        # Parsiranje naziva i brenda sa encoding safety
        name = ""
        brand = ""
        name_tag = item.select_one("h5.product-item-name a")
        if name_tag:
            try:
                full_name = name_tag.get_text(strip=True)
                # Ensure proper encoding
                full_name = str(full_name).encode('utf-8', errors='replace').decode('utf-8')
            except Exception as e:
                fashion_log(f"[ERROR] Name extraction failed: {e}")
                continue
            # Debug: ispis originalnog naziva
            # print(f"[DEBUG] Original: '{full_name}'")
            # Izvuci brend i naziv iz formata "Brand - Naziv proizvoda"
            if " - " in full_name:
                parts = full_name.split(" - ", 1)
                # Pokusaj da detektujem koji deo je brend
                # Brendovi su obicno kraci i pocinju velikim slovom
                part1 = parts[0].strip()
                part2 = parts[1].strip()
                
                # Lista poznatih brendova
                known_brands = ["Replay", "Calvin Klein", "Inuikii", "Tommy Hilfiger", "Guess", "Adidas", "Nike", "Puma"]
                
                if part1 in known_brands:
                    brand = part1
                    name = part2
                elif part2 in known_brands:
                    brand = part2
                    name = part1
                else:
                    # Ako nije u listi, pretpostavi da je kraci deo brend
                    if len(part1) <= len(part2) and part1[0].isupper():
                        brand = part1
                        name = part2
                    else:
                        brand = part2
                        name = part1
                # Debug: ispis parsiranih delova
                # print(f"[DEBUG] Brand: '{brand}', Name: '{name}'")
            else:
                # Ako nema " - ", proverim da li je ceo tekst mozda samo brend
                if full_name in known_brands:
                    brand = full_name
                    name = ""  # Nema naziv, samo brend
                else:
                    name = full_name
                    brand = ""
                # print(f"[DEBUG] No separator - Name: '{name}', Brand: '{brand}'")
        
        price = ""
        price_tag = item.select_one(".price-box .price-final_price .price")
        if price_tag:
            price = price_tag.get_text(strip=True)
        old_price = ""
        old_price_tag = item.select_one(".price-box .old-price .price")
        if old_price_tag:
            old_price = old_price_tag.get_text(strip=True)
        try:
            products.append({
                "code": nsport_sifra,  # upisujes kao N SPORT SIFRA!
                "naziv": name,
                "brand": brand,
                "price": parse_price(price),
                "old_price": parse_price(old_price),
                "store_id": 6
            })
            fashion_log(f"[DEBUG] Successfully processed product: {nsport_sifra}")
        except Exception as e:
            fashion_log(f"[ERROR] Product append failed: {e}")
    return products

def main():
    batch = []
    total_processed = 0
    for cat_url in CATEGORIES:
        fashion_log(f"=== Kategorija: {cat_url} ===")
        fashion_log(f"[DEBUG] sys.argv: {sys.argv}")
        page = 1
        max_pages = 150  # Increased limit for thorough search
        consecutive_empty_pages = 0  # Track empty pages  
        while page <= max_pages:
            if page == 1:
                url = cat_url if cat_url.endswith("/") else cat_url + "/"
            else:
                base = cat_url if cat_url.endswith("/") else cat_url + "/"
                url = f"{base}filter/page:{page}/"
            fashion_log(f"  → Stranica {page}: {url}")
            print(f"...", flush=True)
            try:
                resp = requests.get(url, timeout=15)
                if resp.status_code != 200:
                    print(f"    WARNING:  Greska {resp.status_code}")
                    break
            except Exception as e:
                print(f"    WARNING:  Greska pri otvaranju: {e}")
                break
            products = extract_products_from_html(resp.text)
            fashion_log(f"    [LOG] Na stranici {page} pronadeno {len(products)} proizvoda iz mappinga")
            
            # Track progress but don't exit on empty pages
            if len(products) == 0:
                if page % 10 == 0:  # Log every 10th page to reduce noise
                    fashion_log(f"    [DEBUG] Page {page}: No matching products found (continuing search...)")
            else:
                fashion_log(f"    [INFO] Page {page}: Found {len(products)} matching products!")
            
            # Only stop if we reach natural end of pagination - don't stop on empty matches
            # Fashion & Friends has 15k products, mapping has only 470 - many pages will be empty
            
            batch.extend(products)
            total_processed += len(products)
            while len(batch) >= 50:
                batch_to_send = batch[:50]
                try:
                    response = requests.post(API_URL, json=batch_to_send, timeout=15)
                    if response.status_code == 200:
                        fashion_log(f"[OK]  Upisano 50 proizvoda u bazu")
                    else:
                        fashion_log(f"[ERROR]  API error: {response.status_code}")
                except Exception as e:
                    fashion_log(f"[ERROR]  API request failed: {e}")
                    # Continue processing even if API fails
                batch = batch[50:]
            # Check for next page button
            try:
                soup = BeautifulSoup(resp.text, "html.parser")
                next_btn = soup.select_one("li.pages-item-next")
            except Exception as e:
                fashion_log(f"[ERROR]  BeautifulSoup parsing failed: {e}")
                break  # End pagination if parsing fails
            
            # Multiple ways to detect end of pagination
            has_next = True
            if not next_btn:
                fashion_log(f"    [DEBUG] No next button found - ending pagination")
                has_next = False
            elif "disabled" in next_btn.get("class", []):
                fashion_log(f"    [DEBUG] Next button disabled - ending pagination") 
                has_next = False
            
            # Additional check: look for products on the page
            try:
                product_elements = soup.select("li.item.product")
                if len(product_elements) == 0:
                    fashion_log(f"    [DEBUG] No product elements found - ending pagination")
                    has_next = False
            except Exception as e:
                fashion_log(f"[ERROR]  Product elements check failed: {e}")
                has_next = False
            
            if not has_next:
                break
                
            page += 1
            fashion_log(f"    [DEBUG] Moving to page {page}")
            time.sleep(0.2)
            
        # Check if we hit the safety limit
        if page > max_pages:
            fashion_log(f"    [WARNING] Hit maximum page limit ({max_pages}) - stopping to prevent infinite loop")
            
        if batch:
            try:
                response = requests.post(API_URL, json=batch, timeout=15)
                if response.status_code == 200:
                    fashion_log(f"[OK]  Upisano {len(batch)} proizvoda u bazu")
                else:
                    fashion_log(f"[ERROR]  API error: {response.status_code}")
            except Exception as e:
                fashion_log(f"[ERROR]  Final API request failed: {e}")
                # Continue processing even if API fails
            batch = []
    fashion_log(f"[OK]  Svi proizvodi poslati u bazu! Total products processed: {total_processed}")
    
    # Clear success message even if no products found
    if total_processed == 0:
        fashion_log("ℹ️  No matching products found in any category, but scraper completed successfully")
        print("FASHION SCRAPER COMPLETED: 0 products processed (no matches found)", flush=True)
    else:
        print(f"FASHION SCRAPER COMPLETED: {total_processed} products processed", flush=True)
    
    fashion_log("=== FASHION SCRAPER FINISHED ===")
    print("Fashion scraper execution completed successfully", flush=True)
    
    # Close log file safely
    if fashion_logfile:
        fashion_logfile.close()
    
    # Explicit success exit code
    sys.exit(0)

if __name__ == "__main__":
    try:
        fashion_log("Starting main() execution...")
        main()
    except Exception as e:
        error_msg = f"CRITICAL ERROR in main(): {e}"
        print(error_msg, flush=True)
        fashion_log(error_msg)
        if fashion_logfile:
            fashion_logfile.close()
        sys.exit(1)