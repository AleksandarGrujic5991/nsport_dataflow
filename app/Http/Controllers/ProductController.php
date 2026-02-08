<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Models\Product;
use App\Models\Price;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Log;
use Maatwebsite\Excel\Facades\Excel;
use Illuminate\Support\FileSystem;
use Illuminate\Support\Facades\Storage;
use Maatwebsite\Excel\Concerns\FromArray;

class ProductController extends Controller
{
    public function index()
    {
        $products = Product::paginate(20);
        return view('admin.products.index', compact('products'));
    }

    public function show($id)
    {
        // Možeš vratiti view ili samo redirect
        return redirect()->route('admin.products.index');
    }

    public function listExports()
    {
        // Koristi direktno scandir umesto Storage da izbegnem cache probleme
        $exportPath = storage_path('app/exports/products');
        
        if (!is_dir($exportPath)) {
            $filesWithSessions = collect([]);
        } else {
            $files = collect(scandir($exportPath))
                ->filter(function($f) use ($exportPath) {
                    return $f !== '.' && $f !== '..' && 
                           is_file($exportPath . DIRECTORY_SEPARATOR . $f) &&
                           (str_ends_with($f, '.xlsx') || 
                            str_ends_with($f, '.csv') || 
                            str_ends_with($f, '.xls'));
                })
                ->map(function($f) use ($exportPath) {
                    return $exportPath . DIRECTORY_SEPARATOR . $f; // Vraći punu putanju
                })
                ->sortByDesc(function($f) {
                    return filemtime($f); // Sortiraj po vremenu modifikacije
                });

            // Mapiraj fajlove sa session podacima
            $filesWithSessions = $files->map(function($filePath) {
                $filename = basename($filePath);
                $session = $this->findSessionForFile($filename);
                
                return [
                    'path' => $filePath,
                    'filename' => $filename,
                    'session' => $session,
                    'file_time' => filemtime($filePath)
                ];
            });
        }

        return view('admin.products.exports', [
            'files' => $filesWithSessions,
        ]);
    }

    private function findSessionForFile($filename)
    {
        // Pokušaj da pronađeš session na osnovu filename pattern-a
        
        // Pattern 1: products_export_full_2025-11-02_15-26-12_69077814d5f8d_2m47s.xlsx
        if (preg_match('/products_export_[^_]+_(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})_([a-f0-9]+)_/', $filename, $matches)) {
            $datetime = $matches[1];
            $sessionId = $matches[2];
            
            // Pronađi session sa ovim session_key delom
            return \App\Models\ScrapingSession::where('session_key', 'like', '%' . $sessionId . '%')
                ->first();
        }
        
        // Pattern 2: products_export_buzz_2025-10-31_12-53-33.xlsx (bez session_key)
        if (preg_match('/products_export_[^_]+_(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})\.xlsx/', $filename, $matches)) {
            $datetime = $matches[1];
            
            // Pronađi session sa ovim start time-om
            try {
                $startTime = \Carbon\Carbon::createFromFormat('Y-m-d_H-i-s', $datetime);
                return \App\Models\ScrapingSession::where('started_at', $startTime)->first();
            } catch (\Exception $e) {
                return null;
            }
        }
        
        return null;
    }

    public function downloadExport($file)
    {
        $path = storage_path('app/exports/products/' . $file);
        Log::info('DOWNLOAD attempt:', [
            'file' => $file, 
            'path' => $path, 
            'exists' => file_exists($path), 
            'size' => file_exists($path) ? filesize($path) : 0
        ]);
        
        if (!file_exists($path)) {
            Log::error('File not found for download:', ['path' => $path]);
            abort(404, 'Fajl nije pronađen: ' . $file);
        }
        
        // Automatski detektuj content-type na osnovu ekstenzije
        $extension = pathinfo($file, PATHINFO_EXTENSION);
        
        switch(strtolower($extension)) {
            case 'csv':
                $contentType = 'text/csv';
                break;
            case 'xlsx':
                $contentType = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
                break;
            case 'xls':
                $contentType = 'application/vnd.ms-excel';
                break;
            default:
                $contentType = 'application/octet-stream';
        }
        
        Log::info('Download starting:', ['file' => $file, 'contentType' => $contentType]);
        
        return response()->download($path, null, [
            'Content-Type' => $contentType
        ]);
    }
    public function deleteExport($file)
    {
        $path = storage_path('app/exports/products/' . $file);
        if (file_exists($path)) {
            unlink($path);
            return back()->with('success', 'Fajl je obrisan.');
        }
        return back()->with('error', 'Fajl nije pronađen.');
    }

    public function exportStoreForm()
    {
        $stores = \App\Models\Store::all();
        return view('admin.products.export_store_form', compact('stores'));
    }

    public function exportExcelForStores(Request $request)
    {
        $storeIds = $request->input('stores', []); // očekuje array npr. [1,2,3]
        if (empty($storeIds)) {
            return response()->json(['error' => 'Niste izabrali nijednu prodavnicu.'], 400);
        }

        // Mapiranje store_id => naziv (sada uključuje i NSport prodavnice)
        $storeMap = [
            1 => 'Planeta',
            2 => 'Sportvision',
            3 => 'Djak',
            4 => 'Buzz',
            5 => 'Extra sport',
            6 => 'Fashion Company',
            7 => 'NSport',
            8 => 'NFashion',
            9 => 'Lacoste',
            10 => 'NSelection',
            11 => 'Intersport',
            12 => 'Trendmaker'
        ];

        // Kreiraj header - UVEK dodaj NSport Combined kao 4. kolonu
        $header = ['Sifra', 'Naziv', 'Brend', 'NSport ALL'];
        
        // Dodaj označene ne-NSport prodavnice (1-6)
        $nonNSportStores = array_filter($storeIds, function($id) {
            return $id >= 1 && $id <= 6;
        });
        
        foreach ($nonNSportStores as $storeId) {
            if (isset($storeMap[$storeId])) {
                $header[] = $storeMap[$storeId];
            }
        }
        
        // Dodaj označene NSport prodavnice zasebno (7-12)
        $nsportStores = array_filter($storeIds, function($id) {
            return $id >= 7 && $id <= 12;
        });
        
        foreach ($nsportStores as $storeId) {
            if (isset($storeMap[$storeId])) {
                $header[] = $storeMap[$storeId];
            }
        }

        // Učitaj sve proizvode (šifra, naziv, brend)
        $products = DB::table('products')->select('code', 'naziv', 'brand')->get();
        $codes = $products->pluck('code')->toArray();

        // Učitaj cene za izabrane prodavnice + sve NSport prodavnice (za Combined kolonu)
        $allStoreIds = array_unique(array_merge($storeIds, [7, 8, 9, 10, 11, 12])); // Dodaj NSport IDs
        $allPrices = DB::table('prices')
            ->join('products', 'prices.product_id', '=', 'products.id')
            ->whereIn('products.code', $codes)
            ->whereIn('prices.store_id', $allStoreIds)
            ->select('products.code', 'prices.store_id', 'prices.price')
            ->get();

        // Mapiraj cene po šifri i prodavnici
        $priceMap = [];
        foreach ($allPrices as $row) {
            $priceMap[$row->code][$row->store_id] = $row->price;
        }

        // Debug: Log header informacije
        Log::info('Export Header Debug:', [
            'selected_stores' => $storeIds,
            'header' => $header,
            'non_nsport_stores' => $nonNSportStores,
            'nsport_stores' => $nsportStores
        ]);

        // Pripremi redove za export
        $rows = [];
        $rows[] = $header;
        foreach ($products as $prod) {
            $row = [
                $prod->code,
                $prod->naziv,
                $prod->brand,
            ];
            
            // NSport Combined kolona - uzmi prvu dostupnu cenu iz prodavnica 7-12
            $nsportCombinedPrice = '';
            for ($nsportId = 7; $nsportId <= 12; $nsportId++) {
                if (!empty($priceMap[$prod->code][$nsportId])) {
                    $nsportCombinedPrice = $priceMap[$prod->code][$nsportId];
                    break; // Uzmi prvu pronađenu cenu
                }
            }
            $row[] = $nsportCombinedPrice;
            
            // Dodaj označene ne-NSport prodavnice
            foreach ($nonNSportStores as $storeId) {
                $row[] = $priceMap[$prod->code][$storeId] ?? '';
            }
            
            // Dodaj označene NSport prodavnice zasebno
            foreach ($nsportStores as $storeId) {
                $row[] = $priceMap[$prod->code][$storeId] ?? '';
            }
            
            $rows[] = $row;
        }

        // Uzmi poslednju completed scraping sesiju iz baze
        $latestSession = \App\Models\ScrapingSession::where('status', 'completed')
            ->orderBy('ended_at', 'desc')
            ->first();
            
        if ($latestSession) {
            // Kreiraj timestamp sa session_key + trajanjem
            $duration = $latestSession->duration; // koristi getDurationAttribute
            $timestamp = $latestSession->session_key . '_duration_' . $duration;
        } else {
            // Fallback na obični timestamp
            $timestamp = now()->format('Y-m-d_H-i-s');
        }
        
        // Kreiraj pametno ime fajla na osnovu prodavnica
        $storeNames = [];
        $storeNameMap = [
            1 => 'planeta',
            2 => 'sportvision', 
            3 => 'djak',
            4 => 'buzz',
            5 => 'extrasport',
            6 => 'fashion',
            7 => 'nsport',
            8 => 'nfashion',
            9 => 'lacoste',
            10 => 'nselection',
            11 => 'intersport',
            12 => 'trendmaker'
        ];
        
        // Debug log da vidimo koje prodavnice su poslate
        Log::info('Export stores selected:', ['storeIds' => $storeIds, 'storeNameMap' => $storeNameMap]);
        
        foreach ($storeIds as $storeId) {
            if (isset($storeNameMap[$storeId])) {
                $storeNames[] = $storeNameMap[$storeId];
            } else {
                // Debug: ako prodavnica nije u mapi, dodaj ID
                $storeNames[] = "store{$storeId}";
            }
        }
        
        // Ako su sve prodavnice (12 ukupno), nazovi "full"
        if (count($storeNames) >= 10) { // Ako je označeno 10+ prodavnica, nazovi "full"
            $storeSuffix = 'full';
        } elseif (count($storeNames) == 1) {
            $storeSuffix = $storeNames[0];
        } else {
            $storeSuffix = implode('_', $storeNames);
        }
        
        $filename = "{$storeSuffix}_{$timestamp}.xlsx";
        $path = "exports/products/{$filename}";
        
        // Debug log da vidimo rezultujuće ime fajla
        Log::info('Export filename created:', [
            'storeNames' => $storeNames, 
            'storeSuffix' => $storeSuffix, 
            'filename' => $filename
        ]);

        Excel::store(
            new class($rows) implements FromArray {
                private $rows;
                public function __construct($rows) { $this->rows = $rows; }
                public function array(): array { return $this->rows; }
            },
            $path,
            'local' // OVO JE KLJUČNO!
        );

        return response()->json(['success' => true, 'file' => $filename]);
    }

    public function exportTypeForm()
    {
        $storeMap = [
            1 => 'Planeta',
            2 => 'Sportvision',
            3 => 'Djak',
            4 => 'Buzz',
            5 => 'Extra sport',
            6 => 'Fashion Company',
            7 => 'NSport',
            8 => 'NFashion',
            9 => 'Lacoste',
            10 => 'NSelection',
            11 => 'Intersport',
            12 => 'Trendmaker'
        ];

        // Pretvori u array objekata radi lakšeg prikaza u blade-u
        $stores = [];
        foreach ($storeMap as $id => $naziv) {
            $stores[] = (object)['id' => $id, 'naziv' => $naziv];
        }

        return view('admin.products.export_type_form', compact('stores'));
    }

    public function scraperTypeForm()
    {
        // Read all stores from database instead of hardcoded values
        $stores = DB::select('SELECT id, name as naziv FROM stores ORDER BY id');
        
        // Convert stdClass objects to proper objects
        $stores = collect($stores)->map(function($store) {
            return (object) [
                'id' => $store->id,
                'naziv' => $store->naziv
            ];
        });
        
        return view('admin.products.scraper_type_form', compact('stores'));
    }

    public function runScraper(Request $request)
    {
        if (strtoupper(substr(PHP_OS, 0, 3)) === 'WIN') {
            $venvPython = base_path('venv/Scripts/python.exe');
            $script = base_path('python_scraper/run_ultra_scraper.py');
            $standaloneScript = base_path('python_scraper/run_planeta_pages_standalone.py');
        } else {
            $venvPython = '/var/www/dataFlow/venv/bin/python';
            $script = base_path('python_scraper/run_ultra_scraper.py');
            $standaloneScript = base_path('python_scraper/run_planeta_pages_standalone.py');
        }

        if ($request->has('all_stores')) {
            $cmd = "{$venvPython} {$script} --ultra-parallel 2>&1";
                // Executing scraper for all stores            // Pokreni u pozadini - Linux verzija
            if (strtoupper(substr(PHP_OS, 0, 3)) === 'WIN') {
                // Windows - pokreni u pozadini sa popen (ne čeka)
                $envCmd = "start /MIN cmd /C \"set PYTHONIOENCODING=utf-8 && cd /d \"" . base_path() . "\" && {$cmd} > scraper_output_all.log 2>&1\"";
                pclose(popen($envCmd, "r"));
                // Windows process started in background
            } else {
                // Set proper environment for web server execution
                $envCmd = "cd /var/www/dataFlow && export DISPLAY=:99 && export PATH=/var/www/dataFlow/venv/bin:\$PATH && {$cmd} 2>&1 | tee scraper_output2.log &";
                exec($envCmd, $output, $returnCode);
                Log::info('Linux execution result:', ['output' => $output, 'return_code' => $returnCode]);
            }
        } else {
            $storeKeys = $request->input('stores', []);
            if (empty($storeKeys)) {
                return back()->with('error', 'Niste izabrali nijednu prodavnicu.');
            }
            
            // Proveri da li su izabrane Planeta ili Djak (Selenium scrapers koji trebaju environment fix)
            $isPlanetaSelected = in_array('1', $storeKeys); // '1' je ID za Planeta
            $isDjakSelected = in_array('3', $storeKeys); // '3' je ID za Djak
            $needsEnvironmentFix = $isPlanetaSelected || $isDjakSelected;
            
            if ($needsEnvironmentFix) {
                // Za Selenium scrapers (Planeta/Djak) dodaj environment fix
                $storesArg = implode(',', $storeKeys);
                $cmd = "{$venvPython} {$script} --ultra-parallel --stores {$storesArg}";
                if ($isPlanetaSelected) {
                    $cmd .= " --with-pages";
                }
                $cmd .= " 2>&1";
                // Executing Selenium scrapers
                
                // Pokreni u pozadini - Linux verzija
                if (strtoupper(substr(PHP_OS, 0, 3)) === 'WIN') {
                    // Windows - pokreni u pozadini sa popen (ne čeka)
                    $envCmd = "start /MIN cmd /C \"set PYTHONIOENCODING=utf-8 && cd /d \"" . base_path() . "\" && {$cmd} > scraper_output_planeta.log 2>&1\"";
                    pclose(popen($envCmd, "r"));
                    // Windows Planeta process started
                } else {
                    // Prvo testiraj da li Python uopšte radi
                    exec("{$venvPython} --version 2>&1", $pythonOutput, $pythonReturn);
                    // Python version checked
                    
                    // Set proper environment for web server execution
                    $envCmd = "cd /var/www/dataFlow && export DISPLAY=:99 && export PATH=/var/www/dataFlow/venv/bin:\$PATH && {$cmd} 2>&1 | tee scraper_output.log &";
                    exec($envCmd, $output, $returnCode);
                    Log::info('Linux execution result:', ['output' => $output, 'return_code' => $returnCode]);
                }
            } else {
                // Za ostale prodavnice kao obično
                $storesArg = implode(',', $storeKeys);
                $cmd = "{$venvPython} {$script} --ultra-parallel --stores {$storesArg} 2>&1";
                Log::info('Executing command for other stores:', [
                    'cmd' => $cmd,
                    'storeKeys' => $storeKeys,
                    'storesArg' => $storesArg
                ]);
                
                // Pokreni u pozadini - Linux verzija
                if (strtoupper(substr(PHP_OS, 0, 3)) === 'WIN') {
                    // Windows - pokreni u pozadini sa popen (ne čeka)
                    $envCmd = "start /MIN cmd /C \"set PYTHONIOENCODING=utf-8 && cd /d \"" . base_path() . "\" && {$cmd} > scraper_output.log 2>&1\"";
                    pclose(popen($envCmd, "r"));
                    Log::info('Windows other stores execution result:', ['status' => 'Process started in background', 'cmd' => $envCmd]);
                } else {
                    // Normal execution for other stores (BS4 scrapers don't need special environment)
                    exec("cd /var/www/dataFlow && {$cmd} 2>&1 | tee scraper_output3.log &", $output, $returnCode);
                    Log::info('Linux other stores execution result:', ['output' => $output, 'return_code' => $returnCode]);
                }
            }
        }

        // Prikaz logova iz fajla
        $logFile = base_path('SCRAPER_LOG.txt');
        $logs = [];
        if (file_exists($logFile)) {
            $logs = explode("\n", file_get_contents($logFile));
        }

        // Read all stores from database (same as scraperTypeForm)
        $stores = DB::select('SELECT id, name as naziv FROM stores ORDER BY id');
        
        // Convert stdClass objects to proper objects
        $stores = collect($stores)->map(function($store) {
            return (object) [
                'id' => $store->id,
                'naziv' => $store->naziv
            ];
        });

        return view('admin.products.scraper_type_form', compact('stores', 'logs'))
            ->with('success', 'Scraping je pokrenut!');
    }

    public function exportExcelFromPython(Request $request)
    {
        $start = now();
        $storeMap = [
            1 => 'Planeta',
            2 => 'Sportvision',
            3 => 'Djak',
            4 => 'Buzz',
            5 => 'Extra sport',
            6 => 'Fashion Company',
            7 => 'NSport',
            8 => 'NFashion',
            9 => 'Lacoste',
            10 => 'NSelection',
            11 => 'Intersport',
            12 => 'Trendmaker'
        ];

        // Kreiraj header sa NSport Combined na početku
        $header = ['Sifra', 'Naziv', 'Brend', 'NSport ALL'];
        
        // Dodaj ostale prodavnice (1-6)
        for ($i = 1; $i <= 6; $i++) {
            if (isset($storeMap[$i])) {
                $header[] = $storeMap[$i];
            }
        }
        
        // Dodaj NSport prodavnice zasebno (7-12)
        for ($i = 7; $i <= 12; $i++) {
            if (isset($storeMap[$i])) {
                $header[] = $storeMap[$i];
            }
        }

        $allProducts = DB::table('products')->select('code', 'naziv', 'brand')->get();
        $allCodes = $allProducts->pluck('code')->toArray();

        $allPrices = DB::table('prices')
            ->join('products', 'prices.product_id', '=', 'products.id')
            ->whereIn('products.code', $allCodes)
            ->select('products.code', 'prices.store_id', 'prices.price')
            ->get();

        $priceMap = [];
        foreach ($allPrices as $row) {
            $priceMap[$row->code][$row->store_id] = $row->price;
        }

        $rows = [];
        $rows[] = $header;
        foreach ($allProducts as $prod) {
            $row = [
                $prod->code,
                $prod->naziv,
                $prod->brand,
            ];
            
            // NSport Combined kolona - uzmi prvu dostupnu cenu iz prodavnica 7-12
            $nsportCombinedPrice = '';
            for ($nsportId = 7; $nsportId <= 12; $nsportId++) {
                if (!empty($priceMap[$prod->code][$nsportId])) {
                    $nsportCombinedPrice = number_format((float)$priceMap[$prod->code][$nsportId], 2, '.', '');
                    break; // Uzmi prvu pronađenu cenu
                }
            }
            $row[] = $nsportCombinedPrice;
            
            // Dodaj ostale prodavnice (1-6)
            for ($i = 1; $i <= 6; $i++) {
                if (isset($storeMap[$i])) {
                    $price = $priceMap[$prod->code][$i] ?? '';
                    $row[] = $price !== '' ? number_format((float)$price, 2, '.', '') : '';
                }
            }
            
            // Dodaj NSport prodavnice zasebno (7-12)
            for ($i = 7; $i <= 12; $i++) {
                if (isset($storeMap[$i])) {
                    $price = $priceMap[$prod->code][$i] ?? '';
                    $row[] = $price !== '' ? number_format((float)$price, 2, '.', '') : '';
                }
            }
            
            $rows[] = $row;
        }

        // Uzmi poslednju completed scraping sesiju iz baze
        $latestSession = \App\Models\ScrapingSession::where('status', 'completed')
            ->orderBy('ended_at', 'desc')
            ->first();
            
        if ($latestSession) {
            // Kreiraj filename sa session_key + trajanjem
            $duration = $latestSession->duration; // koristi getDurationAttribute
            $filename = "products_export_full_{$latestSession->session_key}_duration_{$duration}.xlsx";
        } else {
            // Fallback na obični timestamp
            $timestamp = now()->format('Y-m-d_H-i-s');
            $filename = "products_export_full_{$timestamp}.xlsx";
        }
        $path = "exports/products/{$filename}";

        // Pravi pravi Excel fajl!
        Excel::store(
            new class($rows) implements FromArray {
                private $rows;
                public function __construct($rows) { $this->rows = $rows; }
                public function array(): array { return $this->rows; }
            },
            $path,
            'local' // OVO JE KLJUČNO!
        );

        $end = now();
        Log::info("Export start: $start, end: $end, file: $filename");

        return response()->json(['success' => true, 'file' => $filename, 'start' => $start, 'end' => $end]);
    }

    public function showFashionMappingForm()
    {
        $currentMappingPath = base_path('python_scraper/fc_nsport_mapping.xlsx');
        $currentMappingExists = file_exists($currentMappingPath);
        $currentMappingTime = $currentMappingExists ? filemtime($currentMappingPath) : null;
        
        return view('admin.products.fashion-mapping', compact('currentMappingExists', 'currentMappingTime'));
    }

    public function uploadFashionMapping(Request $request)
    {
        $request->validate([
            'mapping_file' => 'required|file|mimes:xlsx,xls|max:10240', // 10MB max
        ]);

        try {
            $file = $request->file('mapping_file');
            $destinationPath = base_path('python_scraper/fc_nsport_mapping.xlsx');
            
            // Backup postojećeg fajla
            if (file_exists($destinationPath)) {
                $backupPath = base_path('python_scraper/fc_nsport_mapping_backup_' . date('Y-m-d_H-i-s') . '.xlsx');
                copy($destinationPath, $backupPath);
            }
            
            // Premesti novi fajl
            $file->move(base_path('python_scraper'), 'fc_nsport_mapping.xlsx');
            
            // Testuj da li se fajl može učitati
            try {
                // Jednostavan test - pokušaj da učitaš fajl kao array
                $data = \Maatwebsite\Excel\Facades\Excel::toArray([], $destinationPath);
                
                if (empty($data) || empty($data[0])) {
                    throw new \Exception('Fajl je prazan ili nema podatke');
                }
                
                // Uzmi prvi red kao header
                $firstRow = $data[0][0] ?? [];
                if (empty($firstRow)) {
                    throw new \Exception('Fajl nema header red');
                }
                
                // Konvertuj vrednosti u stringove i proverim kolumne
                $headers = array_values($firstRow);
                $hasFC = false;
                $hasNSPORT = false;
                
                foreach ($headers as $header) {
                    $header = trim(strval($header));
                    if (strpos($header, 'FC') !== false && strpos($header, 'ŠIFRA') !== false) {
                        $hasFC = true;
                    }
                    if (strpos($header, 'N SPORT') !== false && strpos($header, 'ŠIFRA') !== false) {
                        $hasNSPORT = true;
                    }
                }
                
                if (!$hasFC || !$hasNSPORT) {
                    throw new \Exception('Fajl mora imati kolumne "FC ŠIFRA" i "N SPORT ŠIFRA". Pronađene kolumne: ' . implode(', ', $headers));
                }
                
                $rowCount = count($data[0]) - 1; // -1 za header
                
                return redirect()->back()->with('success', 
                    "Fashion mapping uspešno uploadovan! Učitano $rowCount mapiranja."
                );
                
            } catch (\Exception $e) {
                // Vrati backup ako je testiranje neuspešno
                if (isset($backupPath) && file_exists($backupPath)) {
                    copy($backupPath, $destinationPath);
                    unlink($backupPath);
                }
                throw new \Exception('Greška pri testiranju fajla: ' . $e->getMessage());
            }
            
        } catch (\Exception $e) {
            return redirect()->back()->withErrors(['mapping_file' => $e->getMessage()]);
        }
    }

    public function exportProductsTable(Request $request)
    {
        // Export samo products tabelu bez cena
        $products = DB::table('products')->select('id', 'code', 'naziv', 'brand', 'created_at', 'updated_at')->get();
        
        $rows = [];
        $rows[] = ['ID', 'Šifra', 'Naziv', 'Brend', 'Kreiran', 'Ažuriran']; // Header
        
        foreach ($products as $product) {
            $rows[] = [
                $product->id,
                $product->code,
                $product->naziv,
                $product->brand,
                $product->created_at,
                $product->updated_at
            ];
        }
        
        $timestamp = now()->format('Y-m-d_H-i-s');
        $filename = "products_table_export_{$timestamp}.xlsx";
        $path = "exports/products/{$filename}";

        Excel::store(
            new class($rows) implements FromArray {
                private $rows;
                public function __construct($rows) { $this->rows = $rows; }
                public function array(): array { return $this->rows; }
            },
            $path,
            'local'
        );

        return response()->download(storage_path("app/{$path}"));
    }
}
