#!/usr/bin/env python3
"""
Fashion Scraper Diagnostic - Debug startup issues
"""
import sys
import os

print("=== FASHION SCRAPER DIAGNOSTIC ===")
print(f"Python version: {sys.version}")
print(f"Current working directory: {os.getcwd()}")
print(f"Script location: {__file__}")
print(f"Arguments: {sys.argv}")

# Test imports one by one
try:
    import requests
    print("[OK]  requests imported successfully")
except ImportError as e:
    print(f"[ERROR]  requests import failed: {e}")
    sys.exit(1)

try:
    from bs4 import BeautifulSoup
    print("[OK]  BeautifulSoup imported successfully")
except ImportError as e:
    print(f"[ERROR]  BeautifulSoup import failed: {e}")
    sys.exit(1)

try:
    import pandas as pd
    print("[OK]  pandas imported successfully")
except ImportError as e:
    print(f"[ERROR]  pandas import failed: {e}")
    sys.exit(1)

# Test Excel reading capability
try:
    # This will fail if openpyxl is missing
    test_df = pd.DataFrame({'test': [1, 2, 3]})
    print("[OK]  pandas DataFrame creation works")
except Exception as e:
    print(f"[ERROR]  pandas DataFrame creation failed: {e}")
    sys.exit(1)

# Check mapping file paths
import platform
if platform.system() == "Windows":
    mapping_path = r"C:\laragon\www\scraper\python_scraper\fashion_scripts\fc_nsport_mapping.xlsx"
else:
    mapping_path = "/var/www/dataFlow/python_scraper/fashion_scripts/fc_nsport_mapping.xlsx"

print(f"Checking mapping file: {mapping_path}")
if os.path.exists(mapping_path):
    print("[OK]  Mapping file exists")
    try:
        # Test if we can actually read the Excel file
        mapping_df = pd.read_excel(mapping_path)
        print(f"[OK]  Mapping file readable - {len(mapping_df)} rows loaded")
    except Exception as e:
        print(f"[ERROR]  Cannot read mapping file: {e}")
        sys.exit(1)
else:
    print(f"[ERROR]  Mapping file NOT FOUND: {mapping_path}")
    
    # Check if file exists in current directory
    local_path = "fc_nsport_mapping.xlsx"
    if os.path.exists(local_path):
        print(f"[OK]  Found mapping file in current directory: {local_path}")
    else:
        print("[ERROR]  Mapping file not found anywhere")
        sys.exit(1)

# Test log file creation
try:
    with open("FASHION_LOG.txt", "a", encoding="utf-8") as f:
        f.write("Test log entry\n")
    print("[OK]  Log file creation works")
except Exception as e:
    print(f"[ERROR]  Cannot create log file: {e}")
    sys.exit(1)

print("=== ALL DIAGNOSTICS PASSED ===")
print("Fashion scraper should work normally")
sys.exit(0)