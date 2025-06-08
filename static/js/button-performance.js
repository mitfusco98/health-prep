// Button Performance Optimization
// Improves responsiveness of action buttons throughout the application

document.addEventListener('DOMContentLoaded', function() {
    
    // Debounce function to prevent rapid button clicks
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
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

    // Removed: Duplicate dropdown optimization (already in main.js)
// Removed: Unused form submission optimization
// Removed: Unused modal button optimization

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