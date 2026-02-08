<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;

class DashboardController extends Controller
{
    public function index()
    {
        $productsCount = DB::table('prices')->count();
        $storesCount = \App\Models\Store::count();
        $latestProducts = \App\Models\Product::latest()->take(5)->get();
        return view('admin.dashboard', compact('productsCount', 'storesCount', 'latestProducts'));
    }

    public function runScraper()
    {
        $output = [];
        $result = null;
        exec('python c:/laragon/www/scraper/python_scraper/run_ultra_scraper.py', $output, $result);
        return back()->with('status', 'Scraper pokrenut! Rezultat: ' . implode("\n", $output));
    }
}
