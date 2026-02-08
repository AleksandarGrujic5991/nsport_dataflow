<?php
use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    public function up(): void
    {
        Schema::table('prices', function (Blueprint $table) {
            $table->unsignedBigInteger('store_id')->nullable(false)->change();
            // Foreign key constraint je već kreiran u ranijoj migraciji
        });
    }
    public function down(): void
    {
        Schema::table('prices', function (Blueprint $table) {
            $table->dropForeign(['store_id']);
            $table->unsignedBigInteger('store_id')->nullable()->change();
        });
    }
};
