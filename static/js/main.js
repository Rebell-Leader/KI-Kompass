/**
 * KI Kompass - Main JavaScript
 */

// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Flash Messages
    initFlashMessages();
    
    // Initialize Form Validation
    initFormValidation();
    
    // Initialize Tooltips
    initTooltips();
    
    // Task Management
    initTaskManagement();
});

/**
 * Initialize flash message functionality
 */
function initFlashMessages() {
    const flashMessages = document.querySelectorAll('.alert');
    
    flashMessages.forEach(message => {
        // Add close button if not present
        if (!message.querySelector('.close-btn')) {
            const closeBtn = document.createElement('button');
            closeBtn.classList.add('close-btn');
            closeBtn.innerHTML = '&times;';
            closeBtn.style.float = 'right';
            closeBtn.style.background = 'none';
            closeBtn.style.border = 'none';
            closeBtn.style.fontSize = '20px';
            closeBtn.style.cursor = 'pointer';
            closeBtn.style.marginLeft = '15px';
            message.prepend(closeBtn);
            
            closeBtn.addEventListener('click', () => {
                message.style.opacity = '0';
                setTimeout(() => {
                    message.style.display = 'none';
                }, 300);
            });
        }
        
        // Auto dismiss after 5 seconds
        setTimeout(() => {
            message.style.opacity = '0';
            setTimeout(() => {
                message.style.display = 'none';
            }, 300);
        }, 5000);
    });
}

/**
 * Initialize form validation
 */
function initFormValidation() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            const requiredFields = form.querySelectorAll('[required]');
            let isValid = true;
            
            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    isValid = false;
                    
                    // Add error styling
                    field.classList.add('is-invalid');
                    
                    // Create error message if doesn't exist
                    let errorMessage = field.parentNode.querySelector('.error-message');
                    if (!errorMessage) {
                        errorMessage = document.createElement('div');
                        errorMessage.classList.add('error-message');
                        errorMessage.style.color = '#DC3545';
                        errorMessage.style.fontSize = '14px';
                        errorMessage.style.marginTop = '4px';
                        field.parentNode.appendChild(errorMessage);
                    }
                    
                    errorMessage.textContent = `${field.getAttribute('data-error-message') || 'This field is required'}`;
                } else {
                    field.classList.remove('is-invalid');
                    const errorMessage = field.parentNode.querySelector('.error-message');
                    if (errorMessage) {
                        errorMessage.remove();
                    }
                }
            });
            
            if (!isValid) {
                event.preventDefault();
            }
        });
        
        // Live validation as user types
        const inputs = form.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            input.addEventListener('input', function() {
                if (input.hasAttribute('required') && !input.value.trim()) {
                    input.classList.add('is-invalid');
                } else {
                    input.classList.remove('is-invalid');
                    const errorMessage = input.parentNode.querySelector('.error-message');
                    if (errorMessage) {
                        errorMessage.remove();
                    }
                }
            });
        });
    });
}

/**
 * Initialize tooltips
 */
function initTooltips() {
    const tooltips = document.querySelectorAll('[data-tooltip]');
    
    tooltips.forEach(element => {
        element.style.position = 'relative';
        element.style.cursor = 'pointer';
        
        element.addEventListener('mouseenter', function() {
            const tooltip = document.createElement('div');
            tooltip.classList.add('tooltip');
            tooltip.textContent = element.getAttribute('data-tooltip');
            
            // Style the tooltip
            tooltip.style.position = 'absolute';
            tooltip.style.bottom = '100%';
            tooltip.style.left = '50%';
            tooltip.style.transform = 'translateX(-50%)';
            tooltip.style.marginBottom = '5px';
            tooltip.style.backgroundColor = '#2C3E50';
            tooltip.style.color = '#FFFFFF';
            tooltip.style.padding = '6px 10px';
            tooltip.style.borderRadius = '4px';
            tooltip.style.fontSize = '14px';
            tooltip.style.zIndex = '1000';
            tooltip.style.whiteSpace = 'nowrap';
            
            // Add arrow
            tooltip.style.boxShadow = '0 2px 4px rgba(0,0,0,0.2)';
            tooltip.style.opacity = '0';
            tooltip.style.transition = 'opacity 0.3s';
            
            element.appendChild(tooltip);
            
            // Show after a small delay to prevent flickering
            setTimeout(() => {
                tooltip.style.opacity = '1';
            }, 10);
        });
        
        element.addEventListener('mouseleave', function() {
            const tooltip = element.querySelector('.tooltip');
            if (tooltip) {
                tooltip.style.opacity = '0';
                setTimeout(() => {
                    tooltip.remove();
                }, 300);
            }
        });
    });
}

/**
 * Initialize task management functionality
 */
function initTaskManagement() {
    const taskCheckboxes = document.querySelectorAll('.task-checkbox');
    
    if (!taskCheckboxes.length) return; // Exit if no task checkboxes found
    
    taskCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            const taskId = this.getAttribute('data-task-id');
            const isCompleted = this.checked;
            
            // Get notes if there's a notes field
            let notes = '';
            const notesField = document.querySelector(`#task-notes-${taskId}`);
            if (notesField) {
                notes = notesField.value;
            }
            
            // Update UI immediately for better user experience
            const taskItem = this.closest('.step-item');
            if (taskItem) {
                if (isCompleted) {
                    taskItem.classList.add('completed');
                    const stepIcon = taskItem.querySelector('.step-icon');
                    if (stepIcon) {
                        stepIcon.classList.add('completed');
                        
                        // Add check icon
                        stepIcon.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>';
                    }
                } else {
                    taskItem.classList.remove('completed');
                    const stepIcon = taskItem.querySelector('.step-icon');
                    if (stepIcon) {
                        stepIcon.classList.remove('completed');
                        
                        // Reset icon to number
                        const taskNumber = stepIcon.getAttribute('data-number');
                        stepIcon.textContent = taskNumber || '';
                    }
                }
            }
            
            // Send task update to server
            fetch('/api/task/update', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    task_id: taskId,
                    completed: isCompleted,
                    notes: notes
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Update progress bar if it exists
                    updateProgressIndicators();
                } else {
                    console.error('Error updating task:', data.error);
                    // Revert UI changes if there was an error
                    this.checked = !isCompleted;
                    
                    if (taskItem) {
                        if (!isCompleted) {
                            taskItem.classList.add('completed');
                            const stepIcon = taskItem.querySelector('.step-icon');
                            if (stepIcon) {
                                stepIcon.classList.add('completed');
                                stepIcon.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>';
                            }
                        } else {
                            taskItem.classList.remove('completed');
                            const stepIcon = taskItem.querySelector('.step-icon');
                            if (stepIcon) {
                                stepIcon.classList.remove('completed');
                                const taskNumber = stepIcon.getAttribute('data-number');
                                stepIcon.textContent = taskNumber || '';
                            }
                        }
                    }
                }
            })
            .catch(error => {
                console.error('Error:', error);
                // Revert UI changes if there was an error
                this.checked = !isCompleted;
            });
        });
    });
    
    // Handle task notes updates
    const taskNotes = document.querySelectorAll('.task-notes');
    taskNotes.forEach(notesField => {
        notesField.addEventListener('blur', function() {
            const taskId = this.getAttribute('data-task-id');
            const notes = this.value;
            const checkbox = document.querySelector(`.task-checkbox[data-task-id="${taskId}"]`);
            const isCompleted = checkbox ? checkbox.checked : false;
            
            // Send task update to server
            fetch('/api/task/update', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    task_id: taskId,
                    completed: isCompleted,
                    notes: notes
                })
            })
            .then(response => response.json())
            .then(data => {
                if (!data.success) {
                    console.error('Error updating task notes:', data.error);
                }
            })
            .catch(error => {
                console.error('Error:', error);
            });
        });
    });
}

/**
 * Update progress indicators based on completed tasks
 */
function updateProgressIndicators() {
    // Count total and completed tasks
    const totalTasks = document.querySelectorAll('.task-checkbox').length;
    const completedTasks = document.querySelectorAll('.task-checkbox:checked').length;
    
    if (totalTasks === 0) return;
    
    const progress = Math.round((completedTasks / totalTasks) * 100);
    
    // Update progress bar
    const progressBar = document.querySelector('.progress-bar');
    if (progressBar) {
        progressBar.style.width = `${progress}%`;
        progressBar.setAttribute('aria-valuenow', progress);
    }
    
    // Update progress text
    const progressText = document.querySelector('.progress-text');
    if (progressText) {
        progressText.textContent = `${progress}%`;
    }
    
    // Update completed count
    const completedCount = document.querySelector('.completed-count');
    if (completedCount) {
        completedCount.textContent = completedTasks;
    }
    
    // Update total count
    const totalCount = document.querySelector('.total-count');
    if (totalCount) {
        totalCount.textContent = totalTasks;
    }
}
