@extends('layouts.app')

@section('title', 'Fashion Mapping Upload')

@section('content')
<div class="container mx-auto px-4 py-8">
    <div class="bg-white rounded-lg shadow-lg p-6">
        <h1 class="text-2xl font-bold mb-6 text-gray-800">Fashion Mapping Upload</h1>
        
        <!-- Current mapping info -->
        <div class="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
            <h2 class="text-lg font-semibold text-blue-800 mb-2">Trenutni mapping fajl</h2>
            @if($currentMappingExists)
                <div class="text-sm text-blue-700">
                    <p><strong>Status:</strong>Fajl postoji</p>
                    <p><strong>Poslednja izmena:</strong> {{ date('d.m.Y H:i:s', $currentMappingTime) }}</p>
                    <p><strong>Lokacija:</strong> <code>python_scraper/fc_nsport_mapping.xlsx</code></p>
                </div>
            @else
                <div class="text-sm text-red-700">
                    <p><strong>Status:</strong>Fajl ne postoji</p>
                    <p><strong>Lokacija:</strong> <code>python_scraper/fc_nsport_mapping.xlsx</code></p>
                </div>
            @endif
        </div>

        <!-- Upload form -->
        <div class="border border-gray-300 rounded-lg p-6">
            <h2 class="text-lg font-semibold text-gray-800 mb-4">Upload novi mapping fajl</h2>
            
            <form action="{{ route('admin.products.uploadFashionMapping') }}" method="POST" enctype="multipart/form-data" class="space-y-4">
                @csrf
                
                <div>
                    <label for="mapping_file" class="block text-sm font-medium text-gray-700 mb-2">
                        Excel fajl (.xlsx, .xls)
                    </label>
                    <input type="file" 
                           id="mapping_file" 
                           name="mapping_file" 
                           accept=".xlsx,.xls" 
                           required
                           class="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 border border-gray-300 rounded-lg">
                    @error('mapping_file')
                        <p class="mt-1 text-sm text-red-600">{{ $message }}</p>
                    @enderror
                </div>

                <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                    <h3 class="text-sm font-semibold text-yellow-800 mb-2">Važne napomene:</h3>
                    <ul class="text-sm text-yellow-700 space-y-1">
                        <li>• Fajl mora biti Excel format (.xlsx ili .xls)</li>
                        <li>• Mora imati kolone: <strong>"FC ŠIFRA"</strong> i <strong>"N SPORT ŠIFRA"</strong></li>
                    </ul>
                </div>

                <div class="flex items-center space-x-4">
                    <button type="submit" 
                            class="inline-flex items-center px-4 py-2 bg-blue-600 border border-transparent rounded-md font-semibold text-xs text-white uppercase tracking-widest hover:bg-blue-700 active:bg-blue-900 focus:outline-none focus:border-blue-900 focus:ring ring-blue-300 disabled:opacity-25 transition ease-in-out duration-150">
                        Upload Mapping
                    </button>
                    <a href="{{ route('admin.products.exports') }}" 
                       class="inline-flex items-center px-4 py-2 bg-gray-600 border border-transparent rounded-md font-semibold text-xs text-white uppercase tracking-widest hover:bg-gray-700 focus:outline-none focus:border-gray-900 focus:ring ring-gray-300 transition ease-in-out duration-150">
                        Nazad na export listu
                    </a>
                </div>
            </form>
        </div>

        <!-- Success/Error messages -->
        @if(session('success'))
            <div class="mt-6 bg-green-50 border border-green-200 rounded-lg p-4">
                <div class="flex">
                    <div class="flex-shrink-0">
                        <span class="text-green-400 text-lg">✅</span>
                    </div>
                    <div class="ml-3">
                        <p class="text-sm font-medium text-green-800">{{ session('success') }}</p>
                    </div>
                </div>
            </div>
        @endif

        @if($errors->any())
            <div class="mt-6 bg-red-50 border border-red-200 rounded-lg p-4">
                <div class="flex">
                    <div class="flex-shrink-0">
                        <span class="text-red-400 text-lg">❌</span>
                    </div>
                    <div class="ml-3">
                        <h3 class="text-sm font-medium text-red-800">Greške:</h3>
                        <div class="mt-2 text-sm text-red-700">
                            <ul class="list-disc list-inside space-y-1">
                                @foreach($errors->all() as $error)
                                    <li>{{ $error }}</li>
                                @endforeach
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
        @endif
    </div>
</div>
@endsection