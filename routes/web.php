<?php

use App\Http\Controllers\ProfileController;
use App\Http\Controllers\DashboardController;
use App\Http\Controllers\ProductController;
use App\Http\Controllers\ProductApiController;
use App\Http\Controllers\StoreController;
use Illuminate\Support\Facades\Route;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Facades\Auth;

Route::get('/', function () {
    return view('welcome');
});

Route::middleware('auth')->group(function () {
    Route::get('/profile', [ProfileController::class, 'edit'])->name('profile.edit');
    Route::patch('/profile', [ProfileController::class, 'update'])->name('profile.update');
    Route::delete('/profile', [ProfileController::class, 'destroy'])->name('profile.destroy');
});


Route::prefix('admin')->middleware('auth')->group(function () {
    Route::get('dashboard', [DashboardController::class, 'index'])->name('admin.dashboard');
    Route::resource('products', ProductController::class)->except(['show']);
    Route::resource('stores', StoreController::class);
    Route::get('products/export', [ProductController::class, 'exportExcelDirect'])->name('admin.products.export');
    Route::post('products/import', [ProductController::class, 'import'])->name('admin.products.import');
    Route::post('scraper/run', [ProductController::class, 'runScraper'])->name('admin.scraper.run');
    Route::get('products/exports', [ProductController::class, 'listExports'])->name('admin.products.exports');
    Route::get('products/export-direct', [ProductController::class, 'exportExcelDirect'])->name('admin.products.exportDirect');
    Route::get('products/exports/download/{file}', [ProductController::class, 'downloadExport'])->name('admin.products.downloadExport');
    Route::get('export-products-excel', [ProductController::class, 'exportExcelFromPython'])->name('admin.products.exportFromPython');
    Route::delete('products/exports/delete/{file}', [ProductController::class, 'deleteExport'])->name('admin.products.deleteExport');
    Route::get('products/export-store-form', [ProductController::class, 'exportStoreForm'])->name('admin.products.exportStoreForm');
    Route::post('products/export-store', [ProductController::class, 'exportExcelForStores'])->name('admin.products.exportStore');
    Route::get('products/export-type', [ProductController::class, 'exportTypeForm'])->name('admin.products.exportTypeForm');
    Route::post('products/export-full', [ProductController::class, 'runFullExport'])->name('admin.products.runFullExport');
    Route::get('scraper/type', [ProductController::class, 'scraperTypeForm'])->name('admin.scraper.typeForm');
    
    // Fashion Mapping Routes
    Route::get('products/fashion-mapping', [ProductController::class, 'showFashionMappingForm'])->name('admin.products.fashionMapping');
    Route::post('products/fashion-mapping/upload', [ProductController::class, 'uploadFashionMapping'])->name('admin.products.uploadFashionMapping');
    
    // Export Products Table Route
    Route::get('products/export-table', [ProductController::class, 'exportProductsTable'])->name('admin.products.exportTable');
    
    // Fashion mapping routes - komentarisano jer koristimo ProductController
    // Route::prefix('fashion')->group(function () {
    //     Route::get('mapping', [\App\Http\Controllers\Admin\FashionMappingController::class, 'index'])->name('admin.fashion.mapping');
    //     Route::post('mapping/upload', [\App\Http\Controllers\Admin\FashionMappingController::class, 'uploadMapping'])->name('admin.fashion.upload-mapping');
    //     Route::get('mapping/download', [\App\Http\Controllers\Admin\FashionMappingController::class, 'downloadMapping'])->name('admin.fashion.download-mapping');
    //     Route::get('mapping/backups', [\App\Http\Controllers\Admin\FashionMappingController::class, 'listBackups'])->name('admin.fashion.list-backups');
    //     Route::get('mapping/backups/{filename}', [\App\Http\Controllers\Admin\FashionMappingController::class, 'downloadBackup'])->name('admin.fashion.download-backup');
    // });
});


require __DIR__.'/auth.php';
