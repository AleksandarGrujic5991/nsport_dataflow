<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class ScrapingSession extends Model
{
    use HasFactory;

    protected $fillable = [
        'session_key',
        'stores',
        'started_at',
        'ended_at',
        'products_count',
        'status'
    ];

    protected $casts = [
        'started_at' => 'datetime',
        'ended_at' => 'datetime'
    ];

    public static function startSession($stores, $sessionKey = null)
    {
        return self::create([
            'session_key' => $sessionKey ?: now()->format('Y-m-d_H-i-s') . '_' . uniqid(),
            'stores' => is_array($stores) ? implode(',', $stores) : $stores,
            'started_at' => now(),
            'status' => 'running'
        ]);
    }

    public function endSession($productsCount = 0)
    {
        $this->update([
            'ended_at' => now(),
            'products_count' => $productsCount,
            'status' => 'completed'
        ]);
    }

    public function getDurationAttribute()
    {
        if (!$this->ended_at) return null;

        $diff = $this->started_at->diff($this->ended_at);
        
        if ($diff->h > 0) {
            return $diff->h . 'h ' . $diff->i . 'm';
        } elseif ($diff->i > 0) {
            return $diff->i . 'm ' . $diff->s . 's';
        } else {
            return $diff->s . 's';
        }
    }
}