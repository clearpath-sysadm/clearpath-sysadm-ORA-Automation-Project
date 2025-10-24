/**
 * Oracare Fulfillment - Interactive Guided Tour System
 * Provides step-by-step walkthroughs with spotlight overlays
 */

class GuidedTour {
    constructor(steps) {
        this.steps = steps;
        this.currentStep = 0;
        this.overlay = null;
        this.tooltip = null;
    }

    start() {
        this.createOverlay();
        this.showStep(0);
    }

    createOverlay() {
        // Create dark overlay
        this.overlay = document.createElement('div');
        this.overlay.id = 'tour-overlay';
        this.overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.75);
            z-index: 9998;
            transition: opacity 0.3s ease;
        `;
        document.body.appendChild(this.overlay);

        // Create tooltip
        this.tooltip = document.createElement('div');
        this.tooltip.id = 'tour-tooltip';
        this.tooltip.style.cssText = `
            position: fixed;
            background-color: white;
            border-radius: 12px;
            padding: 24px;
            max-width: 400px;
            z-index: 9999;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            color: #222;
        `;
        document.body.appendChild(this.tooltip);

        // Close on ESC key
        this.escHandler = (e) => {
            if (e.key === 'Escape') this.end();
        };
        document.addEventListener('keydown', this.escHandler);
    }

    showStep(index) {
        if (index >= this.steps.length) {
            this.end();
            return;
        }

        this.currentStep = index;
        const step = this.steps[index];

        // Find target element
        const target = document.querySelector(step.element);
        if (!target) {
            console.warn(`Tour: Element "${step.element}" not found, skipping to next step`);
            this.next();
            return;
        }

        // Highlight target element
        this.highlightElement(target);

        // Position tooltip
        this.positionTooltip(target, step);

        // Update tooltip content
        this.tooltip.innerHTML = `
            <div style="margin-bottom: 16px;">
                <div style="font-size: 12px; color: #5A6B8C; font-weight: 600; margin-bottom: 8px;">
                    STEP ${index + 1} OF ${this.steps.length}
                </div>
                <h3 style="font-size: 18px; font-weight: 600; margin-bottom: 8px; color: #222;">
                    ${step.title}
                </h3>
                <p style="font-size: 14px; line-height: 1.6; color: #555;">
                    ${step.content}
                </p>
            </div>
            <div style="display: flex; gap: 12px; justify-content: flex-end;">
                ${index > 0 ? `<button onclick="tour.previous()" style="background: white; border: 1px solid #D1D5DB; color: #374151; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: 500; box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);">← Back</button>` : ''}
                ${index < this.steps.length - 1 
                    ? `<button onclick="tour.next()" style="background: white; border: 1px solid #D1D5DB; color: #374151; padding: 8px 20px; border-radius: 6px; cursor: pointer; font-weight: 500; box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);">Next →</button>`
                    : `<button onclick="tour.end()" style="background: white; border: 1px solid #D1D5DB; color: #374151; padding: 8px 20px; border-radius: 6px; cursor: pointer; font-weight: 500; box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);">Finish ✓</button>`
                }
            </div>
            <button onclick="tour.end()" style="position: absolute; top: 16px; right: 16px; background: none; border: none; font-size: 24px; color: #999; cursor: pointer; padding: 0; width: 32px; height: 32px;">×</button>
        `;
    }

    highlightElement(element) {
        // Remove previous highlights
        document.querySelectorAll('.tour-highlight').forEach(el => {
            el.classList.remove('tour-highlight');
        });

        // Add highlight to current element
        element.classList.add('tour-highlight');
        element.style.position = 'relative';
        element.style.zIndex = '9999';
        element.style.boxShadow = '0 0 0 4px rgba(90, 107, 140, 0.5)';
        element.style.borderRadius = '8px';

        // Scroll element into view
        element.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    positionTooltip(target, step) {
        const rect = target.getBoundingClientRect();
        const tooltipWidth = 400;
        const tooltipHeight = this.tooltip.offsetHeight || 200;

        let top, left;

        // Determine best position
        const position = step.position || 'bottom';

        switch (position) {
            case 'top':
                top = rect.top - tooltipHeight - 20;
                left = rect.left + (rect.width / 2) - (tooltipWidth / 2);
                break;
            case 'bottom':
                top = rect.bottom + 20;
                left = rect.left + (rect.width / 2) - (tooltipWidth / 2);
                break;
            case 'left':
                top = rect.top + (rect.height / 2) - (tooltipHeight / 2);
                left = rect.left - tooltipWidth - 20;
                break;
            case 'right':
                top = rect.top + (rect.height / 2) - (tooltipHeight / 2);
                left = rect.right + 20;
                break;
        }

        // Keep tooltip within viewport
        if (left < 10) left = 10;
        if (left + tooltipWidth > window.innerWidth - 10) {
            left = window.innerWidth - tooltipWidth - 10;
        }
        if (top < 10) top = 10;

        this.tooltip.style.top = `${top}px`;
        this.tooltip.style.left = `${left}px`;
    }

    next() {
        this.showStep(this.currentStep + 1);
    }

    previous() {
        this.showStep(this.currentStep - 1);
    }

    end() {
        // Remove highlights
        document.querySelectorAll('.tour-highlight').forEach(el => {
            el.classList.remove('tour-highlight');
            el.style.position = '';
            el.style.zIndex = '';
            el.style.boxShadow = '';
        });

        // Remove overlay and tooltip
        if (this.overlay) this.overlay.remove();
        if (this.tooltip) this.tooltip.remove();
        
        // Remove event listener
        document.removeEventListener('keydown', this.escHandler);

        // Clear tour instance
        window.tour = null;
    }
}

// Tour definitions
const TOURS = {
    welcome: [
        {
            element: '.page-title',
            title: 'Welcome to Oracare Fulfillment!',
            content: 'This dashboard shows your fulfillment operations in real-time. Let\'s take a quick tour of the key features.',
            position: 'bottom'
        },
        {
            element: '[href="/"]',
            title: 'Dashboard',
            content: 'Your main hub. Monitor operations, check KPIs, and generate reports from here.',
            position: 'right'
        },
        {
            element: '[href="/xml_import.html"]',
            title: 'Orders Inbox',
            content: 'View all pending orders. XML files are imported automatically every 5 minutes and uploaded to ShipStation.',
            position: 'right'
        },
        {
            element: '.kpi-grid',
            title: 'Key Performance Indicators',
            content: 'These cards show real-time metrics: units in ShipStation, local database, and special order categories. Updates automatically every 30 seconds.',
            position: 'bottom'
        },
        {
            element: '.kpi-card:first-child',
            title: 'ShipStation Units',
            content: 'Shows how many units are currently in ShipStation awaiting shipment. This syncs with ShipStation every 5 minutes.',
            position: 'bottom'
        },
        {
            element: '[href="/lot_inventory.html"]',
            title: 'Lot Inventory',
            content: 'Track inventory levels by SKU and lot number. Red badges warn when stock is running low.',
            position: 'right'
        },
        {
            element: '#weekly-inventory-section',
            title: 'Weekly Inventory Report',
            content: 'See current inventory levels and 52-week averages. Use the EOW button to generate reports for manufacturer and customer.',
            position: 'top'
        },
        {
            element: '.quick-action-btn:has([class*="EOW"])',
            title: 'Report Buttons',
            content: 'EOD (End of Day) syncs shipped items. EOW (End of Week) generates weekly inventory report. EOM (End of Month) generates chargeback report.',
            position: 'top'
        }
    ],

    'orders-inbox': [
        {
            element: '.card-header h2',
            title: 'Orders Inbox',
            content: 'All pending orders appear here. They automatically import from XML files and upload to ShipStation every 5 minutes.',
            position: 'bottom'
        },
        {
            element: '.action-btn:has([class*="Validate"])',
            title: 'Validate Button',
            content: 'Click to check orders for errors before they upload to ShipStation.',
            position: 'bottom'
        },
        {
            element: '.action-btn:has([class*="Manual"])',
            title: 'Manual Import',
            content: 'Use this if an order didn\'t auto-import from XML. You can manually enter order details.',
            position: 'bottom'
        },
        {
            element: '.action-btn:has([class*="Sync"])',
            title: 'Sync Manual',
            content: 'Force synchronization with ShipStation. Use this if orders seem stuck.',
            position: 'bottom'
        },
        {
            element: '.table-container',
            title: 'Orders Table',
            content: 'View order details: number, date, company, SKU, quantity, status, and tracking. Use search to find specific orders.',
            position: 'top'
        }
    ],

    inventory: [
        {
            element: '.page-title',
            title: 'Lot Inventory',
            content: 'Track current inventory levels by SKU and lot number. The system automatically calculates quantities based on shipments.',
            position: 'bottom'
        },
        {
            element: '.table-container',
            title: 'Inventory Table',
            content: 'Shows current quantities, pallet breakdown, 52-week averages, and days of inventory remaining. Red badges indicate low stock.',
            position: 'top'
        },
        {
            element: '.badge.danger',
            title: 'Low Inventory Warning',
            content: 'Red badges (e.g., "11 days") warn when stock is running low. Coordinate with manufacturer to restock.',
            position: 'left'
        }
    ],

    reports: [
        {
            element: '.page-title',
            title: 'Weekly Reports',
            content: 'View shipped order history and generate weekly inventory reports with 52-week rolling averages.',
            position: 'bottom'
        }
    ],

    dashboard: [
        {
            element: '.kpi-grid',
            title: 'Dashboard KPIs',
            content: 'Monitor your fulfillment operations at a glance. These cards update automatically every 30 seconds.',
            position: 'bottom'
        },
        {
            element: '.kpi-card:nth-child(1)',
            title: 'ShipStation Units',
            content: 'Units currently in ShipStation awaiting shipment. Updates from ShipStation API every 5 minutes.',
            position: 'bottom'
        },
        {
            element: '.kpi-card:nth-child(2)',
            title: 'Local DB Units',
            content: 'Units in local database ready to upload to ShipStation. Auto-uploads every 5 minutes.',
            position: 'bottom'
        },
        {
            element: '.kpi-card:nth-child(3)',
            title: 'Benco Orders',
            content: 'Special tracking for Benco orders awaiting shipment.',
            position: 'bottom'
        },
        {
            element: '.kpi-card:nth-child(4)',
            title: 'Hawaiian Orders',
            content: 'Special tracking for Hawaiian orders (must ship via FedEx 2Day).',
            position: 'bottom'
        }
    ]
};

// Initialize tour on page load
document.addEventListener('DOMContentLoaded', function() {
    // Check if tour should auto-start
    const tourToStart = localStorage.getItem('startTour');
    if (tourToStart && TOURS[tourToStart]) {
        localStorage.removeItem('startTour');
        setTimeout(() => {
            window.tour = new GuidedTour(TOURS[tourToStart]);
            window.tour.start();
        }, 500);
    }

    // Welcome tour disabled - users can access from Help & Training page
    // const hasSeenWelcome = localStorage.getItem('hasSeenWelcomeTour');
    // if (!hasSeenWelcome && window.location.pathname === '/') {
    //     localStorage.setItem('hasSeenWelcomeTour', 'true');
    //     
    //     // Show welcome modal
    //     const welcomeModal = document.createElement('div');
    //     welcomeModal.id = 'welcome-tour-modal';
    //     welcomeModal.style.cssText = `
    //         position: fixed;
    //         top: 0;
    //         left: 0;
    //         width: 100%;
    //         height: 100%;
    //         background-color: rgba(0, 0, 0, 0.8);
    //         display: flex;
    //         align-items: center;
    //         justify-content: center;
    //         z-index: 10000;
    //     `;
    //     welcomeModal.innerHTML = `
    //         <div style="background: white; border-radius: 16px; padding: 40px; max-width: 500px; text-align: center;">
    //             <h2 style="font-size: 24px; margin-bottom: 16px; color: #222;">👋 Welcome to Oracare Fulfillment!</h2>
    //             <p style="font-size: 16px; line-height: 1.6; color: #555; margin-bottom: 24px;">
    //                 This system handles your fulfillment operations automatically. Would you like a quick 3-minute tour to get started?
    //             </p>
    //             <div style="display: flex; gap: 12px; justify-content: center;">
    //                 <button onclick="document.getElementById('welcome-tour-modal').remove()" style="background: white; border: 1px solid #D1D5DB; color: #374151; padding: 12px 24px; border-radius: 6px; cursor: pointer; font-weight: 500; box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);">Skip for now</button>
    //                 <button onclick="document.getElementById('welcome-tour-modal').remove(); window.tour = new GuidedTour(TOURS.welcome); window.tour.start();" style="background: white; border: 1px solid #D1D5DB; color: #374151; padding: 12px 24px; border-radius: 6px; cursor: pointer; font-weight: 500; box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);">Start Tour →</button>
    //             </div>
    //         </div>
    //     `;
    //     document.body.appendChild(welcomeModal);
    // }
});

// Global function to start tours
function startTour(tourName) {
    if (TOURS[tourName]) {
        window.tour = new GuidedTour(TOURS[tourName]);
        window.tour.start();
    }
}
