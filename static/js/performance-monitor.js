
// Performance monitoring for JavaScript operations (similar to React Profiler)
class JavaScriptPerformanceMonitor {
    constructor() {
        this.operations = new Map();
        this.renderCounts = new Map();
        this.enabled = localStorage.getItem('js-performance-debug') === 'true';
    }

    // Equivalent to React's useMemo profiling
    memoizedOperation(name, operation, dependencies) {
        if (!this.enabled) return operation();

        const depsKey = JSON.stringify(dependencies);
        const cacheKey = `${name}_${depsKey}`;
        
        if (this.operations.has(cacheKey)) {
            console.log(`🚀 Cache hit for ${name}`);
            return this.operations.get(cacheKey);
        }

        const start = performance.now();
        const result = operation();
        const duration = performance.now() - start;

        this.operations.set(cacheKey, result);
        
        if (duration > 10) { // Log operations taking more than 10ms
            console.warn(`⚠️ Slow operation ${name}: ${duration.toFixed(2)}ms`);
        }

        return result;
    }

    // Equivalent to React's useCallback profiling
    callbackOperation(name, callback, dependencies) {
        if (!this.enabled) return callback;

        const depsKey = JSON.stringify(dependencies);
        const cacheKey = `callback_${name}_${depsKey}`;
        
        if (this.operations.has(cacheKey)) {
            return this.operations.get(cacheKey);
        }

        const wrappedCallback = (...args) => {
            const start = performance.now();
            const result = callback(...args);
            const duration = performance.now() - start;
            
            if (duration > 5) {
                console.warn(`⚠️ Slow callback ${name}: ${duration.toFixed(2)}ms`);
            }
            
            return result;
        };

        this.operations.set(cacheKey, wrappedCallback);
        return wrappedCallback;
    }

    // Track re-render equivalents
    trackOperation(name) {
        const count = (this.renderCounts.get(name) || 0) + 1;
        this.renderCounts.set(name, count);
        
        if (count > 10) {
            console.warn(`⚠️ Operation ${name} called ${count} times - consider optimization`);
        }
    }

    // Enable performance debugging
    static enableDebugging() {
        localStorage.setItem('js-performance-debug', 'true');
        console.log('🔍 JavaScript performance monitoring enabled');
        window.location.reload();
    }

    static disableDebugging() {
        localStorage.setItem('js-performance-debug', 'false');
        console.log('❌ JavaScript performance monitoring disabled');
        window.location.reload();
    }
}

// Global instance
window.JSPerformanceMonitor = new JavaScriptPerformanceMonitor();

// Developer tools
if (window.JSPerformanceMonitor.enabled) {
    console.log('🔍 JavaScript Performance Monitoring Active');
    console.log('Use JSPerformanceMonitor.disableDebugging() to turn off');
} else {
    console.log('Use JSPerformanceMonitor.enableDebugging() to monitor JS performance');
}
