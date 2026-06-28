<script>
  let { sidebarOpen, toggleSidebar, currentPage } = $props();

  const pageTitles = {
    'mission-control': 'Mission Control',
    'tasks': 'Tasks',
    'task-detail': 'Task',
    'chat': 'Chat',
    'agents': 'Agents',
    'memory': 'Memory',
    'settings': 'Settings',
  };
</script>

<header class="header">
  <div class="header-left">
    <button class="btn-ghost menu-btn" onclick={toggleSidebar}>
      {#if sidebarOpen}
        ◁
      {:else}
        ☰
      {/if}
    </button>
    <span class="logo">CosmOS</span>
    <span class="separator">/</span>
    <span class="page-title">{pageTitles[currentPage] || currentPage}</span>
  </div>
  <div class="header-right">
    <span class="version">v0.1.0</span>
    <span class="status-dot status-online">●</span>
    <span class="status-label">Online</span>
  </div>
</header>

<style>
  .header {
    height: var(--header-h);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 16px;
    border-bottom: 1px solid var(--border);
    background: var(--bg-raised);
    flex-shrink: 0;
  }
  .header-left {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .menu-btn {
    font-size: 18px;
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .logo {
    font-weight: 700;
    font-size: 16px;
    color: var(--accent);
    letter-spacing: -0.3px;
  }
  .separator {
    color: var(--text-dim);
  }
  .page-title {
    color: var(--text-dim);
    font-size: 13px;
  }
  .header-right {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .version {
    color: var(--text-dim);
    font-size: 12px;
    padding: 2px 8px;
    border: 1px solid var(--border);
    border-radius: 10px;
  }
  .status-dot {
    font-size: 10px;
  }
  .status-label {
    font-size: 12px;
    color: var(--green);
  }
</style>
