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

    isRoutineLotPromotion(message) {
        const normalizedMessage = message.toLowerCase();
        return normalizedMessage.includes('depleted')
            && normalizedMessage.includes('automatically activated next lot');
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
        
        if (this.dismissedVersion === alertKey) {
            return;
        }

        const messages = this.alertData.message
            .split(/\s*\|\s*/)
            .map(message => message.trim())
            .filter(Boolean);
        const allMessagesAreRoutinePromotions = messages.length > 0
            && messages.every(message => this.isRoutineLotPromotion(message));
        const barColors = allMessagesAreRoutinePromotions
            ? 'background: linear-gradient(135deg, #b45309, #92400e); color: white;'
            : isActive
                ? 'background: linear-gradient(135deg, #dc3545, #c82333); color: white;'
                : 'background: linear-gradient(135deg, #28a745, #218838); color: white;';
        
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
            flex-wrap: wrap;
            align-items: center;
            justify-content: center;
            gap: 16px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
            ${barColors}
        `;
        
        const messageContainer = document.createElement('div');
        messageContainer.style.cssText = `
            flex: 1 1 700px;
            max-width: 1000px;
            min-width: 0;
            text-align: left;
            overflow-wrap: anywhere;
        `;

        messages.forEach((message, index) => {
            const messageRow = document.createElement('div');
            const isRoutinePromotion = this.isRoutineLotPromotion(message);
            messageRow.textContent = message;
            messageRow.style.cssText = `
                padding: ${messages.length > 1 ? '7px 0' : '0'};
                ${index > 0 ? 'border-top: 1px solid rgba(255,255,255,0.28);' : ''}
                ${isRoutinePromotion && !allMessagesAreRoutinePromotions
                    ? 'background: rgba(180,83,9,0.9); border-radius: 6px; padding: 9px 12px;'
                    : ''}
            `;
            messageContainer.appendChild(messageRow);
        });

        bar.appendChild(messageContainer);
        
        const readBtn = document.createElement('button');
        readBtn.type = 'button';
        readBtn.textContent = 'Mark as read';
        readBtn.setAttribute('aria-label', 'Mark alert as read');
        readBtn.title = 'Hide this message until it changes';
        readBtn.style.cssText = `
            background: rgba(255,255,255,0.18);
            border: 1px solid rgba(255,255,255,0.55);
            color: white;
            font-size: 14px;
            font-weight: 600;
            min-height: 44px;
            flex: 0 0 auto;
            border-radius: 6px;
            padding: 9px 14px;
            white-space: nowrap;
            cursor: pointer;
            line-height: 1.2;
            transition: background 0.2s;
        `;
        readBtn.onmouseover = () => readBtn.style.background = 'rgba(255,255,255,0.28)';
        readBtn.onmouseout = () => readBtn.style.background = 'rgba(255,255,255,0.18)';
        readBtn.onclick = () => this.dismiss(alertKey);
        bar.appendChild(readBtn);
        
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
