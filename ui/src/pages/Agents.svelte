<script>
  import { onMount } from 'svelte';
  import { listAgents, doctor } from '../api.js';

  let { navigate } = $props();

  let agents = $state([]);
  let sysInfo = $state({});
  let loading = $state(true);

  onMount(async () => {
    try {
      const [aRes, dRes] = await Promise.all([listAgents(), doctor()]);
      agents = aRes.agents || [];
      sysInfo = dRes.checks || {};
    } catch (e) {
      console.error('Failed to load agents', e);
    } finally {
      loading = false;
    }
  });
</script>

<div class="page">
  <h1 class="page-title">Agents & Hosts</h1>

  {#if loading}
    <p class="loading">Loading...</p>
  {:else}
    <div class="agent-grid">
      {#each agents as agent}
        <div class="agent-card clickable" class:online={agent.available} class:offline={!agent.available} role="button" tabindex="0" onclick={() => navigate('chat', { agent: agent.name })} onkeydown={(e) => e.key === 'Enter' && navigate('chat', { agent: agent.name })}>
          <div class="agent-header">
            <span class="agent-icon">🤖</span>
            <span class="agent-status">
              <span class="status-dot" class:status-online={agent.available} class:status-offline={!agent.available}>●</span>
              {agent.available ? 'Online' : 'Offline'}
            </span>
          </div>
          <div class="agent-name">{agent.name}</div>
          <div class="agent-caps">
            {#each agent.capabilities as cap}
              <span class="cap-badge">{cap}</span>
            {/each}
          </div>
        </div>
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
    margin-bottom: 20px;
  }
  .loading { color: var(--text-dim); padding: 40px; text-align: center; }
  .agent-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap: 12px;
  }
  .agent-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 20px;
    transition: border-color 0.15s;
  }
  .agent-card.online { border-left: 3px solid var(--green); }
  .agent-card.offline { border-left: 3px solid var(--red); }
  .agent-card.clickable { cursor: pointer; transition: background 0.15s, border-color 0.15s; }
  .agent-card.clickable:hover { background: var(--bg-raised); }
  .agent-card.clickable:active { background: var(--bg-hover); }
  .agent-card:hover { border-color: var(--border-hover); }
  .agent-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
  }
  .agent-icon { font-size: 28px; }
  .agent-status {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 12px;
  }
  .status-dot { font-size: 10px; }
  .agent-name {
    font-size: 16px;
    font-weight: 600;
    color: var(--text-bright);
    margin-bottom: 10px;
  }
  .agent-caps {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }
  .cap-badge {
    font-size: 11px;
    padding: 2px 8px;
    background: var(--accent-bg);
    color: var(--accent);
    border-radius: 10px;
  }
</style>
