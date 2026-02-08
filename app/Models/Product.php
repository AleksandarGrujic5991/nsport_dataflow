<?php
namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Product extends Model
{
    protected $fillable = [
        'code',
        'naziv',
        'brand',
    ];
    public function prices()
    {
        return $this->hasMany(Price::class);
    }
}
