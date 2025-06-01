/**
 * Consolidated Checklist JavaScript
 * Handles the consolidated status/notes field for the quality checklist
 * with datalist autocomplete integration
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('Consolidated checklist script loaded');

    // Common functions
    function getStorageKey(elementId) {
        // Extract patient ID from URL or data attribute
        const patientId = document.body.getAttribute('data-patient-id') || 
                         window.location.pathname.split('/')[2];
        return `patient_${patientId}_${elementId}_consolidated`;
    }

    // Status options from the datalists
    const getStatusOptions = () => {
        const options = [];
        document.querySelectorAll('datalist option').forEach(option => {
            const value = option.value;
            if (!options.includes(value)) {
                options.push(value);
            }
        });
        return options;
    };
    
    const statusOptions = getStatusOptions();
    
    // Find all consolidated fields
    const consolidatedFields = document.querySelectorAll('.screening-consolidated-field');
    
    // Load saved values for consolidated fields
    consolidatedFields.forEach(function(field) {
        const fieldId = field.id;
        const storageKey = getStorageKey(fieldId);
        const savedValue = localStorage.getItem(storageKey);
        
        if (savedValue) {
            field.value = savedValue;
            field.classList.add('has-content');
        }
        
        // Add event listener to save state on input
        field.addEventListener('input', function() {
            localStorage.setItem(storageKey, this.value);
            
            // Add/remove has-content class based on whether the field has content
            if (this.value.trim()) {
                this.classList.add('has-content');
            } else {
                this.classList.remove('has-content');
            }
        });
        
        // Add event listener for when user selects an option
        field.addEventListener('change', function() {
            const selectedValue = this.value.trim();
            
            // Check if this is one of our status options
            if (statusOptions.includes(selectedValue)) {
                // User selected a preset status
                // Focus the field again to allow for additional notes
                this.focus();
                // Move cursor to the end of the text
                const len = selectedValue.length;
                this.setSelectionRange(len, len);
                
                // Add a hyphen and space if the user types after selecting
                const originalValue = selectedValue;
                setTimeout(() => {
                    if (this.value === originalValue) {
                        // Only add the separator if the user hasn't typed yet
                        this.addEventListener('keypress', function handleFirstKeypress() {
                            // Check if the next character is already a separator
                            if (this.value.endsWith(' - ')) return;
                            
                            // Insert " - " before the character the user is typing
                            const cursorPos = this.selectionStart;
                            if (cursorPos === this.value.length) {
                                this.value = this.value + ' - ';
                                // Set cursor position after the separator
                                this.setSelectionRange(this.value.length, this.value.length);
                            }
                            
                            // Remove this event listener after first keypress
                            this.removeEventListener('keypress', handleFirstKeypress);
                        });
                    }
                }, 100);
            }
        });
        
        // Add keyboard shortcuts for quick selection
        field.addEventListener('keydown', function(e) {
            // Ctrl+Space or Alt+Space to show the dropdown
            if ((e.ctrlKey || e.altKey) && e.key === ' ') {
                e.preventDefault();
                this.focus();
                
                // Create and dispatch a keyboard event to open the dropdown
                const downEvent = new KeyboardEvent('keydown', {
                    key: 'ArrowDown',
                    code: 'ArrowDown',
                    keyCode: 40,
                    bubbles: true
                });
                this.dispatchEvent(downEvent);
            }
        });
    });
    
    // Add context menu functionality for frequently used terms
    consolidatedFields.forEach(function(field) {
        field.addEventListener('contextmenu', function(e) {
            // Prevent default context menu
            e.preventDefault();
            
            // Create a custom context menu with common phrases
            let menu = document.getElementById('custom-context-menu');
            if (!menu) {
                menu = document.createElement('div');
                menu.id = 'custom-context-menu';
                menu.className = 'custom-context-menu';
                document.body.appendChild(menu);
                
                // Add styles if not already present
                if (!document.getElementById('context-menu-styles')) {
                    const style = document.createElement('style');
                    style.id = 'context-menu-styles';
                    style.textContent = `
                        .custom-context-menu {
                            position: absolute;
                            z-index: 1000;
                            background: white;
                            border: 1px solid #ccc;
                            border-radius: 4px;
                            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                            padding: 5px 0;
                            min-width: 150px;
                        }
                        .custom-context-menu-item {
                            padding: 8px 12px;
                            cursor: pointer;
                        }
                        .custom-context-menu-item:hover {
                            background-color: rgba(var(--bs-primary-rgb), 0.1);
                        }
                        .context-menu-divider {
                            height: 1px;
                            background: #e5e5e5;
                            margin: 5px 0;
                        }
                    `;
                    document.head.appendChild(style);
                }
            }
            
            // Clear any existing menu content
            menu.innerHTML = '';
            
            // Add status options to menu
            statusOptions.forEach(option => {
                const menuItem = document.createElement('div');
                menuItem.className = 'custom-context-menu-item';
                menuItem.textContent = option;
                menuItem.addEventListener('click', function() {
                    // If the field is empty, set value to the option
                    if (!field.value.trim()) {
                        field.value = option;
                    } else {
                        // If field already has status content and has a separator, replace the status
                        if (field.value.includes(' - ')) {
                            const parts = field.value.split(' - ');
                            parts[0] = option;
                            field.value = parts.join(' - ');
                        } else {
                            // Replace entire value if likely a status or add as new status with notes
                            if (statusOptions.includes(field.value.trim())) {
                                field.value = option;
                            } else {
                                field.value = option + ' - ' + field.value;
                            }
                        }
                    }
                    
                    // Save to localStorage
                    localStorage.setItem(getStorageKey(field.id), field.value);
                    field.classList.add('has-content');
                    
                    // Hide menu
                    menu.style.display = 'none';
                });
                menu.appendChild(menuItem);
            });
            
            // Add common notes section
            const divider = document.createElement('div');
            divider.className = 'context-menu-divider';
            menu.appendChild(divider);
            
            // Common phrases to quickly add as notes
            const commonPhrases = [
                "Due this month",
                "Patient declined",
                "Sent letter",
                "Follow up required",
                "Clear all",
            ];
            
            commonPhrases.forEach(phrase => {
                const menuItem = document.createElement('div');
                menuItem.className = 'custom-context-menu-item';
                menuItem.textContent = phrase;
                menuItem.addEventListener('click', function() {
                    if (phrase === "Clear all") {
                        field.value = '';
                        field.classList.remove('has-content');
                    } else if (!field.value.trim()) {
                        field.value = phrase;
                    } else if (field.value.includes(' - ')) {
                        // If there's already a status with separator, add/replace the note
                        const parts = field.value.split(' - ');
                        parts[1] = phrase;
                        field.value = parts.join(' - ');
                    } else if (statusOptions.includes(field.value.trim())) {
                        // If current value is a status, add phrase as note
                        field.value = field.value + ' - ' + phrase;
                    } else {
                        // Otherwise append to existing content
                        field.value = field.value + (field.value.endsWith('.') ? ' ' : '. ') + phrase;
                    }
                    
                    // Save to localStorage
                    localStorage.setItem(getStorageKey(field.id), field.value);
                    
                    if (field.value.trim()) {
                        field.classList.add('has-content');
                    } else {
                        field.classList.remove('has-content');
                    }
                    
                    // Hide menu
                    menu.style.display = 'none';
                });
                menu.appendChild(menuItem);
            });
            
            // Position the menu
            menu.style.top = `${e.pageY}px`;
            menu.style.left = `${e.pageX}px`;
            menu.style.display = 'block';
            
            // Hide the menu when clicking elsewhere
            const hideMenu = function() {
                menu.style.display = 'none';
                document.removeEventListener('click', hideMenu);
            };
            
            // Add a small delay to prevent immediate closing
            setTimeout(() => {
                document.addEventListener('click', hideMenu);
            }, 100);
        });
    });
    
    // Reset checkboxes button
    const resetButton = document.getElementById('reset-checkboxes');
    if (resetButton) {
        resetButton.addEventListener('click', function() {
            // Clear consolidated fields
            consolidatedFields.forEach(function(field) {
                field.value = '';
                field.classList.remove('has-content');
                localStorage.removeItem(getStorageKey(field.id));
            });
        });
    }
    
    // Handle save prep sheet button
    const saveButton = document.getElementById('save-prep-sheet');
    if (saveButton) {
        saveButton.addEventListener('click', function() {
            const patientId = document.body.getAttribute('data-patient-id') || 
                             window.location.pathname.split('/')[2];
            
            // Collect all screening data
            const checkboxes = document.querySelectorAll('.form-check-input');
            const checkedItems = [];
            const screeningData = [];
            
            checkboxes.forEach(function(checkbox, index) {
                if (checkbox.checked) {
                    // Find the corresponding consolidated field
                    const consolidatedField = document.getElementById(`screening_status_note_${index + 1}`);
                    const screeningText = checkbox.nextElementSibling.textContent.trim();
                    
                    checkedItems.push(screeningText);
                    
                    // Add to screening data with status and notes parsed from the consolidated field
                    let status = '';
                    let notes = '';
                    
                    if (consolidatedField && consolidatedField.value) {
                        // Try to extract status and notes if there's a divider
                        if (consolidatedField.value.includes(' - ')) {
                            const parts = consolidatedField.value.split(' - ');
                            status = parts[0].trim();
                            notes = parts.slice(1).join(' - ').trim();
                        } else {
                            // If no divider, assume it's all status
                            status = consolidatedField.value.trim();
                        }
                    }
                    
                    screeningData.push({
                        item: screeningText,
                        status: status,
                        notes: notes,
                        consolidated: consolidatedField ? consolidatedField.value : ''
                    });
                }
            });
            
            // Send data to backend to save as document
            fetch(`/patients/${patientId}/save_prep_sheet`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || ''
                },
                body: JSON.stringify({
                    patient_id: patientId,
                    date: document.querySelector('[data-current-date]')?.getAttribute('data-current-date') || '',
                    checked_screenings: checkedItems,
                    screening_data: screeningData
                })
            })
            .then(response => {
                if (response.ok) {
                    return response.json();
                }
                throw new Error('Failed to save prep sheet');
            })
            .then(data => {
                alert('Prep sheet saved successfully!');
                window.location.href = `/patients/${patientId}`;
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error saving prep sheet. Please try again.');
            });
        });
    }
});