<?php

namespace App\Exports;

use App\Models\Product;
use Illuminate\Support\Facades\DB;
use Maatwebsite\Excel\Concerns\FromArray;
use Maatwebsite\Excel\Concerns\WithHeadings;
use Maatwebsite\Excel\Concerns\WithStyles;
use Maatwebsite\Excel\Concerns\WithColumnWidths;
use Maatwebsite\Excel\Concerns\WithDefaultStyles;
use Maatwebsite\Excel\Concerns\WithEvents;
use Maatwebsite\Excel\Events\AfterSheet;
use PhpOffice\PhpSpreadsheet\Worksheet\Worksheet;
use PhpOffice\PhpSpreadsheet\Style\Style;
use PhpOffice\PhpSpreadsheet\Style\Alignment;
use PhpOffice\PhpSpreadsheet\Style\Fill;
use PhpOffice\PhpSpreadsheet\Style\Font;

class ProductsExport implements FromArray, WithStyles, WithColumnWidths, WithDefaultStyles, WithEvents
{
    public function array(): array
    {
        $data = [];
        
        // Učitaj sve prodavnice iz stores tabele koje imaju cene u prices tabeli
        $storesWithPrices = DB::select('
            SELECT DISTINCT s.id, s.name 
            FROM stores s 
            INNER JOIN prices p ON s.id = p.store_id 
            ORDER BY s.id
        ');
        
        $storeData = collect($storesWithPrices);
        $storeIds = $storeData->pluck('id')->toArray();
        $storeNames = $storeData->pluck('name', 'id')->toArray();
        
        // Kreiraj header - osnovna polja + NSport ALL + NSport prodavnice + ostale prodavnice
        $header = ['Šifra', 'Naziv', 'Brend', 'NSport ALL'];
        
        // Prvo dodaj NSport prodavnice zasebno (7-12)
        foreach ($storeIds as $storeId) {
            if ($storeId >= 7 && $storeId <= 12) {
                $header[] = $storeNames[$storeId];
            }
        }
        
        // Zatim dodaj ostale prodavnice (1-6) 
        foreach ($storeIds as $storeId) {
            if ($storeId >= 1 && $storeId <= 6) {
                $header[] = $storeNames[$storeId];
            }
        }
        $data[] = $header;
        
        // Učitaj proizvode sa cenama po prodavnicama (uključujući sve NSport za Combined kolonu)
        $allNSportIds = [7, 8, 9, 10, 11, 12]; // Uvek učitaj sve NSport
        $allStoreIds = array_unique(array_merge($storeIds, $allNSportIds));
        
        Product::with(['prices' => function($query) use ($allStoreIds) {
            $query->whereIn('store_id', $allStoreIds);
        }])
        ->orderByRaw('(SELECT COUNT(*) FROM prices WHERE product_id = products.id AND store_id IN (7,8,9,10,11,12)) DESC')
        ->chunk(50, function ($products) use (&$data, $storeIds, $allNSportIds) {
            foreach ($products as $product) {
                $row = [
                    $product->code ?? $product->sifra,
                    $product->naziv, 
                    $product->brand
                ];
                
                // NSport ALL kolona - uzmi prvu dostupnu cenu iz prodavnica 7-12
                $nsportCombinedPrice = '';
                foreach ($allNSportIds as $nsportId) {
                    $price = $product->prices->where('store_id', $nsportId)->first();
                    if ($price) {
                        // Srpski format: 16.490,00 (tačka za hiljade, zarez za decimale)
                        $nsportCombinedPrice = number_format((float)$price->price, 2, ',', '.');
                        break; // Uzmi prvu pronađenu cenu
                    }
                }
                $row[] = $nsportCombinedPrice;
                
                // Prvo dodaj NSport prodavnice zasebno (7-12)
                foreach ($storeIds as $storeId) {
                    if ($storeId >= 7 && $storeId <= 12) {
                        $price = $product->prices->where('store_id', $storeId)->first();
                        if ($price) {
                            // Srpski format: 16.490,00 (tačka za hiljade, zarez za decimale)
                            $formatted = number_format((float)$price->price, 2, ',', '.');
                            $row[] = $formatted;
                        } else {
                            $row[] = '';
                        }
                    }
                }
                
                // Zatim dodaj ostale prodavnice (1-6)
                foreach ($storeIds as $storeId) {
                    if ($storeId >= 1 && $storeId <= 6) {
                        $price = $product->prices->where('store_id', $storeId)->first();
                        if ($price) {
                            // Srpski format: 16.490,00 (tačka za hiljade, zarez za decimale)
                            $formatted = number_format((float)$price->price, 2, ',', '.');
                            $row[] = $formatted;
                        } else {
                            $row[] = '';
                        }
                    }
                }
                
                $data[] = $row;
            }
        });
        
        return $data;
    }

    public function styles(Worksheet $sheet)
    {
        // Dobij ukupan broj kolona
        $highestColumn = $sheet->getHighestColumn();
        $highestRow = $sheet->getHighestRow();
        
        return [
            // Stilizuj header red (prvi red)
            1 => [
                'font' => [
                    'bold' => true,
                    'size' => 11,
                    'color' => ['rgb' => 'FFFFFF']
                ],
                'fill' => [
                    'fillType' => Fill::FILL_SOLID,
                    'startColor' => ['rgb' => '4F46E5'] // Indigo boja
                ],
                'alignment' => [
                    'horizontal' => Alignment::HORIZONTAL_LEFT,
                    'vertical' => Alignment::VERTICAL_CENTER
                ]
            ],
            // Stilizuj sve ostale redove
            '2:' . $highestRow => [
                'alignment' => [
                    'horizontal' => Alignment::HORIZONTAL_LEFT,
                    'vertical' => Alignment::VERTICAL_CENTER
                ]
            ]
        ];
    }

    public function columnWidths(): array
    {
        // Učitaj podatke da izračunam širine kolona
        $data = $this->array();
        
        $widths = [];
        $columnCount = count($data[0]); // Broj kolona iz header-a
        
        for ($col = 0; $col < $columnCount; $col++) {
            $maxWidth = 0;
            
            // Prođi kroz sve redove za ovu kolonu
            foreach ($data as $row) {
                if (isset($row[$col])) {
                    $cellLength = mb_strlen((string)$row[$col], 'UTF-8');
                    if ($cellLength > $maxWidth) {
                        $maxWidth = $cellLength;
                    }
                }
            }
            
            // Dodaj dodatni prostor (minimum 10, maximum 50)
            $width = min(max($maxWidth + 3, 10), 50);
            
            // Mapiranje kolona (A, B, C, ...)
            $columnLetter = chr(65 + $col); // A=65, B=66, etc.
            if ($col >= 26) {
                $columnLetter = chr(64 + intval($col / 26)) . chr(65 + ($col % 26));
            }
            
            $widths[$columnLetter] = $width;
        }
        
        return $widths;
    }

    public function defaultStyles(Style $defaultStyle)
    {
        return [
            'font' => [
                'name' => 'Arial',
                'size' => 10
            ],
            'alignment' => [
                'horizontal' => Alignment::HORIZONTAL_LEFT,
                'vertical' => Alignment::VERTICAL_CENTER,
                'wrapText' => false
            ]
        ];
    }

    public function registerEvents(): array
    {
        return [
            AfterSheet::class => function(AfterSheet $event) {
                // Freeze panes - fiksira prvi red (header) i prvu kolonu
                $event->sheet->getDelegate()->freezePane('B2');
                
                // Alternativno, ako želiš samo header red da bude fiksiran:
                // $event->sheet->getDelegate()->freezePane('A2');
            },
        ];
    }
}