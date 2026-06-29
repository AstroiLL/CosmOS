<script>
  import { onMount } from 'svelte';
  import { getTask } from '../api.js';

  let { taskId, from = 'mission-control', navigate } = $props();

  let task = $state(null);
  let loading = $state(true);

  onMount(async () => {
    try {
      const res = await getTask(taskId);
      task = res;
    } catch (e) {
      console.error('Failed to load task', e);
    } finally {
      loading = false;
    }
  });

  function statusClass(status) {
    if (status === 'completed') return 'status-completed';
    if (status === 'failed') return 'status-failed';
    if (status === 'running') return 'status-running';
    return '';
  }
</script>

<div class="page">
  <button class="btn-ghost back-btn" onclick={() => navigate(from === 'tasks' ? 'tasks' : from === 'memory' ? 'memory' : 'mission-control')}>
    ← Back to {from === 'tasks' ? 'Tasks' : from === 'memory' ? 'Memory' : 'Mission Control'}
  </button>

  {#if loading}
    <p class="loading">Loading...</p>
  {:else if !task}
    <p class="loading">Task not found.</p>
  {:else}
    <h1 class="page-title">Task {task.id?.slice(0, 8)}</h1>

    <div class="detail-grid">
      <div class="detail-field">
        <span class="field-label">Description</span>
        <span class="field-value">{task.description}</span>
      </div>
      <div class="detail-field">
        <span class="field-label">Status</span>
        <span class="field-value {statusClass(task.status)}">{task.status}</span>
      </div>
      <div class="detail-field">
        <span class="field-label">Agent</span>
        <span class="field-value">{task.agent}</span>
      </div>
      <div class="detail-field">
        <span class="field-label">Duration</span>
        <span class="field-value">{task.duration_sec ? `${task.duration_sec.toFixed(1)}s` : '-'}</span>
      </div>
    </div>

    {#if task.result}
      <section class="section">
        <h2>Result</h2>
        <pre class="result-box">{task.result}</pre>
      </section>
    {/if}

    {#if task.error}
      <section class="section">
        <h2>Error</h2>
        <pre class="error-box">{task.error}</pre>
      </section>
    {/if}
  {/if}
</div>

<style>
  .page { max-width: 960px; }
  .back-btn { margin-bottom: 12px; }
  .loading { color: var(--text-dim); padding: 40px; text-align: center; }
  .page-title {
    font-size: 22px;
    font-weight: 700;
    color: var(--text-bright);
    margin-bottom: 20px;
  }
  .detail-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    margin-bottom: 24px;
  }
  .detail-field {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 12px;
  }
  .field-label {
    font-size: 11px;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    display: block;
    margin-bottom: 4px;
  }
  .field-value { font-size: 14px; color: var(--text-bright); }
  .section { margin-bottom: 24px; }
  .section h2 {
    font-size: 14px;
    font-weight: 600;
    color: var(--text-dim);
    text-transform: uppercase;
    margin-bottom: 8px;
  }
  .result-box {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 16px;
    font-size: 13px;
    line-height: 1.6;
    white-space: pre-wrap;
    overflow-x: auto;
    max-height: 400px;
    overflow-y: auto;
  }
  .error-box {
    background: var(--bg-card);
    border: 1px solid var(--red);
    border-radius: var(--radius-sm);
    padding: 16px;
    font-size: 13px;
    color: var(--red);
    white-space: pre-wrap;
  }
  @media (max-width: 768px) {
    .detail-grid { grid-template-columns: 1fr; }
  }
</style>
