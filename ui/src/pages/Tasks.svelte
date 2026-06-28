<script>
  import { onMount } from 'svelte';
  import { listTasks } from '../api.js';

  let { navigate } = $props();

  let tasks = $state([]);
  let loading = $state(true);
  let filter = $state('all');

  onMount(async () => {
    try {
      const res = await listTasks(50);
      tasks = res.tasks || [];
    } catch (e) {
      console.error('Failed to load tasks', e);
    } finally {
      loading = false;
    }
  });

  let filtered = $derived(
    filter === 'all' ? tasks : tasks.filter(t => t.status === filter)
  );

  function statusIcon(status) {
    if (status === 'completed') return '✅';
    if (status === 'failed') return '❌';
    if (status === 'running') return '⏳';
    return '⬜';
  }
</script>

<div class="page">
  <h1 class="page-title">Tasks</h1>

  <div class="toolbar">
    {#each ['all', 'completed', 'failed', 'running'] as f}
      <button
        class="btn-outline filter-btn"
        class:active={filter === f}
        onclick={() => filter = f}
      >
        {f === 'all' ? 'All' : f.charAt(0).toUpperCase() + f.slice(1)}
      </button>
    {/each}
  </div>

  {#if loading}
    <p class="loading">Loading...</p>
  {:else if filtered.length === 0}
    <p class="empty">No tasks found.</p>
  {:else}
    <div class="task-list">
      {#each filtered as task}
        <button class="task-row" onclick={() => navigate('task-detail', { id: task.id })}>
          <span class="task-status">{statusIcon(task.status)}</span>
          <span class="task-id">{(task.id || '').slice(0, 8)}</span>
          <span class="task-desc">{(task.description || '').slice(0, 80)}</span>
          <span class="task-agent">{task.agent}</span>
          <span class="task-time">{task.duration_sec ? `${task.duration_sec.toFixed(1)}s` : ''}</span>
        </button>
      {/each}
    </div>
  {/if}
</div>

<style>
  .page { max-width: 960px; }
  .page-title {
    font-size: 22px;
    font-weight: 700;
    color: var(--text-bright);
    margin-bottom: 16px;
  }
  .loading, .empty { color: var(--text-dim); padding: 40px; text-align: center; }
  .toolbar {
    display: flex;
    gap: 6px;
    margin-bottom: 16px;
  }
  .filter-btn {
    font-size: 12px;
    padding: 4px 12px;
  }
  .filter-btn.active {
    background: var(--accent);
    color: white;
    border-color: var(--accent);
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
  .task-id { font-family: monospace; color: var(--text-dim); font-size: 11px; width: 60px; }
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
