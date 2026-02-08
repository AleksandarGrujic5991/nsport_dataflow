<?php

require_once 'vendor/autoload.php';

use Illuminate\Support\Facades\DB;
use App\Models\ScrapingSession;

// Bootstrap Laravel
$app = require_once 'bootstrap/app.php';
$app->make('Illuminate\Contracts\Console\Kernel')->bootstrap();

echo "🔍 Parsiram export fajlove za datum/vreme i trajanje...\n";

// Skeniranje export direktorijuma
$exportDir = storage_path('app/exports/products');
$files = glob($exportDir . '/*.xlsx');

echo "📂 Pronašao " . count($files) . " Excel fajlova\n\n";

foreach ($files as $filePath) {
    $filename = basename($filePath);
    echo "📄 Obrađujem: $filename\n";
    
    // Parse filename patterns:
    // full_2025-11-02_15-26-12_69077814d5f8d_duration_2m47s.xlsx
    // buzz_2025-11-02_15-29-00.xlsx
    // planeta_2025-11-02_02-08-28.xlsx
    
    $parsed = parseFilename($filename);
    
    if ($parsed) {
        echo "   ✅ Parsovano:\n";
        echo "      📅 Datum/vreme: {$parsed['datetime']}\n";
        echo "      ⏰ Trajanje: {$parsed['duration']}\n";
        echo "      🏪 Tip: {$parsed['type']}\n";
        
        // Pronađi ili kreiraj sesiju
        updateOrCreateSession($parsed, $filename);
    } else {
        echo "   ❌ Ne mogu da parsiram format\n";
    }
    
    echo "\n";
}

echo "✅ Završeno!\n";

function parseFilename($filename) {
    // Ukloni .xlsx ekstenziju
    $name = str_replace('.xlsx', '', $filename);
    
    // Pattern 1: products_export_full_2025-11-02_15-26-12_69077814d5f8d_duration_2m47s
    if (preg_match('/^products_export_(full|buzz|planeta|djak|extrasport|fashion)_(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})_[a-f0-9]+_duration_(.+)$/', $name, $matches)) {
        return [
            'type' => $matches[1],
            'datetime' => $matches[2],
            'duration' => $matches[3],
            'has_session_key' => true
        ];
    }
    
    // Pattern 2: buzz_2025-11-02_15-29-00 (bez duration)
    if (preg_match('/^(full|buzz|planeta|djak|extrasport|fashion)_(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})$/', $name, $matches)) {
        return [
            'type' => $matches[1],
            'datetime' => $matches[2],
            'duration' => null,
            'has_session_key' => false
        ];
    }
    
    // Pattern 3: products_export_full_2025-11-02_15-31-23
    if (preg_match('/^products_export_(full|buzz|planeta|djak|extrasport|fashion)_(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})$/', $name, $matches)) {
        return [
            'type' => $matches[1], 
            'datetime' => $matches[2],
            'duration' => null,
            'has_session_key' => false
        ];
    }
    
    return null;
}

function updateOrCreateSession($parsed, $filename) {
    // Konvertuj datetime format iz 2025-11-02_15-26-12 u Carbon
    $datetime = \Carbon\Carbon::createFromFormat('Y-m-d_H-i-s', $parsed['datetime']);
    
    // Generiraj session_key na osnovu datetime-a
    $sessionKey = $parsed['datetime'] . '_' . substr(md5($filename), 0, 8);
    
    // Proveri da li već postoji sesija sa ovim datetime-om
    $session = ScrapingSession::where('started_at', $datetime)->first();
    
    if (!$session) {
        // Kreiraj novu sesiju
        $session = ScrapingSession::create([
            'session_key' => $sessionKey,
            'stores' => $parsed['type'],
            'started_at' => $datetime,
            'ended_at' => $parsed['duration'] ? $datetime->copy()->addMinutes(parseDurationToMinutes($parsed['duration'])) : null,
            'products_count' => 0, // Ovo možemo ažurirati kasnije
            'status' => $parsed['duration'] ? 'completed' : 'running'
        ]);
        
        echo "      ➕ Kreirana nova sesija: {$session->id}\n";
    } else {
        // Ažuriraj postojeću sesiju ako je potrebno
        if ($parsed['duration'] && !$session->ended_at) {
            $session->ended_at = $datetime->copy()->addMinutes(parseDurationToMinutes($parsed['duration']));
            $session->status = 'completed';
            $session->save();
            echo "      🔄 Ažurirana sesija: {$session->id}\n";
        } else {
            echo "      ✓ Sesija već postoji: {$session->id}\n";
        }
    }
    
    return $session;
}

function parseDurationToMinutes($duration) {
    // Parse 2m47s -> minutes
    $totalMinutes = 0;
    
    // Extract hours (1h30m)
    if (preg_match('/(\d+)h/', $duration, $matches)) {
        $totalMinutes += intval($matches[1]) * 60;
    }
    
    // Extract minutes (30m)
    if (preg_match('/(\d+)m/', $duration, $matches)) {
        $totalMinutes += intval($matches[1]);
    }
    
    // Extract seconds (30s) - convert to fraction of minute
    if (preg_match('/(\d+)s/', $duration, $matches)) {
        $totalMinutes += intval($matches[1]) / 60;
    }
    
    return $totalMinutes;
}