
// Debug utility for form submissions
function debugFormData(form) {
    console.log('=== FORM DEBUG ===');
    
    // Get FormData object
    const formData = new FormData(form);
    
    console.log('FormData entries:');
    for (let [key, value] of formData.entries()) {
        console.log(`  ${key}: ${value}`);
    }
    
    console.log('FormData grouped by key:');
    const grouped = {};
    for (let [key, value] of formData.entries()) {
        if (!grouped[key]) {
            grouped[key] = [];
        }
        grouped[key].push(value);
    }
    console.log(grouped);
    
    // Check for checkboxes specifically
    console.log('Checkbox analysis:');
    const checkboxes = form.querySelectorAll('input[type="checkbox"]');
    checkboxes.forEach(checkbox => {
        console.log(`  ${checkbox.name}: ${checkbox.checked ? checkbox.value : 'unchecked'}`);
    });
    
    console.log('=== END FORM DEBUG ===');
}

// Add event listener to forms with debug class
document.addEventListener('DOMContentLoaded', function() {
    const debugForms = document.querySelectorAll('form.debug-form');
    debugForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            debugFormData(this);
        });
    });
});

// Manual debug function you can call in console
window.debugCurrentForm = function(selector = 'form') {
    const form = document.querySelector(selector);
    if (form) {
        debugFormData(form);
    } else {
        console.log('Form not found with selector:', selector);
    }
};
