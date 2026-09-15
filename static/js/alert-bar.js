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
            const response = await fetch('/api/admin/alert', { cache: 'no-store' });
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
        
        const bar = document.createElement('div');
        bar.id = 'admin-alert-bar';
        bar.setAttribute('role', 'status');
        bar.setAttribute('aria-live', 'polite');
        bar.setAttribute('aria-atomic', 'true');
        bar.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            z-index: 10000;
            padding: 14px 18px;
            font-weight: 600;
            font-size: 15px;
            line-height: 1.5;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 16px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
            ${isActive ? 
                'background: linear-gradient(135deg, #dc3545, #c82333); color: white;' : 
                'background: linear-gradient(135deg, #28a745, #218838); color: white;'}
        `;
        
        const messageContainer = document.createElement('div');
        messageContainer.style.cssText = `
            flex: 0 1 1000px;
            min-width: 0;
            text-align: left;
            overflow-wrap: anywhere;
        `;

        const messages = this.alertData.message
            .split(/\s*\|\s*/)
            .map(message => message.trim())
            .filter(Boolean);

        messages.forEach((message, index) => {
            const messageRow = document.createElement('div');
            messageRow.textContent = message;
            messageRow.style.cssText = `
                padding: ${messages.length > 1 ? '7px 0' : '0'};
                ${index > 0 ? 'border-top: 1px solid rgba(255,255,255,0.28);' : ''}
            `;
            messageContainer.appendChild(messageRow);
        });

        bar.appendChild(messageContainer);
        
        if (!isActive) {
            const closeBtn = document.createElement('button');
            closeBtn.type = 'button';
            closeBtn.innerHTML = '&times;';
            closeBtn.setAttribute('aria-label', 'Dismiss alert');
            closeBtn.title = 'Dismiss alert';
            closeBtn.style.cssText = `
                background: rgba(255,255,255,0.2);
                border: none;
                color: white;
                font-size: 20px;
                width: 44px;
                height: 44px;
                flex: 0 0 44px;
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
