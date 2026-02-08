#!/usr/bin/env python3
"""
Fashion Scraper Exact Code Path Test
Run the exact same logic as the Fashion scraper to find the error
"""
import requests
from bs4 import BeautifulSoup
import time
import pandas as pd
import sys
import os
import platform
from datetime import datetime

print("=== FASHION SCRAPER EXACT CODE PATH TEST ===")
print(f"Args: {sys.argv}")

# Simulate the exact arguments the Fashion scraper receives
test_args = ['scraper_fashion_full.py', '--headless', '--category', 'https://www.fashionandfriends.com/rs/zene/odeca/', '--output', 'fashion_company_cat1.json']
sys.argv = test_args

print("=== TESTING LOG FILE SETUP ===")
try:
    # FASHION LOG SETUP - exact same as scraper
    fashion_logfile = open("FASHION_LOG.txt", "a", encoding="utf-8")

    def fashion_log(message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)
        fashion_logfile.write(log_msg + "\n")
        fashion_logfile.flush()

    fashion_log("=== FASHION SCRAPER CODE PATH TEST ===")
    fashion_log(f"[DEBUG] sys.argv: {sys.argv}")
    print("[OK]  Log file setup works")
except Exception as e:
    print(f"[ERROR]  Log file setup failed: {e}")
    sys.exit(1)

print("=== TESTING ARGUMENT PARSING ===")
try:
    # Parse arguments - exact same logic
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

    print(f"[OK]  Argument parsing works - Categories: {CATEGORIES}, Output: {OUTPUT_FILE}, Headless: {HEADLESS_MODE}")
except Exception as e:
    print(f"[ERROR]  Argument parsing failed: {e}")
    sys.exit(1)

print("=== TESTING API URL SETUP ===")
try:
    if platform.system().lower() == "windows":
        API_URL = "http://127.0.0.1:8000/api/products/batch"
    else:
        API_URL = "http://192.168.100.24/api/products/batch"
    print(f"[OK]  API URL setup works: {API_URL}")
except Exception as e:
    print(f"[ERROR]  API URL setup failed: {e}")
    sys.exit(1)

print("=== TESTING MAPPING FILE LOAD ===")
try:
    # Exact same mapping logic
    if platform.system().lower() == "windows":
        mapping_path = r"C:\laragon\www\scraper\python_scraper\fashion_scripts\fc_nsport_mapping.xlsx"
    else:
        mapping_path = "/var/www/dataFlow/python_scraper/fashion_scripts/fc_nsport_mapping.xlsx"

    mapping_df = pd.read_excel(mapping_path)
    fashion_log(f"[DEBUG] Loaded mapping with columns: {mapping_df.columns.tolist()}")
    mapping_df['FC SIFRA'] = mapping_df['FC SIFRA'].astype(str).str.strip().str.upper()
    fc2nsport_map = {fc: nsport for fc, nsport in zip(mapping_df['FC SIFRA'], mapping_df['N SPORT SIFRA'])}
    fashion_log(f"[DEBUG] Loaded {len(fc2nsport_map)} mappings from {mapping_path}")
    print(f"[OK]  Mapping file load works: {len(fc2nsport_map)} mappings")
except Exception as e:
    print(f"[ERROR]  Mapping file load failed: {e}")
    fashion_log(f"[ERROR] Failed to load mapping file {mapping_path}: {e}")
    fc2nsport_map = {}
    sys.exit(1)

print("=== TESTING MAIN FUNCTION START ===")
try:
    batch = []
    total_processed = 0
    print("[OK]  Main function variables initialized")
except Exception as e:
    print(f"[ERROR]  Main function initialization failed: {e}")
    sys.exit(1)

print("=== ALL CODE PATH TESTS PASSED ===")
fashion_log("=== CODE PATH TEST COMPLETED ===")
fashion_logfile.close()
print("Fashion scraper code path should work")
sys.exit(0)