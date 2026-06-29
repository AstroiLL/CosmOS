<script>
  import './app.css';
  import Sidebar from './lib/Sidebar.svelte';
  import Header from './lib/Header.svelte';
  import MissionControl from './pages/MissionControl.svelte';
  import Tasks from './pages/Tasks.svelte';
  import TaskDetail from './pages/TaskDetail.svelte';
  import Chat from './pages/Chat.svelte';
  import Agents from './pages/Agents.svelte';
  import Memory from './pages/Memory.svelte';
  import Settings from './pages/Settings.svelte';

  let currentPage = $state('mission-control');
  let pageParams = $state({});
  let sidebarOpen = $state(true);

  function navigate(page, params = {}) {
    currentPage = page;
    pageParams = params;
    // Close sidebar on mobile after navigation
    if (window.innerWidth <= 768) sidebarOpen = false;
  }

  function toggleSidebar() {
    sidebarOpen = !sidebarOpen;
  }

  // Expose navigate globally for components
  if (typeof window !== 'undefined') {
    window.__cosmosNavigate = navigate;
  }
</script>

<div class="layout">
  <Header {sidebarOpen} {toggleSidebar} {currentPage} />

  <div class="body">
    {#if sidebarOpen}
      <Sidebar {currentPage} {pageParams} {navigate} />
    {/if}

    <main class="main">
      {#if currentPage === 'mission-control'}
        <MissionControl {navigate} />
      {:else if currentPage === 'tasks'}
        <Tasks {navigate} />
      {:else if currentPage === 'task-detail'}
        <TaskDetail taskId={pageParams.id} from={pageParams.from} {navigate} />
      {:else if currentPage === 'chat'}
        <Chat agentName={pageParams.agent} {navigate} />
      {:else if currentPage === 'agents'}
        <Agents {navigate} />
      {:else if currentPage === 'memory'}
        <Memory {navigate} />
      {:else if currentPage === 'settings'}
        <Settings />
      {:else}
        <MissionControl {navigate} />
      {/if}
    </main>
  </div>
</div>

<style>
  .layout {
    height: 100vh;
    height: 100dvh;
    display: flex;
    flex-direction: column;
    background: var(--bg);
  }
  .body {
    display: flex;
    flex: 1;
    overflow: hidden;
  }
  .main {
    flex: 1;
    overflow-y: auto;
    padding: 24px;
  }
  @media (max-width: 768px) {
    .main { padding: 12px; }
  }
</style>
