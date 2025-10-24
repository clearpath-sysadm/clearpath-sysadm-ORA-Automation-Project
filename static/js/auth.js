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
        const sidebar = document.querySelector('.sidebar');
        if (!sidebar) return;
        
        const widget = document.createElement('div');
        widget.className = 'user-profile-widget';
        widget.innerHTML = `
            <div class="profile-section" id="profile-trigger" style="cursor: pointer;" title="Click to view account details">
                <img src="${this.user.profile_image_url || ''}" 
                     alt="${this.user.first_name || 'User'}" 
                     class="profile-avatar"
                     onerror="this.src='data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%2240%22 height=%2240%22%3E%3Crect fill=%22%231B2A4A%22 width=%2240%22 height=%2240%22/%3E%3Ctext x=%2250%25%22 y=%2250%25%22 dominant-baseline=%22middle%22 text-anchor=%22middle%22 fill=%22white%22 font-family=%22sans-serif%22 font-size=%2220%22%3E${(this.user.first_name || 'U').charAt(0)}%3C/text%3E%3C/svg%3E'">
                <div class="user-info">
                    <span class="user-name">${this.user.first_name || ''} ${this.user.last_name || ''}</span>
                    <span class="user-role badge-${this.user.role}">${this.user.role.toUpperCase()}</span>
                </div>
            </div>
            <div id="profile-dropdown" class="profile-dropdown" style="display: none;">
                <div class="dropdown-header">Account Details</div>
                <div class="dropdown-item">
                    <span class="dropdown-label">Name:</span>
                    <span class="dropdown-value">${this.user.first_name || ''} ${this.user.last_name || ''}</span>
                </div>
                <div class="dropdown-item">
                    <span class="dropdown-label">Email:</span>
                    <span class="dropdown-value">${this.user.email || 'N/A'}</span>
                </div>
                <div class="dropdown-item">
                    <span class="dropdown-label">Role:</span>
                    <span class="dropdown-value">
                        <span class="badge-${this.user.role}">${this.user.role.toUpperCase()}</span>
                    </span>
                </div>
                <div class="dropdown-item">
                    <span class="dropdown-label">Login Method:</span>
                    <span class="dropdown-value">${this.getLoginMethod()}</span>
                </div>
                <div class="dropdown-item">
                    <span class="dropdown-label">User ID:</span>
                    <span class="dropdown-value" style="font-family: monospace; font-size: 11px;">${this.user.id}</span>
                </div>
            </div>
            <a href="/auth/logout" class="logout-btn">
                <span>🚪</span> Sign Out
            </a>
        `;
        
        sidebar.appendChild(widget);
        
        // Add click handler for profile dropdown
        const profileTrigger = document.getElementById('profile-trigger');
        const profileDropdown = document.getElementById('profile-dropdown');
        
        profileTrigger.addEventListener('click', (e) => {
            e.stopPropagation();
            const isVisible = profileDropdown.style.display === 'block';
            profileDropdown.style.display = isVisible ? 'none' : 'block';
        });
        
        // Close dropdown when clicking outside
        document.addEventListener('click', () => {
            profileDropdown.style.display = 'none';
        });
        
        // Prevent dropdown from closing when clicking inside it
        profileDropdown.addEventListener('click', (e) => {
            e.stopPropagation();
        });
    }
    
    getLoginMethod() {
        if (this.user.email && this.user.email.includes('@')) {
            // Detect provider from email domain or OAuth data
            if (this.user.profile_image_url && this.user.profile_image_url.includes('googleusercontent.com')) {
                return '🌐 Google';
            } else if (this.user.profile_image_url && this.user.profile_image_url.includes('github')) {
                return '🐙 GitHub';
            } else if (this.user.profile_image_url && this.user.profile_image_url.includes('apple')) {
                return '🍎 Apple';
            }
            return '📧 Replit Auth';
        }
        return '🔐 Replit Auth';
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
