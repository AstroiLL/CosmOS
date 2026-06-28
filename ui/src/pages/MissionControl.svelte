<script>
  import { onMount } from 'svelte';
  import Card from '../lib/Card.svelte';
  import { listAgents, listTasks, doctor, memorySearch } from '../api.js';

  let { navigate } = $props();

  let agents = $state([]);
  let tasks = $state([]);
  let searchQuery = $state('');
  let searchResults = $state([]);
  let sysInfo = $state({});
  let loading = $state(true);

  onMount(async () => {
    try {
      const [aRes, tRes, dRes] = await Promise.all([
        listAgents(),
        listTasks(5),
        doctor(),
      ]);
      agents = aRes.agents || [];
      tasks = tRes.tasks || [];
      sysInfo = dRes.checks || {};
    } catch (e) {
      console.error('Failed to load dashboard', e);
    } finally {
      loading = false;
    }
  });

  async function handleSearch() {
    if (!searchQuery.trim()) return;
    try {
      const res = await memorySearch(searchQuery);
      searchResults = res.results || [];
    } catch (e) {
      console.error('Search failed', e);
    }
  }

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
  {:else}
    <!-- Agent cards -->
    <div class="card-grid">
      {#each agents as agent}
        <Card
          title={agent.name}
          value={agent.available ? 'Online' : 'Offline'}
          icon="🤖"
          status={agent.available ? 'online' : 'offline'}
        />
      {/each}
    </div>

    <!-- Metrics -->
    <div class="card-grid">
      <Card title="Hosts" value={sysInfo.remote_hosts || '0'} icon="🖥" />
      <Card title="Agents Available" value={`${sysInfo.agents_available || 0}/${sysInfo.agents_total || 0}`} icon="✅" />
    </div>

    <!-- Recent tasks -->
    <section class="section">
      <h2>Recent Tasks</h2>
      <div class="task-list">
        {#each tasks as task}
          <button class="task-row" onclick={() => navigate('task-detail', { id: task.id })}>
            <span class="task-status">{statusIcon(task.status)}</span>
            <span class="task-desc">{(task.description || '').slice(0, 60)}</span>
            <span class="task-agent">{task.agent}</span>
            <span class="task-time">{task.duration_sec ? `${task.duration_sec.toFixed(1)}s` : ''}</span>
          </button>
        {/each}
      </div>
    </section>

    <!-- Memory search -->
    <section class="section">
      <h2>Memory Search</h2>
      <div class="search-row">
        <input
          type="text"
          placeholder="Search memory..."
          bind:value={searchQuery}
          onkeydown={(e) => e.key === 'Enter' && handleSearch()}
        />
        <button class="btn-primary" onclick={handleSearch}>Search</button>
      </div>
      {#if searchResults.length > 0}
        <div class="search-results">
          {#each searchResults as item}
            <div class="search-item">
              <span class="search-key">{item.key}</span>
              <span class="search-source">[{item.source}]</span>
              <p class="search-preview">{(item.content || '').slice(0, 120)}</p>
            </div>
          {/each}
        </div>
      {/if}
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
  .card-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 12px;
    margin-bottom: 24px;
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
    width: 100%;
    padding: 10px 16px;
    background: transparent;
    border: none;
    border-bottom: 1px solid var(--border);
    color: var(--text);
    font-size: 13px;
    text-align: left;
    cursor: pointer;
    transition: background 0.15s;
  }
  .task-row:last-child { border-bottom: none; }
  .task-row:hover { background: var(--bg-hover); }
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
  .search-row {
    display: flex;
    gap: 8px;
    margin-bottom: 12px;
  }
  .search-row input { flex: 1; }
  .search-results { display: flex; flex-direction: column; gap: 8px; }
  .search-item {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 12px;
  }
  .search-key { font-weight: 600; color: var(--accent); font-size: 12px; }
  .search-source { color: var(--text-dim); font-size: 11px; margin-left: 6px; }
  .search-preview { color: var(--text-dim); font-size: 12px; margin-top: 4px; }
</style>
