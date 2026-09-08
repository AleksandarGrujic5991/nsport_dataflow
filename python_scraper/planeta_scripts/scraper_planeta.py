from selenium.webdriver.common.by import By
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import sys
import requests
import os
import argparse
import re
import json
import tempfile
import shutil
import uuid
import platform
import signal
import atexit
import random
import subprocess

# Argument parsing
parser = argparse.ArgumentParser()
parser.add_argument('--limit', type=int, help='Limit broj proizvoda')
parser.add_argument('--headless', action='store_true', help='Run in headless mode')
parser.add_argument('--category', type=str, help='Specific category (optional)')
parser.add_argument('--output', type=str, help='Output JSON file')
parser.add_argument('--instance', type=int, help='Instance number')
args = parser.parse_args()

import sys

# DEBUG LOGGING: sve sto ide na stdout/stderr (svi print-ovi u skripti)
# takodje se upisuje u fajl u logs/ folderu, da bi se moglo analizirati
# posle pokretanja na serveru (run_ultra_scraper.py sece output na par stotina karaktera).
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
_log_file_path = os.path.join(LOG_DIR, f"planeta_debug_{time.strftime('%Y%m%d_%H%M%S')}_pid{os.getpid()}.log")
_log_file = open(_log_file_path, 'a', encoding='utf-8')

class _Tee:
    def __init__(self, *streams):
        self.streams = streams
    def write(self, data):
        for s in self.streams:
            s.write(data)
            s.flush()
    def flush(self):
        for s in self.streams:
            s.flush()

sys.stdout = _Tee(sys.stdout, _log_file)
sys.stderr = _Tee(sys.stderr, _log_file)
print(f"[DEBUG-LOG] Log fajl: {_log_file_path}")

def log_step(message, details=None):
    """Ispisuje korak sa timestamp-om (i u konzolu i u log fajl)."""
    ts = time.strftime('%H:%M:%S')
    if details:
        print(f"[{ts}] {message} | {details}")
    else:
        print(f"[{ts}] {message}")

if '--category' in sys.argv:
    idx = sys.argv.index('--category')
    CATEGORY_URLS = [sys.argv[idx + 1]]
else:
    CATEGORY_URLS = [
        'https://planetasport.rs/deca/aksesoari.html',
        'https://planetasport.rs/deca/odeca.html',
        'https://planetasport.rs/deca/obuca.html',
        'https://planetasport.rs/zene/obuca.html',
        'https://planetasport.rs/zene/odeca.html',
        'https://planetasport.rs/zene/aksesoari.html',
        'https://planetasport.rs/muskarci/obuca.html',
        'https://planetasport.rs/muskarci/odeca.html',
        'https://planetasport.rs/muskarci/aksesoari.html',
    ]

if platform.system().lower() == "windows":
    API_URL = 'http://127.0.0.1:8000/api/products/batch'
else:
    API_URL = 'http://192.168.100.24/api/products/batch'
headers = {'User-Agent': 'Mozilla/5.0'}

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

# SELENIUM SETUP
log_step("STEP 2: Setting up Chrome options")
options = uc.ChromeOptions()
# NAPOMENA: headless=new Chrome fingerprint trigeruje Cloudflare blokadu na planetasport.rs
# (potvrdjeno testom na serveru - headless dobija "Attention Required! | Cloudflare",
# a ne-headless Chrome pod Xvfb-om dobija pravu stranicu). Zato se headless NE prisiljava
# vise automatski na Linuxu - koristi se samo ako je eksplicitno trazeno preko --headless.
if args.headless:
    options.add_argument('--headless=new')
    options.add_argument('--disable-gpu')  # samo uz headless - menja WebGL fingerprint, testiran uspesan slucaj ga nije imao
    log_step("STEP 2a: Headless mode enabled")
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--window-size=1920,1080')
# options.add_argument('--remote-debugging-port=0')  # Bitno za DevToolsActivePort

# Dodaj unikalni user-data-dir za svaku instancu (radi samo na Windowsu)
instance_num = args.instance if hasattr(args, 'instance') and args.instance else 0
tmp_dir = tempfile.gettempdir()

# if platform.system() == "Windows":
#     unique_id = f"{instance_num}_{uuid.uuid4().hex}_{int(time.time()*1000)}"
#     user_data_dir = os.path.join(tmp_dir, f"chrome_user_data_planeta_{unique_id}")
# else:
#     user_data_dir = os.path.join(tmp_dir, f"chrome_user_data_planeta_{instance_num}")

# print(f"User data dir: {user_data_dir}")  # Debug

# if os.path.exists(user_data_dir):
#     try:
#         shutil.rmtree(user_data_dir)
#     except Exception as e:
#         print(f"Greska pri brisanju user-data-dir: {e}")
#         user_data_dir = os.path.join(tmp_dir, f"chrome_user_data_planeta_{instance_num}_{uuid.uuid4().hex}_{int(time.time()*1000)}")
#         print(f"Nova putanja za user-data-dir: {user_data_dir}")
#         os.makedirs(user_data_dir, exist_ok=True)
# else:
#     os.makedirs(user_data_dir, exist_ok=True)

limit = args.limit if hasattr(args, 'limit') else None

def save_url_without_code(url, naziv):
    if not url:
        return
    
    try:
        folder = os.path.dirname(os.path.abspath(__file__))
        filename = os.path.join(folder, 'planeta_proizvodi_bez_sifre.txt')
        
        with open(filename, 'a', encoding='utf-8') as f:
            f.write(f"{url}|{naziv}\n")
            
    except Exception as e:
        print(f"[ERROR] Ne mogu da upisem u fajl: {e}")
        # Ne prekidaj izvrsavanje zbog fajla

def parse_price(price_text):
    if not price_text:
        return None
    try:
        clean_price = re.sub(r'[^\d,.]', '', price_text.strip())
        clean_price = clean_price.replace(',', '.')
        if clean_price.count('.') > 1:
            parts = clean_price.split('.')
            clean_price = ''.join(parts[:-1]) + '.' + parts[-1]
        if clean_price:
            return float(clean_price)
        else:
            return None
    except Exception:
        return None

def extract_sifra_from_url(url):
    if not url:
        return ''
    
    # PRIORITET 1: Kompletan kod na kraju URL-a (npr. -dh3827-901.html)
    # Pattern za Nike/Adidas kodove: slova+brojevi-brojevi
    full_code_match = re.search(r'-([a-z]+\d+\-\d+)\.html$', url, re.IGNORECASE)
    if full_code_match:
        full_code = full_code_match.group(1).upper()
        print(f"[URL-FULL-CODE] Ekstraktovao kompletan kod: {full_code} iz {url}")
        return full_code
    
    # PRIORITET 2: ID broj na kraju URL-a (npr. -1072.html) - fallback
    id_match = re.search(r'-(\d{3,6})\.html$', url)
    if id_match:
        id_num = id_match.group(1)
        print(f"[URL-ID] Ekstraktovao ID: {id_num} iz {url}")
        return id_num
    
    # Uzmi deo izmedu poslednjeg '-' i '.html'
    match = re.search(r'-([a-zA-Z0-9\-]+)\.html$', url)
    if match:
        full_segment = match.group(1).upper()
        
        # STRATEGIJA 1: Trazi sifru sa varijantom na kraju (npr. WIE233G404-07)
        if '-' in full_segment:
            parts = full_segment.split('-')
            
            # Pokusaj kombinaciju poslednja 2 dela ako izgledaju kao sifra+varijanta
            if len(parts) >= 2:
                part1, part2 = parts[-2], parts[-1]
                
                # NOVA LOGIKA: Kratke sifre tipa p024-0004 (slova+brojevi)
                if (3 <= len(part1) <= 15 and 3 <= len(part2) <= 15 and
                    re.search(r'[A-Z0-9]', part1) and re.search(r'[A-Z0-9]', part2)):
                    return f"{part1}-{part2}"
                
                # STARA LOGIKA: Glavni deo sa slovima+brojevima, varijanta kratka (2-3 karaktera)  
                if (6 <= len(part1) <= 15 and 
                    re.search(r'[A-Z]', part1) and 
                    re.search(r'[0-9]', part1) and
                    len(part2) <= 3 and re.match(r'^[A-Z0-9]+$', part2)):
                    return f"{part1}-{part2}"
            
            # Trazi deo koji izgleda kao glavna sifra (3+ karaktera sa slovima i brojevima)
            for part in reversed(parts):
                # Prosiri da podrzava krace sifre (3+ umesto 6+)
                if (3 <= len(part) <= 15 and 
                    re.search(r'[A-Z]', part) and 
                    re.search(r'[0-9]', part) and
                    not re.search(r'[^A-Z0-9]', part)):
                    return part
            
            # Mozda je kombinacija brojevi-brojevi (npr. 1388915-001)
            if len(parts) >= 2:
                part1, part2 = parts[-2], parts[-1]
                if (part1.isdigit() and len(part1) >= 6 and 
                    part2.isdigit() and len(part2) >= 2):
                    return f"{part1}-{part2}"
        
        # STRATEGIJA 2: Jednostavna sifra bez crtica
        else:
            if (3 <= len(full_segment) <= 15 and 
                re.search(r'[A-Z]', full_segment) and 
                re.search(r'[0-9]', full_segment)):
                return full_segment
        
        # STRATEGIJA 3: Fallback - uzmi poslednji deo
        if '-' in full_segment:
            return full_segment.split('-')[-1]
        else:
            return full_segment if len(full_segment) <= 20 else ''
    
    return ''

def compare_url_with_name_sifra(url, extracted_sifra):
    """
    JEDNOSTAVNA LOGIKA: Poredi cifre iz URL-a sa ciframa iz imena.
    Ako se poslednje cifre pre .html ne poklapaju sa ciframa u imenu → TXT fajl
    """
    if not url or not extracted_sifra:
        return False
    
    # Ekstraktuj poslednji deo URL-a (bez .html)
    url_part = url.split('/')[-1].replace('.html', '').upper()
    clean_sifra = extracted_sifra.upper().strip()
    
    print(f"[URL-CHECK] Proveravam: '{clean_sifra}' vs URL '{url_part}'")
    
    # METODA 1: Direktno poklapanje cele šifre u URL-u
    if clean_sifra in url_part:
        print(f"[URL-MATCH] Direktno poklapanje: {clean_sifra} u {url_part}")
        return True
    
    # METODA 2: Poklapanje poslednih brojeva iz URL-a sa brojevima iz imena
    # Ekstraktuj sve brojeve iz URL-a (3+ cifara)
    url_numbers = re.findall(r'\d{3,}', url_part)
    # Ekstraktuj sve brojeve iz šifre (3+ cifara)  
    name_numbers = re.findall(r'\d{3,}', clean_sifra)
    
    print(f"[URL-CHECK] URL brojevi: {url_numbers}, Ime brojevi: {name_numbers}")
    
    # Ako nema brojeva ni u jednom, prihvati (slova se poklapaju)
    if not url_numbers and not name_numbers:
        # Proveri poklapanje slova
        url_letters = re.findall(r'[A-Z]+', url_part)
        name_letters = re.findall(r'[A-Z]+', clean_sifra)
        for name_letter in name_letters:
            if len(name_letter) >= 3:  # Značajne grupe slova
                for url_letter in url_letters:
                    if name_letter in url_letter or url_letter in name_letter:
                        print(f"[URL-MATCH] Poklapanje slova: {name_letter} ↔ {url_letter}")
                        return True
    
    # Glavni test: Da li se brojevi poklapaju
    if url_numbers and name_numbers:
        # Poslednji broj iz URL-a
        url_last_number = url_numbers[-1]
        
        # Proveri da li se poslednji broj iz URL-a poklapa sa bilo kojim brojem iz imena
        for name_num in name_numbers:
            if url_last_number == name_num:
                print(f"[URL-MATCH] Poklapanje brojeva: {url_last_number} = {name_num}")
                return True
            # Delimično poklapanje za dugačke brojeve
            if len(url_last_number) >= 4 and len(name_num) >= 4:
                if url_last_number in name_num or name_num in url_last_number:
                    print(f"[URL-MATCH] Delimično poklapanje brojeva: {url_last_number} ↔ {name_num}")
                    return True
    
    print(f"[URL-NO-MATCH] Brojevi se NE poklapaju: URL={url_numbers} vs Ime={name_numbers}")
    return False

def extract_sifra(naziv, product_element=None):
    if not naziv:
        return ''
    
    # PRE-VALIDACIJA: Proveri da li naziv završava sa kategorijskim oznakama bez šifre
    naziv_clean = naziv.strip()
    
    # Sveobuhvatan set kategorijskih oznaka
    category_tags = r'(U|M|W|GG|GPG|GTP|BP|BG|BT|BPG|GP|GT)'
    
    # Ako završava samo sa kategorijskom oznakom - nema šifru
    if re.search(rf'\s+{category_tags}\s*$', naziv_clean):
        print(f"[CATEGORY-ONLY] Naziv završava kategorijskom oznakom bez šifre: {naziv_clean}")
        return ''  # Nema šifru, ide u txt fajl
    
    # Ako ima pattern "kategorija - kratko_nesto OZNAKA" gde je kratko_nesto generično (1-6 karaktera)
    if re.search(rf'(M|W|GG)\s+[^-]+-\s*[^-]{{1,6}}\s+{category_tags}\s*$', naziv_clean):
        print(f"[CATEGORY-GENERIC] Generična kategorija bez prave šifre: {naziv_clean}")
        return ''  # Nema validnu šifru, ide u txt fajl
    
    # Specijalan slučaj: "brand nešto - kratki_broj kategorija" (kao 144 gfx U)
    if re.search(rf'-\s*\d{{1,4}}\s+[a-z]{{1,5}}\s+{category_tags}\s*$', naziv_clean, re.IGNORECASE):
        print(f"[SHORT-NUMBER-CATEGORY] Kratki broj + kategorija, nije validna šifra: {naziv_clean}")
        return ''  # Kratki broj + kategorija nije validna šifra
    
    # PRIORITET 1: SVEOBUHVATAN NAZIV PATTERN MATCHING
    
    # Pattern 1: BRAND opis - SIFRA_DEO1 SIFRA_DEO2#vel (RANG/NIKE format)
    # "RANG Donji deo trenerke jenny W - BASIC 03W02-02D#S"
    match = re.search(r'^[A-Z\s]+.*?\s-\s+([A-Z]+)\s+([A-Z0-9\-]{4,20})(?:#.*)?$', naziv)
    if match:
        prefiks, glavnidel = match.group(1), match.group(2)
        combined = f"{prefiks} {glavnidel}"
        if is_valid_sifra(combined):
            return combined
    
    # Pattern 2: Standardni " - SIFRA" na kraju
    # "SKECHERS Patike slip-ins go walk max - beach casu" -> moze biti skraceno
    if ' - ' in naziv:
        parts = naziv.split(' - ')
        candidate = parts[-1].strip().split('#')[0].strip()
        if candidate and is_valid_sifra(candidate):
            # DODATNA VALIDACIJA SA URL-om
            if product_element:
                try:
                    link_elem = product_element.select_one('strong.product-item-name a')
                    if link_elem:
                        href = link_elem.get('href', '')
                        if href and not compare_url_with_name_sifra(href, candidate):
                            print(f"[PATTERN-2-REJECT] {candidate} odbačen zbog URL mismatch")
                        else:
                            return candidate
                    else:
                        return candidate  # nema URL za proveru
                except:
                    return candidate  # greška u URL proveri
            else:
                return candidate  # nema product element za proveru
        
        # Mozda je sifra u prethodnom delu ako je poslednji previse opisni
        if len(parts) >= 2:
            for i in range(len(parts)-2, -1, -1):  # unazad kroz delove
                candidate = parts[i].strip().split('#')[0].strip()
                if candidate and is_valid_sifra(candidate):
                    # DODATNA VALIDACIJA SA URL-om
                    if product_element:
                        try:
                            link_elem = product_element.select_one('strong.product-item-name a')
                            if link_elem:
                                href = link_elem.get('href', '')
                                if href and not compare_url_with_name_sifra(href, candidate):
                                    print(f"[PATTERN-2-REJECT] {candidate} odbačen zbog URL mismatch")
                                    continue  # probaj sledeći deo
                                else:
                                    return candidate
                            else:
                                return candidate  # nema URL za proveru
                        except:
                            return candidate  # greška u URL proveri
                    else:
                        return candidate  # nema product element za proveru
    
    # Pattern 3: BRAND pattern na pocetku - trazimo sifru kasnije u nazivu
    # "NIKE Stitnik za odbojku streak volleyball knee pad"
    brand_match = re.match(r'^([A-Z]+(?:\s+[A-Z]+)*)\s+(.+)$', naziv)
    if brand_match:
        brand, rest = brand_match.groups()
        
        # Specijalni slucaj za ORDLI: "class 25 gu-u GU - S"
        if brand == "ORDLI":
            ordli_match = re.search(r'class\s+(\d+)\s+gu-u', rest.lower())
            if ordli_match:
                class_num = ordli_match.group(1)
                candidate = f"SI-11-{class_num}"  # Iz URL pattern-a
                if is_valid_sifra(candidate):
                    return candidate
        
        # Trazi pattern poput "n-vp-07-001-ml" unutar opisa
        sifra_match = re.search(r'\b([a-z0-9\-]{8,20})\b', rest.lower())
        if sifra_match:
            candidate = sifra_match.group(1).upper()
            if is_valid_sifra(candidate):
                return candidate
        
        # Trazi numericke sifre poput "216284-bbk", "842015-92-000"
        num_match = re.search(r'\b(\d{6,12}(?:\-\d+)*(?:\-[a-z0-9]{2,6})*)\b', rest.lower())
        if num_match:
            candidate = num_match.group(1).upper()
            if is_valid_sifra(candidate):
                return candidate
    
    # Pattern 4: Alfanumericke sifre u nazivu (bilo gde)
    # "supfr12g", "gltonrxl", itd.
    alpha_match = re.search(r'\b([a-z]{2,6}\d+[a-z0-9]*)\b', naziv.lower())
    if alpha_match:
        candidate = alpha_match.group(1).upper()
        if len(candidate) >= 4 and is_valid_sifra(candidate):
            return candidate
    
    # Pattern 5: Císlice sa crticama "1388915-001", "07208-1"
    num_dash_match = re.search(r'\b(\d{4,8}\-\d{1,4})\b', naziv)
    if num_dash_match:
        candidate = num_dash_match.group(1)
        if is_valid_sifra(candidate):
            return candidate
    
    # Pattern 6: Specijalni format "u727-pink-roma-i"
    special_match = re.search(r'\b([a-z]\d{3,4}\-[a-z]+(?:\-[a-z]+)*)\b', naziv.lower())
    if special_match:
        candidate = special_match.group(1).upper()
        if is_valid_sifra(candidate):
            return candidate
    
    # Pattern 7: Poslednji pokusaj - bilo koja kombinacija slova+brojeva 6+ karaktera
    final_match = re.search(r'\b([A-Z0-9\-]{6,15})\b', naziv.upper())
    if final_match:
        candidate = final_match.group(1)
        if is_valid_sifra(candidate) and not re.search(r'(SIZE|VELICINA|COLOR)', candidate):
            return candidate
    
    # PRIORITET 2: URL FALLBACK SA VALIDACIJOM
    if product_element:
        try:
            link_elem = product_element.select_one('strong.product-item-name a')
            if link_elem:
                href = link_elem.get('href', '')
                
                # Prvo probaj sifru iz URL-a
                url_sifra = extract_sifra_from_url(href)
                if url_sifra and is_valid_sifra(url_sifra):
                    return url_sifra
        except:
            pass
    
    # PRIORITET 3: Ako nista ne radi, ici ce u fajl (return '')
    return ''

def get_chrome_binary_and_version():
    """Nadji putanju do Chrome binarnog fajla i njegovu glavnu verziju iz ISTOG fajla,
    da bi undetected-chromedriver dobio i binary_path i version_main koji se sigurno
    poklapaju. Server moze imati vise instaliranih Chrome/Chromium varijanti (npr.
    google-chrome paket + snap chromium) - ako se verzija cita sa jednog binarnog fajla
    a uc pokrene drugi, dolazi do "ChromeDriver only supports Chrome version X" greske."""
    candidates = ['google-chrome', 'google-chrome-stable', 'chromium-browser', 'chromium']
    for name in candidates:
        path = shutil.which(name)
        if not path:
            continue
        try:
            out = subprocess.check_output([path, '--version'], stderr=subprocess.DEVNULL, text=True)
            match = re.search(r'(\d+)\.', out)
            if match:
                return path, int(match.group(1))
        except Exception:
            continue
    return None, None

UC_DRIVER_LOCK_FILE = os.path.join(tempfile.gettempdir(), 'planeta_uc_chromedriver.lock')

def acquire_uc_driver_lock(timeout=180, stale_after=120):
    """Vise Planeta kategorija se pokrece paralelno (jedan proces po kategoriji), a
    undetected-chromedriver prvi put kad se pokrene za odredjenog korisnika (npr.
    www-data preko admin panela) mora da preuzme i 'zakrpi' chromedriver binarni fajl
    na disku. Ako vise procesa to radi ISTOVREMENO, dolazi do race condition-a i
    'Remote end closed connection without response' greske. Ova brava obezbedjuje da
    samo jedan proces radi tu inicijalizaciju u datom trenutku, dok ostali sacekaju."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            fd = os.open(UC_DRIVER_LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_RDWR)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            return True
        except FileExistsError:
            try:
                if time.time() - os.path.getmtime(UC_DRIVER_LOCK_FILE) > stale_after:
                    os.remove(UC_DRIVER_LOCK_FILE)  # zaostala brava od procesa koji je pukao
                    continue
            except OSError:
                continue
            time.sleep(random.uniform(1, 3))
    return False

def release_uc_driver_lock():
    try:
        os.remove(UC_DRIVER_LOCK_FILE)
    except OSError:
        pass

def extract_cnstrc_sifra(naziv):
    """Ekstraktuje šifru iz novog Planeta naziva pre # veličine."""
    if not naziv:
        return ''

    match = re.search(r'\s-\s+([A-Za-z0-9]+(?:-[A-Za-z0-9]+)+)(?:#|\s*$)', naziv.strip())
    return match.group(1).upper() if match else ''

def extract_product_url(product, category_url):
    """Proba više selektora za link ka proizvodu (stara i nova HTML struktura),
    uz fallback na category_url ako nijedan ne postoji."""
    for selector in ('a.product-item-photo', 'strong.product-item-name a', 'a.product-item-link', 'a[href]'):
        link = product.select_one(selector)
        if link and link.get('href'):
            return link.get('href')
    return category_url

def is_valid_sifra(code):
    if not code:
        return False
        
    code = code.strip()
    
    # DRASTICNO POJEDNOSTAVLJENO - samo osnovne blokove
    if len(code) < 2:
        return False
    
    # Blokiraj SAMO ocigledne ne-sifre
    blocked_patterns = [
        r'^(SIZE|VELICINA|COLOR|BOJA)$',  # tacno ovi termini
        r'^(SMALL|MEDIUM|LARGE|EXTRA)$',  # tacno ovi termini
        r'^(MALI|SREDNJI|VELIKI)$',  # tacno ovi termini
        r'^(BLACK|WHITE|RED|BLUE|GREEN|CRNA|BELA|CRVENA|PLAVA|ZELENA)$',  # tacno ovi termini
        r'^(PLIVANJE|TRENING|FUDBAL|KOSARKA|TENIS|GIMNASTIKA|SKIJANJE)$',  # sport kategorije
        r'^(SLAZENGER|NIKE|ADIDAS|PUMA|REEBOK|UMBRO|KAPPA|SPALDING|GAL-KOM|LITTLE|DAVIDELI|ICEPEAK|WINTRO|RANG|ACTION|SPEEDO|ARENA|YVOLUTION)$',  # brand imena kao sifre
        r'^(PATIKE|DRES|SORTS|MAJICA|JAKNA|TRENERKA|TROTINET|KONSTRUKCIJOM|SANKE|RUKAVICE|NAOCARE)$',  # tipovi odece/proizvoda
        r'^(SEAL|BULLET|SPARKLY|FIRSTY|NEON|BOLT)$',  # delovi naziva proizvoda
    ]
    
    for pattern in blocked_patterns:
        if re.search(pattern, code.upper()):
            return False
    
    # DRASTICNO POJEDNOSTAVLJENO - PRIHVATAJ GOTOVO SVE
    
    # Blokiranje ociglednih dimenzija (2+ X-ova)
    if code.upper().count('X') >= 2:
        return False
    
    # DODATNO BLOKIRANJE: Sifre koje su SAMO slova bez brojeva i duze od 6 karaktera
    if len(code) > 6 and code.isalpha():
        return False
    
    # DODATNO BLOKIRANJE: Sifre koje su kratke i samo slova (2-4 slova)
    if 2 <= len(code) <= 4 and code.isalpha() and code.upper() not in ['RX', 'GU', 'BG', 'GG']:
        return False
    
    # PRIHVATI sve sto ima vise od 2 karaktera i nije blokiran pattern
    return True
    
    return False

global_codes = set()
global_duplikati_count = 0

def scrape_category(category_url, driver, limit=None, all_products=None):
    global global_codes, global_duplikati_count
    print(f"[LOG] Scraping category: {category_url}")
    page = 1
    cat_count = 0
    batch = []
    BATCH_SIZE = 20  # Smanjeno sa 50 na 20 za stabilnost na serveru

    duplikati_count = 0
    bez_sifre_count = 0
    total_products_found = 0

    # --- LOG: pronadi maksimalnu stranicu na prvoj strani ---
    # Loading initial category page
    driver.get(category_url)
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'li#nistruct-constr-li-item, li.item.product.product-item'))
    )
    time.sleep(3)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')
    pagination = soup.select('ul.items.pages-items a.page')
    max_page = 1
    for a in pagination:
        try:
            num = int(a.get('data-page', '0'))
            if num > max_page:
                max_page = num
        except:
            continue
    print(f"[LOG] Pronadjeno paginacija: {max_page} strana")

    while page <= max_page:
        url = category_url if page == 1 else f'{category_url}?p={page}'
        print(f"[LOG] Scrape strana {page}/{max_page} | {url}")
        products_on_page = 0  # ukupni proizvodi na strani
        valid_products_on_page = 0  # validni proizvodi dodani
        if page == 1:
            # Strana 1 je vec ucitana gore (za brojanje paginacije) - NE gadjaj je ponovo.
            # Cloudflare tretira identican URL zatrazen dvaput za par sekundi kao bot obrazac
            # i blokira drugi zahtev ("Attention Required!"), pa se html/soup ovde ne diraju.
            pass
        else:
            # Pauza izmedju strana - Cloudflare blokira prebrz prelazak sa strane na stranu
            # u istoj sesiji (potvrdjeno testom), pa usporavamo da lici na covekov tempo.
            time.sleep(random.uniform(4, 7))

            page_loaded = False
            for attempt in range(2):
                if attempt > 0:
                    backoff = random.uniform(8, 14)
                    print(f"[RETRY] Strana {page}: cekam {backoff:.1f}s pre ponovnog pokusaja...")
                    time.sleep(backoff)
                try:
                    driver.get(url)
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'li#nistruct-constr-li-item, li.item.product.product-item'))
                    )
                    page_loaded = True
                    break
                except Exception as e:
                    print(f"[ERROR] Failed to load page {page} (pokusaj {attempt + 1}/2): {e}")

            if not page_loaded:
                break

            time.sleep(2)
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
        products = soup.select('li#nistruct-constr-li-item, li.item.product.product-item')
        products_on_page = len(products)  # ukupno proizvoda na strani
        total_products_found += products_on_page  # dodaj u ukupan broj

        for i, product in enumerate(products):
            try:
                # Prvo proveri data-cnstrc atribute (novi format sajta)
                naziv = product.get('data-cnstrc-item-name', '').strip()
                product_url = extract_product_url(product, category_url)

                # Ako nema data atributa, koristi staru logiku
                if not naziv:
                    name_tag = product.select_one('strong.product-item-name a')
                    naziv = name_tag.text.strip() if name_tag else ''

                    # Proveri title atribut za pun naziv
                    if name_tag and name_tag.get('title'):
                        full_naziv = name_tag.get('title').strip()
                        if len(full_naziv) > len(naziv):
                            naziv = full_naziv

                # Dodaj brand:
                brand = naziv.split()[0] if naziv else None

                cena = None
                price_regular = None
                price_discount = None
                price_old = None

                price_wrap = product.find('div', class_='price-wrapp')
                if price_wrap:
                    regular_span = price_wrap.find('span', class_='price')
                    if regular_span:
                        price_regular = parse_price(regular_span.text)
                    special_span = price_wrap.find('span', class_='special-price')
                    if special_span:
                        price_discount = parse_price(special_span.text)
                        cena = price_discount
                        price_old = price_regular
                    else:
                        cena = price_regular
                else:
                    special_price = product.find('span', class_='special-price')
                    if special_price:
                        cena = parse_price(special_price.text)
                        price_discount = cena
                    if not cena:
                        price_span = product.find('span', class_='price')
                        if price_span:
                            cena = parse_price(price_span.text)
                    old_price = product.find('span', class_='old-price')
                    if old_price:
                        old_price_span = old_price.find('span', class_='price')
                        if old_price_span:
                            price_regular = parse_price(old_price_span.text)
                            price_old = price_regular

                # POKUSAJ EKSTRAKTOVANJA SIFRE SA URL VALIDACIJOM
                sifra = extract_sifra(naziv, product)
                cnstrc_sifra = extract_cnstrc_sifra(product.get('data-cnstrc-item-name', ''))
                if cnstrc_sifra:
                    sifra = cnstrc_sifra
                if sifra:
                    # DODATNA VALIDACIJA: proveri da li se sifra poklapa sa URL-om
                    if product_url and compare_url_with_name_sifra(product_url, sifra):
                        print(f"[SIFRA-VALID] {sifra} <- {naziv[:40]}... (URL match)")
                    elif product_url:
                        print(f"[SIFRA-INVALID] {sifra} <- {naziv[:40]}... (URL mismatch)")
                        # Sifra se ne poklapa sa URL-om, tretiramo kao nevalidnu
                        sifra = ''
                    else:
                        print(f"[SIFRA-NAZIV] {sifra} <- {naziv[:40]}... (no URL)")
                else:
                    print(f"[SIFRA-FAIL-NAZIV] {naziv[:40]}...")
                
                if not sifra and product_url:
                    sifra = extract_sifra_from_url(product_url)
                    if sifra:
                        print(f"[SIFRA-URL] {sifra} <- {product_url}")
                    else:
                        print(f"[SIFRA-FAIL-URL] {product_url}")

                # ODLUCI GDE DA IDE PROIZVOD
                if naziv and cena and sifra:
                    # KRAJNJA PROVERA: URL-NAME VALIDACIJA
                    if product_url and not compare_url_with_name_sifra(product_url, sifra):
                        print(f"[FINAL-URL-MISMATCH] Šifra {sifra} se ne poklapa sa URL {product_url[:50]}... → TXT fajl")
                        bez_sifre_count += 1
                        if product_url:
                            save_url_without_code(product_url, naziv)
                        continue
                    
                    # PROIZVOD IMA SVE I PROŠAO VALIDACIJU - IDE U BAZU
                    # PROVERA GLOBALNIH DUPLIKATA (between categories)
                    if sifra in global_codes:
                        global_duplikati_count += 1
                        print(f"DUPLIKAT SIFRA (lose ekstraktovana): {sifra} - {naziv[:50]}...")
                        # IDES U TXT FAJL jer je sifra lose ekstraktovana
                        bez_sifre_count += 1
                        if product_url:
                            save_url_without_code(product_url, naziv)
                        continue
                    global_codes.add(sifra)

                    # PROVERA DUPLIKATA U KATEGORIJI
                    if all_products is not None and any(
                        p['code'] == sifra and p['store_id'] == 1 for p in all_products
                    ):
                        duplikati_count += 1
                        print(f"DUPLIKAT U KATEGORIJI (lose ekstraktovana): {sifra} - {naziv[:50]}...")
                        # IDES U TXT FAJL jer je sifra lose ekstraktovana
                        bez_sifre_count += 1
                        if product_url:
                            save_url_without_code(product_url, naziv)
                        continue

                    payload = {
                        'code': sifra,
                        'naziv': naziv,
                        'brand': brand,  # <-- dodaj brand ovde
                        'price': float(cena),
                        'price_regular': float(price_regular) if price_regular else float(cena),
                        'price_discount': float(price_discount) if price_discount else None,
                        'price_old': float(price_old) if price_old else None,
                        'store_id': 1,
                    }
                    batch.append(payload)
                    if all_products is not None:
                        all_products.append(payload)
                    cat_count += 1
                    valid_products_on_page += 1

                    if limit and cat_count >= limit:
                        print(f"[LOG] Limit od {limit} proizvoda dostignut, prekidam kategoriju.")
                        if batch:
                            try:
                                requests.post(API_URL, json=batch, headers={'Accept': 'application/json'})
                            except Exception:
                                pass
                        print(f"[LOG] Category completed: {cat_count} products added")
                        return cat_count

                    if len(batch) >= BATCH_SIZE:
                        try:
                            response = requests.post(API_URL, json=batch, headers={'Accept': 'application/json'})
                            if response.status_code == 200:
                                print(f'[SUCCESS] Sent batch of {len(batch)} products')
                            else:
                                print(f'[ERROR] API error: {response.text}')
                        except Exception as e:
                            print(f"[ERROR] API request failed: {e}")
                        
                        # Memory cleanup
                        batch.clear()
                        import gc
                        gc.collect()
                
                else:
                    # PROIZVOD NEMA SVE POTREBNO - IDE U TXT FAJL
                    bez_sifre_count += 1
                    debug_msg = f"MISSING: naziv={bool(naziv)} cena={bool(cena)} sifra={bool(sifra)}"
                    print(f"[TXT] {debug_msg} - {naziv[:30] if naziv else 'NO_NAME'}...")
                    if product_url:
                        save_url_without_code(product_url, naziv if naziv else "NO_NAME")
                    else:
                        print(f"[TXT] NO URL for product: {naziv[:30] if naziv else 'NO_NAME'}")

            except Exception:
                continue

        if products_on_page == 0:
            print(f"[LOG] Nema proizvoda na strani {page}, prekidam.")
            break
        
        print(f"[LOG] Page {page}: {products_on_page} total, {valid_products_on_page} valid")
        page += 1 

    if batch:
        try:
            response = requests.post(API_URL, json=batch, headers={'Accept': 'application/json'})
        except Exception:
            pass

    print(f"[LOG] Category completed: {cat_count} products added")
    print(f"[LOG] Total found on pages: {total_products_found}, duplicates: {duplikati_count}, no code: {bez_sifre_count}")
    return cat_count

def main():
    # Reset globalnih brojaca
    global global_codes, global_duplikati_count
    global_codes = set()
    global_duplikati_count = 0
    
    # OCISTI FAJL NA POCETKU
    try:
        folder = os.path.dirname(os.path.abspath(__file__))
        filename = os.path.join(folder, 'planeta_proizvodi_bez_sifre.txt')
        with open(filename, 'w', encoding='utf-8') as f:
            pass  # Ocisti fajl
        print(f"[INIT] Ociscen fajl: {filename}")
    except Exception as e:
        print(f"[INIT] Greska pri ciscenju fajla: {e}")
    
    print("PYTHON:", sys.executable)
    print("CWD:", os.getcwd())
    print("Planeta Universal Scraper Starting...")
    print(f"Total categories: {len(CATEGORY_URLS)}")

    # Ukloni podelu po instancama!
    categories_to_process = CATEGORY_URLS

    total_products = 0
    all_products = []

    # Resetuj fajl na pocetku (sa error handling)
    try:
        instance_suffix = f"_{args.instance}" if hasattr(args, 'instance') and args.instance else ""
        filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), f'planeta_proizvodi_bez_sifre{instance_suffix}.txt')
        open(filename, 'w', encoding='utf-8').close()
        # Output file created
    except Exception as e:
        print(f"[WARNING] Cannot create output file: {e}")

    # Creating Chrome driver instance
    global global_driver
    try:
        chrome_binary_path, chrome_major_version = get_chrome_binary_and_version()
        print(f"[LOG] Detektovan Chrome binary: {chrome_binary_path}, verzija: {chrome_major_version}")
        uc_kwargs = {'options': options, 'version_main': chrome_major_version}
        if chrome_binary_path:
            uc_kwargs['browser_executable_path'] = chrome_binary_path

        got_lock = acquire_uc_driver_lock()
        if not got_lock:
            print("[WARNING] Nisam dobio uc_driver_lock na vreme, pokusavam bez brave...")
        try:
            global_driver = uc.Chrome(**uc_kwargs)
        finally:
            if got_lock:
                release_uc_driver_lock()
        log_step("STEP 11a: Chrome driver created successfully")
        for idx, category_url in enumerate(categories_to_process, 1):
            try:
                print(f"Processing category {idx}/{len(categories_to_process)}: {category_url}")
                cat_products = scrape_category(category_url, global_driver, limit, all_products)
                total_products += cat_products
                print(f"Category {idx} completed: {cat_products} products")
            except Exception as e:
                print(f"Category {idx} FAILED: {category_url} - Error: {str(e)}")
                continue
    finally:
        cleanup_driver()

    print(f"\n Planeta Universal Scraper COMPLETED!")
    print(f" Total products processed: {total_products}")
    print(f" Categories processed: {idx}/{len(categories_to_process)}")
    print(f"[LOG] Globalnih duplikata (between categories): {global_duplikati_count}")
    
    if args.output:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(all_products, f, ensure_ascii=False, indent=2)
            print(f" Saved {len(all_products)} products to {args.output}")
        except Exception:
            pass

if __name__ == "__main__":
    main()