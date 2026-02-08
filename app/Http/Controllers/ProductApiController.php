<?php
namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Models\Product;
use App\Models\Price;
use App\Models\ScrapingSession;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Log;
use Maatwebsite\Excel\Facades\Excel;
use Maatwebsite\Excel\Concerns\FromArray;
use Illuminate\Support\Facades\Storage;
use App\Exports\ProductsExport;

class ProductApiController extends Controller
{
    public function storeBatch(Request $request)
    {
        // Debug output
        error_log('=== API BATCH DEBUG START ===');
        Log::info('=== DJAK BATCH START ===');
        Log::info('Raw request data:', $request->all());
        
        // Test database connection
        try {
            $testConnection = DB::connection()->getPdo();
            Log::info('Database connection: OK');
            error_log('Database connection: OK');
        } catch (\Exception $e) {
            Log::error('Database connection failed: ' . $e->getMessage());
            error_log('Database connection failed: ' . $e->getMessage());
        }
        
        $items = $request->all();
        $results = [];
        
        foreach ($items as $index => $item) {
            try {
                Log::info("Processing item {$index}:", $item);
                
                $validated = validator($item, [
                    'code' => 'required|string',
                    'naziv' => 'required|string',
                    'price' => 'required|numeric',
                    'store_id' => 'required|integer|exists:stores,id',
                    'price_regular' => 'nullable|numeric',
                    'price_discount' => 'nullable|numeric',
                    'price_old' => 'nullable|numeric',
                    'brand' => 'nullable|string',
                ])->validate();

                Log::info("Validation passed for item {$index}:", $validated);

                $product = Product::firstOrCreate([
                    'code' => $validated['code'],
                ], [
                    'naziv' => $validated['naziv'],
                    'brand' => $validated['brand'] ?? null,
                ]);

                // Ako se brend promenio, ažuriraj ga
                if ($product->brand !== ($validated['brand'] ?? null)) {
                    $product->brand = $validated['brand'] ?? null;
                    $product->save();
                }

                Log::info("Product created/found:", [
                    'id' => $product->id,
                    'code' => $product->code,
                    'created' => $product->wasRecentlyCreated
                ]);

                // Provera da li već postoji cena za ovaj proizvod i prodavnicu
                $existingPrice = Price::where('product_id', $product->id)
                    ->where('store_id', $validated['store_id'])
                    ->first();

                if ($existingPrice) {
                    Log::info("Duplikat price za product_id={$product->id}, store_id={$validated['store_id']} - preskacem upis.");
                    $results[] = [
                        'success' => false,
                        'error' => 'Duplikat price',
                        'product' => $product,
                        'item' => $item,
                    ];
                    continue; // preskoči duplikat
                }

                $price = Price::create([
                    'product_id' => $product->id,
                    'store_id' => $validated['store_id'],
                    'price' => $validated['price'],
                    'price_regular' => $validated['price_regular'] ?? null,
                    'price_discount' => $validated['price_discount'] ?? null,
                    'price_old' => $validated['price_old'] ?? null,
                    'scraped_at' => now(),
                ]);

                Log::info("Price created:", [
                    'price_id' => $price->id,
                    'product_id' => $price->product_id,
                    'store_id' => $price->store_id,
                    'price' => $price->price
                ]);

                $results[] = [
                    'success' => true,
                    'product' => $product,
                    'price' => $price,
                ];
                
            } catch (\Exception $e) {
                Log::error("Error processing item {$index}:", [
                    'item' => $item,
                    'error' => $e->getMessage(),
                    'trace' => $e->getTraceAsString()
                ]);
                
                $results[] = [
                    'success' => false,
                    'error' => $e->getMessage(),
                    'item' => $item,
                ];
            }
        }
        
        Log::info('=== DJAK BATCH END ===', [
            'total_items' => count($items),
            'results_count' => count($results)
        ]);
        
        return response()->json($results);
    }

    public function store(Request $request)
    {
        $validated = $request->validate([
            'code' => 'required|string',
            'naziv' => 'required|string',
            'price' => 'required|numeric',
            'store_id' => 'required|integer|exists:stores,id',
            'price_regular' => 'nullable|numeric',
            'price_discount' => 'nullable|numeric',
            'price_old' => 'nullable|numeric',
            'brand' => 'nullable|string',
        ]);

        // Pronađi ili kreiraj artikal
        $product = Product::firstOrCreate([
            'code' => $validated['code'],
        ], [
            'naziv' => $validated['naziv'],
            'brand' => $validated['brand'] ?? null,
        ]);

        // Ako se brend promenio, ažuriraj ga
        if ($product->brand !== ($validated['brand'] ?? null)) {
            $product->brand = $validated['brand'] ?? null;
            $product->save();
        }

        // Upisi cenu
        $price = Price::create([
            'product_id' => $product->id,
            'store_id' => $validated['store_id'],
            'price' => $validated['price'],
            'price_regular' => $validated['price_regular'] ?? null,
            'price_discount' => $validated['price_discount'] ?? null,
            'price_old' => $validated['price_old'] ?? null,
            'scraped_at' => now(),
        ]);

        return response()->json([
            'success' => true,
            'product' => $product,
            'price' => $price,
        ]);
    }

    private function generateSmartFilename($stores, $timestamp)
    {
        $storeIdToNameMap = [
            '1' => 'planeta',
            '2' => 'sportvision', 
            '3' => 'djak',
            '4' => 'buzz',
            '5' => 'extrasport',
            '6' => 'fashion',
            '7' => 'nsport',
            '8' => 'nfashion',
            '9' => 'lacoste',
            '10' => 'nselection',
            '11' => 'intersport',
            '12' => 'trendmaker'
        ];

        if ($stores === 'full') {
            return "products_export_full_{$timestamp}.xlsx";
        }

        // Ako su prosledi store ID-jevi ili nazivi
        if (is_string($stores)) {
            $storeList = explode(',', $stores);
        } else {
            $storeList = $stores;
        }

        $storeNames = [];
        foreach ($storeList as $store) {
            $store = trim($store);
            if (isset($storeIdToNameMap[$store])) {
                $storeNames[] = $storeIdToNameMap[$store];
            } elseif (in_array($store, $storeIdToNameMap)) {
                $storeNames[] = $store;
            }
        }

        if (empty($storeNames)) {
            return "products_export_unknown_{$timestamp}.xlsx";
        }

        // Ako su sve prodavnice (12 ukupno), nazovi "full"
        if (count($storeNames) >= 10) { // 10+ prodavnica = full
            return "products_export_full_{$timestamp}.xlsx";
        }

        if (count($storeNames) === 1) {
            return "products_export_{$storeNames[0]}_{$timestamp}.xlsx";
        }

        return "products_export_" . implode('_', $storeNames) . "_{$timestamp}.xlsx";
    }

    public function exportExcelFromPython(Request $request)
    {
        // Povećaj memory limit i execution time za velike export-ove
        ini_set('memory_limit', '512M');
        set_time_limit(180);
        
        // Uzmi poslednju completed scraping sesiju iz baze
        $latestSession = \App\Models\ScrapingSession::where('status', 'completed')
            ->orderBy('ended_at', 'desc')
            ->first();
            
        if ($latestSession) {
            // Kreiraj timestamp sa session_key + trajanjem (kraći format)
            $duration = str_replace(' ', '', $latestSession->duration); // ukloni spaces iz "2m 47s"
            $timestamp = $latestSession->session_key . '_' . $duration;
        } else {
            // Fallback na obični timestamp
            $timestamp = now()->format('Y-m-d_H-i-s');
        }
        
        // Generiši pametno ime fajla na osnovu stores parametra
        $stores = $request->query('stores', 'full');
        Log::info('Export filename debug:', [
            'stores_param' => $stores,
            'stores_type' => gettype($stores)
        ]);
        $filename = $this->generateSmartFilename($stores, $timestamp);
        
        try {
            // Kreiraj direktorijum ako ne postoji
            $dir = storage_path('app/exports/products');
            if (!is_dir($dir)) {
                mkdir($dir, 0755, true);
            }
            
            $exportPath = 'exports/products/' . $filename;
            $fullPath = storage_path('app/' . $exportPath);
            
            // Generiši XLSX fajl u memoriji i sačuvaj
            $export = new ProductsExport();
            $excelContent = Excel::raw($export, \Maatwebsite\Excel\Excel::XLSX);
            
            // Sačuvaj fajl na disk
            file_put_contents($fullPath, $excelContent);
            
            if (!file_exists($fullPath)) {
                Log::error('Export: XLSX fajl nije kreiran', [
                    'expected_path' => $fullPath,
                    'directory_exists' => is_dir(dirname($fullPath))
                ]);
                return response()->json(['success' => false, 'error' => 'File creation failed'], 500);
            }
            
            $fileSize = filesize($fullPath);
            $processedCount = Product::count();
            
            Log::info('Export: XLSX fajl kreiran', [
                'filename' => $filename, 
                'path' => $fullPath,
                'file_exists' => true,
                'file_size' => $fileSize,
                'processed_count' => $processedCount
            ]);
            
            return response()->json([
                'success' => true, 
                'file' => $filename,
                'path' => $fullPath,
                'relative_path' => $exportPath,
                'processed_count' => $processedCount,
                'file_size' => $fileSize,
                'download_url' => "/api/products/download-export/{$filename}"
            ]);
            
        } catch (\Exception $e) {
            Log::error('Export: Excel creation failed', [
                'error' => $e->getMessage(),
                'trace' => $e->getTraceAsString(),
                'line' => $e->getLine(),
                'file' => $e->getFile()
            ]);
            return response()->json(['success' => false, 'error' => $e->getMessage()], 500);
        }
    }

    public function clearDatabase()
    {
        DB::statement('SET FOREIGN_KEY_CHECKS=0;');
        DB::table('prices')->truncate();
        DB::table('products')->truncate();
        DB::statement('SET FOREIGN_KEY_CHECKS=1;');
        
        // Kreiraj novu scraping sesiju
        $sessionKey = now()->format('Y-m-d_H-i-s') . '_' . uniqid();
        $session = \App\Models\ScrapingSession::create([
            'session_key' => $sessionKey,
            'stores' => request('stores', 'unknown'), // iz request parametra
            'started_at' => now(),
            'status' => 'running'
        ]);
        
        return response()->json([
            'success' => true, 
            'message' => 'Baza očišćena!',
            'session_key' => $sessionKey
        ]);
    }

    public function endSession(Request $request)
    {
        $sessionKey = $request->session_key;
        $session = ScrapingSession::where('session_key', $sessionKey)
            ->where('status', 'running')
            ->first();
            
        if ($session) {
            $productsCount = Product::count();
            $session->update([
                'ended_at' => now(),
                'products_count' => $productsCount,
                'status' => 'completed'
            ]);
            
            // Kreiraj finalni session ključ sa trajanjem
            $finalSessionKey = $sessionKey . '_duration_' . $session->fresh()->duration;
            
            return response()->json([
                'success' => true,
                'message' => 'Sesija završena!',
                'duration' => $session->fresh()->duration,
                'products_count' => $productsCount,
                'final_session_key' => $finalSessionKey
            ]);
        }
        
        return response()->json(['success' => false, 'message' => 'Sesija nije pronađena'], 404);
    }

    public function getCount()
    {
        $productCount = Product::count();
        $priceCount = Price::count();
        return response()->json([
            'products' => $productCount,
            'prices' => $priceCount,
            'total' => $productCount + $priceCount
        ]);
    }

    public function downloadExport($filename)
    {
        $path = storage_path('app/exports/products/' . $filename);
        if (!file_exists($path)) {
            return response()->json(['error' => 'File not found'], 404);
        }
        return response()->download($path);
    }

    public function testExport()
    {
        // Test bez Excel-a - samo kreiranje običnog fajla
        $timestamp = now()->format('Y-m-d_H-i-s');
        $filename = "test_export_{$timestamp}.txt";
        $path = storage_path('app/exports/products/' . $filename);
        
        $content = "Test export file created at: " . now() . "\n";
        $content .= "Products count: " . Product::count() . "\n";
        
        $written = file_put_contents($path, $content);
        
        return response()->json([
            'success' => $written !== false,
            'file' => $filename,
            'bytes_written' => $written,
            'path' => $path,
            'file_exists' => file_exists($path)
        ]);
    }

    public function exportSmall()
    {
        // Export samo prvih 10 proizvoda za test
        $products = Product::with('prices')->limit(10)->get();
        
        $timestamp = now()->format('Y-m-d_H-i-s');
        $filename = "small_export_{$timestamp}.csv";
        $fullPath = storage_path('app/exports/products/' . $filename);
        
        // Kreiraj direktorijum ako ne postoji
        $dir = dirname($fullPath);
        if (!is_dir($dir)) {
            mkdir($dir, 0755, true);
        }
        
        $handle = fopen($fullPath, 'w');
        if (!$handle) {
            return response()->json(['success' => false, 'error' => 'Cannot create file'], 500);
        }
        
        // Header
        fputcsv($handle, ['Šifra', 'Naziv', 'Brend', 'Cena'], ';');
        
        // Data
        foreach ($products as $product) {
            $price = $product->prices->first();
            fputcsv($handle, [
                $product->sifra,
                $product->naziv,
                $product->brand,
                $price ? $price->price : 'N/A'
            ], ';');
        }
        
        fclose($handle);
        
        return response()->json([
            'success' => true,
            'file' => $filename,
            'products_count' => $products->count(),
            'file_exists' => file_exists($fullPath),
            'file_size' => file_exists($fullPath) ? filesize($fullPath) : 0
        ]);
    }
}

