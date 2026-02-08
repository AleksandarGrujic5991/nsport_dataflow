<?php
use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up(): void
    {
        Schema::table('prices', function (Blueprint $table) {
            $table->decimal('price_regular', 10, 2)->nullable()->after('price');
            $table->decimal('price_discount', 10, 2)->nullable()->after('price_regular');
            $table->decimal('price_old', 10, 2)->nullable()->after('price_discount');
        });
    }
    public function down(): void
    {
        Schema::table('prices', function (Blueprint $table) {
            $table->dropColumn(['price_regular', 'price_discount', 'price_old']);
        });
    }
};
