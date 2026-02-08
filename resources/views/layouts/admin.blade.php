<!DOCTYPE html>
<html>
<head>
    <title>Admin Panel</title>
    @stack('styles')
</head>
<body>
    <nav>
        <a href="{{ route('admin.dashboard') }}">Dashboard</a> |
        <a href="{{ route('products.index') }}">Artikli</a> |
        <a href="{{ route('stores.index') }}">Prodavnice</a> |
        <a href="{{ route('admin.products.export') }}">Export</a>
    </nav>
    <div class="container">
        @yield('content')
    </div>
</body>
</html>