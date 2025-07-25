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

    // Edit screening type functionality removed - now redirects to dedicated edit page

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

    function toggleScreening(button) {
        const value = button.getAttribute('data-value');
        const isSelected = button.classList.contains('btn-primary');

        if (isSelected) {
            button.classList.remove('btn-primary');
            button.classList.add('btn-outline-primary');
            // Remove from hidden input
            removeFromSelectedScreenings(value);
        } else {
            button.classList.remove('btn-outline-primary');
            button.classList.add('btn-primary');
            // Add to hidden input
            addToSelectedScreenings(value);
        }
    }

    function toggleConsolidatedScreening(button) {
        const baseName = button.getAttribute('data-value');
        const variants = button.getAttribute('data-variants');
        const isSelected = button.classList.contains('btn-primary');

        if (isSelected) {
            button.classList.remove('btn-primary');
            button.classList.add('btn-outline-primary');
            // Remove base name from selected screenings
            removeFromSelectedScreenings(baseName);
            // Also remove all variants if they were individually selected
            if (variants) {
                variants.split(',').forEach(variant => {
                    removeFromSelectedScreenings(variant.trim());
                });
            }
        } else {
            button.classList.remove('btn-outline-primary');
            button.classList.add('btn-primary');
            // Add base name to selected screenings
            addToSelectedScreenings(baseName);
        }
        
        // Update display
        updateScreeningDisplay();
    }
    
    function addToSelectedScreenings(value) {
        const hiddenInput = document.getElementById('screening-selections');
        const currentValue = hiddenInput.value;
        const currentList = currentValue ? currentValue.split(',') : [];
        
        if (!currentList.includes(value)) {
            currentList.push(value);
            hiddenInput.value = currentList.join(',');
        }
    }
    
    function removeFromSelectedScreenings(value) {
        const hiddenInput = document.getElementById('screening-selections');
        const currentValue = hiddenInput.value;
        const currentList = currentValue ? currentValue.split(',') : [];
        
        const index = currentList.indexOf(value);
        if (index > -1) {
            currentList.splice(index, 1);
            hiddenInput.value = currentList.join(',');
        }
    }
    
    function updateScreeningDisplay() {
        const hiddenInput = document.getElementById('screening-selections');
        const displayElement = document.getElementById('screening-list-display');
        
        if (hiddenInput && displayElement) {
            const currentValue = hiddenInput.value;
            const displayText = currentValue ? currentValue.replace(/,/g, ', ') : 'None';
            displayElement.textContent = displayText;
        }
    }
    
    // Make functions globally available
    window.toggleConsolidatedScreening = toggleConsolidatedScreening;
    window.addToSelectedScreenings = addToSelectedScreenings;
    window.removeFromSelectedScreenings = removeFromSelectedScreenings;
    window.updateScreeningDisplay = updateScreeningDisplay;
});