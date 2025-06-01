// Patient Detail - Section History Controls
document.addEventListener('DOMContentLoaded', function() {
    console.log('Patient detail page script loaded');
    
    // Find all section links and add click event listeners
    document.querySelectorAll('.section-link').forEach(function(link) {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Get the section name from data attribute
            const sectionName = this.getAttribute('data-section');
            console.log('Section clicked:', sectionName);
            
            // Find the corresponding history section
            const historySection = document.getElementById(sectionName + '-history');
            
            if (historySection) {
                // Hide all history sections first
                document.querySelectorAll('.history-section').forEach(function(section) {
                    section.style.display = 'none';
                });
                
                // Show the selected history section
                historySection.style.display = 'block';
                historySection.scrollIntoView({behavior: 'smooth'});
                
                console.log('Displayed section:', sectionName + '-history');
            } else {
                console.error('Could not find history section:', sectionName + '-history');
            }
        });
    });
    
    // Add close button functionality to history sections
    document.querySelectorAll('.card-header .btn-close').forEach(function(closeBtn) {
        closeBtn.addEventListener('click', function() {
            // Find the parent history section
            const historySection = this.closest('.history-section');
            if (historySection) {
                historySection.style.display = 'none';
            }
        });
    });
});