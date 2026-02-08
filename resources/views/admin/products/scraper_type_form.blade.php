@extends('layouts.app')

@section('content')
<div class="p-6">
    <div class="mb-6">
        <h1 class="text-2xl font-bold text-gray-900">Pokretanje scraper-a</h1>
        <p class="text-gray-600">Izaberite prodavnice za koje želite da pokrenete scraper</p>
    </div>

    <div class="max-w-4xl space-y-6">
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div class="flex items-center mb-6">
                <h3 class="text-lg font-semibold text-gray-900">Grupno pokretanje scraper-a po prodavnici</h3>
            </div>
            
            <form method="POST" action="{{ route('admin.scraper.run') }}">
                @csrf
                <div class="mb-6">
                    <label class="block text-sm font-medium text-gray-700 mb-3">Izaberite prodavnice:</label>
                    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                        @foreach($stores as $store)
                            <label class="flex items-center space-x-3 bg-gray-50 rounded-lg px-4 py-3 hover:bg-gray-100 transition-colors cursor-pointer border border-gray-200">
                                <input type="checkbox" name="stores[]" value="{{ $store->id }}" 
                                       class="h-4 w-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500">
                                <span class="font-medium text-gray-700">{{ $store->naziv }}</span>
                            </label>
                        @endforeach
                    </div>
                </div>
                
                <button type="submit" 
                        class="w-full md:w-auto px-6 py-3 bg-indigo-600 text-white rounded-lg font-semibold shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 transition-colors">
                     Pokreni grupni scraper
                </button>
            </form>
        </div>

        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div class="flex items-center mb-6">
                <h3 class="text-lg font-semibold text-gray-900">Pokreni scraper za sve prodavnice</h3>
            </div>
            
            <p class="text-gray-600 mb-4">Ova opcija će pokrenuti scraper za sve dostupne prodavnice odjednom.</p>
            
            <form method="POST" action="{{ route('admin.scraper.run') }}">
                @csrf
                <input type="hidden" name="all_stores" value="1">
                <button type="submit" 
                        class="w-full md:w-auto px-6 py-3 bg-green-600 text-white rounded-lg font-semibold shadow-sm hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 transition-colors">
                     Pokreni scraper za sve
                </button>
            </form>
        </div>

        @if(isset($logs) && count($logs))
            <div class="bg-gray-50 rounded-lg border border-gray-200 p-6">
                <div class="flex items-center mb-4">
                    <div class="p-2 bg-yellow-100 rounded-lg mr-3">
                        <span class="text-yellow-600 text-xl">📋</span>
                    </div>
                    <h4 class="text-lg font-semibold text-gray-900">Logovi izvršavanja</h4>
                </div>
                <div class="bg-white rounded border p-4 max-h-96 overflow-y-auto">
                    <pre class="text-sm text-gray-700 whitespace-pre-wrap">{{ implode("\n", $logs) }}</pre>
                </div>
            </div>
        @endif

        @if(session('success'))
            <div class="bg-green-50 border border-green-200 rounded-lg p-4">
                <div class="flex items-center">
                    <span class="text-green-600 text-xl mr-3">✅</span>
                    <p class="text-green-800 font-medium">{{ session('success') }}</p>
                </div>
            </div>
        @endif

        @if(session('error'))
            <div class="bg-red-50 border border-red-200 rounded-lg p-4">
                <div class="flex items-center">
                    <span class="text-red-600 text-xl mr-3">❌</span>
                    <p class="text-red-800 font-medium">{{ session('error') }}</p>
                </div>
            </div>
        @endif
    </div>
</div>
@endsection