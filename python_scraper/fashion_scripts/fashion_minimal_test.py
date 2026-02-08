#!/usr/bin/env python3
"""
Minimal Fashion Scraper Test - Debug the actual failure point
"""
import sys
import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
import platform
from datetime import datetime

print("=== MINIMAL FASHION SCRAPER TEST ===", flush=True)
print(f"Python: {sys.version}", flush=True)
print(f"Args: {sys.argv}", flush=True)

# Test 1: Argument parsing (exact same as real scraper)
print("--- TEST 1: Argument Parsing ---", flush=True)
try:
    CATEGORIES = []
    OUTPUT_FILE = None
    HEADLESS_MODE = False

    if "--category" in sys.argv:
        category_index = sys.argv.index("--category")
        if category_index + 1 < len(sys.argv):
            CATEGORIES = [sys.argv[category_index + 1]]
            print(f"[OK]  Category: {CATEGORIES[0]}", flush=True)

    if "--output" in sys.argv:
        output_index = sys.argv.index("--output")
        if output_index + 1 < len(sys.argv):
            OUTPUT_FILE = sys.argv[output_index + 1]
            print(f"[OK]  Output: {OUTPUT_FILE}", flush=True)

    if "--headless" in sys.argv:
        HEADLESS_MODE = True
        print("[OK]  Headless mode enabled", flush=True)

    if not CATEGORIES:
        print("[ERROR]  No categories specified", flush=True)
        sys.exit(1)
        
except Exception as e:
    print(f"[ERROR]  Argument parsing failed: {e}", flush=True)
    sys.exit(1)

# Test 2: API URL setup
print("--- TEST 2: API URL Setup ---", flush=True)
try:
    if platform.system().lower() == "windows":
        API_URL = "http://127.0.0.1:8000/api/products/batch"
    else:
        API_URL = "http://192.168.100.24/api/products/batch"
    print(f"[OK]  API URL: {API_URL}", flush=True)
except Exception as e:
    print(f"[ERROR]  API URL setup failed: {e}", flush=True)
    sys.exit(1)

# Test 3: Mapping file load
print("--- TEST 3: Mapping File Load ---", flush=True)
try:
    if platform.system().lower() == "windows":
        mapping_path = r"C:\laragon\www\scraper\python_scraper\fashion_scripts\fc_nsport_mapping.xlsx"
    else:
        mapping_path = "/var/www/dataFlow/python_scraper/fashion_scripts/fc_nsport_mapping.xlsx"
    
    print(f"Loading mapping from: {mapping_path}", flush=True)
    mapping_df = pd.read_excel(mapping_path)
    mapping_df['FC SIFRA'] = mapping_df['FC SIFRA'].astype(str).str.strip().str.upper()
    fc2nsport_map = {fc: nsport for fc, nsport in zip(mapping_df['FC SIFRA'], mapping_df['N SPORT SIFRA'])}
    print(f"[OK]  Loaded {len(fc2nsport_map)} mappings", flush=True)
except Exception as e:
    print(f"[ERROR]  Mapping file load failed: {e}", flush=True)
    sys.exit(1)

# Test 4: HTTP Request to first category
print("--- TEST 4: HTTP Request ---", flush=True)
try:
    category_url = CATEGORIES[0]
    print(f"Requesting: {category_url}", flush=True)
    
    response = requests.get(category_url, timeout=15)
    print(f"[OK]  HTTP {response.status_code}", flush=True)
    
    if response.status_code != 200:
        print(f"[ERROR]  Bad status code: {response.status_code}", flush=True)
        sys.exit(1)
        
except Exception as e:
    print(f"[ERROR]  HTTP request failed: {e}", flush=True)
    sys.exit(1)

# Test 5: HTML Parsing
print("--- TEST 5: HTML Parsing ---", flush=True)
try:
    soup = BeautifulSoup(response.text, "html.parser")
    product_elements = soup.select("li.item.product")
    print(f"[OK]  Found {len(product_elements)} product elements", flush=True)
    
    if len(product_elements) == 0:
        # Try alternative selectors
        alt_selectors = [
            "li.product-item",
            "div.product-item", 
            ".product",
            "[data-element-sku]"
        ]
        
        for selector in alt_selectors:
            alt_elements = soup.select(selector)
            if alt_elements:
                print(f"[OK]  Alternative selector '{selector}': {len(alt_elements)} elements", flush=True)
                product_elements = alt_elements
                break
                
except Exception as e:
    print(f"[ERROR]  HTML parsing failed: {e}", flush=True)
    sys.exit(1)

# Test 6: Product Processing
print("--- TEST 6: Product Processing ---", flush=True)
try:
    products_found = 0
    
    for i, item in enumerate(product_elements[:5]):  # Test first 5 products
        try:
            fc_sku = item.get("data-element-sku", "")
            if not fc_sku:
                continue
                
            fc_sku_norm = str(fc_sku).strip().upper()
            nsport_sifra = fc2nsport_map.get(fc_sku_norm)
            
            if nsport_sifra:
                products_found += 1
                print(f"[OK]  Product {i+1}: {fc_sku} -> {nsport_sifra}", flush=True)
                
        except Exception as e:
            print(f"WARNING:   Product {i+1} processing failed: {e}", flush=True)
            continue
            
    print(f"[OK]  Found {products_found} matching products", flush=True)
    
except Exception as e:
    print(f"[ERROR]  Product processing failed: {e}", flush=True)
    sys.exit(1)

# Test 7: API Test (optional, don't fail if API is down)
print("--- TEST 7: API Test ---", flush=True)
try:
    test_data = [{"code": "TEST", "naziv": "Test", "brand": "Test", "price": 100, "old_price": None, "store_id": 6}]
    api_response = requests.post(API_URL, json=test_data, timeout=15)
    print(f"[OK]  API test: {api_response.status_code}", flush=True)
except Exception as e:
    print(f"WARNING:   API test failed (non-fatal): {e}", flush=True)

print("=== ALL TESTS PASSED ===", flush=True)
print("Fashion scraper should work!", flush=True)
sys.exit(0)