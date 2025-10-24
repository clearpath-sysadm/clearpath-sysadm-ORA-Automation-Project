/**
 * ORA Auth Manager
 * Handles authentication checks and UI updates across all pages.
 * 
 * Usage: Add <script src="/static/js/auth.js"></script> to each HTML page
 */
class AuthManager {
    constructor() {
        this.user = null;
        this.isAuthenticated = false;
    }
    
    async init() {
        try {
            const response = await fetch('/api/auth/status');
            const data = await response.json();
            
            this.isAuthenticated = data.authenticated;
            this.user = data.user;
            
            const publicPages = ['/', '/landing.html', '/auth/login', '/auth/logout', '/auth/error'];
            const currentPath = window.location.pathname;
            
            if (!this.isAuthenticated && !publicPages.includes(currentPath) && !currentPath.startsWith('/auth/')) {
                sessionStorage.setItem('returnUrl', window.location.href);
                window.location.href = '/landing.html';
                return;
            }
            
            if (this.isAuthenticated) {
                this.renderUserWidget();
                this.setupRoleBasedUI();
            }
        } catch (err) {
            console.error('Auth check failed:', err);
        }
    }
    
    renderUserWidget() {
        const sidebar = document.querySelector('.sidebar-header');
        if (!sidebar) return;
        
        const widget = document.createElement('div');
        widget.className = 'user-profile-widget';
        widget.innerHTML = `
            <div class="profile-section">
                <img src="${this.user.profile_image_url || ''}" 
                     alt="${this.user.first_name || 'User'}" 
                     class="profile-avatar"
                     onerror="this.src='data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%2240%22 height=%2240%22%3E%3Crect fill=%22%231B2A4A%22 width=%2240%22 height=%2240%22/%3E%3Ctext x=%2250%25%22 y=%2250%25%22 dominant-baseline=%22middle%22 text-anchor=%22middle%22 fill=%22white%22 font-family=%22sans-serif%22 font-size=%2220%22%3E${(this.user.first_name || 'U').charAt(0)}%3C/text%3E%3C/svg%3E'">
                <div class="user-info">
                    <span class="user-name">${this.user.first_name || ''} ${this.user.last_name || ''}</span>
                    <span class="user-role badge-${this.user.role}">${this.user.role.toUpperCase()}</span>
                </div>
            </div>
            <a href="/auth/logout" class="logout-btn">
                <span>🚪</span> Sign Out
            </a>
        `;
        
        sidebar.appendChild(widget);
    }
    
    setupRoleBasedUI() {
        if (this.user.role === 'viewer') {
            document.querySelectorAll('[data-action="write"]').forEach(btn => {
                btn.disabled = true;
                btn.title = 'Read-only access - contact admin for changes';
                btn.style.opacity = '0.5';
                btn.style.cursor = 'not-allowed';
            });
            
            document.querySelectorAll('form').forEach(form => {
                const method = (form.method || 'GET').toUpperCase();
                if (['POST', 'PUT', 'DELETE'].includes(method)) {
                    form.addEventListener('submit', (e) => {
                        e.preventDefault();
                        alert('Read-only access - contact admin for changes');
                    });
                }
            });
        }
    }
    
    isAdmin() {
        return this.isAuthenticated && this.user && this.user.role === 'admin';
    }
    
    isViewer() {
        return this.isAuthenticated && this.user && this.user.role === 'viewer';
    }
}

const authManager = new AuthManager();
document.addEventListener('DOMContentLoaded', () => authManager.init());

window.authManager = authManager;
