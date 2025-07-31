
// Universal Navigation System
// Provides back/forward functionality throughout the application

document.addEventListener('DOMContentLoaded', function() {
    const backBtn = document.getElementById('universal-back-btn');
    const forwardBtn = document.getElementById('universal-forward-btn');
    
    if (!backBtn || !forwardBtn) {
        console.warn('Universal navigation buttons not found');
        return;
    }

    // Update button states based on browser history
    function updateNavigationButtons() {
        // Check if we can go back (more than 1 entry in history)
        backBtn.disabled = window.history.length <= 1;
        
        // Forward button state - unfortunately we can't reliably detect this
        // So we'll enable it by default and let the browser handle it
        forwardBtn.disabled = false;
        
        // Add visual feedback for disabled state
        if (backBtn.disabled) {
            backBtn.classList.add('opacity-50');
            backBtn.title = 'No previous page';
        } else {
            backBtn.classList.remove('opacity-50');
            backBtn.title = 'Go Back';
        }
    }

    // Back button functionality
    backBtn.addEventListener('click', function(e) {
        e.preventDefault();
        
        if (!this.disabled && window.history.length > 1) {
            // Add loading state
            this.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            
            // Use history.back() for true browser navigation
            window.history.back();
            
            // Reset button after short delay
            setTimeout(() => {
                this.innerHTML = '<i class="fas fa-arrow-left"></i>';
            }, 500);
        }
    });

    // Forward button functionality
    forwardBtn.addEventListener('click', function(e) {
        e.preventDefault();
        
        if (!this.disabled) {
            // Add loading state
            this.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            
            // Use history.forward() for true browser navigation
            window.history.forward();
            
            // Reset button after short delay
            setTimeout(() => {
                this.innerHTML = '<i class="fas fa-arrow-right"></i>';
            }, 500);
        }
    });

    // Update button states when page loads
    updateNavigationButtons();
    
    // Update button states when user navigates
    window.addEventListener('popstate', updateNavigationButtons);
    
    // Update button states when new pages are loaded via JavaScript
    const originalPushState = history.pushState;
    const originalReplaceState = history.replaceState;
    
    history.pushState = function() {
        originalPushState.apply(history, arguments);
        setTimeout(updateNavigationButtons, 100);
    };
    
    history.replaceState = function() {
        originalReplaceState.apply(history, arguments);
        setTimeout(updateNavigationButtons, 100);
    };

    // Keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Alt + Left Arrow = Back
        if (e.altKey && e.key === 'ArrowLeft' && !backBtn.disabled) {
            e.preventDefault();
            backBtn.click();
        }
        
        // Alt + Right Arrow = Forward
        if (e.altKey && e.key === 'ArrowRight' && !forwardBtn.disabled) {
            e.preventDefault();
            forwardBtn.click();
        }
    });

    console.log('Universal navigation system initialized');
});

// Helper function to check if current page should have navigation
function shouldShowNavigation() {
    const currentPath = window.location.pathname;
    
    // Hide navigation on login/register pages
    const hideOnPages = ['/login', '/register'];
    
    return !hideOnPages.some(page => currentPath.includes(page));
}

// Hide navigation buttons on certain pages
document.addEventListener('DOMContentLoaded', function() {
    if (!shouldShowNavigation()) {
        const navControls = document.querySelector('.universal-nav-controls');
        if (navControls) {
            navControls.style.display = 'none';
        }
    }
});
