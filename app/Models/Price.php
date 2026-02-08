<?php
namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Price extends Model
{
    protected $fillable = [
        'product_id',
        'store_id',
        'price',
        'price_regular',
        'price_discount',
        'price_old',
        'scraped_at',
    ];

    protected $casts = [
        'price' => 'decimal:2',
        'price_regular' => 'decimal:2',
        'price_discount' => 'decimal:2',
        'price_old' => 'decimal:2',
        'scraped_at' => 'datetime',
    ];
    public function product()
    {
        return $this->belongsTo(Product::class);
    }
    public function store()
    {
        return $this->belongsTo(Store::class);
    }
}
