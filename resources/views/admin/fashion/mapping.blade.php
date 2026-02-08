@extends('layouts.admin')

@section('title', 'Fashion Mapping Upload')

@section('content')
<div class="container mx-auto px-4 py-8">
    <div class="max-w-4xl mx-auto">
        <!-- Header -->
        <div class="bg-white rounded-lg shadow-sm border p-6 mb-6">
            <h1 class="text-3xl font-bold text-gray-900 mb-2">Fashion & Friends Mapping</h1>
            <p class="text-gray-600">Upload novi mapping fajl za Fashion scraper (FC ŠIFRA → N SPORT ŠIFRA)</p>
        </div>

        <!-- Success/Error Messages -->
        @if(session('success'))
            <div class="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-6">
                <div class="flex">
                    <span class="text-xl mr-3">✅</span>
                    <div>
                        <strong>Uspešno!</strong> {{ session('success') }}
                        @if(session('file_info'))
                            <div class="mt-2 text-sm">
                                <strong>Detalji fajla:</strong><br>
                                📊 Ukupno mapiranja: {{ session('file_info.total_mappings') }}<br>
                                📁 Veličina fajla: {{ session('file_info.file_size') }}<br>
                                🕒 Vreme upload-a: {{ session('file_info.upload_time') }}
                            </div>
                        @endif
                    </div>
                </div>
            </div>
        @endif

        @if(session('error'))
            <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-6">
                <div class="flex">
                    <span class="text-xl mr-3">❌</span>
                    <div>
                        <strong>Greška!</strong> {{ session('error') }}
                    </div>
                </div>
            </div>
        @endif

        @if($errors->any())
            <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-6">
                <div class="flex">
                    <span class="text-xl mr-3">⚠️</span>
                    <div>
                        <strong>Validacijske greške:</strong>
                        <ul class="mt-2 list-disc list-inside">
                            @foreach($errors->all() as $error)
                                <li>{{ $error }}</li>
                            @endforeach
                        </ul>
                    </div>
                </div>
            </div>
        @endif

        <!-- Current File Info -->
        <div class="bg-blue-50 rounded-lg shadow-sm border p-6 mb-6">
            <h2 class="text-xl font-semibold text-gray-900 mb-4">📋 Trenutni mapping fajl</h2>
            
            @if($currentFileExists)
                <div class="space-y-2">
                    <div class="flex justify-between">
                        <span class="font-medium">Status:</span>
                        <span class="text-green-600">✅ Postoji</span>
                    </div>
                    <div class="flex justify-between">
                        <span class="font-medium">Lokacija:</span>
                        <span class="font-mono text-sm">{{ $currentFilePath }}</span>
                    </div>
                    <div class="flex justify-between">
                        <span class="font-medium">Poslednja izmena:</span>
                        <span>{{ $currentFileModified }}</span>
                    </div>
                    <div class="flex justify-between">
                        <span class="font-medium">Veličina:</span>
                        <span>{{ $currentFileSize }}</span>
                    </div>
                    @if($currentFileStats)
                        <div class="flex justify-between">
                            <span class="font-medium">Broj mapiranja:</span>
                            <span class="text-blue-600 font-semibold">{{ $currentFileStats['total_mappings'] ?? 'N/A' }}</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="font-medium">Kolumne:</span>
                            <span class="text-sm">{{ implode(', ', $currentFileStats['columns'] ?? []) }}</span>
                        </div>
                    @endif
                </div>
            @else
                <div class="text-center py-4">
                    <span class="text-red-500">❌ Fajl ne postoji</span>
                    <p class="text-sm text-gray-500 mt-2">Upload-ujte novi mapping fajl</p>
                </div>
            @endif
        </div>

        <!-- Upload Form -->
        <div class="bg-white rounded-lg shadow-sm border p-6">
            <h2 class="text-xl font-semibold text-gray-900 mb-4">📤 Upload novi mapping fajl</h2>
            
            <form action="{{ route('admin.fashion.upload-mapping') }}" method="POST" enctype="multipart/form-data" class="space-y-6">
                @csrf
                
                <!-- File Input -->
                <div>
                    <label for="mapping_file" class="block text-sm font-medium text-gray-700 mb-2">
                        Izaberite Excel fajl (.xlsx)
                    </label>
                    <div class="mt-1 flex justify-center px-6 pt-5 pb-6 border-2 border-gray-300 border-dashed rounded-md hover:border-gray-400 transition-colors">
                        <div class="space-y-1 text-center">
                            <svg class="mx-auto h-12 w-12 text-gray-400" stroke="currentColor" fill="none" viewBox="0 0 48 48">
                                <path d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
                            </svg>
                            <div class="flex text-sm text-gray-600">
                                <label for="mapping_file" class="relative cursor-pointer bg-white rounded-md font-medium text-indigo-600 hover:text-indigo-500 focus-within:outline-none">
                                    <span>Upload fajl</span>
                                    <input id="mapping_file" name="mapping_file" type="file" class="sr-only" accept=".xlsx,.xls" required>
                                </label>
                                <p class="pl-1">ili prevucite ovde</p>
                            </div>
                            <p class="text-xs text-gray-500">Excel fajlovi do 10MB</p>
                        </div>
                    </div>
                </div>

                <!-- Requirements -->
                <div class="bg-yellow-50 border border-yellow-200 rounded-md p-4">
                    <h3 class="text-sm font-medium text-yellow-800 mb-2">📋 Zahtevi za fajl:</h3>
                    <ul class="text-sm text-yellow-700 space-y-1">
                        <li>• Format: Excel (.xlsx ili .xls)</li>
                        <li>• Obavezne kolumne: <strong>"FC ŠIFRA"</strong> i <strong>"N SPORT ŠIFRA"</strong></li>
                        <li>• Prvi red mora biti header sa nazivima kolumna</li>
                        <li>• Maksimalna veličina: 10MB</li>
                    </ul>
                </div>

                <!-- Options -->
                <div class="space-y-4">
                    <div class="flex items-center">
                        <input id="backup_current" name="backup_current" type="checkbox" checked class="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded">
                        <label for="backup_current" class="ml-2 block text-sm text-gray-900">
                            🛡️ Napravi backup trenutnog fajla pre zamene
                        </label>
                    </div>
                    
                    <div class="flex items-center">
                        <input id="validate_data" name="validate_data" type="checkbox" checked class="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded">
                        <label for="validate_data" class="ml-2 block text-sm text-gray-900">
                            ✅ Validiraj podatke pre upload-a
                        </label>
                    </div>
                </div>

                <!-- Submit Button -->
                <div class="flex justify-end">
                    <button type="submit" class="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors">
                        <svg class="-ml-1 mr-3 h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                        </svg>
                        Upload Mapping Fajl
                    </button>
                </div>
            </form>
        </div>

        <!-- Download Backup Section -->
        @if($currentFileExists)
            <div class="bg-gray-50 rounded-lg shadow-sm border p-6 mt-6">
                <h2 class="text-xl font-semibold text-gray-900 mb-4">💾 Backup opcije</h2>
                <div class="flex space-x-4">
                    <a href="{{ route('admin.fashion.download-mapping') }}" 
                       class="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm bg-white text-sm font-medium text-gray-700 hover:bg-gray-50">
                        <svg class="-ml-1 mr-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        Preuzmi trenutni fajl
                    </a>
                </div>
            </div>
        @endif
    </div>
</div>

<script>
// File drag & drop functionality
document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('mapping_file');
    const dropZone = fileInput.closest('.border-dashed');
    
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, highlight, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, unhighlight, false);
    });
    
    function highlight(e) {
        dropZone.classList.add('border-indigo-400', 'bg-indigo-50');
    }
    
    function unhighlight(e) {
        dropZone.classList.remove('border-indigo-400', 'bg-indigo-50');
    }
    
    dropZone.addEventListener('drop', handleDrop, false);
    
    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        
        if (files.length > 0) {
            fileInput.files = files;
            updateFileName(files[0].name);
        }
    }
    
    fileInput.addEventListener('change', function(e) {
        if (e.target.files.length > 0) {
            updateFileName(e.target.files[0].name);
        }
    });
    
    function updateFileName(name) {
        const label = dropZone.querySelector('label span');
        label.textContent = name;
        label.className = 'text-indigo-600 font-medium';
    }
});
</script>
@endsection