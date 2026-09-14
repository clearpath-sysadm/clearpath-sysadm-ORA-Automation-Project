import './_group.css';

type PulseCard = {
  value: string;
  label: string;
  change: string;
  valueClass?: string;
  changeClass?: string;
  status?: 'green' | 'gray';
};

const pulseCards: PulseCard[] = [
  { value: '124', label: 'Units to Pick', change: 'Benco: 12 · Exp: 8 · View summary →', changeClass: 'pulse-change-compact' },
  { value: '6', label: 'On Hold Units', change: 'Updated: 8 min ago', changeClass: 'pulse-change-compact' },
  { value: '12', label: 'Benco Orders', change: 'Awaiting Shipment' },
  { value: '3', label: 'Hawaiian Orders', change: 'Awaiting Shipment' },
  { value: '4', label: 'Canadian Orders', change: 'Awaiting Shipment' },
  { value: '7', label: 'Other International', change: 'Awaiting Shipment' },
  { value: 'Online', label: 'System Status', change: 'All services operational', status: 'green' },
  { value: 'Healthy', label: 'Production Health', change: 'Database and services healthy', status: 'green' },
  { value: '18', label: 'New Orders Since Last Ship', change: 'Since today', valueClass: 'pulse-value-large', changeClass: 'pulse-change-compact' },
  { value: '51 min ago', label: 'Last New Order', change: 'Sep 14, 2025 at 2:17 PM', valueClass: 'pulse-value-time', changeClass: 'pulse-change-compact' },
  { value: 'just now', label: 'Last Reconciliation', change: 'ShipStation sync', valueClass: 'pulse-value-time', changeClass: 'pulse-change-compact' },
];

function PulseCardView({ card }: { card: PulseCard }) {
  return (
    <div className="stat-card">
      <div className={`stat-value ${card.valueClass ?? ''}`}>
        {card.status && <span className={`status-indicator status-${card.status}`} />}
        {card.value}
      </div>
      <div className="stat-label">{card.label}</div>
      <div className={`stat-change ${card.changeClass ?? ''}`}>{card.change}</div>
    </div>
  );
}

function PulseSection({ mobile = false }: { mobile?: boolean }) {
  return (
    <div className={`context-shell ${mobile ? 'mobile-context' : 'desktop-context'}`}>
      <div className="context-caption">{mobile ? '390px mobile context' : 'Desktop context'}</div>
      <section className="pulse-section" aria-label="Operational Pulse">
        <div className="pulse-section-toggle">
          <h2>Operational Pulse</h2>
          <span className="pulse-chevron" aria-hidden="true">▾</span>
        </div>
        <div className="stats-grid">
          {pulseCards.map((card) => (
            <PulseCardView key={card.label} card={card} />
          ))}
        </div>
      </section>
    </div>
  );
}

export function Current() {
  return (
    <main className="dashboard-pulse-preview dark-mode min-h-screen">
      <div className="contexts">
        <PulseSection />
        <PulseSection mobile />
      </div>
    </main>
  );
}