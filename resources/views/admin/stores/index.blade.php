@extends('layouts.admin')

@section('content')
<h1>Prodavnice</h1>
<table>
    <thead>
        <tr>
            <th>Naziv</th>
            <th>Kontakt</th>
        </tr>
    </thead>
    <tbody>
        @foreach($stores as $store)
        <tr>
            <td>{{ $store->name }}</td>
            <td>{{ $store->contact }}</td>
        </tr>
        @endforeach
    </tbody>
</table>
@endsection