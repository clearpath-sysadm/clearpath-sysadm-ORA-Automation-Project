/**
 * Admin Alert Bar
 * Displays admin-set alert messages at the top of all pages
 * Polls for updates every 30 seconds
 */
class AdminAlertBar {
    constructor() {
        this.alertData = null;
        this.dismissedVersion = null;
        this.pollInterval = null;
    }
    
    async init() {
        await this.fetchAndRender();
        this.startPolling();
    }
    
    async fetchAndRender() {
        try {
            const response = await fetch('/api/admin/alert');
            if (!response.ok) return;
            
            const newData = await response.json();
            this.dismissedVersion = localStorage.getItem('alertDismissed');
            
            const hasChanged = JSON.stringify(this.alertData) !== JSON.stringify(newData);
            this.alertData = newData;
            
            if (hasChanged) {
                this.render();
            }
        } catch (err) {
            console.error('Failed to load admin alert:', err);
        }
    }
    
    startPolling() {
        this.pollInterval = setInterval(() => this.fetchAndRender(), 30000);
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    render() {
        const existingBar = document.getElementById('admin-alert-bar');
        if (existingBar) {
            existingBar.remove();
            document.body.style.paddingTop = '0';
        }
        
        if (!this.alertData || !this.alertData.message || this.alertData.message.trim() === '') {
            return;
        }
        
        const isActive = this.alertData.is_active;
        const alertKey = `${this.alertData.message}_${isActive}`;
        
        if (!isActive && this.dismissedVersion === alertKey) {
            return;
        }
        
        if (!document.getElementById('admin-alert-pulse-style')) {
            const style = document.createElement('style');
            style.id = 'admin-alert-pulse-style';
            style.textContent = `
                @keyframes alertPulse {
                    0%, 100% { opacity: 1; }
                    50% { opacity: 0.6; }
                }
            `;
            document.head.appendChild(style);
        }
        
        const bar = document.createElement('div');
        bar.id = 'admin-alert-bar';
        bar.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            z-index: 10000;
            padding: 12px 20px;
            text-align: center;
            font-weight: 500;
            font-size: 14px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 15px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
            animation: alertPulse 2s ease-in-out infinite;
            ${isActive ? 
                'background: linear-gradient(135deg, #dc3545, #c82333); color: white;' : 
                'background: linear-gradient(135deg, #28a745, #218838); color: white;'}
        `;
        
        const messageSpan = document.createElement('span');
        messageSpan.innerHTML = this.escapeHtml(this.alertData.message);
        bar.appendChild(messageSpan);
        
        if (!isActive) {
            const closeBtn = document.createElement('button');
            closeBtn.innerHTML = '&times;';
            closeBtn.style.cssText = `
                background: rgba(255,255,255,0.2);
                border: none;
                color: white;
                font-size: 20px;
                width: 28px;
                height: 28px;
                border-radius: 50%;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                line-height: 1;
                transition: background 0.2s;
            `;
            closeBtn.onmouseover = () => closeBtn.style.background = 'rgba(255,255,255,0.3)';
            closeBtn.onmouseout = () => closeBtn.style.background = 'rgba(255,255,255,0.2)';
            closeBtn.onclick = () => this.dismiss(alertKey);
            bar.appendChild(closeBtn);
        }
        
        document.body.insertBefore(bar, document.body.firstChild);
        
        document.body.style.paddingTop = (bar.offsetHeight) + 'px';
    }
    
    dismiss(alertKey) {
        localStorage.setItem('alertDismissed', alertKey);
        const bar = document.getElementById('admin-alert-bar');
        if (bar) {
            bar.remove();
            document.body.style.paddingTop = '0';
        }
    }
}

const adminAlertBar = new AdminAlertBar();
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => adminAlertBar.init(), 100);
});
