/**
 * Notification System JavaScript
 * Handle tender deadline notifications in the navbar dropdown
 */

class NotificationSystem {
    constructor() {
        this.notificationsLoaded = false;
        this.refreshInterval = 300000; // 5 minutes
        this.init();
    }

    init() {
        // Load notification count on page load
        document.addEventListener('DOMContentLoaded', () => {
            this.loadNotificationCount();
            // Refresh count every 5 minutes
            setInterval(() => this.loadNotificationCount(), this.refreshInterval);
        });

        // Reset notifications loaded flag when dropdown is hidden
        const dropdown = document.getElementById('notificationsDropdown');
        if (dropdown) {
            dropdown.addEventListener('hidden.bs.dropdown', () => {
                this.notificationsLoaded = false;
            });
        }
    }

    /**
     * Load notification count for the badge
     */
    async loadNotificationCount() {
        try {
            const response = await fetch('/api/notifications/count');
            const data = await response.json();
            
            const badge = document.getElementById('notificationCount');
            if (badge) {
                if (data.count > 0) {
                    badge.textContent = data.count;
                    badge.style.display = 'block';
                } else {
                    badge.style.display = 'none';
                }
            }
        } catch (error) {
            console.error('Error loading notification count:', error);
        }
    }

    /**
     * Load full notifications list when dropdown is opened
     */
    async loadNotifications() {
        if (this.notificationsLoaded) return;
        
        try {
            const response = await fetch('/api/notifications');
            const data = await response.json();
            
            const container = document.getElementById('notificationsList');
            if (!container) return;
            
            if (data.notifications && data.notifications.length > 0) {
                container.innerHTML = data.notifications.map(notification => 
                    this.renderNotificationItem(notification)
                ).join('');
            } else {
                container.innerHTML = this.renderEmptyState();
            }
            
            this.notificationsLoaded = true;
        } catch (error) {
            console.error('Error loading notifications:', error);
            this.renderErrorState();
        }
    }

    /**
     * Render a single notification item
     */
    renderNotificationItem(notification) {
        const isUnread = !notification.is_read;
        const unreadClass = isUnread ? 'bg-light' : '';
        const unreadBadge = isUnread ? '<span class="badge bg-warning ms-1">New</span>' : '';
        
        return `
            <li>
                <div class="dropdown-item ${unreadClass}" 
                     style="white-space: normal; cursor: pointer;"
                     onclick="notificationSystem.viewTender(${notification.tender_id}, ${notification.id})">
                    <div class="d-flex justify-content-between align-items-start">
                        <div class="flex-grow-1">
                            <h6 class="mb-1 text-primary">
                                ${this.escapeHtml(notification.tender_reference || 'N/A')}
                                ${unreadBadge}
                            </h6>
                            <p class="mb-1 small">${this.escapeHtml(notification.tender_title || notification.message)}</p>
                            <small class="text-muted">
                                <i class="fas fa-clock"></i> 
                                ${notification.days_remaining} days remaining
                            </small>
                            <br>
                            <small class="text-muted">
                                <i class="fas fa-calendar"></i> 
                                ${this.formatDate(notification.created_at)}
                            </small>
                        </div>
                        <div class="ms-2">
                            <button class="btn btn-sm btn-outline-success" 
                                    onclick="event.stopPropagation(); notificationSystem.processNotification(${notification.id})"
                                    title="Process Notification">
                                <i class="fas fa-check"></i>
                            </button>
                        </div>
                    </div>
                </div>
            </li>
        `;
    }

    /**
     * Render empty state when no notifications
     */
    renderEmptyState() {
        return `
            <li>
                <div class="dropdown-item-text text-center text-muted">
                    <i class="fas fa-check-circle text-success"></i><br>
                    No pending notifications
                </div>
            </li>
        `;
    }

    /**
     * Render error state
     */
    renderErrorState() {
        const container = document.getElementById('notificationsList');
        if (container) {
            container.innerHTML = `
                <li>
                    <div class="dropdown-item-text text-center text-danger">
                        <i class="fas fa-exclamation-triangle"></i><br>
                        Error loading notifications
                    </div>
                </li>
            `;
        }
    }

    /**
     * View tender and mark notification as read
     */
    async viewTender(tenderId, notificationId) {
        // Mark as read
        await this.markNotificationRead(notificationId);
        
        // Navigate to tender
        window.location.href = `/tenders/${tenderId}`;
    }

    /**
     * Mark notification as read
     */
    async markNotificationRead(notificationId) {
        try {
            // FIXED: Removed /api/ from URL
            await fetch(`/notifications/${notificationId}/read`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            this.loadNotificationCount();
            this.notificationsLoaded = false; // Force reload
        } catch (error) {
            console.error('Error marking notification as read:', error);
        }
    }

    /**
     * Process individual notification with comment (FIXED)
     */
    async processNotification(notificationId) {
        const comment = prompt('Add a processing comment (required):');
        if (comment === null) return; // User cancelled
        
        // Validate comment is not empty
        if (!comment || comment.trim() === '') {
            this.showToast('Processing comment is required', 'error');
            return;
        }
        
        try {
            // FIXED: Removed /api/ from URL and changed 'note' to 'comment'
            const response = await fetch(`/notifications/${notificationId}/process`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({ comment: comment.trim() })  // FIXED: 'comment' not 'note'
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showToast('Notification processed successfully', 'success');
                this.loadNotificationCount();
                this.notificationsLoaded = false; // Force reload
                
                // Close dropdown after successful processing
                const dropdown = document.getElementById('notificationsDropdown');
                if (dropdown) {
                    const bsDropdown = bootstrap.Dropdown.getInstance(dropdown);
                    if (bsDropdown) {
                        bsDropdown.hide();
                    }
                }
            } else {
                this.showToast(`Error: ${data.error}`, 'error');
            }
        } catch (error) {
            console.error('Error processing notification:', error);
            this.showToast('Network error processing notification', 'error');
        }
    }

    /**
     * Process all notifications at once (FIXED)
     */
    async processAllNotifications() {
        const comment = prompt('Add a processing comment for all notifications (required):');
        if (comment === null) return; // User cancelled
        
        // Validate comment is not empty
        if (!comment || comment.trim() === '') {
            this.showToast('Processing comment is required', 'error');
            return;
        }
        
        if (!confirm('Are you sure you want to process all notifications?')) return;
        
        try {
            // FIXED: Removed /api/ from URL and changed 'note' to 'comment'
            const response = await fetch('/notifications/process-all', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({ comment: comment.trim() })  // FIXED: 'comment' not 'note'
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showToast(`Processed ${data.count} notifications`, 'success');
                this.loadNotificationCount();
                this.notificationsLoaded = false; // Force reload
                
                // Close dropdown
                const dropdown = document.getElementById('notificationsDropdown');
                if (dropdown) {
                    const bsDropdown = bootstrap.Dropdown.getInstance(dropdown);
                    if (bsDropdown) {
                        bsDropdown.hide();
                    }
                }
            } else {
                this.showToast(`Error: ${data.error}`, 'error');
            }
        } catch (error) {
            console.error('Error processing all notifications:', error);
            this.showToast('Network error processing notifications', 'error');
        }
    }

    /**
     * Get CSRF token from meta tag or form
     */
    getCSRFToken() {
        const token = document.querySelector('meta[name="csrf-token"]');
        return token ? token.getAttribute('content') : '';
    }

    /**
     * Show toast notification
     */
    showToast(message, type = 'info') {
        const alertClass = type === 'success' ? 'alert-success' : 
                          type === 'error' ? 'alert-danger' : 'alert-info';
        
        const toast = document.createElement('div');
        toast.className = `alert ${alertClass} alert-dismissible fade show position-fixed`;
        toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        toast.innerHTML = `
            ${this.escapeHtml(message)}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(toast);
        
        // Auto remove after 4 seconds
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 4000);
    }

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Format date for display
     */
    formatDate(dateString) {
        if (!dateString) return 'N/A';
        
        try {
            const date = new Date(dateString);
            return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit'
            });
        } catch (error) {
            return dateString;
        }
    }

    /**
     * Refresh notifications manually
     */
    refresh() {
        this.notificationsLoaded = false;
        this.loadNotificationCount();
        this.loadNotifications();
    }
}

// Initialize notification system
const notificationSystem = new NotificationSystem();