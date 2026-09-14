import './_group.css';

type PulseItem = {
  value: string;
  label: string;
  detail: string;
  tone?: 'urgent' | 'watch' | 'neutral' | 'healthy';
  compact?: boolean;
};

const priorityItems: PulseItem[] = [
  { value: '124', label: 'Units to Pick', detail: 'Benco: 12 · Exp: 8 · View summary →', tone: 'urgent' },
  { value: '6', label: 'On Hold Units', detail: 'Updated: 8 min ago', tone: 'watch' },
  { value: '12', label: 'Benco Orders', detail: 'Awaiting Shipment', tone: 'neutral', compact: true },
  { value: '3', label: 'Hawaiian Orders', detail: 'Awaiting Shipment', tone: 'neutral', compact: true },
  { value: '4', label: 'Canadian Orders', detail: 'Awaiting Shipment', tone: 'neutral', compact: true },
  { value: '7', label: 'Other International', detail: 'Awaiting Shipment', tone: 'neutral', compact: true },
];

const activityItems: PulseItem[] = [
  { value: '18', label: 'New Orders Since Last Ship', detail: 'Since today', tone: 'neutral' },
  { value: '51 min ago', label: 'Last New Order', detail: 'Sep 14, 2025 at 2:17 PM', tone: 'neutral', compact: true },
  { value: 'just now', label: 'Last Reconciliation', detail: 'ShipStation sync', tone: 'healthy', compact: true },
];

function PriorityCard({ item, lead = false }: { item: PulseItem; lead?: boolean }) {
  return (
    <article className={`priority-card ${item.tone ?? 'neutral'} ${lead ? 'lead-card' : ''} ${item.compact ? 'compact-card' : ''}`}>
      <div className="priority-card-top">
        <span className="priority-kicker">{lead ? 'Needs attention' : item.tone === 'watch' ? 'Review queue' : 'Workload'}</span>
        {lead && <span className="priority-arrow" aria-hidden="true">↗</span>}
      </div>
      <div className="priority-value">{item.value}</div>
      <div className="priority-label">{item.label}</div>
      <div className="priority-detail">{item.detail}</div>
    </article>
  );
}

function HealthRow({ label, value, detail, teal = false }: { label: string; value: string; detail: string; teal?: boolean }) {
  return (
    <div className="health-row">
      <div className={`health-dot ${teal ? 'teal' : ''}`} />
      <div className="health-copy">
        <div className="health-label">{label}</div>
        <div className="health-detail">{detail}</div>
      </div>
      <strong className="health-value">{value}</strong>
    </div>
  );
}

function PulseSection({ mobile = false }: { mobile?: boolean }) {
  return (
    <div className={`context-shell ${mobile ? 'mobile-context' : 'desktop-context'}`}>
      <div className="context-caption">{mobile ? '390px mobile context' : 'Desktop context'}</div>
      <section className="priority-pulse" aria-label="Operational Pulse">
        <div className="priority-header">
          <div>
            <div className="eyebrow">Fulfillment control station</div>
            <h2>Operational Pulse</h2>
          </div>
          <div className="pulse-meta"><span className="live-dot" />Live snapshot <span className="meta-divider">·</span> 2:18 PM</div>
        </div>

        <div className="priority-hero">
          <div className="hero-copy">
            <span className="hero-index">01 / ACTION QUEUE</span>
            <h3>Clear the queue<br /><em>in order.</em></h3>
            <p>Two signals need a decision before the next ship window.</p>
          </div>
          <div className="hero-rule" aria-hidden="true" />
          <div className="hero-summary">
            <span className="summary-label">Open workload</span>
            <strong>130 <small>units</small></strong>
            <span className="summary-note">124 ready · 6 held</span>
          </div>
        </div>

        <div className="action-grid">
          <PriorityCard item={priorityItems[0]} lead />
          <PriorityCard item={priorityItems[1]} lead />
        </div>

        <div className="subsection-heading">
          <span>Special-order lanes</span>
          <span className="subsection-line" />
          <span className="subsection-count">4 lanes</span>
        </div>
        <div className="special-grid">
          {priorityItems.slice(2).map((item) => <PriorityCard key={item.label} item={item} />)}
        </div>

        <div className="lower-grid">
          <div className="health-panel">
            <div className="panel-heading"><span>System condition</span><span className="panel-status">All clear</span></div>
            <HealthRow label="System Status" value="Online" detail="All services operational" teal />
            <HealthRow label="Production Health" value="Healthy" detail="Database and services healthy" teal />
          </div>
          <div className="activity-panel">
            <div className="panel-heading"><span>Activity signals</span><span className="panel-status muted">Passive</span></div>
            <div className="activity-grid">
              {activityItems.map((item) => (
                <div className="activity-item" key={item.label}>
                  <div className="activity-value">{item.value}</div>
                  <div className="activity-label">{item.label}</div>
                  <div className="activity-detail">{item.detail}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

export function PriorityBased() {
  return (
    <main className="dashboard-pulse-preview dark-mode priority-preview">
      <style>{`
        .priority-preview { --ink: #e8eef8; --muted: #91a0ba; --faint: #64748e; --panel: #121d2e; --panel-2: #17243a; --line: rgba(179,198,226,.13); --blue: #4a9bff; --teal: #50c7b7; --amber: #e8b453; }
        .priority-preview .contexts { gap: 30px; }
        .priority-preview .context-shell { border-color: rgba(122,153,196,.25); }
        .priority-pulse { padding: 24px; background: linear-gradient(145deg, #101a2a 0%, #142238 100%); }
        .priority-header { display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:22px; }
        .eyebrow,.hero-index { color:var(--blue); font-size:10px; font-weight:700; letter-spacing:1.35px; text-transform:uppercase; }
        .priority-header h2 { margin:4px 0 0; color:var(--ink); font-size:23px; letter-spacing:-.4px; text-transform:none; }
        .pulse-meta { color:var(--muted); font-size:12px; display:flex; align-items:center; gap:7px; white-space:nowrap; }
        .live-dot,.health-dot { width:7px; height:7px; border-radius:50%; background:var(--teal); box-shadow:0 0 0 3px rgba(80,199,183,.12); }
        .meta-divider { color:var(--faint); }
        .priority-hero { display:grid; grid-template-columns: 1.3fr 1px .8fr; gap:22px; align-items:end; padding:20px 22px; border:1px solid var(--line); border-radius:10px; background:rgba(27,47,76,.52); margin-bottom:14px; }
        .hero-copy h3 { margin:7px 0 7px; color:var(--ink); font-size:31px; line-height:1.02; letter-spacing:-1.2px; }
        .hero-copy h3 em { color:var(--blue); font-style:normal; }
        .hero-copy p { margin:0; color:var(--muted); font-size:13px; }
        .hero-rule { height:74px; background:var(--line); }
        .hero-summary { display:flex; flex-direction:column; gap:4px; }
        .summary-label,.summary-note { color:var(--muted); font-size:11px; }
        .hero-summary strong { color:var(--ink); font-size:38px; line-height:1; letter-spacing:-1px; }
        .hero-summary small { color:var(--muted); font-size:13px; font-weight:500; letter-spacing:0; }
        .action-grid { display:grid; grid-template-columns:1.25fr 1fr; gap:12px; }
        .priority-card { position:relative; padding:16px; border:1px solid var(--line); border-radius:9px; background:var(--panel); transition:transform .2s ease, border-color .2s ease; overflow:hidden; }
        .priority-card:hover { transform:translateY(-2px); border-color:rgba(74,155,255,.55); }
        .priority-card::before { content:''; position:absolute; inset:0 auto 0 0; width:3px; background:var(--faint); }
        .priority-card.urgent::before { background:var(--blue); }
        .priority-card.watch::before { background:var(--amber); }
        .priority-card.healthy::before { background:var(--teal); }
        .priority-card-top { display:flex; justify-content:space-between; min-height:16px; }
        .priority-kicker { color:var(--faint); font-size:10px; font-weight:700; letter-spacing:1px; text-transform:uppercase; }
        .priority-arrow { color:var(--blue); font-size:16px; line-height:12px; }
        .priority-value { margin-top:8px; color:var(--ink); font-size:42px; font-weight:700; line-height:1; font-variant-numeric:tabular-nums; letter-spacing:-1px; }
        .watch .priority-value { color:var(--amber); }
        .priority-label { margin-top:8px; color:var(--ink); font-size:13px; font-weight:600; }
        .priority-detail { margin-top:3px; color:var(--muted); font-size:11px; }
        .compact-card { padding:13px 14px; }
        .compact-card .priority-value { margin-top:7px; font-size:27px; }
        .compact-card .priority-label { margin-top:6px; font-size:12px; }
        .subsection-heading { display:flex; align-items:center; gap:10px; margin:22px 0 10px; color:var(--muted); font-size:11px; font-weight:700; letter-spacing:1px; text-transform:uppercase; }
        .subsection-line { height:1px; flex:1; background:var(--line); }
        .subsection-count { color:var(--faint); font-size:10px; font-weight:500; letter-spacing:.4px; }
        .special-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:9px; }
        .lower-grid { display:grid; grid-template-columns:.9fr 1.6fr; gap:12px; margin-top:12px; }
        .health-panel,.activity-panel { padding:15px; border:1px solid var(--line); border-radius:9px; background:rgba(18,29,46,.72); }
        .panel-heading { display:flex; justify-content:space-between; padding-bottom:11px; color:var(--ink); font-size:11px; font-weight:700; letter-spacing:.8px; text-transform:uppercase; }
        .panel-status { color:var(--teal); font-size:10px; letter-spacing:.5px; }
        .panel-status.muted { color:var(--faint); }
        .health-row { display:flex; align-items:center; gap:10px; padding:11px 0; border-top:1px solid var(--line); }
        .health-copy { min-width:0; flex:1; }
        .health-label { color:var(--ink); font-size:12px; font-weight:600; }
        .health-detail { overflow:hidden; color:var(--muted); font-size:10px; text-overflow:ellipsis; white-space:nowrap; }
        .health-value { color:var(--teal); font-size:12px; }
        .activity-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:0; border-top:1px solid var(--line); }
        .activity-item { padding:11px 12px 0 0; border-right:1px solid var(--line); }
        .activity-item + .activity-item { padding-left:12px; }
        .activity-item:last-child { border-right:0; }
        .activity-value { color:var(--ink); font-size:18px; font-weight:600; }
        .activity-label { margin-top:3px; color:var(--muted); font-size:11px; line-height:1.25; }
        .activity-detail { margin-top:3px; color:var(--faint); font-size:10px; }
        .mobile-context .priority-pulse { padding:14px; }
        .mobile-context .priority-header { margin-bottom:14px; }
        .mobile-context .priority-header h2 { font-size:20px; }
        .mobile-context .pulse-meta { font-size:0; }
        .mobile-context .pulse-meta .live-dot { margin-top:2px; }
        .mobile-context .priority-hero { grid-template-columns:1fr; gap:10px; padding:15px; }
        .mobile-context .hero-copy h3 { font-size:27px; }
        .mobile-context .hero-copy p { font-size:12px; }
        .mobile-context .hero-rule { display:none; }
        .mobile-context .hero-summary { display:grid; grid-template-columns:1fr auto; align-items:end; margin-top:4px; }
        .mobile-context .summary-label { grid-column:1; }
        .mobile-context .hero-summary strong { grid-column:2; grid-row:1 / span 2; font-size:31px; }
        .mobile-context .summary-note { grid-column:1; }
        .mobile-context .action-grid { grid-template-columns:1.15fr 1fr; gap:8px; }
        .mobile-context .priority-card { padding:13px 12px; }
        .mobile-context .priority-value { font-size:34px; }
        .mobile-context .compact-card .priority-value { font-size:23px; }
        .mobile-context .subsection-heading { margin:17px 0 8px; }
        .mobile-context .special-grid { grid-template-columns:1fr 1fr; gap:8px; }
        .mobile-context .lower-grid { grid-template-columns:1fr; gap:8px; margin-top:8px; }
        .mobile-context .activity-grid { grid-template-columns:1fr 1fr 1fr; }
        .mobile-context .activity-item { padding-right:7px; }
        .mobile-context .activity-item + .activity-item { padding-left:7px; }
        .mobile-context .activity-value { font-size:15px; }
        .mobile-context .activity-label { font-size:10px; }
        .mobile-context .activity-detail { font-size:9px; }
        @media (max-width:640px) { .priority-preview { padding:12px; } .priority-preview .desktop-context { overflow-x:visible; } }
      `}</style>
      <div className="contexts">
        <PulseSection />
        <PulseSection mobile />
      </div>
    </main>
  );
}