// Production Health Check Modal
// Displays environment and workflow status
// Requires: timezone-utils.js for formatWorkflowTimestamp()

let healthData = null;

// Format minutes to human-readable time
function formatMinutesToReadable(minutes) {
    if (minutes === 999999 || !minutes) return 'Never';
    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    
    const days = Math.floor(hours / 24);
    if (days === 1) return '1 day ago';
    if (days < 7) return `${days} days ago`;
    
    const weeks = Math.floor(days / 7);
    if (weeks === 1) return '1 week ago';
    if (weeks < 4) return `${weeks} weeks ago`;
    
    const months = Math.floor(days / 30);
    if (months === 1) return '1 month ago';
    return `${months} months ago`;
}

function openHealthModal() {
    const modal = document.getElementById('health-modal');
    if (modal) {
        modal.classList.add('show');
        loadHealthDetails();
    }
}

function closeHealthModal() {
    const modal = document.getElementById('health-modal');
    if (modal) modal.classList.remove('show');
}

// Update closeModalOnBackdrop to handle both modals
const originalCloseModalOnBackdrop = window.closeModalOnBackdrop;
window.closeModalOnBackdrop = function(event) {
    if (event.target.id === 'health-modal') {
        closeHealthModal();
    } else if (originalCloseModalOnBackdrop) {
        originalCloseModalOnBackdrop(event);
    }
};

async function loadHealthDetails() {
    const container = document.getElementById('health-details');
    if (!container) return;
    
    container.innerHTML = '<p style="text-align: center; color: var(--text-tertiary); padding: 40px;">Loading health data...</p>';
    
    try {
        const response = await fetch('/health');
        healthData = await response.json();
        renderHealthDetails();
    } catch (error) {
        console.error('Failed to load health data:', error);
        container.innerHTML = `
            <div style="text-align: center; padding: 40px; color: var(--text-secondary);">
                <p style="font-size: 48px; margin: 0 0 16px 0;">⚠️</p>
                <p style="margin: 0;">Failed to load health data</p>
                <p style="margin: 8px 0 0 0; color: var(--text-tertiary); font-size: 14px;">${error.message}</p>
            </div>
        `;
    }
}

function renderHealthDetails() {
    const container = document.getElementById('health-details');
    if (!container || !healthData) return;
    
    const isProd = healthData.environment === 'PRODUCTION';
    const envColor = isProd ? '#10b981' : '#f59e0b';
    const envIcon = isProd ? '🚀' : '🔧';
    
    let html = `
        <div style="padding: 0 24px 24px 24px;">
            <!-- Environment Badge -->
            <div style="display: inline-flex; align-items: center; gap: 8px; padding: 8px 16px; background: ${envColor}22; border: 2px solid ${envColor}; border-radius: 8px; margin-bottom: 24px;">
                <span style="font-size: 20px;">${envIcon}</span>
                <span style="font-weight: 600; color: ${envColor};">${healthData.environment}</span>
            </div>
            
            <!-- System Info -->
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px;">
                <div style="padding: 16px; background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 8px;">
                    <div style="font-size: 12px; color: var(--text-tertiary); margin-bottom: 4px;">Repl Slug</div>
                    <div style="font-weight: 600; color: var(--text-primary);">${healthData.repl_slug || 'unknown'}</div>
                </div>
                <div style="padding: 16px; background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 8px;">
                    <div style="font-size: 12px; color: var(--text-tertiary); margin-bottom: 4px;">Database</div>
                    <div style="font-weight: 600; color: ${healthData.database_connected ? '#10b981' : '#ef4444'};">
                        ${healthData.database_connected ? '✓ Connected' : '✗ Disconnected'}
                    </div>
                </div>
                <div style="padding: 16px; background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 8px;">
                    <div style="font-size: 12px; color: var(--text-tertiary); margin-bottom: 4px;">Checked At</div>
                    <div style="font-weight: 600; color: var(--text-primary); font-size: 14px;">
                        ${new Date(healthData.timestamp).toLocaleTimeString()}
                    </div>
                </div>
            </div>
    `;
    
    // Deployment Status Section
    if (healthData.deployment) {
        const dep = healthData.deployment;
        const workflowsMatch = dep.actual_workflows === dep.expected_workflows;
        const deployColor = dep.configured && workflowsMatch ? '#10b981' : '#f59e0b';
        const deployIcon = dep.configured && workflowsMatch ? '✓' : '⚠️';
        
        html += `
            <div style="padding: 16px; background: ${deployColor}11; border: 1px solid ${deployColor}; border-radius: 8px; margin-bottom: 24px;">
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
                    <span style="font-size: 18px;">${deployIcon}</span>
                    <span style="font-weight: 600; color: ${deployColor};">Deployment Configuration</span>
                </div>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; font-size: 13px;">
                    <div>
                        <span style="color: var(--text-tertiary);">Command:</span>
                        <code style="margin-left: 6px; padding: 2px 6px; background: var(--card-bg); border-radius: 4px; color: var(--text-primary);">${dep.command}</code>
                    </div>
                    <div>
                        <span style="color: var(--text-tertiary);">Workflows:</span>
                        <span style="color: ${workflowsMatch ? '#10b981' : '#f59e0b'}; font-weight: 600; margin-left: 4px;">
                            ${dep.actual_workflows}/${dep.expected_workflows} Running
                        </span>
                    </div>
                </div>
                ${dep.missing_workflows && dep.missing_workflows.length > 0 ? `
                <div style="margin-top: 12px; padding: 12px; background: #ef444411; border: 1px solid #ef4444; border-radius: 6px;">
                    <div style="font-weight: 600; color: #ef4444; margin-bottom: 4px;">Missing Workflows:</div>
                    <div style="color: var(--text-secondary); font-size: 12px;">${dep.missing_workflows.join(', ')}</div>
                </div>
                ` : ''}
            </div>
        `;
    }
    
    // Workflows section
    if (healthData.workflows && healthData.workflows.length > 0) {
        html += `
            <div style="margin-top: 24px;">
                <h3 style="font-size: 14px; font-weight: 600; color: var(--text-secondary); margin: 0 0 16px 0; text-transform: uppercase; letter-spacing: 0.5px;">
                    Automation Workflows (${healthData.workflows.length})
                </h3>
                <div style="display: flex; flex-direction: column; gap: 12px;">
        `;
        
        healthData.workflows.forEach(workflow => {
            const isRecent = workflow.age_minutes < 30;
            const isEnabled = workflow.enabled;
            const statusColor = !isEnabled ? '#6b7280' : 
                              isRecent ? '#10b981' : 
                              workflow.age_minutes < 60 ? '#f59e0b' : '#ef4444';
            const statusIcon = !isEnabled ? '⏸️' :
                             isRecent ? '✓' : 
                             workflow.age_minutes < 60 ? '⚠️' : '✗';
            const statusText = !isEnabled ? 'Disabled' :
                             workflow.last_run === 'Never' ? 'Never ran' :
                             isRecent ? 'Healthy' : 'Stale';
            
            html += `
                <div style="padding: 20px; background: var(--card-bg); border-left: 4px solid ${statusColor}; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
                        <div style="font-weight: 600; font-size: 15px; color: var(--text-primary);">${workflow.name}</div>
                        <div style="display: inline-flex; align-items: center; gap: 6px; padding: 6px 14px; background: ${statusColor}22; border-radius: 6px;">
                            <span style="font-size: 16px;">${statusIcon}</span>
                            <span style="font-size: 13px; font-weight: 600; color: ${statusColor};">${statusText}</span>
                        </div>
                    </div>
                    <div style="display: flex; flex-direction: column; gap: 8px;">
                        <div style="display: flex; align-items: baseline; gap: 8px;">
                            <span style="color: var(--text-tertiary); font-size: 13px; min-width: 70px;">Last Run:</span>
                            <span style="color: var(--text-primary); font-weight: 500; font-size: 14px;">${workflow.last_run_at ? formatWorkflowTimestamp(workflow.last_run_at) : 'Never'}</span>
                        </div>
                        ${workflow.status ? `
                        <div style="display: flex; align-items: baseline; gap: 8px;">
                            <span style="color: var(--text-tertiary); font-size: 13px; min-width: 70px;">Status:</span>
                            <span style="color: var(--text-secondary); font-weight: 500; font-size: 14px;">${workflow.status}</span>
                        </div>
                        ` : ''}
                    </div>
                </div>
            `;
        });
        
        html += `
                </div>
            </div>
        `;
    } else if (healthData.error) {
        html += `
            <div style="padding: 24px; background: #ef444422; border: 1px solid #ef4444; border-radius: 8px; margin-top: 24px;">
                <div style="font-weight: 600; color: #ef4444; margin-bottom: 8px;">Error Loading Workflows</div>
                <div style="color: var(--text-secondary); font-size: 14px;">${healthData.error}</div>
            </div>
        `;
    } else {
        html += `
            <div style="text-align: center; padding: 40px; color: var(--text-tertiary);">
                <p style="font-size: 48px; margin: 0 0 16px 0;">📋</p>
                <p style="margin: 0;">No workflows found</p>
            </div>
        `;
    }
    
    html += `
        </div>
    `;
    
    container.innerHTML = html;
}
