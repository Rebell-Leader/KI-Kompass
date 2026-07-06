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

    // Initialize tab functionality if elements exist
    const tabElements = document.querySelectorAll('[data-tab]');
    if (tabElements.length > 0) {
        tabElements.forEach(function(tab) {
            if (tab && typeof tab.addEventListener === 'function') {
                tab.addEventListener('click', function() {
                    // Tab click handling
                    console.log('Tab clicked:', this.dataset.tab);
                });
            }
        });
    }
});

/**
 * Initialize flash message functionality
 */
function initFlashMessages() {
    // Auto-hide flash messages after 5 seconds
    const flashMessages = document.querySelectorAll('.alert');
    flashMessages.forEach(function(message) {
        if (message) {
            // Add close button if not present
            if (!message.querySelector('.close-btn')) {
                const closeBtn = document.createElement('button');
                closeBtn.innerHTML = '×';
                closeBtn.className = 'close-btn';
                closeBtn.style.cssText = 'float: right; background: none; border: none; font-size: 20px; cursor: pointer; color: inherit;';
                closeBtn.onclick = function() {
                    hideFlashMessage(message);
                };
                message.insertBefore(closeBtn, message.firstChild);
            }

            // Auto-hide after 5 seconds
            setTimeout(function() {
                hideFlashMessage(message);
            }, 5000);
        }
    });
}

function hideFlashMessage(message) {
    if (message && message.parentNode) {
        message.style.opacity = '0';
        message.style.transition = 'opacity 0.3s';
        setTimeout(function() {
            if (message.parentNode) {
                message.parentNode.removeChild(message);
            }
        }, 300);
    }
}

function showFlashMessage(text, type = 'info') {
    const alertClass = type === 'error' ? 'alert-danger' : 
                     type === 'success' ? 'alert-success' : 
                     type === 'warning' ? 'alert-warning' : 'alert-info';

    const messageDiv = document.createElement('div');
    messageDiv.className = `alert ${alertClass}`;
    messageDiv.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 1000; min-width: 300px;';
    messageDiv.innerHTML = text;

    document.body.appendChild(messageDiv);

    // Auto-hide and add close functionality
    const closeBtn = document.createElement('button');
    closeBtn.innerHTML = '×';
    closeBtn.className = 'close-btn';
    closeBtn.style.cssText = 'float: right; background: none; border: none; font-size: 20px; cursor: pointer; color: inherit; margin-left: 10px;';
    closeBtn.onclick = function() {
        hideFlashMessage(messageDiv);
    };
    messageDiv.insertBefore(closeBtn, messageDiv.firstChild);

    setTimeout(function() {
        hideFlashMessage(messageDiv);
    }, 5000);
}

/**
 * Initialize tooltip functionality
 */
function initTooltips() {
    const tooltipElements = document.querySelectorAll('[data-tooltip]');
    tooltipElements.forEach(function(element) {
        if (element) {
            element.addEventListener('mouseenter', function() {
                const tooltipText = this.dataset.tooltip;
                if (tooltipText) {
                    const tooltip = document.createElement('div');
                    tooltip.className = 'tooltip';
                    tooltip.textContent = tooltipText;
                    tooltip.style.cssText = 'position: absolute; background: #333; color: white; padding: 5px 10px; border-radius: 4px; font-size: 12px; z-index: 1000; pointer-events: none;';
                    document.body.appendChild(tooltip);

                    const rect = this.getBoundingClientRect();
                    tooltip.style.left = (rect.left + rect.width / 2 - tooltip.offsetWidth / 2) + 'px';
                    tooltip.style.top = (rect.top - tooltip.offsetHeight - 5) + 'px';

                    this.tooltip = tooltip;
                }
            });

            element.addEventListener('mouseleave', function() {
                if (this.tooltip) {
                    document.body.removeChild(this.tooltip);
                    this.tooltip = null;
                }
            });
        }
    });
}

/**
 * Initialize form validation
 */
function initFormValidation() {
    const forms = document.querySelectorAll('form[data-validate]');
    forms.forEach(function(form) {
        if (form) {
            form.addEventListener('submit', function(e) {
                const requiredFields = this.querySelectorAll('[required]');
                let isValid = true;

                requiredFields.forEach(function(field) {
                    if (!field.value.trim()) {
                        isValid = false;
                        field.classList.add('error');
                        field.addEventListener('input', function() {
                            this.classList.remove('error');
                        }, { once: true });
                    }
                });

                if (!isValid) {
                    e.preventDefault();
                    showFlashMessage('Please fill in all required fields', 'error');
                }
            });
        }
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
                'X-CSRFToken': getCsrfToken(),
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
                'X-CSRFToken': getCsrfToken(),
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