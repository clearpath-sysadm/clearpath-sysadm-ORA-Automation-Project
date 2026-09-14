import './_group.css';

type WorkloadItem = {
  value: string;
  label: string;
  detail: string;
  emphasis?: boolean;
};

const workloadItems: WorkloadItem[] = [
  { value: '124', label: 'Units to Pick', detail: 'Benco: 12 · Exp: 8 · View summary →', emphasis: true },
  { value: '6', label: 'On Hold Units', detail: 'Updated: 8 min ago', emphasis: true },
  { value: '12', label: 'Benco Orders', detail: 'Awaiting Shipment' },
  { value: '3', label: 'Hawaiian Orders', detail: 'Awaiting Shipment' },
  { value: '4', label: 'Canadian Orders', detail: 'Awaiting Shipment' },
  { value: '7', label: 'Other International', detail: 'Awaiting Shipment' },
];

function WorkloadBlock() {
  return (
    <section className="ga-workload" aria-labelledby="ga-workload-heading">
      <div className="ga-section-heading">
        <div>
          <span className="ga-kicker">Action queue</span>
          <h3 id="ga-workload-heading">Workload</h3>
        </div>
        <span className="ga-heading-note">6 signals</span>
      </div>
      <div className="ga-workload-grid">
        {workloadItems.map((item, index) => (
          <article className={`ga-workload-item ${item.emphasis ? 'ga-workload-item--emphasis' : ''}`} key={item.label}>
            <span className="ga-index">{String(index + 1).padStart(2, '0')}</span>
            <div className="ga-item-copy">
              <div className="ga-workload-value">{item.value}</div>
              <div className="ga-workload-label">{item.label}</div>
              <div className="ga-workload-detail">{item.detail}</div>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function HealthRow({ label, value, detail, tone = 'teal' }: { label: string; value: string; detail: string; tone?: 'teal' | 'blue' }) {
  return (
    <div className="ga-health-row">
      <span className={`ga-status-dot ga-status-dot--${tone}`} aria-hidden="true" />
      <div className="ga-health-copy">
        <span className="ga-health-label">{label}</span>
        <strong>{value}</strong>
      </div>
      <span className="ga-health-detail">{detail}</span>
    </div>
  );
}

function ActivityModule() {
  return (
    <section className="ga-activity" aria-labelledby="ga-activity-heading">
      <div className="ga-activity-header">
        <div>
          <span className="ga-kicker">System monitor</span>
          <h3 id="ga-activity-heading">Activity &amp; health</h3>
        </div>
        <span className="ga-live-chip"><span />Live</span>
      </div>

      <div className="ga-health-list">
        <HealthRow label="System Status" value="Online" detail="All services operational" />
        <HealthRow label="Production Health" value="Healthy" detail="Database and services healthy" />
      </div>

      <div className="ga-activity-divider">
        <span>Recent movement</span>
      </div>

      <div className="ga-activity-list">
        <div className="ga-activity-row ga-activity-row--orders">
          <div className="ga-activity-mark">+</div>
          <div className="ga-activity-copy">
            <span>New Orders Since Last Ship</span>
            <strong>18</strong>
          </div>
          <small>Since today</small>
        </div>
        <div className="ga-activity-row">
          <div className="ga-activity-mark ga-activity-mark--muted">↗</div>
          <div className="ga-activity-copy">
            <span>Last New Order</span>
            <strong>51 min ago</strong>
          </div>
          <small>Sep 14, 2025 at 2:17 PM</small>
        </div>
        <div className="ga-activity-row">
          <div className="ga-activity-mark ga-activity-mark--muted">↻</div>
          <div className="ga-activity-copy">
            <span>Last Reconciliation</span>
            <strong>just now</strong>
          </div>
          <small>ShipStation sync</small>
        </div>
      </div>
    </section>
  );
}

function PulseContext({ mobile = false }: { mobile?: boolean }) {
  return (
    <div className={`context-shell ${mobile ? 'mobile-context' : 'desktop-context'}`}>
      <div className="context-caption">{mobile ? '390px mobile context' : 'Desktop context'}</div>
      <section className="ga-pulse-section" aria-label="Operational Pulse">
        <div className="ga-titlebar">
          <div>
            <span className="ga-eyebrow">Fulfillment control station</span>
            <h2>Operational Pulse</h2>
          </div>
          <span className="ga-updated">Updated 2 min ago</span>
        </div>
        <div className="ga-composition">
          <WorkloadBlock />
          <ActivityModule />
        </div>
      </section>
    </div>
  );
}

export function GroupedActivity() {
  return (
    <main className="dashboard-pulse-preview dark-mode min-h-screen">
      <style>{`
        .dashboard-pulse-preview .ga-pulse-section { padding: 24px; background: var(--bg-secondary); }
        .dashboard-pulse-preview .ga-titlebar { display:flex; justify-content:space-between; align-items:flex-end; gap:16px; margin-bottom:22px; padding-bottom:16px; border-bottom:1px solid var(--border-color); }
        .dashboard-pulse-preview .ga-eyebrow, .dashboard-pulse-preview .ga-kicker { display:block; color:var(--accent-blue); font-size:10px; font-weight:700; letter-spacing:1.2px; text-transform:uppercase; }
        .dashboard-pulse-preview .ga-titlebar h2, .dashboard-pulse-preview .ga-section-heading h3, .dashboard-pulse-preview .ga-activity-header h3 { margin:3px 0 0; color:var(--text-primary); font-size:20px; font-weight:600; letter-spacing:-.3px; }
        .dashboard-pulse-preview .ga-updated, .dashboard-pulse-preview .ga-heading-note { color:var(--text-tertiary); font-size:11px; white-space:nowrap; }
        .dashboard-pulse-preview .ga-composition { display:grid; grid-template-columns:minmax(0,1.55fr) minmax(340px,.9fr); gap:20px; align-items:start; }
        .dashboard-pulse-preview .ga-section-heading, .dashboard-pulse-preview .ga-activity-header { display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:14px; }
        .dashboard-pulse-preview .ga-section-heading h3, .dashboard-pulse-preview .ga-activity-header h3 { font-size:16px; }
        .dashboard-pulse-preview .ga-workload-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); border:1px solid var(--border-color); border-radius:8px; overflow:hidden; background:var(--bg-primary); }
        .dashboard-pulse-preview .ga-workload-item { min-height:126px; position:relative; display:flex; gap:12px; padding:18px 16px 15px; border-right:1px solid var(--border-color); border-bottom:1px solid var(--border-color); transition:background .2s, transform .2s; }
        .dashboard-pulse-preview .ga-workload-item:nth-child(3n) { border-right:0; }
        .dashboard-pulse-preview .ga-workload-item:nth-child(n+4) { border-bottom:0; }
        .dashboard-pulse-preview .ga-workload-item:hover { background:var(--bg-tertiary); }
        .dashboard-pulse-preview .ga-workload-item--emphasis { background:linear-gradient(135deg, rgba(43,125,233,.13), rgba(31,47,71,.18)); }
        .dashboard-pulse-preview .ga-index { color:var(--text-tertiary); font-size:10px; font-weight:600; letter-spacing:.5px; }
        .dashboard-pulse-preview .ga-item-copy { min-width:0; }
        .dashboard-pulse-preview .ga-workload-value { color:var(--text-primary); font-size:30px; font-weight:700; line-height:1; font-variant-numeric:tabular-nums; }
        .dashboard-pulse-preview .ga-workload-label { margin-top:8px; color:var(--text-secondary); font-size:12px; font-weight:600; line-height:1.2; }
        .dashboard-pulse-preview .ga-workload-detail { margin-top:7px; color:var(--text-tertiary); font-size:10px; line-height:1.35; }
        .dashboard-pulse-preview .ga-activity { border:1px solid var(--border-color); border-radius:8px; background:var(--bg-primary); overflow:hidden; }
        .dashboard-pulse-preview .ga-activity-header { margin:0; padding:18px 18px 15px; border-bottom:1px solid var(--border-color); }
        .dashboard-pulse-preview .ga-live-chip { display:flex; align-items:center; gap:6px; color:var(--success-teal); font-size:11px; font-weight:600; }
        .dashboard-pulse-preview .ga-live-chip span { width:6px; height:6px; border-radius:50%; background:var(--success-teal); }
        .dashboard-pulse-preview .ga-health-list { padding:2px 18px; }
        .dashboard-pulse-preview .ga-health-row { display:flex; align-items:center; gap:10px; min-height:53px; border-bottom:1px solid var(--border-translucent); }
        .dashboard-pulse-preview .ga-status-dot { width:7px; height:7px; flex:0 0 7px; border-radius:50%; }
        .dashboard-pulse-preview .ga-status-dot--teal { background:var(--success-teal); }
        .dashboard-pulse-preview .ga-status-dot--blue { background:var(--accent-blue); }
        .dashboard-pulse-preview .ga-health-copy { display:flex; flex-direction:column; min-width:112px; }
        .dashboard-pulse-preview .ga-health-label, .dashboard-pulse-preview .ga-activity-copy span { color:var(--text-tertiary); font-size:10px; text-transform:uppercase; letter-spacing:.45px; }
        .dashboard-pulse-preview .ga-health-copy strong { color:var(--text-primary); font-size:14px; line-height:1.25; }
        .dashboard-pulse-preview .ga-health-detail, .dashboard-pulse-preview .ga-activity-row small { margin-left:auto; color:var(--text-tertiary); font-size:10px; text-align:right; }
        .dashboard-pulse-preview .ga-activity-divider { display:flex; align-items:center; gap:10px; padding:15px 18px 6px; color:var(--text-tertiary); font-size:10px; font-weight:600; letter-spacing:.8px; text-transform:uppercase; }
        .dashboard-pulse-preview .ga-activity-divider:after { content:''; height:1px; flex:1; background:var(--border-translucent); }
        .dashboard-pulse-preview .ga-activity-list { padding:0 18px 9px; }
        .dashboard-pulse-preview .ga-activity-row { display:grid; grid-template-columns:24px minmax(0,1fr) auto; align-items:center; gap:9px; min-height:54px; border-bottom:1px solid var(--border-translucent); }
        .dashboard-pulse-preview .ga-activity-row:last-child { border-bottom:0; }
        .dashboard-pulse-preview .ga-activity-mark { display:grid; width:22px; height:22px; place-items:center; border:1px solid rgba(43,125,233,.4); border-radius:5px; color:var(--accent-blue); font-size:14px; }
        .dashboard-pulse-preview .ga-activity-mark--muted { border-color:var(--border-color); color:var(--text-tertiary); font-size:12px; }
        .dashboard-pulse-preview .ga-activity-copy { display:flex; flex-direction:column; gap:1px; min-width:0; }
        .dashboard-pulse-preview .ga-activity-copy strong { color:var(--text-primary); font-size:14px; font-weight:600; line-height:1.25; }
        .dashboard-pulse-preview .ga-activity-row--orders .ga-activity-copy strong { color:var(--accent-blue); font-size:22px; }
        .dashboard-pulse-preview .mobile-context .ga-pulse-section { padding:14px; }
        .dashboard-pulse-preview .mobile-context .ga-titlebar { align-items:flex-start; margin-bottom:15px; padding-bottom:12px; }
        .dashboard-pulse-preview .mobile-context .ga-titlebar h2 { font-size:18px; }
        .dashboard-pulse-preview .mobile-context .ga-updated { font-size:9px; }
        .dashboard-pulse-preview .mobile-context .ga-composition { display:block; }
        .dashboard-pulse-preview .mobile-context .ga-workload-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
        .dashboard-pulse-preview .mobile-context .ga-workload-item { min-height:102px; padding:13px 10px; gap:8px; }
        .dashboard-pulse-preview .mobile-context .ga-workload-item:nth-child(3n) { border-right:1px solid var(--border-color); }
        .dashboard-pulse-preview .mobile-context .ga-workload-item:nth-child(2n) { border-right:0; }
        .dashboard-pulse-preview .mobile-context .ga-workload-item:nth-child(n+4) { border-bottom:1px solid var(--border-color); }
        .dashboard-pulse-preview .mobile-context .ga-workload-item:nth-child(n+5) { border-bottom:0; }
        .dashboard-pulse-preview .mobile-context .ga-workload-value { font-size:24px; }
        .dashboard-pulse-preview .mobile-context .ga-workload-label { margin-top:6px; font-size:11px; }
        .dashboard-pulse-preview .mobile-context .ga-workload-detail { margin-top:5px; font-size:9px; }
        .dashboard-pulse-preview .mobile-context .ga-activity { margin-top:16px; }
        .dashboard-pulse-preview .mobile-context .ga-activity-header { padding:14px; }
        .dashboard-pulse-preview .mobile-context .ga-health-list, .dashboard-pulse-preview .mobile-context .ga-activity-list { padding-left:14px; padding-right:14px; }
        .dashboard-pulse-preview .mobile-context .ga-activity-divider { padding-left:14px; padding-right:14px; }
        .dashboard-pulse-preview .mobile-context .ga-health-detail, .dashboard-pulse-preview .mobile-context .ga-activity-row small { max-width:112px; }
        @media (max-width: 720px) {
          .dashboard-pulse-preview .ga-pulse-section { padding:14px; }
          .dashboard-pulse-preview .ga-titlebar { align-items:flex-start; margin-bottom:15px; padding-bottom:12px; }
          .dashboard-pulse-preview .ga-titlebar h2 { font-size:18px; }
          .dashboard-pulse-preview .ga-updated { font-size:9px; }
          .dashboard-pulse-preview .ga-composition { display:block; }
          .dashboard-pulse-preview .ga-workload-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
          .dashboard-pulse-preview .ga-workload-item { min-height:102px; padding:13px 10px; gap:8px; }
          .dashboard-pulse-preview .ga-workload-item:nth-child(3n) { border-right:1px solid var(--border-color); }
          .dashboard-pulse-preview .ga-workload-item:nth-child(2n) { border-right:0; }
          .dashboard-pulse-preview .ga-workload-item:nth-child(n+4) { border-bottom:1px solid var(--border-color); }
          .dashboard-pulse-preview .ga-workload-item:nth-child(n+5) { border-bottom:0; }
          .dashboard-pulse-preview .ga-workload-value { font-size:24px; }
          .dashboard-pulse-preview .ga-workload-label { margin-top:6px; font-size:11px; }
          .dashboard-pulse-preview .ga-workload-detail { margin-top:5px; font-size:9px; }
          .dashboard-pulse-preview .ga-activity { margin-top:16px; }
          .dashboard-pulse-preview .ga-activity-header { padding:14px; }
          .dashboard-pulse-preview .ga-health-list, .dashboard-pulse-preview .ga-activity-list { padding-left:14px; padding-right:14px; }
          .dashboard-pulse-preview .ga-activity-divider { padding-left:14px; padding-right:14px; }
          .dashboard-pulse-preview .ga-health-detail, .dashboard-pulse-preview .ga-activity-row small { max-width:112px; }
        }
      `}</style>
      <div className="contexts">
        <PulseContext />
        <PulseContext mobile />
      </div>
    </main>
  );
}