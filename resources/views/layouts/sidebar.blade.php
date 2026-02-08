<aside class="w-64 bg-white shadow-lg border-r border-gray-200 flex flex-col h-screen justify-between">
    <div>
        <div class="p-6 border-b border-gray-100 flex items-center">
            <svg class="w-8 h-8 text-indigo-500 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
            </svg>
            <span class="sidebar-logo text-xl font-bold text-gray-800">Admin Panel</span>
        </div>
        <nav class="px-4 py-6 space-y-2">
            <a href="{{ route('admin.dashboard') }}"
               class="sidebar-link flex items-center {{ request()->routeIs('admin.dashboard') ? 'sidebar-link-active' : '' }}">
                <span class="mr-2">🏠</span> Dashboard
            </a>
            <a href="{{ route('admin.products.exports') }}"
               class="sidebar-link flex items-center">
                <span class="mr-2">🗂️</span> Lista eksportovanih fajlova
            </a>
            <a href="{{ route('admin.products.fashionMapping') }}"
               class="sidebar-link flex items-center {{ request()->routeIs('admin.products.fashionMapping') ? 'sidebar-link-active' : '' }}">
                <span class="mr-2">📤</span> Fashion Mapping
            </a>
            <a href="{{ route('admin.scraper.typeForm') }}"
            class="sidebar-link flex items-center {{ request()->routeIs('admin.scraper.typeForm') ? 'sidebar-link-active' : '' }}">
                <span class="mr-2">🔄</span> Pokreni scraper
            </a>
            <hr class="my-4">
            <a href="#" class="sidebar-link flex items-center">
                <span class="mr-2">📊</span> Statistika
            </a>
        </nav>
    </div>
    <div class="p-4 border-t border-gray-100 text-sm text-gray-500">
        Prijavljen: {{ Auth::user()->name ?? 'Admin' }}
    </div>
</aside>