// Shipping Violations Alert System
// Shared across all pages

let violationsData = [];

async function loadShippingViolations() {
    try {
        const response = await fetch('/api/shipping_violations');
        const result = await response.json();
        
        if (result.success) {
            violationsData = result.violations;
            updateViolationsAlert(result.count);
        }
    } catch (error) {
        console.error('Failed to load violations:', error);
    }
}

function updateViolationsAlert(count) {
    const alert = document.getElementById('violations-alert');
    const summary = document.getElementById('violations-summary');
    
    if (!alert || !summary) return;
    
    if (count > 0) {
        const violationTypes = {};
        violationsData.forEach(v => {
            violationTypes[v.violation_type] = (violationTypes[v.violation_type] || 0) + 1;
        });
        
        const typeSummary = Object.entries(violationTypes)
            .map(([type, count]) => {
                const displayName = type === 'hawaiian_service' ? 'Hawaiian' : 
                                  type === 'canadian_service' ? 'Canadian' : 
                                  type === 'benco_carrier' ? 'Benco' :
                                  type === 'duplicate_order_sku' ? 'Duplicate' : type;
                return `${count} ${displayName}`;
            })
            .join(', ');
        
        summary.textContent = `${count} order${count > 1 ? 's' : ''} detected with incorrect shipping configuration (${typeSummary})`;
        alert.classList.add('show');
    } else {
        alert.classList.remove('show');
    }
}

function dismissAlert() {
    const alert = document.getElementById('violations-alert');
    if (alert) alert.classList.remove('show');
}

function openViolationsModal() {
    const modal = document.getElementById('violations-modal');
    if (modal) {
        modal.classList.add('show');
        renderViolationsList();
    }
}

function closeViolationsModal() {
    const modal = document.getElementById('violations-modal');
    if (modal) modal.classList.remove('show');
}

function closeModalOnBackdrop(event) {
    if (event.target.id === 'violations-modal') {
        closeViolationsModal();
    }
}

function renderViolationsList() {
    const listContainer = document.getElementById('violations-list');
    if (!listContainer) return;
    
    if (violationsData.length === 0) {
        listContainer.innerHTML = '<p style="text-align: center; color: var(--text-tertiary);">No violations found</p>';
        return;
    }
    
    listContainer.innerHTML = violationsData.map(v => {
        const typeLabel = v.violation_type === 'hawaiian_service' ? 'Hawaiian Shipping' : 
                        v.violation_type === 'canadian_service' ? 'Canadian Shipping' : 'Benco Account';
        
        return `
            <div class="violation-item">
                <div class="violation-header">
                    <div class="violation-order">Order #${v.order_number}</div>
                    <div class="violation-type-badge">${typeLabel}</div>
                </div>
                
                <div class="violation-details-grid">
                    <div class="violation-detail">
                        <div class="violation-detail-label">Ship To Location</div>
                        <div class="violation-detail-value">
                            ${v.ship_state ? v.ship_state + ', ' : ''}${v.ship_country || 'US'}
                        </div>
                    </div>
                    <div class="violation-detail">
                        <div class="violation-detail-label">Company</div>
                        <div class="violation-detail-value">${v.ship_company || 'N/A'}</div>
                    </div>
                </div>
                
                <div class="violation-issue">
                    <div class="violation-issue-label">Issue Detected</div>
                    <div class="violation-issue-text">
                        Expected: <strong>${v.expected_value}</strong><br>
                        Actual: <strong>${v.actual_value}</strong>
                    </div>
                </div>
                
                <button class="btn-resolve-violation" onclick="resolveViolation(${v.id})" id="resolve-btn-${v.id}">
                    Mark as Resolved
                </button>
            </div>
        `;
    }).join('');
}

async function resolveViolation(violationId) {
    const btn = document.getElementById(`resolve-btn-${violationId}`);
    const originalText = btn.textContent;
    
    try {
        btn.disabled = true;
        btn.textContent = 'Resolving...';
        
        const response = await fetch(`/api/shipping_violations/${violationId}/resolve`, {
            method: 'PUT'
        });
        
        const result = await response.json();
        
        if (result.success) {
            btn.textContent = '✓ Resolved';
            btn.style.backgroundColor = 'var(--text-tertiary)';
            
            // Remove from local data
            violationsData = violationsData.filter(v => v.id !== violationId);
            
            // Update alert and re-render
            setTimeout(() => {
                updateViolationsAlert(violationsData.length);
                renderViolationsList();
            }, 500);
        } else {
            throw new Error(result.error || 'Failed to resolve');
        }
    } catch (error) {
        console.error('Failed to resolve violation:', error);
        btn.textContent = originalText;
        btn.disabled = false;
        alert('Failed to resolve violation. Please try again.');
    }
}

// Auto-load violations when page loads
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadShippingViolations);
} else {
    loadShippingViolations();
}

// Refresh violations every 60 seconds
setInterval(loadShippingViolations, 60000);
