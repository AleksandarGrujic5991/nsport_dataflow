<?php

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Route;
use App\Http\Controllers\ProductApiController;

/*
|--------------------------------------------------------------------------
| API Routes
|--------------------------------------------------------------------------
|
| Here is where you can register API routes for your application. These
| routes are loaded by the RouteServiceProvider and all of them will
| be assigned to the "api" middleware group. Make something great!
|
*/

// Product API routes - no middleware for testing
Route::post('/products/batch', [ProductApiController::class, 'storeBatch']);
Route::post('/products', [ProductApiController::class, 'store']);
Route::get('/products/export-excel', [ProductApiController::class, 'exportExcelFromPython']);
Route::delete('/products/clear', [ProductApiController::class, 'clearDatabase']);
Route::post('/products/end-session', [ProductApiController::class, 'endSession']);
Route::get('/products/count', [ProductApiController::class, 'getCount']);
Route::get('/products/download-export/{filename}', [ProductApiController::class, 'downloadExport']);
Route::get('/products/test-export', [ProductApiController::class, 'testExport']);
Route::get('/products/export-small', [ProductApiController::class, 'exportSmall']);
Route::get('/products/export-small', [ProductApiController::class, 'exportSmall']);