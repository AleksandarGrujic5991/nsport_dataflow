@extends('layouts.app')

@section('content')
<div class="p-6">
    <div class="mb-6">
        <h1 class="text-2xl font-bold text-gray-900">Admin Dashboard</h1>
        <p class="text-gray-600">Dobrodošli u admin panel</p>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <div class="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
            <div class="flex items-center">
                <div class="p-3 rounded-full bg-blue-100 text-blue-600">
                    <span class="text-xl">📦</span>
                </div>
                <div class="ml-4">
                    <p class="text-sm font-medium text-gray-600">Ukupno proizvoda</p>
                    <p class="text-2xl font-bold text-gray-900">{{ $productsCount }}</p>
                </div>
            </div>
        </div>
        
        <div class="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
            <div class="flex items-center">
                <div class="p-3 rounded-full bg-green-100 text-green-600">
                    <span class="text-xl">🏪</span>
                </div>
                <div class="ml-4">
                    <p class="text-sm font-medium text-gray-600">Ukupno prodavnica</p>
                    <p class="text-2xl font-bold text-gray-900">{{ $storesCount }}</p>
                </div>
            </div>
        </div>
    </div>

    @if(session('status'))
        <div class="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-4">
            {{ session('status') }}
        </div>
    @endif

    <!-- <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 class="text-lg font-semibold text-gray-900 mb-4">Brze akcije</h2>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <a href="{{ route('admin.products.exportDirect') }}" 
               class="flex items-center p-4 bg-blue-50 hover:bg-blue-100 rounded-lg border border-blue-200 transition-colors">
                <span class="text-2xl mr-3">📊</span>
                <div>
                    <p class="font-medium text-blue-900">Export proizvoda</p>
                    <p class="text-sm text-blue-700">Izvezi sve proizvode u Excel</p>
                </div>
            </a>
            
            <a href="{{ route('admin.scraper.typeForm') }}" 
               class="flex items-center p-4 bg-green-50 hover:bg-green-100 rounded-lg border border-green-200 transition-colors">
                <span class="text-2xl mr-3">🔄</span>
                <div>
                    <p class="font-medium text-green-900">Pokreni scraper</p>
                    <p class="text-sm text-green-700">Skini nove proizvode</p>
                </div>
            </a>
            
            <a href="{{ route('admin.products.exports') }}" 
               class="flex items-center p-4 bg-purple-50 hover:bg-purple-100 rounded-lg border border-purple-200 transition-colors">
                <span class="text-2xl mr-3">🗂️</span>
                <div>
                    <p class="font-medium text-purple-900">Eksportovani fajlovi</p>
                    <p class="text-sm text-purple-700">Pregled i download</p>
                </div>
            </a>
        </div>
    </div> -->
</div>
@endsection