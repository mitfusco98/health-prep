/**
 * Enhanced Status Entry Functionality
 * 
 * This script adds direct custom status entry to all status dropdowns by:
 * 1. Double-clicking on any dropdown to enter custom text
 * 2. Right-clicking on a dropdown shows a context menu to enter custom status
 * 3. Selecting "custom" from the dropdown enables free text entry in both status and note fields
 * 4. Automatically saves custom status entries to localStorage
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('Enhanced status entry script loaded');
    
    // Find all status dropdowns in the screening checklist
    const statusSelects = document.querySelectorAll('.screening-status-select');
    
    // Check if custom status option is enabled in settings
    const customStatusEnabled = document.querySelector('#status_custom') ? 
                               document.querySelector('#status_custom').checked : 
                               true; // Default to enabled if not in settings page
    
    if (!customStatusEnabled && window.location.pathname.includes('checklist-settings')) {
        console.log('Custom status not enabled in settings');
        return; // Skip enhancement if we're on settings page and it's disabled
    }
    
    statusSelects.forEach(function(select) {
        // Create a hidden input field that will store the custom value
        const hiddenInput = document.createElement('input');
        hiddenInput.type = 'text';
        hiddenInput.className = 'form-control form-control-sm custom-status-input';
        hiddenInput.style.display = 'none';
        hiddenInput.placeholder = 'Type custom status here...';
        
        // Insert the hidden input after the select
        select.parentNode.insertBefore(hiddenInput, select.nextSibling);
        
        // Store a reference to the original select
        hiddenInput.dataset.selectId = select.id;
        
        // Get the patient ID from the page
        const patientId = document.body.getAttribute('data-patient-id') || 
                         window.location.pathname.split('/')[2];
        
        // Storage keys for this dropdown
        const customValueKey = `patient_${patientId}_${select.id}_custom_value`;
        const isCustomKey = `patient_${patientId}_${select.id}_is_custom`;
        
        // Find the corresponding note field (if exists)
        const itemIndex = select.id.replace('screening_status_', '');
        const noteField = document.getElementById(`screening_note_${itemIndex}`);
        
        // Load saved values if they exist
        const savedCustomValue = localStorage.getItem(customValueKey);
        const isCustom = localStorage.getItem(isCustomKey) === 'true';
        
        if (savedCustomValue && isCustom) {
            // Show the custom input instead of the dropdown
            select.style.display = 'none';
            hiddenInput.style.display = 'block';
            hiddenInput.value = savedCustomValue;
        }
        
        // Double-click to directly enter custom status
        select.addEventListener('dblclick', function(e) {
            activateCustomInput(select, hiddenInput, noteField);
        });
        
        // Right-click for context menu option
        select.addEventListener('contextmenu', function(e) {
            e.preventDefault();
            activateCustomInput(select, hiddenInput, noteField);
        });
        
        // Handle status dropdown change
        select.addEventListener('change', function(e) {
            if (this.value === 'custom') {
                // If "custom" is selected, activate the custom input
                activateCustomInput(select, hiddenInput, noteField);
            } else if (this.value) {
                // For other selections, store the value and deactivate custom mode
                localStorage.setItem(isCustomKey, 'false');
                localStorage.removeItem(customValueKey);
                
                // Reset note field styling if it was in custom mode
                if (noteField) {
                    noteField.classList.remove('custom-status-active');
                    noteField.placeholder = 'Add note...';
                    
                    // If note field is empty, set a default note based on the selected status
                    if (!noteField.value.trim()) {
                        noteField.placeholder = `Add note for ${this.value.replace('_', ' ')}...`;
                    }
                }
            }
        });
        
        // Handle input blur (when user finishes typing)
        hiddenInput.addEventListener('blur', function() {
            // Find the parent row to manage custom mode
            const rowElement = select.closest('.screening-row');
            
            if (this.value.trim()) {
                // Save the custom value
                localStorage.setItem(customValueKey, this.value);
                localStorage.setItem(isCustomKey, 'true');
                
                // Ensure row stays in custom mode
                if (rowElement) {
                    rowElement.classList.add('custom-mode');
                }
            } else {
                // If no text was entered, revert to select dropdown
                this.style.display = 'none';
                select.style.display = 'block';
                select.value = '';
                localStorage.removeItem(customValueKey);
                localStorage.removeItem(isCustomKey);
                
                // Reset note field styling
                if (noteField) {
                    noteField.classList.remove('custom-status-active');
                    noteField.placeholder = 'Add note...';
                }
                
                // Remove custom mode from row if note field is empty too
                if (rowElement && (!noteField || !noteField.value.trim())) {
                    rowElement.classList.remove('custom-mode');
                }
            }
        });
        
        // Handle input keydown (for pressing Enter)
        hiddenInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === 'Escape') {
                this.blur();
            }
        });
        
        // Make note field active for custom entry when in custom mode
        if (noteField) {
            // Style the note field when in focus to indicate it's for custom entry
            noteField.addEventListener('focus', function() {
                const isCustomActive = select.style.display === 'none' || select.value === 'custom';
                if (isCustomActive) {
                    this.classList.add('custom-status-active');
                    this.placeholder = 'Add details for custom status...';
                    
                    // Find the parent row to highlight in custom mode
                    const rowElement = this.closest('.screening-row');
                    if (rowElement) {
                        rowElement.classList.add('custom-mode');
                    }
                }
            });
            
            // Handle when user is typing in the note field
            noteField.addEventListener('input', function() {
                const isCustomActive = select.style.display === 'none' || select.value === 'custom';
                if (isCustomActive && this.value.trim()) {
                    // If we're in custom mode and adding text to the note, save to storage
                    const patientId = document.body.getAttribute('data-patient-id') || 
                                    window.location.pathname.split('/')[2];
                    const noteKey = `patient_${patientId}_${this.id}_note`;
                    localStorage.setItem(noteKey, this.value);
                }
            });
            
            // Add special handling for note field when custom status is active
            noteField.addEventListener('blur', function() {
                const isCustomActive = select.style.display === 'none' || select.value === 'custom';
                const rowElement = this.closest('.screening-row');
                
                if (!isCustomActive) {
                    this.classList.remove('custom-status-active');
                    
                    // Remove custom mode if no longer active
                    if (rowElement && !hiddenInput.value.trim()) {
                        rowElement.classList.remove('custom-mode');
                    }
                } else if (!this.value.trim() && !hiddenInput.value.trim()) {
                    // If both fields are empty, exit custom mode completely
                    this.classList.remove('custom-status-active');
                    this.placeholder = 'Add note...';
                    
                    // Reset select dropdown if no values in either field
                    hiddenInput.style.display = 'none';
                    select.style.display = 'block';
                    select.value = '';
                    
                    // Remove custom highlighting
                    if (rowElement) {
                        rowElement.classList.remove('custom-mode');
                    }
                }
                
                // If note is empty, reset placeholder based on mode
                if (!this.value.trim()) {
                    if (isCustomActive && hiddenInput.value.trim()) {
                        this.placeholder = 'Add details for custom status...';
                    } else {
                        this.placeholder = 'Add note...';
                    }
                }
            });
            
            // Load saved note values if they exist
            const noteKey = `patient_${patientId}_${noteField.id}_note`;
            const savedNote = localStorage.getItem(noteKey);
            if (savedNote) {
                noteField.value = savedNote;
                
                // If this is a custom entry (status is hidden), apply custom styling to note
                if (isCustom) {
                    noteField.classList.add('custom-status-active');
                    
                    // Add custom mode to row
                    const rowElement = select.closest('.screening-row');
                    if (rowElement) {
                        rowElement.classList.add('custom-mode');
                    }
                }
            }
        }
    });
    
    // Helper function to activate custom input
    function activateCustomInput(select, input, noteField) {
        // Show custom input instead of dropdown
        select.style.display = 'none';
        input.style.display = 'block';
        input.focus();
        
        // Find the parent row to highlight it in custom mode
        const rowElement = select.closest('.screening-row');
        if (rowElement) {
            rowElement.classList.add('custom-mode');
        }
        
        // If there's a note field, mark it as being in custom mode
        if (noteField) {
            noteField.classList.add('custom-status-active');
            noteField.placeholder = 'Add details for custom status...';
        }
    }
    
    // Add logic for the reset button
    const resetButton = document.getElementById('reset-checkboxes');
    if (resetButton) {
        resetButton.addEventListener('click', function(e) {
            // Reset all custom inputs
            const customInputs = document.querySelectorAll('.custom-status-input');
            const noteFields = document.querySelectorAll('.screening-note');
            const customRows = document.querySelectorAll('.screening-row.custom-mode');
            const patientId = document.body.getAttribute('data-patient-id') || 
                            window.location.pathname.split('/')[2];
            
            customInputs.forEach(function(input) {
                // Hide the custom input
                input.style.display = 'none';
                input.value = '';
                
                // Show the select
                const selectElement = document.getElementById(input.dataset.selectId);
                selectElement.style.display = 'block';
                selectElement.value = '';
                
                // Clear storage
                localStorage.removeItem(`patient_${patientId}_${input.dataset.selectId}_custom_value`);
                localStorage.removeItem(`patient_${patientId}_${input.dataset.selectId}_is_custom`);
            });
            
            // Reset note fields styling
            noteFields.forEach(function(noteField) {
                noteField.classList.remove('custom-status-active');
                noteField.placeholder = 'Add note...';
            });
            
            // Remove custom mode from rows
            customRows.forEach(function(row) {
                row.classList.remove('custom-mode');
            });
        });
    }
    
    // Add tooltip to dropdowns to inform about custom entry
    statusSelects.forEach(function(select) {
        select.title = "Select 'Custom' or double-click for free text entry";
    });
});