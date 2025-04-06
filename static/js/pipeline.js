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
