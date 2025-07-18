/**
 * High-Performance Screening List Optimizations
 * Implements client-side performance enhancements for the screening table
 */

class ScreeningListOptimizer {
    constructor() {
        this.searchTimeout = null;
        this.filterTimeout = null;
        this.initialized = false;
        
        this.init();
    }
    
    init() {
        if (this.initialized) return;
        
        // Initialize search optimization
        this.initSearchOptimization();
        
        // Initialize filter optimization
        this.initFilterOptimization();
        
        // Initialize table optimization
        this.initTableOptimization();
        
        // Initialize cache management
        this.initCacheManagement();
        
        this.initialized = true;
        console.log('✅ Screening List Optimizer initialized');
    }
    
    initSearchOptimization() {
        const searchInput = document.getElementById('searchQuery');
        if (!searchInput) return;
        
        // Add loading indicator
        const searchContainer = searchInput.closest('.input-group') || searchInput.parentElement;
        const loadingSpinner = document.createElement('div');
        loadingSpinner.className = 'spinner-border spinner-border-sm text-primary d-none';
        loadingSpinner.id = 'searchLoadingSpinner';
        searchContainer.appendChild(loadingSpinner);
        
        // Debounced search with loading state
        searchInput.addEventListener('input', (e) => {
            clearTimeout(this.searchTimeout);
            
            // Show loading spinner
            loadingSpinner.classList.remove('d-none');
            
            this.searchTimeout = setTimeout(() => {
                this.performSearch(e.target.value);
                loadingSpinner.classList.add('d-none');
            }, 500); // 500ms debounce for search
        });
        
        // Clear search functionality
        const clearButton = document.createElement('button');
        clearButton.className = 'btn btn-outline-secondary';
        clearButton.type = 'button';
        clearButton.innerHTML = '<i class="fas fa-times"></i>';
        clearButton.title = 'Clear search';
        clearButton.addEventListener('click', () => {
            searchInput.value = '';
            this.performSearch('');
        });
        
        if (searchContainer.classList.contains('input-group')) {
            searchContainer.appendChild(clearButton);
        }
    }
    
    initFilterOptimization() {
        const statusFilter = document.getElementById('statusFilter');
        const typeFilter = document.getElementById('screeningTypeFilter');
        
        // Debounced filter changes
        [statusFilter, typeFilter].forEach(filter => {
            if (!filter) return;
            
            filter.addEventListener('change', (e) => {
                clearTimeout(this.filterTimeout);
                
                this.filterTimeout = setTimeout(() => {
                    this.applyFilters();
                }, 200); // 200ms debounce for filters
            });
        });
    }
    
    initTableOptimization() {
        const table = document.querySelector('.screening-table');
        if (!table) return;
        
        // Virtual scrolling for large datasets (if more than 100 rows)
        const rows = table.querySelectorAll('tbody tr');
        if (rows.length > 100) {
            this.implementVirtualScrolling(table, rows);
        }
        
        // Optimize row rendering
        this.optimizeRowRendering(table);
        
        // Add progressive loading
        this.addProgressiveLoading(table);
    }
    
    initCacheManagement() {
        // Cache common filter combinations
        this.filterCache = new Map();
        
        // Preload common pages
        this.preloadCommonPages();
        
        // Clear cache on data changes
        window.addEventListener('beforeunload', () => {
            // Clear any pending timeouts
            clearTimeout(this.searchTimeout);
            clearTimeout(this.filterTimeout);
        });
    }
    
    performSearch(query) {
        const currentUrl = new URL(window.location);
        
        if (query.trim()) {
            currentUrl.searchParams.set('search', query);
        } else {
            currentUrl.searchParams.delete('search');
        }
        
        // Reset to first page on new search
        currentUrl.searchParams.set('page', '1');
        
        // Navigate to new URL
        window.location.href = currentUrl.toString();
    }
    
    applyFilters() {
        const statusFilter = document.getElementById('statusFilter');
        const typeFilter = document.getElementById('screeningTypeFilter');
        
        const currentUrl = new URL(window.location);
        
        // Apply status filter
        if (statusFilter && statusFilter.value) {
            currentUrl.searchParams.set('status', statusFilter.value);
        } else {
            currentUrl.searchParams.delete('status');
        }
        
        // Apply type filter
        if (typeFilter && typeFilter.value) {
            currentUrl.searchParams.set('screening_type', typeFilter.value);
        } else {
            currentUrl.searchParams.delete('screening_type');
        }
        
        // Reset to first page on filter change
        currentUrl.searchParams.set('page', '1');
        
        // Navigate to new URL
        window.location.href = currentUrl.toString();
    }
    
    implementVirtualScrolling(table, rows) {
        // Simple virtual scrolling implementation
        const tableContainer = table.closest('.table-responsive') || table.parentElement;
        const rowHeight = 60; // Approximate row height
        const visibleRows = Math.ceil(window.innerHeight / rowHeight) + 5; // Buffer
        
        let startIndex = 0;
        let endIndex = Math.min(visibleRows, rows.length);
        
        // Hide non-visible rows initially
        for (let i = endIndex; i < rows.length; i++) {
            rows[i].style.display = 'none';
        }
        
        // Add scroll listener for virtual scrolling
        tableContainer.addEventListener('scroll', () => {
            const scrollTop = tableContainer.scrollTop;
            const newStartIndex = Math.floor(scrollTop / rowHeight);
            const newEndIndex = Math.min(newStartIndex + visibleRows, rows.length);
            
            if (newStartIndex !== startIndex) {
                // Hide previously visible rows
                for (let i = startIndex; i < endIndex; i++) {
                    if (i < newStartIndex || i >= newEndIndex) {
                        rows[i].style.display = 'none';
                    }
                }
                
                // Show newly visible rows
                for (let i = newStartIndex; i < newEndIndex; i++) {
                    rows[i].style.display = '';
                }
                
                startIndex = newStartIndex;
                endIndex = newEndIndex;
            }
        });
    }
    
    optimizeRowRendering(table) {
        // Use DocumentFragment for bulk updates
        const tbody = table.querySelector('tbody');
        if (!tbody) return;
        
        // Add intersection observer for lazy loading of row details
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const row = entry.target;
                    this.loadRowDetails(row);
                    observer.unobserve(row);
                }
            });
        }, {
            rootMargin: '100px' // Load when within 100px of viewport
        });
        
        // Observe all rows
        tbody.querySelectorAll('tr').forEach(row => {
            observer.observe(row);
        });
    }
    
    addProgressiveLoading(table) {
        // Add skeleton loading for better perceived performance
        const tbody = table.querySelector('tbody');
        if (!tbody || tbody.children.length === 0) {
            this.showSkeletonLoader(tbody);
        }
    }
    
    showSkeletonLoader(tbody) {
        const skeletonRows = 5;
        for (let i = 0; i < skeletonRows; i++) {
            const row = document.createElement('tr');
            row.className = 'skeleton-row';
            row.innerHTML = `
                <td><div class="skeleton-text"></div></td>
                <td><div class="skeleton-text"></div></td>
                <td><div class="skeleton-text"></div></td>
                <td><div class="skeleton-text"></div></td>
                <td><div class="skeleton-text"></div></td>
            `;
            tbody.appendChild(row);
        }
        
        // Remove skeleton after content loads
        setTimeout(() => {
            tbody.querySelectorAll('.skeleton-row').forEach(row => row.remove());
        }, 1000);
    }
    
    loadRowDetails(row) {
        // Placeholder for lazy loading row details
        // Could be used for loading document counts, etc.
        console.log('Loading details for row:', row);
    }
    
    preloadCommonPages() {
        // Preload next page if user is scrolling down
        let scrollTimeout;
        window.addEventListener('scroll', () => {
            clearTimeout(scrollTimeout);
            scrollTimeout = setTimeout(() => {
                const scrollPercent = (window.scrollY + window.innerHeight) / document.body.scrollHeight;
                if (scrollPercent > 0.8) { // 80% scrolled
                    this.preloadNextPage();
                }
            }, 100);
        });
    }
    
    preloadNextPage() {
        const nextPageLink = document.querySelector('.pagination .page-item:not(.disabled) .page-link[href*="page="]');
        if (nextPageLink && !nextPageLink.dataset.preloaded) {
            const link = document.createElement('link');
            link.rel = 'prefetch';
            link.href = nextPageLink.href;
            document.head.appendChild(link);
            nextPageLink.dataset.preloaded = 'true';
        }
    }
}

// Initialize optimizer when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new ScreeningListOptimizer();
});

// CSS for skeleton loading (inject into page)
const skeletonCSS = `
.skeleton-text {
    height: 16px;
    background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
    background-size: 200% 100%;
    animation: skeleton-loading 1.5s infinite;
    border-radius: 4px;
}

@keyframes skeleton-loading {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
}

.skeleton-row td {
    padding: 12px 8px;
}
`;

// Inject skeleton CSS
const style = document.createElement('style');
style.textContent = skeletonCSS;
document.head.appendChild(style);