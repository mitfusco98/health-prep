// Button Performance Optimization
// Improves responsiveness of action buttons throughout the application

document.addEventListener('DOMContentLoaded', function() {
    
    // Advanced debouncing with memoization (equivalent to useCallback + useMemo)
    function createOptimizedDebounce(func, wait, immediate = false) {
        let timeout;
        let lastArgs;
        let lastThis;
        let maxTimeoutId;
        let result;

        const debounced = function executedFunction(...args) {
            lastArgs = args;
            lastThis = this;

            const later = () => {
                timeout = null;
                if (!immediate) {
                    result = func.apply(lastThis, lastArgs);
                }
            };

            const callNow = immediate && !timeout;
            
            clearTimeout(timeout);
            clearTimeout(maxTimeoutId);
            
            timeout = setTimeout(later, wait);
            
            // Ensure function is called at least every 2x wait time (prevent indefinite delays)
            maxTimeoutId = setTimeout(() => {
                if (timeout) {
                    clearTimeout(timeout);
                    later();
                }
            }, wait * 2);

            if (callNow) {
                result = func.apply(lastThis, lastArgs);
            }

            return result;
        };

        debounced.cancel = function() {
            clearTimeout(timeout);
            clearTimeout(maxTimeoutId);
            timeout = null;
        };

        return debounced;
    }

    // Memoize event handlers for better performance
    const memoizedHandlers = new Map();
    
    function getMemoizedHandler(key, handlerFactory) {
        if (!memoizedHandlers.has(key)) {
            memoizedHandlers.set(key, handlerFactory());
        }
        return memoizedHandlers.get(key);
    }

    // Optimize all action buttons
    const actionButtons = document.querySelectorAll('.btn');
    
    actionButtons.forEach(button => {
        // Prevent double-clicks on submit buttons
        if (button.type === 'submit' || button.classList.contains('btn-primary')) {
            button.addEventListener('click', function(e) {
                if (this.disabled) {
                    e.preventDefault();
                    return false;
                }
                
                // Disable button temporarily to prevent double-submission
                this.disabled = true;
                
                // Re-enable after a short delay unless it's a form submission
                if (!this.closest('form')) {
                    setTimeout(() => {
                        this.disabled = false;
                    }, 1000);
                }
            });
        }
        
        // Add visual feedback for better responsiveness perception
        button.addEventListener('mousedown', function() {
            this.style.transform = 'scale(0.98)';
        });
        
        button.addEventListener('mouseup', function() {
            this.style.transform = 'scale(1)';
        });
        
        button.addEventListener('mouseleave', function() {
            this.style.transform = 'scale(1)';
        });
    });

    // Optimize dropdown buttons specifically
    const dropdownButtons = document.querySelectorAll('.dropdown-toggle');
    dropdownButtons.forEach(button => {
        // Use faster event delegation instead of individual listeners
        button.addEventListener('click', debounce(function(e) {
            // Immediate visual feedback
            this.classList.add('active');
            setTimeout(() => {
                this.classList.remove('active');
            }, 150);
        }, 100));
    });

    // Optimize form submission buttons
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitBtn = this.querySelector('button[type="submit"], input[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = submitBtn.innerHTML.includes('spinner') ? 
                    submitBtn.innerHTML : 
                    '<span class="spinner-border spinner-border-sm me-2" role="status"></span>' + submitBtn.textContent;
            }
        });
    });

    // Optimize modal buttons
    const modalButtons = document.querySelectorAll('[data-bs-toggle="modal"]');
    modalButtons.forEach(button => {
        button.addEventListener('click', function() {
            // Immediate feedback
            this.style.opacity = '0.7';
            setTimeout(() => {
                this.style.opacity = '1';
            }, 200);
        });
    });

    // Performance optimization for tables with many action buttons
    const tables = document.querySelectorAll('table');
    tables.forEach(table => {
        // Use event delegation for better performance with many buttons
        table.addEventListener('click', function(e) {
            if (e.target.classList.contains('btn') || e.target.closest('.btn')) {
                const button = e.target.classList.contains('btn') ? e.target : e.target.closest('.btn');
                
                // Provide immediate visual feedback
                button.style.transform = 'scale(0.95)';
                setTimeout(() => {
                    button.style.transform = 'scale(1)';
                }, 100);
            }
        });
    });

    // Remove unnecessary event listeners that might be slowing things down
    const unnecessaryElements = document.querySelectorAll('[data-unnecessary-listener]');
    unnecessaryElements.forEach(el => {
        // Clean up any redundant event listeners
        el.removeEventListener('click', el.onclick);
    });

    console.log('Button performance optimizations loaded');
});

// CSS optimizations injected via JavaScript for immediate effect
const style = document.createElement('style');
style.textContent = `
    .btn {
        transition: transform 0.1s ease, opacity 0.1s ease !important;
        will-change: transform;
    }
    
    .btn:active {
        transform: scale(0.95) !important;
    }
    
    .btn:disabled {
        pointer-events: none;
        opacity: 0.6;
    }
    
    .table .btn {
        transition: transform 0.05s ease !important;
    }
    
    .dropdown-toggle::after {
        transition: transform 0.1s ease;
    }
    
    .dropdown-toggle[aria-expanded="true"]::after {
        transform: rotate(180deg);
    }
`;
document.head.appendChild(style);