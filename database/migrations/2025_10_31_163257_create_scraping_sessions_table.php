<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::create('scraping_sessions', function (Blueprint $table) {
            $table->id();
            $table->string('session_key')->unique(); // unique key za sesiju
            $table->string('stores'); // koje prodavnice se scrape-uju (buzz, planeta, itd.)
            $table->timestamp('started_at'); // kada je poceo scraping
            $table->timestamp('ended_at')->nullable(); // kada je zavrsio scraping 
            $table->integer('products_count')->default(0); // koliko proizvoda je dodano
            $table->string('status')->default('running'); // running, completed, failed
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('scraping_sessions');
    }
};
