/**
 * Checklist Settings Javascript
 * Handles interactive functionality for the prep sheet quality checklist settings page
 * Includes custom status options management for autocomplete suggestions
 */

document.addEventListener('DOMContentLoaded', function() {
    // Elements in the Display Options form
    const layoutStyle = document.querySelector('select[name="layout_style"]');
    const statusOptions = document.querySelectorAll('input[name="status_options"]');
    const showNotes = document.getElementById('show_notes');
    
    // Custom status options elements
    const customStatusInput = document.getElementById('custom_status_input');
    const addCustomStatusBtn = document.getElementById('add_custom_status');
    const customStatusList = document.getElementById('custom_status_list');
    
    // Elements in the preview
    const screeningContainer = document.querySelector('.screening-container');
    const noteCells = document.querySelectorAll('.screening-note-cell');
    const statusSelects = document.querySelectorAll('.screening-status-select');
    
    // Reset preview button
    const resetPreviewBtn = findButtonByText('Reset Preview');
    
    // Handle layout style changes
    if (layoutStyle) {
        layoutStyle.addEventListener('change', function() {
            updatePreviewLayout(this.value);
        });
    }
    
    // Handle show/hide notes toggle
    if (showNotes) {
        showNotes.addEventListener('change', function() {
            toggleNoteVisibility(this.checked);
        });
    }
    
    // Handle status options changes
    statusOptions.forEach(option => {
        option.addEventListener('change', function() {
            updateStatusOptions();
        });
    });
    
    // Reset preview button functionality
    if (resetPreviewBtn) {
        resetPreviewBtn.addEventListener('click', resetPreview);
    }
    
    // Custom status options functionality
    if (addCustomStatusBtn && customStatusInput && customStatusList) {
        // Add custom status when button is clicked
        addCustomStatusBtn.addEventListener('click', function() {
            addCustomStatus();
        });
        
        // Add custom status when Enter key is pressed in the input
        customStatusInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                addCustomStatus();
            }
        });
        
        // Handle removing custom status items
        customStatusList.addEventListener('click', function(e) {
            if (e.target.classList.contains('btn-close')) {
                const statusItem = e.target.closest('.custom-status-item');
                if (statusItem) {
                    const statusToRemove = e.target.getAttribute('data-status');
                    
                    // Remove from DOM
                    statusItem.remove();
                    updatePreviewWithCustomStatuses();
                    
                    // Also send AJAX request to remove from database for permanent removal
                    if (statusToRemove) {
                        removeCustomStatusFromDb(statusToRemove);
                    }
                }
            }
        });
    }
    
    // Function to remove custom status from database
    function removeCustomStatusFromDb(status) {
        // Create form data
        const formData = new FormData();
        formData.append('status', status);
        
        // Send AJAX request to remove status
        fetch('/checklist-settings/remove-custom-status', {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || ''
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                console.log(`Custom status "${status}" removed successfully`);
                // You could add a flash message or notification here
            } else {
                console.error(`Error removing custom status: ${data.error}`);
            }
        })
        .catch(error => {
            console.error('Error:', error);
        });
    }
    
    // Function to add a new custom status
    function addCustomStatus() {
        const statusText = customStatusInput.value.trim();
        
        // Validate input
        if (!statusText) {
            return;
        }
        
        // Check if this status already exists
        const existingStatuses = Array.from(
            customStatusList.querySelectorAll('.custom-status-item')
        ).map(item => item.textContent.trim());
        
        if (existingStatuses.includes(statusText)) {
            alert('This status option already exists');
            return;
        }
        
        // Create new status item
        const newItem = document.createElement('div');
        newItem.className = 'custom-status-item badge bg-light text-dark p-2 d-flex align-items-center';
        newItem.innerHTML = `
            ${statusText}
            <button type="button" class="btn-close btn-close-dark ms-2 shadow-sm" style="background-color: #f8d7da; padding: 4px; border-radius: 50%;" aria-label="Remove" data-status="${statusText}"></button>
            <input type="hidden" name="custom_status_options" value="${statusText}">
        `;
        
        // Add to the list
        customStatusList.appendChild(newItem);
        
        // Clear input
        customStatusInput.value = '';
        customStatusInput.focus();
        
        // Update the preview with new custom statuses
        updatePreviewWithCustomStatuses();
    }
    
    // Function to update preview with custom statuses
    function updatePreviewWithCustomStatuses() {
        // Get all custom statuses
        const customStatuses = Array.from(
            customStatusList.querySelectorAll('.custom-status-item')
        ).map(item => {
            return {
                value: item.querySelector('input').value,
                text: item.textContent.trim()
            };
        });
        
        // Update preview dropdowns
        updateCustomStatusesInPreview(customStatuses);
    }
    
    // Function to update custom statuses in preview dropdowns
    function updateCustomStatusesInPreview(customStatuses) {
        // Add to consolidated field in the preview section 
        // by updating the datalist elements in the preview
        // This would be implemented if we had a datalist preview in the settings page
        
        // For now, just log the new statuses to confirm they're being tracked
        console.log('Updated custom statuses:', customStatuses.map(s => s.text));
        
        // In a real implementation, we would update a preview datalist here
    }
    
    // Function to update preview layout based on selected style
    function updatePreviewLayout(style) {
        if (style === 'table') {
            screeningContainer.classList.add('table-style');
            screeningContainer.classList.remove('list-style');
        } else {
            screeningContainer.classList.add('list-style');
            screeningContainer.classList.remove('table-style');
        }
    }
    
    // Function to toggle visibility of note fields
    function toggleNoteVisibility(visible) {
        noteCells.forEach(cell => {
            cell.style.display = visible ? 'table-cell' : 'none';
        });
    }
    
    // Function to update available status options in dropdown
    function updateStatusOptions() {
        // Collect all selected status options
        const selectedOptions = Array.from(statusOptions)
            .filter(opt => opt.checked)
            .map(opt => opt.value);
        
        // Update all status dropdowns in the preview
        statusSelects.forEach(select => {
            // Save current selection
            const currentValue = select.value;
            
            // Clear all options except the first "Select status..." option
            while (select.options.length > 1) {
                select.remove(1);
            }
            
            // Add the selected status options
            selectedOptions.forEach(option => {
                const optionEl = document.createElement('option');
                optionEl.value = option;
                
                // Format the display text
                let displayText = '';
                switch(option) {
                    case 'due':
                        displayText = 'Due';
                        break;
                    case 'due_soon':
                        displayText = 'Due Soon';
                        break;
                    case 'sent_incomplete':
                        displayText = 'Sent & Incomplete';
                        break;
                    case 'completed':
                        displayText = 'Completed';
                        break;
                    default:
                        displayText = option;
                }
                
                optionEl.textContent = displayText;
                select.appendChild(optionEl);
            });
            
            // Try to restore the previous selection if it's still available
            if (selectedOptions.includes(currentValue)) {
                select.value = currentValue;
            }
        });
    }
    
    // Function to reset preview to default state
    function resetPreview() {
        // Reset checkboxes
        document.querySelectorAll('.screening-container .form-check-input').forEach(cb => {
            cb.checked = false;
        });
        
        // Reset status dropdowns
        statusSelects.forEach(select => {
            select.selectedIndex = 0;
        });
        
        // Reset note fields
        document.querySelectorAll('.screening-note').forEach(note => {
            note.value = '';
        });
    }
    
    // Initialize preview based on form state
    function initializePreview() {
        // Apply initial layout
        if (layoutStyle) {
            updatePreviewLayout(layoutStyle.value);
        }
        
        // Apply initial notes visibility
        if (showNotes) {
            toggleNoteVisibility(showNotes.checked);
        }
        
        // Apply initial status options
        updateStatusOptions();
        
        // Initialize custom statuses display if any exist from previous settings
        if (customStatusList && customStatusList.children.length > 0) {
            updatePreviewWithCustomStatuses();
        }
    }
    
    // Initialize the preview when the page loads
    initializePreview();
    
    // Add listener to textarea to show override notice if user types while buttons are selected
    const textarea = document.getElementById('default_items_textarea');
    const overrideNotice = document.getElementById('button-override-notice');
    
    if (textarea && overrideNotice) {
        textarea.addEventListener('input', function() {
            // Check if there are any selected screening buttons in the checklist tab
            // This would need to check the screening list page state, but for now
            // we'll show the notice if there's text and the user is typing
            if (this.value.trim()) {
                overrideNotice.style.display = 'inline';
                overrideNotice.textContent = 'Note: If screening types are selected via buttons on the screening list page, they will override this manual input.';
            } else {
                overrideNotice.style.display = 'none';
            }
        });
    }
});

// Find a button by its text content
function findButtonByText(text) {
    const buttons = document.querySelectorAll('button');
    for (let i = 0; i < buttons.length; i++) {
        if (buttons[i].textContent.trim() === text) {
            return buttons[i];
        }
    }
    return null;
}