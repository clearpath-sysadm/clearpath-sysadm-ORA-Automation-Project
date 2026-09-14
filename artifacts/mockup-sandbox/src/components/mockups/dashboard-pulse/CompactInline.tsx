import './_group.css';

type PulseCard = {
  value: string;
  label: string;
  change: string;
  accent?: 'blue' | 'teal' | 'gold';
};

const workloadCards: PulseCard[] = [
  { value: '124', label: 'Units to Pick', change: 'Benco: 12 · Exp: 8 · View summary →', accent: 'blue' },
  { value: '6', label: 'On Hold Units', change: 'Updated: 8 min ago', accent: 'gold' },
  { value: '12', label: 'Benco Orders', change: 'Awaiting Shipment', accent: 'blue' },
  { value: '3', label: 'Hawaiian Orders', change: 'Awaiting Shipment', accent: 'teal' },
  { value: '4', label: 'Canadian Orders', change: 'Awaiting Shipment', accent: 'teal' },
  { value: '7', label: 'Other International', change: 'Awaiting Shipment', accent: 'teal' },
];

const activityItems = [
  { value: '18', label: 'New Orders Since Last Ship', detail: 'Since today', kind: 'count' },
  { value: '51 min ago', label: 'Last New Order', detail: 'Sep 14, 2025 at 2:17 PM', kind: 'time' },
  { value: 'just now', label: 'Last Reconciliation', detail: 'ShipStation sync', kind: 'time' },
];

function WorkloadCard({ card, index }: { card: PulseCard; index: number }) {
  return (
    <article className={`compact-card compact-card-${card.accent}`} style={{ animationDelay: `${index * 45}ms` }}>
      <div className="compact-card-topline">
        <span className="compact-kicker">{index === 0 ? 'Priority queue' : 'Awaiting shipment'}</span>
        <span className="compact-index">0{index + 1}</span>
      </div>
      <div className="compact-value">{card.value}</div>
      <div className="compact-label">{card.label}</div>
      <div className="compact-change">{card.change}</div>
    </article>
  );
}

function HealthSignal({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <div className="health-signal">
      <span className="health-dot" aria-hidden="true" />
      <div>
        <div className="health-label">{label}</div>
        <div className="health-value">{value}</div>
      </div>
      <span className="health-detail">{detail}</span>
    </div>
  );
}

function PulseSection({ mobile = false }: { mobile?: boolean }) {
  return (
    <div className={`context-shell ${mobile ? 'mobile-context' : 'desktop-context'}`}>
      <div className="context-caption">{mobile ? '390px mobile context' : 'Desktop context'}</div>
      <section className="compact-pulse" aria-label="Operational Pulse">
        <div className="compact-heading">
          <div>
            <div className="compact-eyebrow">Today · Tue, Sep 14</div>
            <h2>Operational Pulse</h2>
          </div>
          <div className="compact-live"><span />Live snapshot</div>
        </div>

        <div className="workload-header">
          <span>Workload</span>
          <span>6 queues</span>
        </div>
        <div className="workload-grid">
          {workloadCards.map((card, index) => <WorkloadCard key={card.label} card={card} index={index} />)}
        </div>

        <div className="secondary-row">
          <div className="health-panel">
            <div className="panel-label">System condition</div>
            <div className="health-signals">
              <HealthSignal label="System Status" value="Online" detail="All services operational" />
              <HealthSignal label="Production Health" value="Healthy" detail="Database and services healthy" />
            </div>
          </div>
          <div className="activity-panel">
            <div className="panel-label">Recent activity</div>
            <div className="activity-list">
              {activityItems.map((item) => (
                <div className="activity-item" key={item.label}>
                  <div className={`activity-value activity-${item.kind}`}>{item.value}</div>
                  <div className="activity-copy">
                    <div className="activity-label">{item.label}</div>
                    <div className="activity-detail">{item.detail}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

export function CompactInline() {
  return (
    <main className="dashboard-pulse-preview dark-mode compact-inline-preview">
      <style>{`
        .compact-inline-preview { padding: 28px; background: #101726; }
        .compact-inline-preview .contexts { gap: 28px; max-width: 1500px; }
        .compact-pulse { padding: 22px; background: #182337; }
        .compact-heading { display:flex; align-items:flex-end; justify-content:space-between; gap:16px; margin-bottom:22px; }
        .compact-eyebrow { margin-bottom:4px; color:#6B7B96; font-size:11px; font-weight:600; letter-spacing:1.1px; text-transform:uppercase; }
        .compact-heading h2 { margin:0; color:#E3E9F5; font-size:20px; line-height:1.2; font-weight:600; letter-spacing:-.2px; }
        .compact-live { display:flex; align-items:center; gap:7px; color:#8dcac5; font-size:12px; white-space:nowrap; }
        .compact-live span { width:7px; height:7px; border-radius:50%; background:#3CAEA3; box-shadow:0 0 0 3px rgba(60,174,163,.12); }
        .workload-header, .panel-label { display:flex; justify-content:space-between; margin-bottom:10px; color:#A5B4CD; font-size:11px; font-weight:600; letter-spacing:.85px; text-transform:uppercase; }
        .workload-header span:last-child { color:#6B7B96; font-weight:500; }
        .workload-grid { display:grid; grid-template-columns:repeat(6, minmax(0, 1fr)); gap:10px; }
        .compact-card { position:relative; min-width:0; overflow:hidden; padding:13px 14px 14px; border:1px solid rgba(227,233,245,.08); border-radius:8px; background:#1F2F47; box-shadow:0 1px 3px rgba(0,0,0,.2); animation: compact-rise .4s ease-out both; transition:transform .2s ease, border-color .2s ease; }
        .compact-card:hover { transform:translateY(-2px); border-color:rgba(43,125,233,.55); }
        .compact-card::before { position:absolute; top:0; left:0; width:100%; height:3px; background:#2B7DE9; content:''; }
        .compact-card-teal::before { background:#3CAEA3; }
        .compact-card-gold::before { background:#F2C14E; }
        .compact-card-topline { display:flex; justify-content:space-between; color:#6B7B96; font-size:10px; font-weight:600; letter-spacing:.55px; text-transform:uppercase; }
        .compact-index { color:#536581; font-variant-numeric:tabular-nums; }
        .compact-value { margin-top:14px; color:#E3E9F5; font-size:30px; line-height:1; font-weight:700; font-variant-numeric:tabular-nums; }
        .compact-label { margin-top:9px; color:#D4DDED; font-size:12px; font-weight:600; line-height:1.25; }
        .compact-change { margin-top:8px; min-height:16px; color:#7F91AE; font-size:10px; line-height:1.35; }
        .secondary-row { display:grid; grid-template-columns:minmax(280px,.72fr) minmax(460px,1.28fr); gap:10px; margin-top:18px; }
        .health-panel, .activity-panel { padding:13px 14px; border:1px solid rgba(227,233,245,.08); border-radius:8px; background:#152238; }
        .health-signals { display:grid; grid-template-columns:1fr 1fr; gap:14px; }
        .health-signal { display:grid; grid-template-columns:8px 1fr; column-gap:8px; align-items:start; }
        .health-dot { width:8px; height:8px; margin-top:4px; border-radius:50%; background:#3CAEA3; box-shadow:0 0 0 3px rgba(60,174,163,.1); }
        .health-label, .activity-label { color:#8D9DB7; font-size:10px; font-weight:600; letter-spacing:.45px; text-transform:uppercase; }
        .health-value { margin-top:2px; color:#E3E9F5; font-size:14px; font-weight:600; }
        .health-detail { grid-column:2; margin-top:3px; color:#6B7B96; font-size:10px; line-height:1.3; }
        .activity-list { display:grid; grid-template-columns:repeat(3,1fr); }
        .activity-item { display:flex; align-items:center; gap:10px; padding:0 14px; border-left:1px solid rgba(227,233,245,.09); }
        .activity-item:first-child { padding-left:0; border-left:0; }
        .activity-value { color:#E3E9F5; font-size:17px; font-weight:600; line-height:1; font-variant-numeric:tabular-nums; white-space:nowrap; }
        .activity-count { color:#72aaf0; font-size:24px; }
        .activity-copy { min-width:0; }
        .activity-detail { margin-top:3px; color:#6B7B96; font-size:10px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
        @keyframes compact-rise { from { opacity:0; transform:translateY(6px); } to { opacity:1; transform:translateY(0); } }
        .compact-inline-preview .mobile-context .compact-pulse { padding:14px 12px 12px; }
        .compact-inline-preview .mobile-context .compact-heading { align-items:flex-start; margin-bottom:18px; }
        .compact-inline-preview .mobile-context .compact-heading h2 { font-size:18px; }
        .compact-inline-preview .mobile-context .compact-live { padding-top:3px; font-size:10px; }
        .compact-inline-preview .mobile-context .workload-grid { grid-template-columns:repeat(2, minmax(0,1fr)); gap:8px; }
        .compact-inline-preview .mobile-context .compact-card { padding:11px 11px 12px; }
        .compact-inline-preview .mobile-context .compact-card-topline { font-size:9px; }
        .compact-inline-preview .mobile-context .compact-value { margin-top:11px; font-size:25px; }
        .compact-inline-preview .mobile-context .compact-label { font-size:11px; }
        .compact-inline-preview .mobile-context .compact-change { font-size:9px; }
        .compact-inline-preview .mobile-context .secondary-row { grid-template-columns:1fr; gap:8px; margin-top:14px; }
        .compact-inline-preview .mobile-context .health-panel, .compact-inline-preview .mobile-context .activity-panel { padding:11px; }
        .compact-inline-preview .mobile-context .health-signals { gap:8px; }
        .compact-inline-preview .mobile-context .health-label, .compact-inline-preview .mobile-context .activity-label { font-size:9px; }
        .compact-inline-preview .mobile-context .health-value { font-size:13px; }
        .compact-inline-preview .mobile-context .health-detail, .compact-inline-preview .mobile-context .activity-detail { font-size:9px; }
        .compact-inline-preview .mobile-context .activity-list { grid-template-columns:1fr; gap:0; }
        .compact-inline-preview .mobile-context .activity-item, .compact-inline-preview .mobile-context .activity-item:first-child { min-height:38px; padding:7px 0; border-top:1px solid rgba(227,233,245,.09); border-left:0; }
        .compact-inline-preview .mobile-context .activity-item:first-child { padding-top:0; border-top:0; }
        .compact-inline-preview .mobile-context .activity-value { min-width:64px; font-size:15px; }
        .compact-inline-preview .mobile-context .activity-count { font-size:22px; }
        @media (max-width: 640px) {
          .compact-inline-preview { padding:12px; }
          .compact-inline-preview .contexts { gap:18px; }
          .compact-pulse { padding:14px 12px 12px; }
          .compact-heading { align-items:flex-start; margin-bottom:18px; }
          .compact-heading h2 { font-size:18px; }
          .compact-live { padding-top:3px; font-size:10px; }
          .workload-grid { grid-template-columns:repeat(2, minmax(0,1fr)); gap:8px; }
          .compact-card { padding:11px 11px 12px; }
          .compact-card-topline { font-size:9px; }
          .compact-value { margin-top:11px; font-size:25px; }
          .compact-label { font-size:11px; }
          .compact-change { font-size:9px; }
          .secondary-row { grid-template-columns:1fr; gap:8px; margin-top:14px; }
          .health-panel, .activity-panel { padding:11px; }
          .health-signals { gap:8px; }
          .health-label, .activity-label { font-size:9px; }
          .health-value { font-size:13px; }
          .health-detail, .activity-detail { font-size:9px; }
          .activity-list { grid-template-columns:1fr; gap:0; }
          .activity-item, .activity-item:first-child { min-height:38px; padding:7px 0; border-top:1px solid rgba(227,233,245,.09); border-left:0; }
          .activity-item:first-child { padding-top:0; border-top:0; }
          .activity-value { min-width:64px; font-size:15px; }
          .activity-count { font-size:22px; }
        }
      `}</style>
      <div className="contexts">
        <PulseSection />
        <PulseSection mobile />
      </div>
    </main>
  );
}