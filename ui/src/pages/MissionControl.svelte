<script>
  import { onMount } from 'svelte';

  let agents = $state([]);
  let tasks = $state([]);
  let sysInfo = $state({});
  let loading = $state(true);
  let error = $state('');

  onMount(() => {
    Promise.all([
      fetch('/api/v1/agents').then(r => r.json()),
      fetch('/api/v1/tasks?limit=5').then(r => r.json()),
      fetch('/api/v1/doctor').then(r => r.json()),
    ]).then(([aRes, tRes, dRes]) => {
      agents = aRes.agents || [];
      tasks = tRes.tasks || [];
      sysInfo = dRes.checks || {};
      loading = false;
    }).catch(e => {
      error = e.message || String(e);
      loading = false;
    });
  });

  function statusIcon(status) {
    if (status === 'completed') return '✅';
    if (status === 'failed') return '❌';
    if (status === 'running') return '⏳';
    return '⬜';
  }
</script>

<div class="page">
  <h1 class="page-title">Mission Control</h1>
  <p class="page-desc">Status of every agent, every task, every memory.</p>

  {#if loading}
    <p class="loading">Loading...</p>
  {:else if error}
    <p class="error">Error: {error}</p>
  {:else}
    <!-- Agent cards (inline, no Card component) -->
    <div class="card-grid">
      {#each agents as agent}
        <div class="card" class:online={agent.available} class:offline={!agent.available}>
          <div class="card-icon">🤖</div>
          <div class="card-body">
            <div class="card-title">{agent.name}</div>
            <div class="card-value">{agent.available ? 'Online' : 'Offline'}</div>
          </div>
        </div>
      {/each}
    </div>

    <!-- Metrics -->
    <div class="card-grid">
      <div class="card neutral">
        <div class="card-icon">🖥</div>
        <div class="card-body">
          <div class="card-title">Hosts</div>
          <div class="card-value">{sysInfo.remote_hosts || '0'}</div>
        </div>
      </div>
      <div class="card neutral">
        <div class="card-icon">✅</div>
        <div class="card-body">
          <div class="card-title">Agents Available</div>
          <div class="card-value">{sysInfo.agents_available || 0}/{sysInfo.agents_total || 0}</div>
        </div>
      </div>
    </div>

    <!-- Recent tasks -->
    <section class="section">
      <h2>Recent Tasks</h2>
      <div class="task-list">
        {#each tasks as task}
          <div class="task-row">
            <span class="task-status">{statusIcon(task.status)}</span>
            <span class="task-desc">{(task.description || '').slice(0, 60)}</span>
            <span class="task-agent">{task.agent}</span>
            <span class="task-time">{task.duration_sec ? `${task.duration_sec.toFixed(1)}s` : ''}</span>
          </div>
        {/each}
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
    margin-bottom: 4px;
  }
  .page-desc {
    color: var(--text-dim);
    margin-bottom: 24px;
  }
  .loading { color: var(--text-dim); padding: 40px; text-align: center; }
  .error { color: red; padding: 40px; text-align: center; }
  
  .card-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 12px;
    margin-bottom: 24px;
  }
  .card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px;
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .card.online { border-left: 3px solid var(--green); }
  .card.offline { border-left: 3px solid var(--red); }
  .card.neutral { border-left: 3px solid var(--border); }
  .card-icon {
    font-size: 24px;
    width: 40px; height: 40px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg-raised);
    border-radius: var(--radius-sm);
  }
  .card-body { flex: 1; min-width: 0; }
  .card-title {
    font-size: 12px;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  .card-value {
    font-size: 18px;
    font-weight: 600;
    color: var(--text-bright);
    margin-top: 2px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  
  .section { margin-bottom: 24px; }
  .section h2 {
    font-size: 14px;
    font-weight: 600;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 12px;
  }
  .task-list {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow: hidden;
  }
  .task-row {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 16px;
    border-bottom: 1px solid var(--border);
    color: var(--text);
    font-size: 13px;
  }
  .task-row:last-child { border-bottom: none; }
  .task-status { font-size: 14px; width: 20px; }
  .task-desc { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .task-agent {
    font-size: 11px;
    color: var(--accent);
    padding: 2px 8px;
    background: var(--accent-bg);
    border-radius: 10px;
  }
  .task-time {
    font-size: 11px;
    color: var(--text-dim);
    width: 50px;
    text-align: right;
  }
</style>
