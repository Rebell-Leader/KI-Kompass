/**
 * KI Kompass - Pipeline JavaScript
 */

// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    initPipeline();
});

/**
 * Initialize pipeline functionality
 */
function initPipeline() {
    // Initialize filters
    initializeFilters();
    
    // Initialize task details expansion
    initTaskDetails();
    
    // Initialize task sorting
    initTaskSorting();
    
    // Initialize task timeline view
    initTimelineView();
    
    // Initialize task checkbox functionality
    initTaskCheckboxes();
    
    // Initialize optional tasks functionality
    initOptionalTasks();
    
    // Initialize pipeline regeneration
    initPipelineRegeneration();
}

/**
 * Initialize pipeline filters
 */
function initializeFilters() {
    const filterButtons = document.querySelectorAll('.filter-btn');
    const tasks = document.querySelectorAll('.step-item');
    
    if (!filterButtons.length || !tasks.length) return;
    
    filterButtons.forEach(button => {
        button.addEventListener('click', function() {
            // Remove active class from all buttons
            filterButtons.forEach(btn => btn.classList.remove('active'));
            
            // Add active class to clicked button
            this.classList.add('active');
            
            const filter = this.getAttribute('data-filter');
            
            tasks.forEach(task => {
                // If 'all' filter or task category matches filter
                if (filter === 'all') {
                    task.style.display = '';
                } else if (filter === 'completed' && task.classList.contains('completed')) {
                    task.style.display = '';
                } else if (filter === 'pending' && !task.classList.contains('completed')) {
                    task.style.display = '';
                } else if (task.getAttribute('data-category') === filter) {
                    task.style.display = '';
                } else {
                    task.style.display = 'none';
                }
            });
            
            // Update "no tasks" message
            updateNoTasksMessage(filter);
        });
    });
}

/**
 * Update the "no tasks" message based on visible tasks
 * @param {string} filter - The current active filter
 */
function updateNoTasksMessage(filter) {
    const visibleTasks = document.querySelectorAll('.step-item[style=""]').length;
    let messageContainer = document.querySelector('.no-tasks-message');
    
    if (visibleTasks === 0) {
        if (!messageContainer) {
            messageContainer = document.createElement('div');
            messageContainer.classList.add('no-tasks-message', 'alert', 'alert-info', 'mt-3');
            
            const taskList = document.querySelector('.step-list');
            if (taskList) {
                taskList.appendChild(messageContainer);
            }
        }
        
        let message = 'No tasks found';
        switch (filter) {
            case 'completed':
                message = 'No completed tasks found. Keep going!';
                break;
            case 'pending':
                message = 'No pending tasks. Great job!';
                break;
            default:
                message = `No tasks found in category "${filter}"`;
        }
        
        messageContainer.textContent = message;
        messageContainer.style.display = 'block';
    } else if (messageContainer) {
        messageContainer.style.display = 'none';
    }
}

/**
 * Initialize task details expand/collapse functionality
 */
function initTaskDetails() {
    const taskHeaders = document.querySelectorAll('.step-title');
    
    taskHeaders.forEach(header => {
        header.addEventListener('click', function() {
            const task = this.closest('.step-item');
            const details = task.querySelector('.step-details');
            
            if (!details) return;
            
            // Toggle details visibility
            if (details.style.display === 'none' || !details.style.display) {
                details.style.display = 'block';
                this.classList.add('expanded');
                
                // Animate height
                const height = details.scrollHeight;
                details.style.height = '0';
                details.style.overflow = 'hidden';
                details.style.transition = 'height 0.3s ease';
                
                setTimeout(() => {
                    details.style.height = height + 'px';
                }, 10);
                
                setTimeout(() => {
                    details.style.height = '';
                    details.style.overflow = '';
                }, 300);
            } else {
                // Animate height closing
                const height = details.scrollHeight;
                details.style.height = height + 'px';
                details.style.overflow = 'hidden';
                details.style.transition = 'height 0.3s ease';
                
                setTimeout(() => {
                    details.style.height = '0';
                }, 10);
                
                setTimeout(() => {
                    details.style.display = 'none';
                    details.style.height = '';
                    details.style.overflow = '';
                    this.classList.remove('expanded');
                }, 300);
            }
        });
    });
}

/**
 * Initialize task sorting functionality
 */
function initTaskSorting() {
    const sortSelect = document.getElementById('sort-tasks');
    
    if (!sortSelect) return;
    
    sortSelect.addEventListener('change', function() {
        const sortValue = this.value;
        const tasksList = document.querySelector('.step-list');
        const tasks = Array.from(document.querySelectorAll('.step-item'));
        
        if (!tasksList || !tasks.length) return;
        
        // Sort tasks based on selected option
        tasks.sort((a, b) => {
            switch (sortValue) {
                case 'priority':
                    const priorityA = parseInt(a.getAttribute('data-priority') || '3');
                    const priorityB = parseInt(b.getAttribute('data-priority') || '3');
                    return priorityA - priorityB;
                    
                case 'deadline':
                    const deadlineA = new Date(a.getAttribute('data-deadline') || '9999-12-31');
                    const deadlineB = new Date(b.getAttribute('data-deadline') || '9999-12-31');
                    return deadlineA - deadlineB;
                    
                case 'timeline':
                    const timelineA = parseInt(a.getAttribute('data-timeline') || '0');
                    const timelineB = parseInt(b.getAttribute('data-timeline') || '0');
                    return timelineA - timelineB;
                    
                default:
                    // Default to original order
                    const indexA = parseInt(a.getAttribute('data-index') || '0');
                    const indexB = parseInt(b.getAttribute('data-index') || '0');
                    return indexA - indexB;
            }
        });
        
        // Reappend tasks in sorted order
        tasks.forEach(task => tasksList.appendChild(task));
    });
}

/**
 * Initialize timeline view
 */
function initTimelineView() {
    const timelineToggle = document.getElementById('view-timeline');
    const listToggle = document.getElementById('view-list');
    
    if (!timelineToggle || !listToggle) return;
    
    const taskList = document.querySelector('.step-list');
    const timelineView = document.querySelector('.timeline-view');
    
    if (!taskList || !timelineView) return;
    
    timelineToggle.addEventListener('click', function(e) {
        e.preventDefault();
        
        timelineToggle.classList.add('active');
        listToggle.classList.remove('active');
        
        // Hide task list, show timeline
        taskList.style.display = 'none';
        timelineView.style.display = 'block';
        
        // Generate timeline if needed
        generateTimeline();
    });
    
    listToggle.addEventListener('click', function(e) {
        e.preventDefault();
        
        listToggle.classList.add('active');
        timelineToggle.classList.remove('active');
        
        // Show task list, hide timeline
        taskList.style.display = 'block';
        timelineView.style.display = 'none';
    });
}

/**
 * Initialize task checkbox functionality
 */
function initTaskCheckboxes() {
    const taskCheckboxes = document.querySelectorAll('.task-checkbox');
    const taskNotes = document.querySelectorAll('.task-notes');
    
    taskCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            const taskId = this.getAttribute('data-task-id');
            const completed = this.checked;
            
            updateTaskStatus(taskId, completed);
        });
    });
    
    taskNotes.forEach(noteField => {
        noteField.addEventListener('blur', function() {
            const taskId = this.getAttribute('data-task-id');
            const notes = this.value;
            const checkbox = document.querySelector(`.task-checkbox[data-task-id="${taskId}"]`);
            const completed = checkbox ? checkbox.checked : false;
            
            updateTaskStatus(taskId, completed, notes);
        });
    });
}

/**
 * Update task status in backend
 */
function updateTaskStatus(taskId, completed, notes = '') {
    const taskItem = document.querySelector(`.step-item[data-task-id="${taskId}"]`);
    if (!taskItem) return;
    
    fetch('/api/task/update', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            task_id: taskId,
            completed: completed,
            notes: notes
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            if (completed) {
                taskItem.classList.add('completed');
            } else {
                taskItem.classList.remove('completed');
            }
            
            // Update progress indicators
            updateProgressIndicators();
        } else {
            console.error('Failed to update task:', data.error);
            // Revert checkbox state
            const checkbox = document.querySelector(`.task-checkbox[data-task-id="${taskId}"]`);
            if (checkbox) {
                checkbox.checked = !completed;
            }
            
            // Show error message
            showToast('Error updating task status', 'danger');
        }
    })
    .catch(error => {
        console.error('Error updating task:', error);
        showToast('Error updating task status', 'danger');
    });
}

/**
 * Update UI progress indicators
 */
function updateProgressIndicators() {
    const totalTasks = document.querySelectorAll('.task-checkbox').length;
    const completedTasks = document.querySelectorAll('.task-checkbox:checked').length;
    
    if (totalTasks === 0) return;
    
    const progressPercentage = Math.round((completedTasks / totalTasks) * 100);
    
    // Update progress bar
    const progressBar = document.querySelector('.progress-bar');
    if (progressBar) {
        progressBar.style.width = `${progressPercentage}%`;
        progressBar.setAttribute('aria-valuenow', progressPercentage);
    }
    
    // Update progress text
    const progressText = document.querySelector('.progress-text');
    if (progressText) {
        progressText.textContent = `${progressPercentage}%`;
    }
    
    // Update stats card
    const completedStatsValue = document.querySelector('.dashboard-stats .stat-value:nth-child(1)');
    if (completedStatsValue) {
        completedStatsValue.textContent = `${progressPercentage}%`;
    }
    
    const completedTasksValue = document.querySelector('.dashboard-stats .stat-value:nth-child(3)');
    if (completedTasksValue) {
        completedTasksValue.textContent = completedTasks;
    }
    
    const pendingTasksValue = document.querySelector('.dashboard-stats .stat-value:nth-child(5)');
    if (pendingTasksValue) {
        pendingTasksValue.textContent = totalTasks - completedTasks;
    }
}

/**
 * Initialize optional tasks functionality
 */
function initOptionalTasks() {
    const addTasksButton = document.getElementById('add-optional-tasks');
    if (!addTasksButton) return;
    
    // Open modal with available optional tasks
    addTasksButton.addEventListener('click', function() {
        const modal = document.getElementById('optionalTasksModal');
        if (!modal) return;
        
        // Show loading state
        const loadingEl = document.getElementById('optional-tasks-loading');
        const containerEl = document.getElementById('optional-tasks-container');
        const noTasksEl = document.getElementById('no-optional-tasks');
        const errorEl = document.getElementById('optional-tasks-error');
        
        if (loadingEl) loadingEl.style.display = 'block';
        if (containerEl) containerEl.style.display = 'none';
        if (noTasksEl) noTasksEl.style.display = 'none';
        if (errorEl) errorEl.style.display = 'none';
        
        // Fetch optional tasks
        fetch('/api/tasks/optional')
            .then(response => response.json())
            .then(data => {
                if (loadingEl) loadingEl.style.display = 'none';
                
                if (data.success) {
                    if (data.tasks && data.tasks.length > 0) {
                        renderOptionalTasks(data.tasks);
                        if (containerEl) containerEl.style.display = 'block';
                    } else {
                        if (noTasksEl) noTasksEl.style.display = 'block';
                    }
                } else {
                    if (errorEl) {
                        errorEl.textContent = data.error || 'Failed to load optional tasks';
                        errorEl.style.display = 'block';
                    }
                }
            })
            .catch(error => {
                if (loadingEl) loadingEl.style.display = 'none';
                if (errorEl) {
                    errorEl.textContent = 'Error loading optional tasks';
                    errorEl.style.display = 'block';
                }
                console.error('Error fetching optional tasks:', error);
            });
        
        // Show modal
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    });
    
    // Handle adding selected tasks
    const addSelectedButton = document.getElementById('add-selected-tasks');
    if (addSelectedButton) {
        addSelectedButton.addEventListener('click', function() {
            const selectedTasks = document.querySelectorAll('.optional-task-item input:checked');
            if (!selectedTasks.length) return;
            
            // Disable button while processing
            addSelectedButton.disabled = true;
            addSelectedButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Adding...';
            
            // Track progress
            let tasksAdded = 0;
            let tasksToAdd = selectedTasks.length;
            
            // Add each selected task
            selectedTasks.forEach(checkbox => {
                const taskId = checkbox.value;
                
                fetch('/api/tasks/add', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ task_id: taskId })
                })
                .then(response => response.json())
                .then(data => {
                    tasksAdded++;
                    
                    // Mark task as added in UI
                    const taskItem = checkbox.closest('.optional-task-item');
                    if (taskItem) {
                        taskItem.classList.add('added');
                        taskItem.querySelector('input').disabled = true;
                    }
                    
                    // When all tasks are added, close modal and refresh page
                    if (tasksAdded === tasksToAdd) {
                        showToast('Tasks added successfully', 'success');
                        setTimeout(() => {
                            window.location.reload();
                        }, 1000);
                    }
                })
                .catch(error => {
                    console.error('Error adding task:', error);
                    tasksAdded++;
                    
                    if (tasksAdded === tasksToAdd) {
                        addSelectedButton.disabled = false;
                        addSelectedButton.textContent = 'Add Selected Tasks';
                        showToast('Some tasks could not be added', 'warning');
                    }
                });
            });
        });
    }
}

/**
 * Render optional tasks in the modal
 */
function renderOptionalTasks(tasks) {
    const container = document.getElementById('optional-tasks-container');
    if (!container) return;
    
    container.innerHTML = '';
    
    // Create task items
    tasks.forEach(task => {
        const taskElement = document.createElement('div');
        taskElement.classList.add('optional-task-item', 'card', 'mb-3');
        
        // Determine priority class
        let priorityBadge = '<span class="badge badge-warning">Medium Priority</span>';
        if (task.priority === 1) {
            priorityBadge = '<span class="badge badge-danger">High Priority</span>';
        } else if (task.priority === 3) {
            priorityBadge = '<span class="badge badge-info">Low Priority</span>';
        }
        
        taskElement.innerHTML = `
            <div class="card-body">
                <div class="form-check mb-2">
                    <input type="checkbox" class="form-check-input" id="task-option-${task.id}" value="${task.id}">
                    <label class="form-check-label" for="task-option-${task.id}">
                        <strong>${task.title}</strong>
                    </label>
                </div>
                <p class="mb-2">${task.description}</p>
                <div class="task-meta">
                    <span class="badge badge-primary">${task.category}</span>
                    ${priorityBadge}
                    <span class="badge badge-secondary">${task.estimated_time}</span>
                </div>
            </div>
        `;
        
        container.appendChild(taskElement);
        
        // Add event listener for checkbox
        const checkbox = taskElement.querySelector('input[type="checkbox"]');
        checkbox.addEventListener('change', updateSelectedTasksCount);
    });
    
    // Enable/disable add button based on selection
    updateSelectedTasksCount();
}

/**
 * Update the selected tasks count and button state
 */
function updateSelectedTasksCount() {
    const selectedTasks = document.querySelectorAll('.optional-task-item input:checked');
    const addButton = document.getElementById('add-selected-tasks');
    
    if (addButton) {
        if (selectedTasks.length > 0) {
            addButton.disabled = false;
            addButton.textContent = `Add Selected Tasks (${selectedTasks.length})`;
        } else {
            addButton.disabled = true;
            addButton.textContent = 'Add Selected Tasks';
        }
    }
}

/**
 * Initialize pipeline regeneration
 */
function initPipelineRegeneration() {
    const regenerateButton = document.getElementById('regenerate-pipeline');
    if (!regenerateButton) return;
    
    regenerateButton.addEventListener('click', function() {
        const modal = document.getElementById('regeneratePipelineModal');
        if (modal) {
            // Show modal using Bootstrap 5 API
            const modalInstance = new bootstrap.Modal(modal);
            modalInstance.show();
        }
    });
    
    const confirmButton = document.getElementById('confirm-regenerate');
    if (confirmButton) {
        confirmButton.addEventListener('click', function() {
            // Show loading state
            confirmButton.disabled = true;
            confirmButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Regenerating...';
            
            // Call API to regenerate pipeline
            fetch('/api/pipeline/regenerate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showToast('Pipeline regenerated successfully', 'success');
                    
                    // Reload page to show new pipeline
                    setTimeout(() => {
                        window.location.reload();
                    }, 1000);
                } else {
                    confirmButton.disabled = false;
                    confirmButton.textContent = 'Regenerate Pipeline';
                    showToast(data.error || 'Failed to regenerate pipeline', 'danger');
                }
            })
            .catch(error => {
                console.error('Error regenerating pipeline:', error);
                confirmButton.disabled = false;
                confirmButton.textContent = 'Regenerate Pipeline';
                showToast('Error regenerating pipeline', 'danger');
            });
        });
    }
}

/**
 * Show a toast message
 */
function showToast(message, type = 'info') {
    const toastContainer = document.querySelector('.toast-container');
    
    // Create container if it doesn't exist
    if (!toastContainer) {
        const container = document.createElement('div');
        container.classList.add('toast-container', 'position-fixed', 'bottom-0', 'end-0', 'p-3');
        document.body.appendChild(container);
    }
    
    // Create toast
    const toastElement = document.createElement('div');
    toastElement.classList.add('toast', 'align-items-center', 'text-white', `bg-${type}`);
    toastElement.setAttribute('role', 'alert');
    toastElement.setAttribute('aria-live', 'assertive');
    toastElement.setAttribute('aria-atomic', 'true');
    
    toastElement.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    document.querySelector('.toast-container').appendChild(toastElement);
    
    // Check if Bootstrap 5 is available
    if (typeof bootstrap !== 'undefined' && bootstrap.Toast) {
        // Initialize Bootstrap 5 toast
        const toast = new bootstrap.Toast(toastElement, {
            autohide: true,
            delay: 5000
        });
        toast.show();
    } else {
        // Fallback if Bootstrap Toast is not available
        document.querySelector('.toast-container').appendChild(toastElement);
        setTimeout(() => {
            toastElement.classList.add('show');
        }, 100);
        
        setTimeout(() => {
            toastElement.classList.remove('show');
            setTimeout(() => {
                toastElement.remove();
            }, 500);
        }, 5000);
    }
}

/**
 * Generate timeline visualization
 */
function generateTimeline() {
    const timelineContainer = document.querySelector('.timeline-container');
    if (!timelineContainer) return;
    
    // Clear existing timeline
    timelineContainer.innerHTML = '';
    
    // Get all tasks with timeline data
    const tasks = Array.from(document.querySelectorAll('.step-item[data-timeline]'));
    
    if (!tasks.length) {
        timelineContainer.innerHTML = '<div class="alert alert-info">No timeline data available</div>';
        return;
    }
    
    // Get arrival date
    const arrivalDateElem = document.getElementById('arrival-date');
    const arrivalDate = arrivalDateElem ? new Date(arrivalDateElem.getAttribute('data-value')) : new Date();
    
    // Create timeline header
    const header = document.createElement('div');
    header.classList.add('timeline-header');
    header.innerHTML = `
        <div class="timeline-arrival">
            <div class="timeline-date">${arrivalDate.toLocaleDateString()}</div>
            <div class="timeline-label">Your Arrival</div>
        </div>
    `;
    timelineContainer.appendChild(header);
    
    // Create timeline track
    const track = document.createElement('div');
    track.classList.add('timeline-track');
    
    // Sort tasks by timeline offset
    tasks.sort((a, b) => {
        const offsetA = parseInt(a.getAttribute('data-timeline') || '0');
        const offsetB = parseInt(b.getAttribute('data-timeline') || '0');
        return offsetA - offsetB;
    });
    
    // Add tasks to timeline
    tasks.forEach(task => {
        const offset = parseInt(task.getAttribute('data-timeline') || '0');
        const taskDate = new Date(arrivalDate);
        taskDate.setDate(taskDate.getDate() + offset);
        
        const isCompleted = task.classList.contains('completed');
        const title = task.querySelector('.step-title-text').textContent;
        const priority = parseInt(task.getAttribute('data-priority') || '3');
        
        let priorityClass = 'priority-medium';
        if (priority === 1) priorityClass = 'priority-high';
        if (priority === 3) priorityClass = 'priority-low';
        
        const taskElement = document.createElement('div');
        taskElement.classList.add('timeline-item', priorityClass);
        if (isCompleted) taskElement.classList.add('completed');
        
        // Position task based on offset
        // Pre-arrival tasks are on the left, post-arrival on the right
        const position = offset < 0 ? 'left' : 'right';
        taskElement.classList.add(`timeline-${position}`);
        
        // Calculate relative position (1 week = approximately 100px)
        const distanceFromArrival = Math.abs(offset);
        const weeks = Math.ceil(distanceFromArrival / 7);
        const topPosition = 100 + (weeks * 80) * (offset < 0 ? -1 : 1);
        
        taskElement.style.top = `${topPosition}px`;
        
        taskElement.innerHTML = `
            <div class="timeline-connector"></div>
            <div class="timeline-point ${isCompleted ? 'completed' : ''}"></div>
            <div class="timeline-content">
                <div class="timeline-date">${taskDate.toLocaleDateString()}</div>
                <div class="timeline-title">${title}</div>
                <div class="timeline-badge ${offset < 0 ? 'pre-arrival' : 'post-arrival'}">
                    ${offset < 0 ? 'Before Arrival' : 'After Arrival'}
                </div>
            </div>
        `;
        
        track.appendChild(taskElement);
    });
    
    timelineContainer.appendChild(track);
    
    // Add event listeners to timeline items
    const timelineItems = track.querySelectorAll('.timeline-item');
    timelineItems.forEach((item, index) => {
        item.addEventListener('click', function() {
            const taskId = tasks[index].getAttribute('data-task-id');
            
            // Highlight corresponding task in list view
            document.querySelectorAll('.step-item').forEach(t => t.classList.remove('highlighted'));
            tasks[index].classList.add('highlighted');
            
            // Switch to list view and scroll to task
            document.getElementById('view-list').click();
            tasks[index].scrollIntoView({ behavior: 'smooth', block: 'center' });
        });
    });
}
