/**
 * Notification system for KI Kompass
 * Handles popup notifications and real-time alerts
 */

class NotificationManager {
    constructor() {
        this.notifications = [];
        this.container = null;
        this.checkInterval = null;
        this.init();
    }

    init() {
        this.createNotificationContainer();
        this.bindEvents();
        this.startPeriodicCheck();
        this.loadNotifications();
    }

    createNotificationContainer() {
        // Create notification container if it doesn't exist
        this.container = document.getElementById('notification-container');
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.id = 'notification-container';
            this.container.className = 'notification-container';
            document.body.appendChild(this.container);
        }
    }

    bindEvents() {
        // Listen for notification events
        document.addEventListener('notificationReceived', (event) => {
            this.showNotification(event.detail);
        });

        // Close notifications when clicking outside
        document.addEventListener('click', (event) => {
            if (event.target.classList.contains('notification-overlay')) {
                this.closeNotification(event.target.closest('.notification'));
            }
        });
    }

    startPeriodicCheck() {
        // Check for new notifications every 30 seconds
        this.checkInterval = setInterval(() => {
            this.loadNotifications();
        }, 30000);
    }

    async loadNotifications() {
        try {
            const response = await fetch('/api/notifications');
            const data = await response.json();

            if (data.success && data.notifications) {
                this.processNotifications(data.notifications);
            }
        } catch (error) {
            console.error('Error loading notifications:', error);
        }
    }

    processNotifications(notifications) {
        // Show new notifications that haven't been displayed yet
        notifications.forEach(notification => {
            if (!this.isNotificationDisplayed(notification.id)) {
                this.showNotification(notification);
            }
        });
    }

    isNotificationDisplayed(notificationId) {
        return this.notifications.some(n => n.id === notificationId);
    }

    showNotification(notification) {
        // Add to displayed notifications list
        this.notifications.push(notification);

        // Create notification element
        const notificationElement = this.createNotificationElement(notification);
        this.container.appendChild(notificationElement);

        // Animate in
        setTimeout(() => {
            notificationElement.classList.add('show');
        }, 100);

        // Auto-dismiss for low priority notifications
        if (notification.priority >= 3) {
            setTimeout(() => {
                this.closeNotification(notificationElement);
            }, 5000);
        }

        // Update notification badge
        this.updateNotificationBadge();
    }

    createNotificationElement(notification) {
        const element = document.createElement('div');
        element.className = `notification notification-${notification.type} priority-${notification.priority}`;
        element.dataset.notificationId = notification.id;

        const priorityClass = notification.priority === 1 ? 'high' : notification.priority === 2 ? 'medium' : 'low';
        
        element.innerHTML = `
            <div class="notification-content">
                <div class="notification-header">
                    <span class="notification-icon">${this.getNotificationIcon(notification.type)}</span>
                    <h4 class="notification-title">${notification.title}</h4>
                    <span class="priority-badge priority-${priorityClass}">${priorityClass}</span>
                </div>
                <p class="notification-message">${notification.message}</p>
                <div class="notification-actions">
                    ${notification.action_url ? `<a href="${notification.action_url}" class="notification-action-btn">View</a>` : ''}
                    <button class="notification-dismiss-btn" onclick="notificationManager.closeNotification(this.closest('.notification'))">Dismiss</button>
                </div>
                <div class="notification-time">${this.formatTimestamp(notification.timestamp)}</div>
            </div>
        `;

        return element;
    }

    getNotificationIcon(type) {
        const icons = {
            'overdue': '⚠️',
            'upcoming': '📅',
            'welcome': '👋',
            'onboarding': '📋',
            'feature': '✨',
            'error': '❌',
            'success': '✅',
            'info': 'ℹ️'
        };
        return icons[type] || 'ℹ️';
    }

    formatTimestamp(timestamp) {
        if (!timestamp) return '';
        
        const date = new Date(timestamp);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMins / 60);
        const diffDays = Math.floor(diffHours / 24);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;
        
        return date.toLocaleDateString();
    }

    async closeNotification(notificationElement) {
        if (!notificationElement) return;

        const notificationId = notificationElement.dataset.notificationId;
        
        // Mark as read on server
        try {
            await fetch(`/api/notifications/${notificationId}/read`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
        } catch (error) {
            console.error('Error marking notification as read:', error);
        }

        // Remove from displayed list
        this.notifications = this.notifications.filter(n => n.id !== notificationId);

        // Animate out and remove
        notificationElement.classList.add('dismissing');
        setTimeout(() => {
            if (notificationElement.parentNode) {
                notificationElement.parentNode.removeChild(notificationElement);
            }
            this.updateNotificationBadge();
        }, 300);
    }

    updateNotificationBadge() {
        const badge = document.querySelector('.notification-badge');
        const count = this.notifications.length;
        
        if (badge) {
            if (count > 0) {
                badge.textContent = count > 99 ? '99+' : count;
                badge.style.display = 'inline-block';
            } else {
                badge.style.display = 'none';
            }
        }
    }

    dismissAll() {
        const notificationElements = this.container.querySelectorAll('.notification');
        notificationElements.forEach(element => {
            this.closeNotification(element);
        });
    }

    destroy() {
        if (this.checkInterval) {
            clearInterval(this.checkInterval);
        }
        if (this.container) {
            this.container.remove();
        }
    }
}

// Global notification functions
function showNotification(title, message, type = 'info', priority = 3, actionUrl = null) {
    const notification = {
        id: 'manual_' + Date.now(),
        type: type,
        priority: priority,
        title: title,
        message: message,
        action_url: actionUrl,
        timestamp: new Date().toISOString()
    };
    
    if (window.notificationManager) {
        window.notificationManager.showNotification(notification);
    }
}

function showSuccessNotification(message) {
    showNotification('Success', message, 'success', 2);
}

function showErrorNotification(message) {
    showNotification('Error', message, 'error', 1);
}

function showInfoNotification(message) {
    showNotification('Information', message, 'info', 3);
}

// Initialize notification manager when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    window.notificationManager = new NotificationManager();
});

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (window.notificationManager) {
        window.notificationManager.destroy();
    }
});