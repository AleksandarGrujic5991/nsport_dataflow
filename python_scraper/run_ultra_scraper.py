import subprocess
import multiprocessing as mp
import threading
import time
import psutil
import os
import sys
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import json
from datetime import datetime
from pathlib import Path
import requests
import pandas as pd
import platform
import argparse

def get_python_executable():
    """Auto-detect venv Python path or fallback to sys.executable"""
    venv_python = None
    if platform.system().lower() == "windows":
        # Try common venv paths
        possible_paths = [
            '/c/laragon/www/testexp/venv/Scripts/python.exe',
            'C:/laragon/www/testexp/venv/Scripts/python.exe',
            'venv/Scripts/python.exe',
            '../venv/Scripts/python.exe'
        ]
        for path in possible_paths:
            if os.path.exists(path):
                venv_python = path
                break
    else:
        # Linux/Unix venv paths
        possible_paths = [
            '/var/www/dataFlow/venv/bin/python',
            'venv/bin/python',
            '../venv/bin/python'
        ]
        for path in possible_paths:
            if os.path.exists(path):
                venv_python = path
                break
    
    return venv_python if venv_python else sys.executable

# PRIVREMENO ZAKOMENTIRANO ZA TESTIRANJE
# logfile = open("SCRAPER_LOG.txt", "a", encoding="utf-8")
# sys.stdout = logfile
# sys.stderr = logfile
print("=== SCRAPER STARTED ===")

# Global varijabla za session key
session_key = None

SCRIPTS = [
    "python_scraper/scraper_buzz.py",
    "python_scraper/scraper_extrasport.py",
    "python_scraper/scraper_sportvision.py",
    "python_scraper/planeta_scripts/scraper_planeta.py",
    "python_scraper/planeta_scripts/scraper_planeta_product_pages.py",
    "python_scraper/djak_scripts/scraper_djak.py",
    "python_scraper/fashion_scripts/scraper_fashion_company_full.py",
    "python_scraper/scraper_nsport.py",
    "python_scraper/scraper_nselection.py",
    "python_scraper/scraper_intersport.py",
    "python_scraper/scraper_trendmaker.py",
    "python_scraper/scraper_etsport.py",
]

STORE_ID_MAP = {
    "1": "planeta",
    "2": "sportvision",
    "3": "djak",
    "4": "buzz",
    "5": "extrasport",
    "6": "fashion",
    "7": "nsport",        # NSport glavna
    "8": "nfashion",      # NSport Fashion
    "9": "lacoste",       # NSport Lacoste
    "10": "nselection",   # N Selection
    "11": "intersport",   # Intersport (nova)
    "12": "trendmaker",   # Trendmaker
    "13": "etsport",      # ETSport (nova)
    "12": "trendmaker"    # Trendmaker (nova)
}

SCRAPER_CATEGORIES = {
    'fashion_scripts/scraper_fashion_full.py': [
        "https://www.fashionandfriends.com/rs/zene/odeca/",
        "https://www.fashionandfriends.com/rs/zene/obuca/",
        "https://www.fashionandfriends.com/rs/zene/torbe/",
        "https://www.fashionandfriends.com/rs/zene/aksesoari/",
        "https://www.fashionandfriends.com/rs/zene/cosmetics/",
        "https://www.fashionandfriends.com/rs/muskarci/odeca/",
        "https://www.fashionandfriends.com/rs/muskarci/obuca/",
        "https://www.fashionandfriends.com/rs/muskarci/aksesoari/",
        "https://www.fashionandfriends.com/rs/muskarci/cosmetics/",
        "https://www.fashionandfriends.com/rs/deca/devojcice/odeca/",
        "https://www.fashionandfriends.com/rs/deca/devojcice/obuca/",
        "https://www.fashionandfriends.com/rs/deca/devojcice/aksesoari/",
        "https://www.fashionandfriends.com/rs/deca/decaci/odeca/",
        "https://www.fashionandfriends.com/rs/deca/decaci/obuca/",
        "https://www.fashionandfriends.com/rs/deca/decaci/aksesoari/",
    ],
    'scraper_buzz.py': [
        "https://www.buzzsneakers.rs/obuca/za-muskarce",
        "https://www.buzzsneakers.rs/odeca/za-muskarce", 
        "https://www.buzzsneakers.rs/oprema/za-muskarce",
        "https://www.buzzsneakers.rs/obuca/za-zene",
        "https://www.buzzsneakers.rs/odeca/za-zene",
        "https://www.buzzsneakers.rs/oprema/za-zene",
        "https://www.buzzsneakers.rs/odeca/za-decake+za-devojcice+kids/",
        "https://www.buzzsneakers.rs/obuca/za-decake+za-devojcice+kids/",
        "https://www.buzzsneakers.rs/oprema/za-decake+za-devojcice+kids/",
    ],
    'scraper_extrasport.py': [
        "https://www.extrasports.com/SRB_rs/obuca/za-muskarce+unisex/",
        "https://www.extrasports.com/SRB_rs/odeca/za-muskarce+unisex/",
        "https://www.extrasports.com/SRB_rs/oprema/za-muskarce+unisex/",
        "https://www.extrasports.com/SRB_rs/obuca/unisex+za-zene/",
        "https://www.extrasports.com/SRB_rs/odeca/unisex+za-zene/",
        "https://www.extrasports.com/SRB_rs/oprema/za-zene+unisex/",
        "https://www.extrasports.com/SRB_rs/obuca/kids-boys+kids-girls+kids-other/",
        "https://www.extrasports.com/SRB_rs/odeca/kids-boys+kids-girls+kids-other/",
        "https://www.extrasports.com/SRB_rs/oprema/kids-boys+kids-girls+kids-other/",
    ],
    'scraper_sportvision.py': [
        'https://www.sportvision.rs/obuca/za-muskarce+unisex/za-odrasle/',
        'https://www.sportvision.rs/odeca/za-muskarce+unisex/za-odrasle/',
        'https://www.sportvision.rs/oprema/za-muskarce+unisex/za-odrasle/',
        'https://www.sportvision.rs/obuca/za-zene/',
        'https://www.sportvision.rs/odeca/za-zene/za-odrasle/',
        'https://www.sportvision.rs/oprema/za-zene/za-odrasle/',
        'https://www.sportvision.rs/obuca/za-tinejdzere+za-malu-decu+za-bebe/',
        'https://www.sportvision.rs/odeca/za-tinejdzere+za-malu-decu+za-bebe/',
        'https://www.sportvision.rs/oprema/za-tinejdzere+za-malu-decu+za-bebe/'
    ],
    'planeta_scripts/scraper_planeta.py': [
        'https://planetasport.rs/deca/aksesoari.html',
        'https://planetasport.rs/deca/odeca.html',
        'https://planetasport.rs/deca/obuca.html',
        'https://planetasport.rs/zene/obuca.html',
        'https://planetasport.rs/zene/odeca.html',
        'https://planetasport.rs/zene/aksesoari.html',
        'https://planetasport.rs/muskarci/obuca.html',
        'https://planetasport.rs/muskarci/odeca.html',
        'https://planetasport.rs/muskarci/aksesoari.html',
    ],
    'planeta_scripts/scraper_planeta_product_pages.py': [
        'https://planetasport.rs/deca/aksesoari.html',
        'https://planetasport.rs/deca/odeca.html',
        'https://planetasport.rs/deca/obuca.html',
        'https://planetasport.rs/zene/obuca.html',
        'https://planetasport.rs/zene/odeca.html',
        'https://planetasport.rs/zene/aksesoari.html',
        'https://planetasport.rs/muskarci/obuca.html',
        'https://planetasport.rs/muskarci/odeca.html',
        'https://planetasport.rs/muskarci/aksesoari.html',
    ],
    'djak_scripts/scraper_djak.py': [
        'https://www.djaksport.com/deca',
        'https://www.djaksport.com/muskarci',
        'https://www.djaksport.com/zene',
        ],
    'scraper_nsport.py': [
        # Regular NSport categories (store_id=7)
        'https://www.n-sport.net/patike?filter_submited=1&show_filters=1&filters[Pol][]=Muškarci',
        'https://www.n-sport.net/obuca?filter_submited=1&show_filters=1&filters[Pol][]=Muškarci',
        'https://www.n-sport.net/odeca?filter_submited=1&show_filters=1&filters[Pol][]=Muškarci',
        'https://www.n-sport.net/aksesoari?filter_submited=1&show_filters=1&filters[Pol][]=Muškarci',
        'https://www.n-sport.net/sportska-oprema?filter_submited=1&show_filters=1&filters[Pol][]=Muškarci',
        'https://www.n-sport.net/patike?filter_submited=1&show_filters=1&filters[Pol][]=Žene',
        'https://www.n-sport.net/obuca?filter_submited=1&show_filters=1&filters[Pol][]=Žene',
        'https://www.n-sport.net/odeca?filter_submited=1&show_filters=1&filters[Pol][]=Žene',
        'https://www.n-sport.net/aksesoari?filter_submited=1&show_filters=1&filters[Pol][]=Žene',
        'https://www.n-sport.net/sportska-oprema?filter_submited=1&show_filters=1&filters[Pol][]=Žene',
        'https://www.n-sport.net/patike?filter_submited=1&show_filters=1&filters[Pol][]=Deca',
        'https://www.n-sport.net/obuca?filter_submited=1&show_filters=1&filters[Pol][]=Deca',
        'https://www.n-sport.net/odeca?filter_submited=1&show_filters=1&filters[Pol][]=Deca',
        'https://www.n-sport.net/aksesoari?filter_submited=1&show_filters=1&filters[Pol][]=Deca',
        'https://www.n-sport.net/sportska-oprema?filter_submited=1&show_filters=1&filters[Pol][]=Deca',
        
        # NFashion categories (store_id=8)
        'https://www.n-sport.net/patike?filter_submited=1&show_filters=1&filters[Pol][]=Muškarci&fashion=1',
        'https://www.n-sport.net/obuca?filter_submited=1&show_filters=1&filters[Pol][]=Muškarci&fashion=1',
        'https://www.n-sport.net/odeca?filter_submited=1&show_filters=1&filters[Pol][]=Muškarci&fashion=1',
        'https://www.n-sport.net/aksesoari?filter_submited=1&show_filters=1&filters[Pol][]=Muškarci&fashion=1',
        'https://www.n-sport.net/sportska-oprema?filter_submited=1&show_filters=1&filters[Pol][]=Muškarci&fashion=1',
        'https://www.n-sport.net/patike?filter_submited=1&show_filters=1&filters[Pol][]=Žene&fashion=1',
        'https://www.n-sport.net/obuca?filter_submited=1&show_filters=1&filters[Pol][]=Žene&fashion=1',
        'https://www.n-sport.net/odeca?filter_submited=1&show_filters=1&filters[Pol][]=Žene&fashion=1',
        'https://www.n-sport.net/aksesoari?filter_submited=1&show_filters=1&filters[Pol][]=Žene&fashion=1',
        'https://www.n-sport.net/sportska-oprema?filter_submited=1&show_filters=1&filters[Pol][]=Žene&fashion=1',
        'https://www.n-sport.net/patike?filter_submited=1&show_filters=1&filters[Pol][]=Deca&fashion=1',
        'https://www.n-sport.net/obuca?filter_submited=1&show_filters=1&filters[Pol][]=Deca&fashion=1',
        'https://www.n-sport.net/odeca?filter_submited=1&show_filters=1&filters[Pol][]=Deca&fashion=1',
        'https://www.n-sport.net/aksesoari?filter_submited=1&show_filters=1&filters[Pol][]=Deca&fashion=1',
        'https://www.n-sport.net/sportska-oprema?filter_submited=1&show_filters=1&filters[Pol][]=Deca&fashion=1',
        
        # Lacoste categories (store_id=9)
        'https://www.n-sport.net/patike?filter_submited=1&show_filters=1&filters[Pol][]=Muškarci&lacoste=1',
        'https://www.n-sport.net/obuca?filter_submited=1&show_filters=1&filters[Pol][]=Muškarci&lacoste=1',
        'https://www.n-sport.net/odeca?filter_submited=1&show_filters=1&filters[Pol][]=Muškarci&lacoste=1',
        'https://www.n-sport.net/aksesoari?filter_submited=1&show_filters=1&filters[Pol][]=Muškarci&lacoste=1',
        'https://www.n-sport.net/sportska-oprema?filter_submited=1&show_filters=1&filters[Pol][]=Muškarci&lacoste=1',
        'https://www.n-sport.net/patike?filter_submited=1&show_filters=1&filters[Pol][]=Žene&lacoste=1',
        'https://www.n-sport.net/obuca?filter_submited=1&show_filters=1&filters[Pol][]=Žene&lacoste=1',
        'https://www.n-sport.net/odeca?filter_submited=1&show_filters=1&filters[Pol][]=Žene&lacoste=1',
        'https://www.n-sport.net/aksesoari?filter_submited=1&show_filters=1&filters[Pol][]=Žene&lacoste=1',
        'https://www.n-sport.net/sportska-oprema?filter_submited=1&show_filters=1&filters[Pol][]=Žene&lacoste=1',
        'https://www.n-sport.net/patike?filter_submited=1&show_filters=1&filters[Pol][]=Deca&lacoste=1',
        'https://www.n-sport.net/obuca?filter_submited=1&show_filters=1&filters[Pol][]=Deca&lacoste=1',
        'https://www.n-sport.net/odeca?filter_submited=1&show_filters=1&filters[Pol][]=Deca&lacoste=1',
        'https://www.n-sport.net/aksesoari?filter_submited=1&show_filters=1&filters[Pol][]=Deca&lacoste=1',
        'https://www.n-sport.net/sportska-oprema?filter_submited=1&show_filters=1&filters[Pol][]=Deca&lacoste=1',
    ],
    'scraper_nselection.py': [
        'https://www.nselection.rs/patike?filter_submited=1&show_filters=1&filters[Pol][]=Muškarci',
        'https://www.nselection.rs/obuca?filter_submited=1&show_filters=1&filters[Pol][]=Muškarci',
        'https://www.nselection.rs/odeca?filter_submited=1&show_filters=1&filters[Pol][]=Muškarci',
        'https://www.nselection.rs/aksesoari?filter_submited=1&show_filters=1&filters[Pol][]=Muškarci',
        'https://www.nselection.rs/sportska-oprema?filter_submited=1&show_filters=1&filters[Pol][]=Muškarci',
        'https://www.nselection.rs/patike?filter_submited=1&show_filters=1&filters[Pol][]=Žene',
        'https://www.nselection.rs/obuca?filter_submited=1&show_filters=1&filters[Pol][]=Žene',
        'https://www.nselection.rs/odeca?filter_submited=1&show_filters=1&filters[Pol][]=Žene',
        'https://www.nselection.rs/aksesoari?filter_submited=1&show_filters=1&filters[Pol][]=Žene',
        'https://www.nselection.rs/sportska-oprema?filter_submited=1&show_filters=1&filters[Pol][]=Žene',
        'https://www.nselection.rs/patike?filter_submited=1&show_filters=1&filters[Pol][]=Deca',
        'https://www.nselection.rs/obuca?filter_submited=1&show_filters=1&filters[Pol][]=Deca',
        'https://www.nselection.rs/odeca?filter_submited=1&show_filters=1&filters[Pol][]=Deca',
        'https://www.nselection.rs/aksesoari?filter_submited=1&show_filters=1&filters[Pol][]=Deca',
        'https://www.nselection.rs/sportska-oprema?filter_submited=1&show_filters=1&filters[Pol][]=Deca',
    ],
    'scraper_intersport.py': [
        'https://www.intersport.rs/patike?filter_submited=1&show_filters=1&filters[Pol][]=Muškarci',
        'https://www.intersport.rs/obuca?filter_submited=1&show_filters=1&filters[Pol][]=Muškarci',
        'https://www.intersport.rs/odeca?filter_submited=1&show_filters=1&filters[Pol][]=Muškarci',
        'https://www.intersport.rs/aksesoari?filter_submited=1&show_filters=1&filters[Pol][]=Muškarci',
        'https://www.intersport.rs/sportska-oprema?filter_submited=1&show_filters=1&filters[Pol][]=Muškarci',
        'https://www.intersport.rs/patike?filter_submited=1&show_filters=1&filters[Pol][]=Žene',
        'https://www.intersport.rs/obuca?filter_submited=1&show_filters=1&filters[Pol][]=Žene',
        'https://www.intersport.rs/odeca?filter_submited=1&show_filters=1&filters[Pol][]=Žene',
        'https://www.intersport.rs/aksesoari?filter_submited=1&show_filters=1&filters[Pol][]=Žene',
        'https://www.intersport.rs/sportska-oprema?filter_submited=1&show_filters=1&filters[Pol][]=Žene',
        'https://www.intersport.rs/patike?filter_submited=1&show_filters=1&filters[Pol][]=Deca',
        'https://www.intersport.rs/obuca?filter_submited=1&show_filters=1&filters[Pol][]=Deca',
        'https://www.intersport.rs/odeca?filter_submited=1&show_filters=1&filters[Pol][]=Deca',
        'https://www.intersport.rs/aksesoari?filter_submited=1&show_filters=1&filters[Pol][]=Deca',
        'https://www.intersport.rs/sportska-oprema?filter_submited=1&show_filters=1&filters[Pol][]=Deca',
    ],
    'scraper_trendmaker.py': [
        'https://www.trendmaker.rs/patike?filter_submited=1&show_filters=1&filters[Pol][]=Muškarci',
        'https://www.trendmaker.rs/obuca?filter_submited=1&show_filters=1&filters[Pol][]=Muškarci',
        'https://www.trendmaker.rs/odeca?filter_submited=1&show_filters=1&filters[Pol][]=Muškarci',
        'https://www.trendmaker.rs/aksesoari?filter_submited=1&show_filters=1&filters[Pol][]=Muškarci',
        'https://www.trendmaker.rs/sportska-oprema?filter_submited=1&show_filters=1&filters[Pol][]=Muškarci',
        'https://www.trendmaker.rs/patike?filter_submited=1&show_filters=1&filters[Pol][]=Žene',
        'https://www.trendmaker.rs/obuca?filter_submited=1&show_filters=1&filters[Pol][]=Žene',
        'https://www.trendmaker.rs/odeca?filter_submited=1&show_filters=1&filters[Pol][]=Žene',
        'https://www.trendmaker.rs/aksesoari?filter_submited=1&show_filters=1&filters[Pol][]=Žene',
        'https://www.trendmaker.rs/sportska-oprema?filter_submited=1&show_filters=1&filters[Pol][]=Žene',
        'https://www.trendmaker.rs/patike?filter_submited=1&show_filters=1&filters[Pol][]=Deca',
        'https://www.trendmaker.rs/obuca?filter_submited=1&show_filters=1&filters[Pol][]=Deca',
        'https://www.trendmaker.rs/odeca?filter_submited=1&show_filters=1&filters[Pol][]=Deca',
        'https://www.trendmaker.rs/aksesoari?filter_submited=1&show_filters=1&filters[Pol][]=Deca',
        'https://www.trendmaker.rs/sportska-oprema?filter_submited=1&show_filters=1&filters[Pol][]=Deca',
    ],
    'scraper_etsport.py': [
        'https://www.etsport.rs/obuca/muskarci/',
        'https://www.etsport.rs/odeca/muskarci/',
        'https://www.etsport.rs/aksesoari/muskarci/',
        'https://www.etsport.rs/obuca/zene/',
        'https://www.etsport.rs/odeca/zene/',
        'https://www.etsport.rs/aksesoari/zene/',
        'https://www.etsport.rs/obuca/deca/',
        'https://www.etsport.rs/odeca/deca/',
        'https://www.etsport.rs/aksesoari/deca/',
    ],
}

def clear_database():
    try:
        print("[CLEAN] Cistim bazu i kreiram scraping sesiju...")
        
        if platform.system().lower().startswith("win"):
            url = "http://127.0.0.1:8000/api/products/clear"
        else:
            url = "http://192.168.100.24/api/products/clear"
        
        # Posalji i stores info ako je dostupno
        data = {}
        if 'args' in globals() and hasattr(args, 'stores') and args.stores:
            data['stores'] = args.stores
        else:
            data['stores'] = 'unknown'
        
        resp = requests.delete(url, json=data)
        response_data = resp.json()
        
        # Sacuvaj session_key za kasnije
        global session_key
        session_key = response_data.get('session_key', '')
        
        print(f"[OK] Baza ociscena i sesija kreirana: {session_key}")
        print(f"[INFO] Response: {resp.text[:200]}")
    except Exception as e:
        print(f"[ERROR] Greska pri ciscenju baze: {e}")
        import traceback
        traceback.print_exc()

def cleanup_chrome_processes():
    """Ubija samo chromedriver procese, ne dira glavni Chrome browser"""
    try:
        if platform.system().lower().startswith("win"):
            result = subprocess.run(['taskkill', '/F', '/IM', 'chromedriver.exe'], 
                         capture_output=True, check=False, text=True)
            if result.returncode == 0:
                print("Chrome procesi ocisceni")
        else:
            subprocess.run(['pkill', '-f', 'chromedriver'], capture_output=True, check=False)
            print("Chrome procesi ocisceni (Linux)")
    except Exception as e:
        print(f"Napomena: Nije mogao da ocisti chromedriver procese: {e}")

def split_excel_file(input_file, num_chunks):
    df = pd.read_excel(input_file)
    chunk_size = (len(df) + num_chunks - 1) // num_chunks
    files = []
    for i in range(num_chunks):
        chunk_df = df.iloc[i*chunk_size:(i+1)*chunk_size]
        out_file = input_file.replace('.xlsx', f'_chunk{i+1}.xlsx')
        chunk_df.to_excel(out_file, index=False)
        files.append(out_file)
    return files

def split_txt_file(input_file, num_chunks):
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = [line for line in f if line.strip()]
    chunk_size = (len(lines) + num_chunks - 1) // num_chunks
    files = []
    for i in range(num_chunks):
        chunk_lines = lines[i*chunk_size:(i+1)*chunk_size]
        out_file = input_file.replace('.txt', f'_chunk{i+1}.txt')
        with open(out_file, 'w', encoding='utf-8') as out:
            out.writelines(chunk_lines)
        files.append(out_file)
    return files

def run_script(script_path):
    python_executable = get_python_executable()
    args = [python_executable, script_path, "--headless"]
    try:
        result = subprocess.run(
            args,
            cwd=os.getcwd(),
            capture_output=True,
            text=False,
            timeout=1800
        )
        products = 0
        stdout_text = result.stdout.decode('utf-8', errors='ignore') if result.stdout else ""
        if stdout_text:
            import re
            match = re.search(r'Total products processed: (\d+)', stdout_text)
            if match:
                products = int(match.group(1))
        return (script_path, result.returncode, products, stdout_text[-300:])
    except Exception as e:
        return (script_path, -1, 0, str(e))
    
def split_urls_file(input_file, num_chunks):
    # CLEANUP: obrisi stare chunk fajlove pre kreiranja novih
    import glob
    base_pattern = input_file.replace('.txt', '_*.txt')
    old_chunks = glob.glob(base_pattern)
    for old_file in old_chunks:
        try:
            os.remove(old_file)
        except Exception:
            pass
    
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = [line for line in f if line.strip()]
    chunk_size = (len(lines) + num_chunks - 1) // num_chunks
    files = []
    for i in range(num_chunks):
        chunk_lines = lines[i*chunk_size:(i+1)*chunk_size]
        out_file = input_file.replace('.txt', f'_{i+1}.txt')
        with open(out_file, 'w', encoding='utf-8') as out:
            out.writelines(chunk_lines)
        files.append(out_file)
    return files

def run_planeta_product_pages_parallel(num_instances=10):
    print(f"[PRODUCT-PAGES-DEBUG] Starting with {num_instances} instances")
    input_file = 'python_scraper/planeta_scripts/planeta_proizvodi_bez_sifre.txt'
    print(f"[PRODUCT-PAGES-DEBUG] Checking input file: {input_file}")
    if not os.path.exists(input_file):
        print(f"SKIP: {input_file} ne postoji - preskacam product pages")
        return
    print(f"[PRODUCT-PAGES-DEBUG] Input file exists, splitting into chunks")
    chunk_files = split_urls_file(input_file, num_instances)
    
    python_executable = get_python_executable()
    
    with ThreadPoolExecutor(max_workers=num_instances) as executor:
        futures = []
        for chunk_file in chunk_files:
            # Use relative path from current directory
            chunk_filename = os.path.basename(chunk_file)
            args = [
                python_executable,
                'scraper_planeta_product_pages.py',  # Correct filename in planeta_scripts folder
                '--headless',
                '--input', chunk_filename  # Just filename, not full path
            ]
            planeta_scripts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'planeta_scripts')
            print(f"[PRODUCT-PAGES-DEBUG] Launching: {' '.join(args)} in cwd={planeta_scripts_dir}")
            # Run from planeta_scripts directory
            future = executor.submit(
                subprocess.run, 
                args, 
                capture_output=True, 
                text=False,
                cwd=planeta_scripts_dir  # Set working directory with full path
            )
            futures.append(future)
        for future in as_completed(futures):
            result = future.result()
            stdout_text = result.stdout.decode('utf-8', errors='ignore') if result.stdout else ""
            stderr_text = result.stderr.decode('utf-8', errors='ignore') if result.stderr else ""
            print(f"[PRODUCT-PAGES-DEBUG] Process finished with return code: {result.returncode}")
            if stdout_text:
                print(f"[PRODUCT-PAGES-STDOUT] {stdout_text[-300:]}")
            if stderr_text:
                print(f"[PRODUCT-PAGES-STDERR] {stderr_text[-300:]}")

class UltraScraperOrchestrator:
    def __init__(self, planeta_limit=None, djak_limit=None):
        # AUTO-DETECT BASE PATH (cross-platform)
        current_dir = Path(os.getcwd())
        
        # If we're in python_scraper subdirectory, go up one level
        if current_dir.name == 'python_scraper':
            self.base_path = current_dir.parent
        # If we're in the main directory and python_scraper exists
        elif (current_dir / 'python_scraper').exists():
            self.base_path = current_dir
        # Fallback - search for python_scraper in current and parent dirs
        else:
            for potential_base in [current_dir, current_dir.parent]:
                if (potential_base / 'python_scraper').exists():
                    self.base_path = potential_base
                    break
            else:
                # Last resort - use current directory
                self.base_path = current_dir
        
        self.cpu_cores = psutil.cpu_count()
        self.memory_gb = psutil.virtual_memory().total / (1024**3)
        self.results = []
        self.active_processes = {}
        self.monitoring = True

        # Skip permissions fix - causes Operation not permitted errors
        # Will use alternative working directory strategy

        # Strategija na osnovu sistema
        self.strategy = self.calculate_strategy(planeta_limit, djak_limit)
        
        print(f"SISTEM INFO: {self.cpu_cores} cores, {self.memory_gb:.1f}GB RAM")
        print(f"   Current: {os.getcwd()}")
        
        python_scraper_path = self.base_path / 'python_scraper'
        if not python_scraper_path.exists():
            print(f"WARNING: python_scraper directory not found at {python_scraper_path}")
        
    def is_server_environment(self):
        """Detektuj VPS/Server environment"""
        server_indicators = [
            os.getenv('SSH_CONNECTION') is not None,
            os.getenv('TERM') in ['xterm', 'screen', 'tmux'],
            not os.getenv('DISPLAY'),
            os.path.exists('/proc/version'),
            'ubuntu' in str(os.uname().sysname).lower() if hasattr(os, 'uname') else False,
            'server' in os.getenv('USER', '').lower(),
            'root' == os.getenv('USER', ''),
            os.path.exists('/etc/os-release'),
            not os.path.exists('/System/Library/CoreServices/SystemVersion.plist'),  # Not macOS
            'vps' in os.getenv('HOSTNAME', '').lower(),
            'cloud' in os.getenv('HOSTNAME', '').lower(),
        ]
        
        detected_count = sum(bool(indicator) for indicator in server_indicators)
        is_server = detected_count >= 2
        
        # Server detection without verbose output
        
        return is_server

    def fix_server_permissions(self):
        """Fix permissions for root user on server"""
        try:
            python_scraper_path = self.base_path / 'python_scraper'
            result = os.system(f"chmod -R 777 {python_scraper_path}")
            if result == 0:
                print("Server permissions fixed!")
        except Exception:
            pass

    def calculate_strategy(self, planeta_limit=None, djak_limit=None):
        """BEAST MODE - MAKSIMALNA OPTIMIZACIJA ZA UNIVERZALNE SKRIPTE"""
        is_server = self.is_server_environment()
        strategy = {}  # <-- DODAJ OVO NA POCETAK

        if is_server:
            print("SERVER ULTRA STRATEGY MODE")
            if self.memory_gb >= 16 and self.cpu_cores >= 8:
                strategy = {
                    'bs4_concurrent': 4,
                    'fashion_workers': 4,
                    'planeta_instances': 3,
                    'djak_instances': 3,
                    'selenium_total_concurrent': 6,
                    'pause_between_batches': 1,
                    'max_timeout': 2400,
                    'aggressive_mode': True,
                    'chunk_size': 2000
                }
            elif self.memory_gb >= 8 and self.cpu_cores >= 4:
                strategy = {
                    'bs4_concurrent': 4,
                    'fashion_workers': 4,
                    'planeta_instances': 3,
                    'djak_instances': 3,
                    'selenium_total_concurrent': 6,
                    'pause_between_batches': 1,
                    'max_timeout': 2400,
                    'aggressive_mode': True,
                    'chunk_size': 2000
                }
            else:
                strategy = {
                    'bs4_concurrent': 6,
                    'fashion_workers': 6,
                    'planeta_instances': 2,
                    'djak_instances': 2,
                    'selenium_total_concurrent': 4,
                    'pause_between_batches': 2,
                    'max_timeout': 1200,
                    'aggressive_mode': True,
                    'chunk_size': 1000
                }
        else:
            if self.memory_gb >= 16 and self.cpu_cores >= 8:
                strategy = {
                    'bs4_concurrent': 8,
                    'fashion_workers': 10,
                    'planeta_instances': 4,
                    'djak_instances': 4,
                    'selenium_total_concurrent': 8,
                    'pause_between_batches': 5,
                    'max_timeout': 1500,
                    'aggressive_mode': False,
                    'chunk_size': 1200
                }
            elif self.memory_gb >= 8:
                strategy = {
                    'bs4_concurrent': 4,
                    'fashion_workers': 6,
                    'planeta_instances': 2,
                    'djak_instances': 2,
                    'selenium_total_concurrent': 4,
                    'pause_between_batches': 10,
                    'max_timeout': 1200,
                    'aggressive_mode': False,
                    'chunk_size': 800
                }
            else:
                strategy = {
                    'bs4_concurrent': 2,
                    'fashion_workers': 2,
                    'planeta_instances': 1,
                    'djak_instances': 1,
                    'selenium_total_concurrent': 2,
                    'pause_between_batches': 5,
                    'max_timeout': 900,
                    'aggressive_mode': False,
                    'chunk_size': 500
                }

        # OVDE OVERRIDE:
        if planeta_limit is not None:
            strategy['planeta_instances'] = planeta_limit
        if djak_limit is not None:
            strategy['djak_instances'] = djak_limit
        return strategy

    def discover_scrapers(self):
        """POKRENI SVE DOSTUPNE SKRIPTOVE - KOMPLETNA LISTA!"""
        # BS4 skriptovi (9) - brzi concurrent scraping 
        bs4_scrapers = [
            ('bs4_buzz', 'scraper_buzz.py'),
            ('bs4_extrasport', 'scraper_extrasport.py'),
            ('bs4_sportvision', 'scraper_sportvision.py'),
            ('bs4_nsport', 'scraper_nsport.py'),
            ('bs4_nselection', 'scraper_nselection.py'),
            ('bs4_intersport', 'scraper_intersport.py'),
            ('bs4_trendmaker', 'scraper_trendmaker.py'),
            ('bs4_etsport', 'scraper_etsport.py'),
        ]
        
        # Fashion uvek postoji
        fashion_found = True
        
        # Selenium skriptovi - PLANETA + DJAK + FASHION
        selenium_scrapers = [
            # Planeta skriptovi
            ('planeta_universal', 'planeta_scripts/scraper_planeta.py'),
            ('planeta_product_pages', 'planeta_scripts/scraper_planeta_product_pages.py'),
            
            # Djak skriptovi  
            ('djak_universal', 'djak_scripts/scraper_djak.py'),
            
            # Fashion skriptovi
            ('fashion_company', 'fashion_scripts/scraper_fashion_full.py'),
        ]
        
        print(f"DISCOVERED SCRAPERS:")
        print(f"   BS4: {len(bs4_scrapers)} scrapers (Buzz, Extrasport, Sportvision, NSport, N Selection, Intersport, Trendmaker, ETSport)")
        print(f"   Selenium: {len(selenium_scrapers)} scrapers")
        print(f"   Planeta: 2 variants (universal, product_pages)")
        print(f"   Djak: 1 scraper")
        print(f"   NSport family: 6 stores with unique IDs (7-12)")
        print(f"     - NSport glavna (7), NFashion (8), Lacoste (9)")
        print(f"     - N Selection (10), Intersport (11), Trendmaker (12)")
        print(f"   ETSport: Store ID 13")
        print(f"   Fashion: {'OK' if fashion_found else 'NOT FOUND'}")
        
        return bs4_scrapers, fashion_found, selenium_scrapers

    def run_universal_selenium_instance(self, instance_name, script_path, test_mode, instance_num, total_instances, scraper_type):
        """Pokreni jednu instancu univerzalne selenium skripte SA BEAST OPTIMIZACIJAMA"""
        full_path = self.base_path / "python_scraper" / script_path
        start_time = time.time()
        is_server = self.is_server_environment()
        try:
            python_executable = get_python_executable()
            args = []
            if platform.system().lower() == "linux":
                args = ['xvfb-run', '-a', python_executable, str(full_path)]
            else:
                args = [python_executable, str(full_path)]
            args.append('--headless')
            output_file = f"store_{scraper_type}_{instance_num}.json"
            args.extend(['--output', output_file])
            args.extend(['--instance', str(instance_num)])

            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            env['PYTHONLEGACYWINDOWSSTDIO'] = '1'
            env['PYTHONUNBUFFERED'] = '1'
            # UKLONI: env['DISPLAY'] = ':99'
            # ...ostale env varijable...

            timeout_duration = self.strategy['max_timeout'] if not test_mode else 900

            result = subprocess.run(
                args,
                cwd=str(self.base_path),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False,
                timeout=timeout_duration
            )
            stdout_text = result.stdout.decode('utf-8', errors='ignore') if result.stdout else ""
            stderr_text = result.stderr.decode('utf-8', errors='ignore') if result.stderr else ""
            print(f"\n--- OUTPUT {instance_name} ---\n{stdout_text}\n{stderr_text}\n--- END ---\n")
            
            duration = time.time() - start_time
            
            # PARSE OUTPUT ZA BROJ PROIZVODA - POBOLJSANO
            products_processed = 0
            if result.stdout:
                import re
                # Trazi razlicite pattern-e
                patterns = [
                    r'Total products processed: (\d+)',
                    r'(\d+) products processed',
                    r'completed: (\d+) products',
                    r'scraped (\d+) products',
                    r'found (\d+) products',
                    r'added (\d+) products'
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, result.stdout, re.IGNORECASE)
                    if match:
                        products_processed = int(match.group(1))
                        break
                
                # Ako nema ukupan broj, pokusaj da saberes batch-ove
                if products_processed == 0:
                    batch_matches = re.findall(r'batch of (\d+)', result.stdout, re.IGNORECASE)
                    if batch_matches:
                        products_processed = sum(int(match) for match in batch_matches)
            
            # DYNAMIC MESSAGE SA BEAST INFO
            limit_info = f"limit {args[args.index('--limit') + 1]}" if '--limit' in args else "no limit"
            mode_note = ""
            if is_server:
                mode_note = f" (beast-{scraper_type}-i{instance_num})"
            else:
                mode_note = f" ({scraper_type}-i{instance_num})"
                
            if result.returncode == 0:
                if products_processed > 0:
                    throughput = products_processed / (duration/60) if duration > 0 else 0
                    message = f'Success - {products_processed} products ({throughput:.0f}/min, {limit_info}){mode_note}'
                else:
                    message = f'Success ({limit_info}){mode_note}'
            else:
                message = f'Exit code: {result.returncode} ({limit_info}){mode_note}'
            
            return {
                'scraper': instance_name,
                'success': result.returncode == 0,
                'message': message,
                'duration': duration,
                'products_processed': products_processed,
                'scraper_type': scraper_type,
                'instance_num': instance_num,
                'output': result.stdout[-500:] if result.stdout else "",
                'error': result.stderr[-300:] if result.stderr else ""
            }
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            timeout_msg = f'Beast timeout ({timeout_duration/60:.0f}min) ({scraper_type}-i{instance_num})' if is_server else f'Timeout ({timeout_duration/60:.0f}min) ({scraper_type}-i{instance_num})'
            return self.create_error_result(instance_name, timeout_msg, duration)
        except Exception as e:
            duration = time.time() - start_time
            return self.create_error_result(instance_name, f'{str(e)} ({scraper_type}-i{instance_num})', duration)

    def run_universal_selenium_instance_category(self, instance_name, script_path, category_url, test_mode):
        full_path = self.base_path / "python_scraper" / script_path
        print(f"   [LOG] {instance_name}: category = {category_url}")
        start_time = time.time()
        is_server = self.is_server_environment()
        process = None  # Za cleanup u slucaju greske
        try:
            python_executable = get_python_executable()
            args = []
            if platform.system().lower() == "linux":
                args = ['xvfb-run', '-a', python_executable, str(full_path)]
            else:
                args = [python_executable, str(full_path)]
            args.append('--headless')
            args.extend(['--category', category_url])
            # No JSON output needed - scraper writes directly to database via API

            print(f"   [LOG] {instance_name}: args = {args}")

            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            env['PYTHONLEGACYWINDOWSSTDIO'] = '1'
            env['PYTHONUNBUFFERED'] = '1'

            # Specijalni timeout-ovi za razlicite scraper-e
            if "djak" in instance_name:
                timeout_duration = 3600  # 1 sat za Djak (dovoljno za svih 13k proizvoda)
                print(f"   [LOG] {instance_name}: DJAK TIMEOUT = 1 sat (svih 13k proizvoda)")
            elif "fashion" in instance_name:
                timeout_duration = 1800  # 30 minuta za Fashion (spor scraper, mnogo stranica)
                print(f"   [LOG] {instance_name}: FASHION TIMEOUT = 30 minuta (spor scraper)")
            else:
                timeout_duration = self.strategy['max_timeout'] if not test_mode else 900

            # Determine correct working directory based on script path
            script_dir = os.path.dirname(str(full_path))
            # No JSON files needed - scraper writes directly to database
            
            # Koristimo Popen umesto run da mozemo ubiti proces ako treba
            process = subprocess.Popen(
                args,
                cwd=script_dir,  # Use script's directory as CWD
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False
            )
            
            # Cekaj da se zavrsi SA TIMEOUT
            try:
                stdout, stderr = process.communicate(timeout=timeout_duration)
                result_returncode = process.returncode
            except subprocess.TimeoutExpired:
                print(f"   [LOG] {instance_name}: TIMEOUT - ubijam proces PID {process.pid}")
                process.kill()  # SIGKILL
                process.wait()  # Cekaj da se zavrsi
                stdout, stderr = process.communicate()
                result_returncode = -9  # Timeout killed
                
            print(f"   [LOG] {instance_name}: subprocess zavrsen sa kodom {result_returncode}")

            duration = time.time() - start_time

            # Parse output for products processed
            products_processed = 0
            stdout_text = ""
            try:
                stdout_text = stdout.decode('utf-8', errors='ignore') if stdout else ""
            except:
                stdout_text = str(stdout) if stdout else ""
                
            if stdout_text:
                import re
                patterns = [
                    r'Total products processed: (\d+)',
                    r'(\d+) products processed',
                    r'completed: (\d+) products',
                    r'scraped (\d+) products',
                    r'found (\d+) products',
                    r'added (\d+) products'
                ]
                for pattern in patterns:
                    match = re.search(pattern, stdout_text, re.IGNORECASE)
                    if match:
                        products_processed = int(match.group(1))
                        break
                # If not found, try to sum batches
                if products_processed == 0:
                    batch_matches = re.findall(r'batch of (\d+)', stdout_text, re.IGNORECASE)
                    if batch_matches:
                        products_processed = sum(int(match) for match in batch_matches)

            # Dynamic message
            if result_returncode == 0:
                if products_processed > 0:
                    throughput = products_processed / (duration/60) if duration > 0 else 0
                    message = f'Success - {products_processed} products ({throughput:.0f}/min)'
                else:
                    message = 'Success'
            elif result_returncode == -9:
                message = 'FORCE KILLED - Timeout exceeded'
            else:
                message = f'Exit code: {result_returncode}'

            stderr_text = ""
            try:
                stderr_text = stderr.decode('utf-8', errors='ignore') if stderr else ""
            except:
                stderr_text = str(stderr) if stderr else ""
                
            return {
                'scraper': instance_name,
                'success': result_returncode == 0,
                'message': message,
                'duration': duration,
                'products_processed': products_processed,
                'output': stdout_text[-500:] if stdout_text else "",
                'error': stderr_text[-300:] if stderr_text else ""
            }

        except Exception as e:
            duration = time.time() - start_time
            # Pokusaj da ubijes proces ako jos uvek radi
            if process and process.poll() is None:
                print(f"   [LOG] {instance_name}: EXCEPTION - ubijam proces PID {process.pid}")
                process.kill()
                process.wait()
            return self.create_error_result(instance_name, f'Error: {str(e)}', duration)   

    def run_store_by_store(self, test_mode=False, stores=None, with_pages=False):
        """
        Pokrece samo izabrane prodavnice (po store ID-jevima iz PHP-a).
        stores: lista stringova, npr. ["buzz", "planeta"]
        """
        bs4_scrapers, fashion_found, selenium_scrapers = self.discover_scrapers()

        # DEBUG LOG
        print(f"[DEBUG] run_store_by_store called with stores={stores}")
        print(f"[DEBUG] selenium_scrapers={selenium_scrapers}")
        print(f"[DEBUG] Starting DJAK processing...")

         # 3. DJAK WAVE - 3 POTPUNO ZASEBNE SKRIPTE (JEDNA PO JEDNA)
        # NEZAVISAN od selenium_scrapers - direktno proveravamo stores
        if not stores or "djak" in stores:
            print(f"[DEBUG] DJAK WAVE STARTED - executing 3 separate scripts (independent of selenium_scrapers)")
            
            # 3 potpuno zasebne skripte za svaku kategoriju - KORISTIMO NOVU RADNU SKRIPTU
            djak_scripts = [
                ("djak_universal_cat1", "djak_scripts/scraper_djak_nova.py", "https://www.djaksport.com/deca"),
                ("djak_universal_cat2", "djak_scripts/scraper_djak_nova.py", "https://www.djaksport.com/muskarci"), 
                ("djak_universal_cat3", "djak_scripts/scraper_djak_nova.py", "https://www.djaksport.com/zene")
            ]
            
            # Pokreni SEKVENCIJALNO - jednu po jednu DIREKTNO
            for instance_name, script_path, category_url in djak_scripts:
                print(f"   [DEBUG] Starting {instance_name} execution...")
                print(f"   [LOG] {instance_name}: category = {category_url}")
                print(f"   [LOG] {instance_name}: args = [python_executable, '{script_path}', '--headless']")
                
                full_path = self.base_path / "python_scraper" / script_path
                print(f"   [DEBUG] full_path = {full_path}")
                print(f"   [DEBUG] path exists = {full_path.exists()}")
                start_time = time.time()
                
                try:
                    python_executable = get_python_executable()
                    args = []
                    if platform.system().lower() == "linux":
                        args = ['xvfb-run', '-a', python_executable, str(full_path)]
                    else:
                        args = [python_executable, str(full_path)]
                    args.append('--headless')
                    args.extend(['--category', category_url])  # Dodaj kategoriju kao argument
                    
                    # DJAK timeout je UNLIMITED
                    print(f"   [LOG] {instance_name}: DJAK TIMEOUT = UNLIMITED (svih 13k proizvoda)")
                    
                    env = os.environ.copy()
                    env['PYTHONIOENCODING'] = 'utf-8'
                    env['PYTHONLEGACYWINDOWSSTDIO'] = '1'
                    env['PYTHONUNBUFFERED'] = '1'
                    
                    script_dir = os.path.dirname(str(full_path))
                    
                    # Pokreni subprocess DIREKTNO
                    process = subprocess.Popen(
                        args,
                        cwd=script_dir,
                        env=env,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=False
                    )
                    
                    # Cekaj da se zavrsi BEZ timeout-a (UNLIMITED)
                    stdout, stderr = process.communicate()
                    result_returncode = process.returncode
                    
                    print(f"   [LOG] {instance_name}: subprocess zavrsen sa kodom {result_returncode}")
                    
                    duration = time.time() - start_time
                    
                    # Parse output za broj proizvoda
                    products_processed = 0
                    stdout_text = ""
                    try:
                        stdout_text = stdout.decode('utf-8', errors='ignore') if stdout else ""
                    except:
                        stdout_text = str(stdout) if stdout else ""
                        
                    if stdout_text:
                        import re
                        patterns = [
                            r'Total products processed: (\d+)',
                            r'(\d+) products processed',
                            r'completed: (\d+) products',
                            r'scraped (\d+) products',
                            r'found (\d+) products',
                            r'added (\d+) products'
                        ]
                        for pattern in patterns:
                            matches = re.findall(pattern, stdout_text, re.IGNORECASE)
                            if matches:
                                products_processed = int(matches[-1])
                                break
                    
                    # Kreiraj rezultat
                    if result_returncode == 0:
                        if products_processed > 0:
                            message = f'Success - {products_processed} products'
                        else:
                            message = 'Success'
                        success = True
                    else:
                        message = f'Exit code: {result_returncode}'
                        success = False
                    
                    result = {
                        'scraper': instance_name,
                        'success': success,
                        'message': message,
                        'duration': duration,
                        'products_processed': products_processed
                    }
                    self.results.append(result)
                    self.print_result(result)
                    
                except Exception as e:
                    print(f"[ERROR] Greska u {instance_name}: {e}")
                    duration = time.time() - start_time
                    error_result = {
                        'scraper': instance_name,
                        'success': False,
                        'message': f'Greska: {str(e)}',
                        'duration': duration,
                        'products_processed': 0
                    }
                    self.results.append(error_result)

        # 1. BS4 store-ovi (Buzz, Extrasport, Sportvision)
        for name, script in bs4_scrapers:
            # name: npr. "bs4_buzz"
            if stores:
                allowed_names = [f"bs4_{s}" for s in stores]
                if name not in allowed_names:
                    continue
            print(f"\n Pokrecem {name} (BS4, sve kategorije paralelno)")
            categories = SCRAPER_CATEGORIES.get(script, [])
            # Ogranicavam BS4 na max 6 paralelnih procesa
            max_workers_bs4 = min(6, len(categories))
            print(f"   Max workers (BS4): {max_workers_bs4}")
            with ThreadPoolExecutor(max_workers=max_workers_bs4) as executor:
                futures = []
                for idx, category_url in enumerate(categories):
                    instance_name = f"{name}_cat{idx+1}"
                    future = executor.submit(
                        self.run_universal_selenium_instance_category,
                        instance_name, script, category_url, test_mode
                    )
                    futures.append((future, instance_name))
                for future, instance_name in futures:
                    result = future.result()
                    self.results.append(result)
                    self.print_result(result)

        # 1b. NSport FAMILY (NSport, NFashion, Lacoste) - BS4 scrapers with special handling
        nsport_stores = ["nsport", "nfashion", "lacoste"]
        for store_name in nsport_stores:
            if stores and store_name not in stores:
                continue
            
            print(f"\n🚀 Pokrecem {store_name.upper()} (NSport family BS4 scraper)")
            # NSport scraper handles all 3 variants internally - just run it once for the specific store
            script = "scraper_nsport.py"
            categories = SCRAPER_CATEGORIES.get(script, [])
            
            # Filter categories for this specific store
            if store_name == "nsport":
                # NSport: regular URLs without &fashion=1 or &lacoste=1
                filtered_categories = [url for url in categories if "&fashion=1" not in url and "&lacoste=1" not in url]
            elif store_name == "nfashion":
                # NFashion: URLs with &fashion=1
                filtered_categories = [url for url in categories if "&fashion=1" in url]
            elif store_name == "lacoste":
                # Lacoste: URLs with &lacoste=1  
                filtered_categories = [url for url in categories if "&lacoste=1" in url]
            
            print(f"   {store_name} kategorije ({len(filtered_categories)})")
            if len(filtered_categories) == 0:
                print(f"   [WARNING] Nema kategorija za {store_name}")
                continue
                
            # Run NSport scraper - it handles store_id internally
            max_workers_nsport = min(6, len(filtered_categories))
            print(f"   Max workers ({store_name}): {max_workers_nsport}")
            with ThreadPoolExecutor(max_workers=max_workers_nsport) as executor:
                futures = []
                for idx, category_url in enumerate(filtered_categories):
                    instance_name = f"{store_name}_cat{idx+1}"
                    future = executor.submit(
                        self.run_universal_selenium_instance_category,
                        instance_name, script, category_url, test_mode
                    )
                    futures.append((future, instance_name))
                for future, instance_name in futures:
                    result = future.result()
                    self.results.append(result)
                    self.print_result(result)

        # 2. PLANETA WAVE - kategorijski scrapers
        planeta_scrapers = [(name, script) for name, script in selenium_scrapers if 'planeta' in name]
        if planeta_scrapers and (not stores or "planeta" in stores):
            for name, script in planeta_scrapers:
                print(f"\n[WORLD] WAVE 1: Pokrecem {name} (planeta kategorijski)")
                categories = SCRAPER_CATEGORIES.get(script, [])
                print(f"   Kategorije ({len(categories)}): {categories}")
                if len(categories) == 0:
                    print(f"   [ERROR] Nema kategorija za {script}")
                    continue
                
                # Planeta paralelno po kategorijama
                max_workers = len(categories)
                print(f"   Planeta: paralelno {max_workers} kategorija")
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = []
                    for idx, category_url in enumerate(categories):
                        instance_name = f"{name}_cat{idx+1}"
                        future = executor.submit(
                            self.run_universal_selenium_instance_category,
                            instance_name, script, category_url, test_mode
                        )
                        futures.append((future, instance_name))
                    for future, instance_name in futures:
                        result = future.result()
                        self.results.append(result)
                        self.print_result(result)

        # 2b. PLANETA PRODUCT PAGES odmah nakon kategorijskih
        if (not stores or "planeta" in stores) and with_pages:
            print("\n[WORLD] WAVE 1b: PLANETA PRODUCT PAGES (odmah nakon kategorijskih)")
            # Proveri da li se fajl kreirao tokom kategorijskog scraping-a
            input_file_path = 'python_scraper/planeta_scripts/planeta_proizvodi_bez_sifre.txt'
            if os.path.exists(input_file_path):
                with open(input_file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    print(f" Fajl planeta_proizvodi_bez_sifre.txt postoji sa {len(lines)} linija")
            else:
                print(f"[WARNING]  Fajl {input_file_path} NE POSTOJI - proveravaj save_url_without_code funkciju")
            
            try:
                run_planeta_product_pages_parallel(num_instances=10)
                print("[OK] PLANETA PRODUCT PAGES zavrseni uspesno!")
            except Exception as e:
                print(f"[ERROR] Greska pri pokretanju planeta_product_pages: {e}")
                import traceback
                traceback.print_exc()


        # 4. FASHION WAVE - paralelno max 4
        fashion_scrapers = [(name, script) for name, script in selenium_scrapers if 'fashion' in name]
        if fashion_scrapers and (not stores or "fashion" in stores):
            for name, script in fashion_scrapers:
                print(f"\n[FASHION] WAVE 3: Pokrecem {name} (fashion paralelno max 4)")
                categories = SCRAPER_CATEGORIES.get(script, [])
                print(f"   Kategorije ({len(categories)}): {categories}")
                if len(categories) == 0:
                    print(f"   [ERROR] Nema kategorija za {script}")
                    continue
                
                # Fashion max 4 paralelno
                max_workers = min(4, len(categories))
                print(f"   Fashion: paralelno max {max_workers} kategorija")
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = []
                    for idx, category_url in enumerate(categories):
                        instance_name = f"{name}_cat{idx+1}"
                        future = executor.submit(
                            self.run_universal_selenium_instance_category,
                            instance_name, script, category_url, test_mode
                        )
                        futures.append((future, instance_name))
                    for future, instance_name in futures:
                        result = future.result()
                        self.results.append(result)
                        self.print_result(result)

        # 5. Ocisti Chrome procese nakon selenium scrapers
        print("\n[CLEAN] Cistim Chrome procese nakon selenium scrapers...")
        cleanup_chrome_processes()

        # 6. Finalno ciscenje Chrome procesa pre export-a
        print("\n[CLEAN] Finalno ciscenje Chrome procesa...")
        cleanup_chrome_processes()
        
        # 7. Pokreni Laravel export tek kada se SVE zavrsi
        print("\n[EXPORT] Pokrecem finalni Laravel export...")
        trigger_laravel_export(stores)


    def run_fashion_wave(self, test_mode):
        """Wave 3: Fashion - pokrece kategoriju po kategoriju kao sto radi u store_by_store"""
        print("[FIRE] Fashion: pokrecem kategoriju po kategoriju (kao u store_by_store)")
        
        # Koristim iste kategorije kao u SCRAPER_CATEGORIES
        fashion_script = 'fashion_scripts/scraper_fashion_full.py'
        categories = SCRAPER_CATEGORIES.get(fashion_script, [])
        print(f"   Fashion kategorije ({len(categories)}): {categories}")
        
        if len(categories) == 0:
            print(f"   [ERROR] Nema kategorija za Fashion")
            return
            
        # Fashion max 4 paralelno
        max_workers = min(4, len(categories))
        print(f"   Fashion: paralelno max {max_workers}")
        
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for idx, category_url in enumerate(categories):
                instance_name = f"fashion_company_cat{idx+1}"
                future = executor.submit(
                    self.run_universal_selenium_instance_category,
                    instance_name, fashion_script, category_url, test_mode
                )
                futures.append((future, instance_name))
            for future, instance_name in futures:
                result = future.result()
                self.results.append(result)
                self.print_result(result)

    def run_single_scraper(self, scraper_name, scraper_path, test_mode):
        """Pokreni BS4 skriptu SA REAL-TIME OUTPUT TRACKING"""
        full_path = self.base_path / "python_scraper" / scraper_path
        
        if not full_path.exists():
            return self.create_error_result(scraper_name, f'Script not found: {scraper_path}')
        
        print(f"  {scraper_name}")
        start_time = time.time()
        
        try:
            python_executable = get_python_executable()
            args = [python_executable, str(full_path)]
            is_server = self.is_server_environment()
            
            # BEAST MODE ENVIRONMENT VARIABLES
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            env['PYTHONLEGACYWINDOWSSTDIO'] = '1'
            env['PYTHONUNBUFFERED'] = '1'
            
            if is_server:
                env['BEAST_MODE'] = '1'
                env['CHROME_NO_SANDBOX'] = '1'
            
            timeout_duration = self.strategy['max_timeout'] if not test_mode else 600
            
            print(f"   🔧 BS4 script - running without --limit argument")
            
            result = subprocess.run(
                args,
                cwd=str(self.base_path),
                capture_output=True,
                text=False,
                env=env,
                timeout=timeout_duration
            )
            
            duration = time.time() - start_time
            
            # Parse products processed
            products_processed = 0
            stdout_text = result.stdout.decode('utf-8', errors='ignore') if result.stdout else ""
            stderr_text = result.stderr.decode('utf-8', errors='ignore') if result.stderr else ""
            
            if stdout_text:
                import re
                patterns = [
                    r'Total products processed: (\d+)',
                    r'(\d+) products sent',
                    r'batch: (\d+) products',
                    r'found (\d+) products'
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, stdout_text, re.IGNORECASE)
                    if matches:
                        if pattern == r'(\d+) products sent' or pattern == r'batch: (\d+) products':
                            # Sum all batches
                            products_processed = sum(int(match) for match in matches)
                        else:
                            products_processed = int(matches[-1])
                        break
            
            # MESSAGE
            if result.returncode == 0:
                if products_processed > 0:
                    message = f'Success - {products_processed} products (no limit)'
                else:
                    message = 'Success (no limit)'
            else:
                message = f'Exit code: {result.returncode} (no limit)'
                
            if is_server and result.returncode == 0:
                message += " (beast)"
            
            return {
                'scraper': scraper_name,
                'success': result.returncode == 0,
                'message': message,
                'duration': duration,
                'products_processed': products_processed,
                'output': result.stdout[-300:] if result.stdout else "",
                'error': result.stderr[-200:] if result.stderr else ""
            }
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            timeout_msg = f'Beast timeout ({timeout_duration/60:.0f}min)' if is_server else f'Timeout ({timeout_duration/60:.0f}min)'
            return self.create_error_result(scraper_name, timeout_msg, duration)
        except Exception as e:
            duration = time.time() - start_time
            return self.create_error_result(scraper_name, str(e), duration)

    def create_error_result(self, scraper_name, message, duration=0):
        """Kreiraj error rezultat"""
        return {
            'scraper': scraper_name,
            'success': False,
            'message': message,
            'duration': duration,
            'products_processed': 0
        }

    def print_result(self, result):
        """Prikazi rezultat sa BEAST MODE styling"""
        status = "[OK]" if result['success'] else "[ERROR]"
        duration = f"{result['duration']/60:.1f}min" if result['duration'] > 60 else f"{result['duration']:.0f}s"
        
        products_info = ""
        if result.get('products_processed', 0) > 0:
            products_info = f" | {result['products_processed']} products"
        
        # BEAST MODE styling
        if self.is_server_environment() and result['success'] and 'beast' in result.get('message', ''):
            print(f"[FIRE] {result['scraper']}: {result['message']} ({duration}){products_info}")
        else:
            print(f"{status} {result['scraper']}: {result['message']} ({duration}){products_info}")

    def generate_final_report(self, total_time):
        """Generisi finalni izvestaj sa BEAST MODE statistikama"""
        if not self.results:
            print("[STATS] No results to display")
            return
            
        total_scrapers = len(self.results)
        successful = len([r for r in self.results if r['success']])
        failed = total_scrapers - successful
        is_server = self.is_server_environment()
        
        # Calculate total products
        total_products = sum(r.get('products_processed', 0) for r in self.results if r.get('products_processed', 0) > 0)
        
        print("\n" + "="*70)
        if is_server:
            print("[FIRE] BEAST MODE FINAL REPORT - UNIVERSAL SCRAPERS")
        else:
            print("[STATS] ULTRA SCRAPER FINAL REPORT - UNIVERSAL SCRAPERS")
        print("="*70)
        
        print(f"[TIME] Total Time: {total_time/60:.1f} minutes ({total_time/3600:.1f} hours)")
        print(f"[STATS] Scrapers: {successful}[OK] / {failed}[ERROR] / {total_scrapers} total")
        
        if total_products > 0:
            throughput = total_products / (total_time/60) if total_time > 0 else 0
            print(f"[TARGET] Products: {total_products:,} total ({throughput:.0f}/min throughput)")
            
            if is_server:
                print(f"[FIRE] BEAST PERFORMANCE: {total_products:,} products in {total_time/60:.1f}min!")
        
        # Group by scraper type
        bs4_results = [r for r in self.results if 'bs4_' in r['scraper']]
        selenium_results = [r for r in self.results if any(x in r['scraper'] for x in ['planeta', 'djak'])]
        fashion_results = [r for r in self.results if 'fashion' in r['scraper']]
        
        if bs4_results:
            bs4_products = sum(r.get('products_processed', 0) for r in bs4_results)
            bs4_success = sum(1 for r in bs4_results if r['success'])
            print(f"[FAST] BS4: {bs4_success}/{len(bs4_results)} successful | {bs4_products:,} products")
        
        if selenium_results:
            selenium_products = sum(r.get('products_processed', 0) for r in selenium_results)
            selenium_success = sum(1 for r in selenium_results if r['success'])
            planeta_count = len([r for r in selenium_results if 'planeta' in r['scraper']])
            djak_count = len([r for r in selenium_results if 'djak' in r['scraper']])
            print(f"[WAVE] Universal Selenium: {selenium_success}/{len(selenium_results)} successful | {selenium_products:,} products")
            print(f"   └─ Planeta: {planeta_count} instances | Djak: {djak_count} instances")
        
        if fashion_results:
            fashion_products = sum(r.get('products_processed', 0) for r in fashion_results)
            fashion_success = sum(1 for r in fashion_results if r['success'])
            print(f"[FIRE] Fashion: {fashion_success}/{len(fashion_results)} successful | {fashion_products:,} products")
        
        # Failed scrapers
        failed_scrapers = [r for r in self.results if not r['success']]
        if failed_scrapers:
            print(f"\n[ERROR] Failed scrapers ({len(failed_scrapers)}):")
            for r in failed_scrapers[:5]:  # Show first 5
                print(f"   • {r['scraper']}: {r['message']}")
            if len(failed_scrapers) > 5:
                print(f"   ... and {len(failed_scrapers) - 5} more")
        
        if is_server and total_products > 0:
            print(f"\n[FIRE] BEAST MODE MISSION ACCOMPLISHED!")
            print(f"[TARGET] {total_products:,} products scraped in {total_time/60:.1f} minutes")
            print(f"[FAST] AVERAGE: {throughput:.0f} products per minute")
        
        print("="*70)
        
def trigger_laravel_export(stores_run=None):
    try:
        start = datetime.now()
        print(f"[EXPORT] Zavrsavam scraping sesiju i pokrecem Laravel eksport: {start}")
        
        # Zavrsi scraping sesiju prvo
        if 'session_key' in globals() and session_key:
            try:
                if platform.system().lower().startswith("win"):
                    end_session_url = "http://127.0.0.1:8000/api/products/end-session"
                else:
                    end_session_url = "http://192.168.100.24/api/products/end-session"
                
                session_resp = requests.post(end_session_url, json={'session_key': session_key})
                session_data = session_resp.json()
                
                if session_data.get('success'):
                    print(f"[OK] Scraping sesija zavrsena!")
                    print(f"[TIME] Trajanje scraping-a: {session_data.get('duration', 'N/A')}")
                    print(f"[STATS] Ukupno proizvoda: {session_data.get('products_count', 0)}")
                    
                    # Koristi finalni session kljuc sa trajanjem za export
                    final_session_key = session_data.get('final_session_key', session_key)
                    print(f"[TARGET] Finalni session kljuc za export: {final_session_key}")
                else:
                    print(f"[WARNING] Problem sa zavrsavanjem sesije: {session_data.get('message')}")
                    final_session_key = session_key  # fallback
                    
            except Exception as e:
                print(f"[WARNING] Greska pri zavrsavanju sesije: {e}")
                final_session_key = session_key  # fallback
        else:
            final_session_key = session_key if 'session_key' in globals() else None
        
        # Pokreni export sa finalnim session kljucem
        url_suffix = ""
        if stores_run:
            if isinstance(stores_run, list):
                url_suffix = f"?stores={','.join(stores_run)}"
            else:
                url_suffix = f"?stores={stores_run}"
        
        # Dodaj finalni session kljuc u URL ako postoji
        if final_session_key:
            separator = "&" if url_suffix else "?"
            url_suffix += f"{separator}session_key={final_session_key}"
        
        if platform.system().lower().startswith("win"):
            resp = requests.get(f"http://127.0.0.1:8000/api/products/export-excel{url_suffix}")
        else:
            resp = requests.get(f"http://192.168.100.24/api/products/export-excel{url_suffix}")
        
        end = datetime.now()
        print(f"[OK] Laravel eksport zavrsen: {end}")
        print(f"[TIME] Trajanje eksportovanja: {(end-start).total_seconds():.1f}s")
        print(f"Laravel response: {resp.text[:300]}")
        
    except Exception as e:
        print(f"[ERROR] Greska pri eksportovanju u Laravelu: {e}")

def main():

    print("[FAST] ULTRA SCRAPER ORCHESTRATOR v4.0 BEAST MODE - UNIVERSAL SCRAPERS")
    print("=" * 70)

    # OBRISI BAZU PRE SCRAPINGA
    clear_database()

    print("[FAST] ULTRA SCRAPER ORCHESTRATOR v4.0 BEAST MODE - UNIVERSAL SCRAPERS")
    print("=" * 70)

    # DODAJ INPUT ZA LIMITE
    try:
        planeta_limit = int(input("Rucno limitiraj Planeta instance (npr. 1): ").strip())
    except:
        planeta_limit = None
    try:
        djak_limit = int(input("Rucno limitiraj Djak instance (npr. 1): ").strip())
    except:
        djak_limit = None

    orchestrator = UltraScraperOrchestrator(planeta_limit=planeta_limit, djak_limit=djak_limit)

    print("\nOPTIONS:")
    print("1. Test Mode (quick test with limits)")
    print("2.  Production Mode (sequential waves)")
    print("3. [FAST] ULTRA-PARALLEL Mode (all waves simultaneous)")
    print("4.  Discovery Only (scan scripts)")  
    print("5. [ERROR] Exit")
    print("6.  Paralelni product page scraper (Planeta)")

    choice = input("\nChoice (1/2/3/4/5/6): ").strip()

    if choice == "5":
        print(" Goodbye!")
        return
    elif choice == "4":
        orchestrator.discover_scrapers()
        return
    elif choice == "1":
        print("\n TEST MODE SELECTED")
        if orchestrator.is_server_environment():
            print("   - BEAST MODE: BS4 no limit, Fashion test, Universal Selenium limit 30")
        else:
            print("   - BS4 scripts: no limit")
            print("   - Fashion: test mode")
            print("   - Universal Selenium: limit 30 per instance")
        orchestrator.run_ultra_strategy(test_mode=True)
    elif choice == "3":
        if orchestrator.is_server_environment():
            print("\n[FAST] ULTRA-PARALLEL BEAST MODE SELECTED")
            print("   - ALL WAVES RUN SIMULTANEOUSLY!")
            print(f"   - BS4 ({orchestrator.strategy['bs4_concurrent']} concurrent) + Universal Selenium ({orchestrator.strategy['planeta_instances'] + orchestrator.strategy['djak_instances']} instances) + Fashion ({orchestrator.strategy['fashion_workers']} workers)")
            print("   - MAXIMUM POSSIBLE THROUGHPUT!")
        else:
            print("\n[FAST] ULTRA-PARALLEL MODE SELECTED")
            print("   - All scraper types run simultaneously")
            print("   - Maximum resource utilization")
        orchestrator.run_ultra_strategy_parallel(test_mode=False)
    elif choice == "6":
        try:
            num_instances = int(input("Broj paralelnih instanci (npr. 4): ").strip())
        except:
            num_instances = 4
        run_planeta_product_pages_parallel(num_instances)
        return
    else:
        if orchestrator.is_server_environment():
            print("\n[FIRE] BEAST PRODUCTION MODE SELECTED")
            print("   - Sequential waves: BS4 → Universal Selenium → Fashion")
        else:
            print("\n PRODUCTION MODE SELECTED")
            print("   - Sequential scraping waves")
        orchestrator.run_ultra_strategy(test_mode=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--stores', type=str, default=None)
    parser.add_argument('--with-pages', action='store_true', help='Pokreni i product pages za Planeta')
    args, unknown = parser.parse_known_args()
    stores = None
    with_pages = args.with_pages
    
    if args.stores:
        # Mapiraj ID-jeve u stringove ili prihvati direktno ime prodavnice
        stores = []
        for s in args.stores.split(','):
            s = s.strip()
            if s in STORE_ID_MAP:
                # ID broj prodavnice (npr. "1" za planeta)
                stores.append(STORE_ID_MAP[s])
            elif s in STORE_ID_MAP.values():
                # Direktno ime prodavnice (npr. "planeta")
                stores.append(s)
            else:
                print(f"[WARNING]  Nepoznata prodavnica: {s}")
                print(f"   Dostupne: {list(STORE_ID_MAP.values())} ili ID-jevi: {list(STORE_ID_MAP.keys())}")

    if '--test' in sys.argv:
        orchestrator = UltraScraperOrchestrator()
        orchestrator.run_ultra_strategy(test_mode=True)
        sys.exit(0)
    if '--ultra-parallel' in sys.argv:
        clear_database()
        orchestrator = UltraScraperOrchestrator()
        orchestrator.run_store_by_store(test_mode=False, stores=stores, with_pages=with_pages)
        # trigger_laravel_export() se poziva unutar run_store_by_store
        sys.exit(0)
    orchestrator = UltraScraperOrchestrator()
    if orchestrator.is_server_environment():
        print("\n[FIRE] BEAST MODE AUTO-START za server/cron okruzenje!")
        orchestrator.run_ultra_strategy(test_mode=False)
        trigger_laravel_export("full")
    else:
        main()
        
print("=== SCRAPER ZAVRSEN ===")
# logfile.flush()
# logfile.close()