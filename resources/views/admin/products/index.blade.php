@extends('layouts.admin')

@section('content')
<h1>Artikli</h1>
<a href="{{ route('admin.products.export') }}" class="btn">Download Excel</a>
<table class="products-table">
    <thead>
        <tr>
            <th>Šifra</th>
            <th>Naziv</th>
            <th>Cena</th>
            <th>Prodavnica</th>
        </tr>
    </thead>
    <tbody>
        @foreach($products as $product)
        <tr>
            <td>{{ $product->code }}</td>
            <td>{{ $product->naziv }}</td>
            <td>{{ $product->price }}</td>
            <td>{{ $product->store }}</td>
        </tr>
        @endforeach
    </tbody>
</table>
{{ $products->links() }}
@endsection

@push('styles')
<style>
.products-table { width: 100%; border-collapse: collapse; margin-top: 20px; }
.products-table th, .products-table td { border: 1px solid #ddd; padding: 8px; text-align: left; }
.products-table th { background-color: #f2f2f2; }
.btn { display: inline-block; padding: 8px 16px; margin-bottom: 10px; background: #007bff; color: #fff; text-decoration: none; border-radius: 4px; }
.btn:hover { background: #0056b3; }
</style>
@endpush