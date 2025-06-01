// Screening Management Modal Functionality
// This file controls the modal dialogs for adding and editing screenings

document.addEventListener('DOMContentLoaded', function() {
    console.log('Screening modals script loaded');
    
    // Open Add Screening modal
    const openAddScreeningBtn = document.getElementById('openAddScreeningModal');
    if (openAddScreeningBtn) {
        openAddScreeningBtn.addEventListener('click', function() {
            const modal = document.getElementById('addScreeningRecommendationModal');
            openModal(modal);
        });
    }
    
    // Open Add Screening Type modal
    const openAddTypeBtn = document.getElementById('openAddTypeModal');
    if (openAddTypeBtn) {
        openAddTypeBtn.addEventListener('click', function() {
            const modal = document.getElementById('addScreeningTypeModal');
            openModal(modal);
        });
    }
    
    // Handle edit screening buttons
    const editScreeningBtns = document.querySelectorAll('.edit-screening-btn');
    editScreeningBtns.forEach(function(btn) {
        btn.addEventListener('click', function() {
            // Get data attributes
            const id = this.getAttribute('data-id');
            const patientId = this.getAttribute('data-patient-id');
            const patientName = this.getAttribute('data-patient-name');
            const screeningType = this.getAttribute('data-screening-type');
            const dueDate = this.getAttribute('data-due-date');
            const lastCompleted = this.getAttribute('data-last-completed');
            const frequency = this.getAttribute('data-frequency');
            const priority = this.getAttribute('data-priority');
            const notes = this.getAttribute('data-notes');
            
            // Set form values
            const form = document.getElementById('editScreeningForm');
            form.action = `/patients/${patientId}/screenings/${id}/edit?ts=${Date.now()}`;
            
            document.getElementById('edit-patient-id').value = patientId;
            document.getElementById('edit-patient-name').textContent = patientName;
            document.getElementById('edit-screening-type').value = screeningType;
            
            if (dueDate) {
                document.getElementById('edit-due-date').value = dueDate;
            }
            
            if (lastCompleted) {
                document.getElementById('edit-last-completed').value = lastCompleted;
            }
            
            document.getElementById('edit-frequency').value = frequency || '';
            document.getElementById('edit-priority').value = priority || '';
            document.getElementById('edit-notes').value = notes || '';
            
            // Open the modal
            const modal = document.getElementById('editScreeningModal');
            openModal(modal);
        });
    });
    
    // Handle edit screening type buttons
    const editTypeBtns = document.querySelectorAll('.edit-screening-type-btn');
    editTypeBtns.forEach(function(btn) {
        btn.addEventListener('click', function() {
            // Get data attributes
            const id = this.getAttribute('data-id');
            const name = this.getAttribute('data-name');
            const description = this.getAttribute('data-description');
            const frequency = this.getAttribute('data-frequency');
            const gender = this.getAttribute('data-gender');
            const minAge = this.getAttribute('data-min-age');
            const maxAge = this.getAttribute('data-max-age');
            const active = this.getAttribute('data-active') === '1';
            
            // Set form values
            const form = document.getElementById('editScreeningTypeForm');
            form.action = `/screening-types/${id}/edit?ts=${Date.now()}`;
            
            document.getElementById('edit-name').value = name;
            document.getElementById('edit-description').value = description || '';
            document.getElementById('edit-frequency').value = frequency || '';
            document.getElementById('edit-gender').value = gender || '';
            document.getElementById('edit-min-age').value = minAge || '';
            document.getElementById('edit-max-age').value = maxAge || '';
            document.getElementById('edit-active').checked = active;
            
            // Open the modal
            const modal = document.getElementById('editScreeningTypeModal');
            openModal(modal);
        });
    });
    
    // Close buttons
    document.querySelectorAll('.modal .btn-close, .modal .btn-secondary').forEach(function(btn) {
        btn.addEventListener('click', function() {
            const modal = this.closest('.modal');
            closeModal(modal);
        });
    });
    
    // Close on backdrop click
    document.addEventListener('click', function(event) {
        if (event.target.classList.contains('modal') && event.target.classList.contains('show')) {
            closeModal(event.target);
        }
    });
    
    // Helper function to open modal
    function openModal(modal) {
        if (!modal) return;
        
        console.log('Opening modal:', modal.id);
        
        // Remove any existing backdrop
        const existingBackdrop = document.querySelector('.modal-backdrop');
        if (existingBackdrop) {
            existingBackdrop.remove();
        }
        
        // Create backdrop
        const backdrop = document.createElement('div');
        backdrop.className = 'modal-backdrop fade show';
        document.body.appendChild(backdrop);
        
        // Show modal
        modal.style.display = 'block';
        modal.classList.add('show');
        document.body.classList.add('modal-open');
        document.body.style.overflow = 'hidden';
        document.body.style.paddingRight = '15px';
    }
    
    // Helper function to close modal
    function closeModal(modal) {
        if (!modal) return;
        
        console.log('Closing modal:', modal.id);
        
        // Hide modal
        modal.style.display = 'none';
        modal.classList.remove('show');
        
        // Remove backdrop
        const backdrop = document.querySelector('.modal-backdrop');
        if (backdrop) {
            backdrop.remove();
        }
        
        // Restore body
        document.body.classList.remove('modal-open');
        document.body.style.overflow = '';
        document.body.style.paddingRight = '';
    }
});