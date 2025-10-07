// Quantity Mismatch Alert System
// Monitors discrepancies between ShipStation and Orders Inbox

let mismatchData = null;

async function loadQuantityMismatch() {
    try {
        const response = await fetch('/api/quantity_mismatch');
        const result = await response.json();
        
        if (result.success) {
            mismatchData = result;
            updateMismatchAlert(result);
        }
    } catch (error) {
        console.error('Failed to load quantity mismatch:', error);
    }
}

function updateMismatchAlert(data) {
    const alert = document.getElementById('mismatch-alert');
    const details = document.getElementById('mismatch-details');
    
    if (!alert || !details) return;
    
    if (data.has_mismatch) {
        const direction = data.difference > 0 ? 'more' : 'fewer';
        const absValue = Math.abs(data.difference);
        
        details.textContent = `ShipStation shows ${data.shipstation_units} units, Orders Inbox shows ${data.local_units} units (${absValue} ${direction} in ShipStation)`;
        alert.classList.add('show');
    } else {
        alert.classList.remove('show');
    }
}

function dismissMismatchAlert() {
    const alert = document.getElementById('mismatch-alert');
    if (alert) alert.classList.remove('show');
}

function refreshMismatchCheck() {
    loadQuantityMismatch();
}

// Auto-load mismatch check when page loads
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadQuantityMismatch);
} else {
    loadQuantityMismatch();
}

// Refresh every 60 seconds
setInterval(loadQuantityMismatch, 60000);
