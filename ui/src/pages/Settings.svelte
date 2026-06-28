<script>
  import { health, doctor } from '../api.js';

  let info = $state({});
  let loading = $state(true);

  function init() {
    Promise.all([health(), doctor()]).then(([h, d]) => {
      info = { ...h, checks: d.checks || {} };
      loading = false;
    }).catch(e => {
      console.error('Failed to load info', e);
      loading = false;
    });
  }

  $effect(init);
</script>

<div class="page">
  <h1 class="page-title">Settings</h1>

  {#if loading}
    <p class="loading">Loading...</p>
  {:else}
    <section class="section">
      <h2>System</h2>
      <div class="info-grid">
        <div class="info-item">
          <span class="info-label">Name</span>
          <span class="info-value">{info.name || 'CosmOS'}</span>
        </div>
        <div class="info-item">
          <span class="info-label">Version</span>
          <span class="info-value">{info.version || '0.1.0'}</span>
        </div>
        <div class="info-item">
          <span class="info-label">Status</span>
          <span class="info-value status-online">{info.status || 'ok'}</span>
        </div>
      </div>
    </section>

    <section class="section">
      <h2>Config</h2>
      <p class="hint">Configuration is managed through <code>cosmos.yaml</code> and <code>.env</code>.</p>
      <div class="info-grid">
        <div class="info-item">
          <span class="info-label">Remote Hosts</span>
          <span class="info-value">{info.checks?.remote_hosts || '0'}</span>
        </div>
        <div class="info-item">
          <span class="info-label">Agents Available</span>
          <span class="info-value">{info.checks?.agents_available || 0}/{info.checks?.agents_total || 0}</span>
        </div>
      </div>
    </section>
  {/if}
</div>

<style>
  .page { max-width: 960px; }
  .page-title {
    font-size: 22px;
    font-weight: 700;
    color: var(--text-bright);
    margin-bottom: 24px;
  }
  .loading { color: var(--text-dim); padding: 40px; text-align: center; }
  .section { margin-bottom: 32px; }
  .section h2 {
    font-size: 14px;
    font-weight: 600;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 12px;
  }
  .hint {
    color: var(--text-dim);
    font-size: 13px;
    margin-bottom: 12px;
  }
  .hint code { background: var(--bg-card); padding: 1px 6px; border-radius: 3px; }
  .info-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 8px;
  }
  .info-item {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 12px;
  }
  .info-label {
    font-size: 11px;
    color: var(--text-dim);
    text-transform: uppercase;
    display: block;
    margin-bottom: 4px;
  }
  .info-value {
    font-size: 18px;
    font-weight: 600;
    color: var(--text-bright);
  }
</style>
