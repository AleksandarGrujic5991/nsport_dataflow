#!/usr/bin/env python3
# Auto-generated parallel fashion script
import sys
import os
import multiprocessing as mp
import pandas as pd
import time
from pathlib import Path

# Add fashion_scripts to path
script_dir = Path(__file__).parent
fashion_dir = script_dir / "fashion_scripts"
sys.path.append(str(fashion_dir))

try:
    from scraper_fashion_company import setup_driver_fixed, search_fixed, send_ultra_fast, create_store
except ImportError as e:
    print(f"[ERROR]  Cannot import Fashion modules: {e}")
    print(f"   Fashion dir: {fashion_dir}")
    print(f"   Exists: {fashion_dir.exists()}")
    sys.exit(1)

def worker_fashion(worker_id, fc_codes_chunk, results_queue, test_mode=False):
    """Worker proces za deo Fashion kodova"""
    print(f"🔄 Fashion Worker {worker_id} started with {len(fc_codes_chunk)} codes")
    
    driver = setup_driver_fixed(headless=True)
    
    products_batch = []
    processed = 0
    found = 0
    
    try:
        for fc_code, nsport_code in fc_codes_chunk.items():
            processed += 1
            print(f"W{worker_id}[{processed}] {fc_code[:10]}", end="->", flush=True)
            
            result = search_fixed(driver, fc_code)
            
            if result['found']:
                found += 1
                print(f"[OK] {result['price']}")
                
                products_batch.append({
                    'code': nsport_code,
                    'naziv': result['naziv'],
                    'price': result['price'],
                    'store_id': 7
                })
                
                # Manji batch za workers
                if len(products_batch) >= 5:
                    send_ultra_fast(products_batch)
                    products_batch = []
            else:
                print("[ERROR] ")
            
            # Test mode - samo prvih 10 po worker-u
            if test_mode and processed >= 10:
                print(f"W{worker_id} - Test mode limit reached")
                break
        
        # Posalji ostatak
        if products_batch:
            send_ultra_fast(products_batch)
            
    except Exception as e:
        print(f"[ERROR]  Worker {worker_id} error: {e}")
    finally:
        driver.quit()
        results_queue.put({
            'worker_id': worker_id,
            'processed': processed,
            'found': found
        })

def main():
    # Parse arguments
    num_workers = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    test_mode = '--test' in sys.argv
    
    mode_text = "TEST MODE" if test_mode else "PRODUCTION"
    print(f"🚀 PARALLEL FASHION SCRAPER - {num_workers} workers ({mode_text})")
    
    # Ucitaj Excel
    excel_file = Path("python_scraper") / "fashion_scripts" / "fc_nsport_mapping.xlsx"
    
    if not excel_file.exists():
        print(f"[ERROR]  Excel file not found: {excel_file}")
        # Fallback test data
        mapping = {
            'SDM1110439A-2DI': 'M1110439A-2DI',
            'SDM1011245A-G8R': 'M1011245A-G8R', 
            'SDM1012078A-01C': 'M1012078A-01C'
        }
    else:
        try:
            df = pd.read_excel(excel_file)
            mapping = {}
            for _, row in df.iterrows():
                fc_code = str(row['FC SIFRA']).strip()
                nsport_code = str(row['N SPORT SIFRA']).strip()
                mapping[fc_code] = nsport_code
        except Exception as e:
            print(f"[ERROR]  Error reading Excel: {e}")
            sys.exit(1)
    
    print(f" Total products: {len(mapping)}")
    
    # Test mode - ogranici na 40 proizvoda ukupno
    if test_mode:
        items = list(mapping.items())[:40]
        mapping = dict(items)
        print(f" Test mode: Limited to {len(mapping)} products")
    
    # Podeli u chunks
    items = list(mapping.items())
    chunk_size = len(items) // num_workers
    
    chunks = []
    for i in range(num_workers):
        start = i * chunk_size
        end = start + chunk_size if i < num_workers - 1 else len(items)
        chunk = dict(items[start:end])
        chunks.append(chunk)
        print(f"Worker {i+1}: {len(chunk)} products")
    
    # Kreiraj store
    create_store()
    
    # Pokreni workers
    results_queue = mp.Queue()
    processes = []
    
    start_time = time.time()
    
    for i, chunk in enumerate(chunks):
        p = mp.Process(target=worker_fashion, args=(i+1, chunk, results_queue, test_mode))
        p.start()
        processes.append(p)
    
    # Cekaj rezultate
    results = []
    for i in range(num_workers):
        result = results_queue.get()
        results.append(result)
        print(f"[OK]  Worker {result['worker_id']}: {result['processed']} processed | {result['found']} found")
    
    # Cekaj da se zavrse svi procesi
    for p in processes:
        p.join()
    
    elapsed = time.time() - start_time
    total_processed = sum(r['processed'] for r in results)
    total_found = sum(r['found'] for r in results)
    
    print(f"\n🎉 PARALLEL FASHION COMPLETED!")
    print(f"⏱️ Time: {elapsed/60:.1f} minutes")
    print(f" Processed: {total_processed} | Found: {total_found}")
    print(f" Speed: {total_processed/(elapsed/60):.0f} products/min")

if __name__ == "__main__":
    main()
