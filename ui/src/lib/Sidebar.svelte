<script>
  let { currentPage, pageParams = {}, navigate } = $props();

  const agents = [
    { name: 'hermes', status: 'online' },
    { name: 'claude', status: 'online' },
    { name: 'opencode', status: 'online' },
    { name: 'geekom/opencode', status: 'online' },
    { name: 'kz/opencode', status: 'online' },
    { name: 'relaxagent/opencode', status: 'online' },
  ];
</script>

<aside class="sidebar">
  <div class="section">
    <div class="section-title">WORKSPACE</div>
    <button
      class="nav-item"
      class:active={currentPage === 'mission-control'}
      onclick={() => navigate('mission-control')}
    >
      <span class="nav-icon">◆</span>
      Mission Control
    </button>
    <button
      class="nav-item"
      class:active={currentPage === 'tasks'}
      onclick={() => navigate('tasks')}
    >
      <span class="nav-icon">📋</span>
      Tasks
    </button>
  </div>

  <div class="section">
    <div class="section-title">AGENTS</div>
    {#each agents as agent}
      <button
        class="nav-item"
        class:active={currentPage === 'chat' && pageParams.agent === agent.name}
        onclick={() => navigate('chat', { agent: agent.name })}
      >
        <span class="agent-dot status-{agent.status}">●</span>
        <span class="agent-name">{agent.name}</span>
      </button>
    {/each}
  </div>

  <div class="section">
    <div class="section-title">MEMORY</div>
    <button
      class="nav-item"
      class:active={currentPage === 'memory'}
      onclick={() => navigate('memory')}
    >
      <span class="nav-icon">🔍</span>
      Search
    </button>
  </div>

  <div class="section">
    <div class="section-title">SYSTEM</div>
    <button
      class="nav-item"
      class:active={currentPage === 'agents'}
      onclick={() => navigate('agents')}
    >
      <span class="nav-icon">🤖</span>
      Agents
    </button>
    <button
      class="nav-item"
      class:active={currentPage === 'settings'}
      onclick={() => navigate('settings')}
    >
      <span class="nav-icon">⚙</span>
      Settings
    </button>
  </div>
</aside>

<style>
  .sidebar {
    width: var(--sidebar-w);
    background: var(--bg-raised);
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 12px 8px;
    overflow-y: auto;
    flex-shrink: 0;
  }
  .section {
    margin-bottom: 12px;
  }
  .section-title {
    font-size: 10px;
    font-weight: 600;
    color: var(--text-dim);
    letter-spacing: 1px;
    padding: 8px 12px 4px;
  }
  .nav-item {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    padding: 8px 12px;
    background: transparent;
    border: none;
    color: var(--text);
    font-size: 13px;
    text-align: left;
    border-radius: var(--radius-sm);
    cursor: pointer;
    transition: background 0.15s;
  }
  .nav-item:hover { background: var(--bg-hover); }
  .nav-item.active {
    background: var(--accent-bg);
    color: var(--accent);
  }
  .nav-icon { font-size: 14px; width: 18px; text-align: center; }
  .agent-dot { font-size: 10px; }
  .agent-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
