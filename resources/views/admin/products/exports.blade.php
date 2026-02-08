@extends('layouts.app')

@section('content')
<div class="p-6 w-full">
    <div class="mb-6">
        <h1 class="text-2xl font-bold text-gray-900">Exportovani fajlovi</h1>
        <p class="text-gray-600">Pregled eksportovanih fajlova (poslednjih 7 dana)</p>
    </div>

    <div class="bg-white shadow-sm rounded-lg border border-gray-200 w-full">
        <div class="px-6 py-4 border-b border-gray-200">
            <div class="flex items-center justify-between">
                <h3 class="text-lg font-medium text-gray-900">Lista fajlova</h3>
                <div class="flex items-center space-x-2">
                    <span class="text-sm text-gray-500">{{ $files->count() }} fajlova</span>
                </div>
            </div>
        </div>
        
        <div class="overflow-x-auto">
            @if($files->isEmpty())
                <div class="px-6 py-12 text-center">
                    <div class="mx-auto w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4">
                        <span class="text-2xl">📁</span>
                    </div>
                    <p class="text-gray-500 text-lg">Nema eksportovanih fajlova za prikaz</p>
                    <p class="text-gray-400 text-sm mt-1">Eksportovani fajlovi će se prikazati ovde</p>
                </div>
            @else
                <table class="min-w-full divide-y divide-gray-200">
                    <thead class="bg-gray-50">
                        <tr>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Naziv fajla
                            </th>
                            <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Datum i vreme
                            </th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Trajanje
                            </th>
                            <th class="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Akcije
                            </th>
                        </tr>
                    </thead>
                    <tbody class="bg-white divide-y divide-gray-200">
                        @foreach($files as $fileData)
                            @php
                                $filename = $fileData['filename'];
                                $session = $fileData['session'];
                                
                                // Koristi session podatke ako postoje, inače fallback na parsing
                                if ($session) {
                                    $datum = $session->started_at->format('d.m.Y');
                                    $sat = $session->started_at->format('H:i:s');
                                    $trajanje = $session->duration ?? '-';
                                } else {
                                    // Fallback na parsing iz filename-a
                                    if (preg_match('/(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})/', $filename, $matches)) {
                                        try {
                                            $dt = \Carbon\Carbon::createFromFormat('Y-m-d_H-i-s', $matches[1]);
                                            $datum = $dt->format('d.m.Y');
                                            $sat = $dt->format('H:i:s');
                                        } catch (\Exception $e) {
                                            $datum = 'Nepoznato';
                                            $sat = '';
                                        }
                                    } else {
                                        $datum = 'Nepoznato';
                                        $sat = '';
                                    }
                                    
                                    // Parsiranje trajanja iz naziva fajla
                                    if (preg_match('/_(\d+)m(\d+)s\.xlsx?$/', $filename, $durationMatches)) {
                                        $minutes = $durationMatches[1];
                                        $seconds = $durationMatches[2];
                                        $trajanje = $minutes . 'm ' . $seconds . 's';
                                    } else {
                                        $trajanje = '-';
                                    }
                                }
                            @endphp
                            <tr class="hover:bg-gray-50">
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="flex items-center">
                                        <span class="text-xl mr-3">📄</span>
                                        <div>
                                            <div class="text-sm font-medium text-gray-900 font-mono">
                                                @php
                                                    // Ukloni products_export_ prefix
                                                    $cleanName = preg_replace('/^products_export_/', '', $filename);
                                                @endphp
                                                {{ $cleanName }}
                                            </div>
                                        </div>
                                    </div>
                                </td>
                                <td class="px-3 py-4 whitespace-nowrap text-sm text-gray-900 font-medium">
                                    {{ $datum }} <span class="text-gray-500">{{ $sat }}</span>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 font-mono">
                                    {{ $trajanje }}
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap text-center text-sm font-medium">
                                    <div class="flex items-center justify-center space-x-3">
                                        <a href="{{ url('/api/products/download-export/' . $filename) }}"
                                           download="{{ $filename }}"
                                           class="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors">
                                            ⬇️ Preuzmi
                                        </a>
                                        <form action="{{ route('admin.products.deleteExport', ['file' => $filename]) }}" method="POST" 
                                              onsubmit="return confirm('Da li ste sigurni da želite da obrišete ovaj fajl?')" class="inline">
                                            @csrf
                                            @method('DELETE')
                                            <button type="submit" 
                                                    class="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 transition-colors">
                                                🗑️ Obriši
                                            </button>
                                        </form>
                                    </div>
                                </td>
                            </tr>
                        @endforeach
                    </tbody>
                </table>
            @endif
        </div>
    </div>
</div>
@endsection