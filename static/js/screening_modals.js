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
});

function populateEditForm(screening) {
    document.getElementById('edit_screening_id').value = screening.id;
    document.getElementById('edit_name').value = screening.name || '';
    document.getElementById('edit_description').value = screening.description || '';

    // Handle frequency fields
    document.getElementById('edit_frequency_number').value = screening.frequency_number || '';
    document.getElementById('edit_frequency_unit').value = screening.frequency_unit || '';

    document.getElementById('edit_gender_specific').value = screening.gender_specific || '';
    document.getElementById('edit_min_age').value = screening.min_age || '';
    document.getElementById('edit_max_age').value = screening.max_age || '';
    document.getElementById('edit_is_active').checked = screening.is_active;

    // Clear existing keywords and trigger conditions first
    editKeywordsList = [];
    editTriggerConditions = [];
    updateEditKeywordsDisplay();
    updateEditTriggerConditionsDisplay();

    // Load keywords for this screening type
    loadKeywordsForEdit(screening.id);

    // Load trigger conditions
    loadTriggerConditionsForEdit(screening.id);
}

function loadKeywordsForEdit(screeningId) {
    fetch(`/api/screening-keywords/${screeningId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success && data.keywords) {
                // Clear existing keywords first
                editKeywordsList = [];

                // Deduplicate keywords using a Set to prevent duplicates
                const uniqueKeywords = new Set();

                data.keywords.forEach(keyword => {
                    if (keyword && typeof keyword === 'string' && keyword.trim()) {
                        const cleanKeyword = keyword.trim().toLowerCase();
                        if (!uniqueKeywords.has(cleanKeyword)) {
                            uniqueKeywords.add(cleanKeyword);
                            editKeywordsList.push(keyword.trim());
                        }
                    }
                });

                updateEditKeywordsDisplay();
                console.log(`Loaded ${editKeywordsList.length} unique keywords for screening ${screeningId}`);
            } else {
                console.warn('No keywords found for screening:', screeningId);
                editKeywordsList = [];
                updateEditKeywordsDisplay();
            }
        })
        .catch(error => {
            console.error('Error loading keywords:', error);
            editKeywordsList = [];
            updateEditKeywordsDisplay();
        });
}

function addEditKeyword() {
    const input = document.getElementById('edit_keyword_input');
    const keyword = input.value.trim();

    if (keyword) {
        // Check for duplicates case-insensitively
        const keywordLower = keyword.toLowerCase();
        const isDuplicate = editKeywordsList.some(existing => existing.toLowerCase() === keywordLower);

        if (!isDuplicate) {
            editKeywordsList.push(keyword);
            updateEditKeywordsDisplay();
            input.value = '';
            console.log(`Added keyword: "${keyword}"`);
        } else {
            console.warn(`Keyword "${keyword}" already exists`);
            input.value = '';
        }
    }
}

function saveEditScreeningType() {
    const screeningId = document.getElementById('edit_screening_id').value;
    const formData = new FormData();

    // Basic fields
    formData.append('name', document.getElementById('edit_name').value);
    formData.append('description', document.getElementById('edit_description').value);
    formData.append('frequency_number', document.getElementById('edit_frequency_number').value);
    formData.append('frequency_unit', document.getElementById('edit_frequency_unit').value);
    formData.append('gender_specific', document.getElementById('edit_gender_specific').value);
    formData.append('min_age', document.getElementById('edit_min_age').value);
    formData.append('max_age', document.getElementById('edit_max_age').value);

    if (document.getElementById('edit_is_active').checked) {
        formData.append('is_active', 'on');
    }

    // Deduplicate keywords before saving
    const uniqueKeywords = [...new Set(editKeywordsList.map(k => k.toLowerCase()))].map(k => {
        // Find original case version
        return editKeywordsList.find(orig => orig.toLowerCase() === k);
    });

    console.log(`Saving ${uniqueKeywords.length} unique keywords:`, uniqueKeywords);

    // Keywords - convert to JSON
    formData.append('keywords', JSON.stringify(uniqueKeywords));

    // Trigger conditions - convert to JSON
    formData.append('trigger_conditions', JSON.stringify(editTriggerConditions));

    fetch(`/screening-types/${screeningId}/edit`, {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (response.ok) {
            location.reload();
        } else {
            console.error('Error saving screening type');
        }
    })
    .catch(error => {
        console.error('Error:', error);
    });
}