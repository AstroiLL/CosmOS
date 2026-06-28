<script>
  import { marked } from 'marked';

  let { role = 'user', content = '', timestamp = '' } = $props();

  let html = $derived(marked.parse(content, { breaks: true }));
</script>

<div class="bubble" class:bubble-agent={role === 'agent'} class:bubble-user={role === 'user'}>
  <div class="bubble-avatar">
    {#if role === 'agent'}
      🤖
    {:else}
      🧑
    {/if}
  </div>
  <div class="bubble-content">
    <div class="bubble-header">
      <span class="bubble-role">{role === 'agent' ? 'Agent' : 'You'}</span>
      {#if timestamp}
        <span class="bubble-time">{timestamp}</span>
      {/if}
    </div>
    <div class="markdown">{@html html}</div>
  </div>
</div>

<style>
  .bubble {
    display: flex;
    gap: 12px;
    margin-bottom: 16px;
  }
  .bubble-agent { flex-direction: row; }
  .bubble-user { flex-direction: row-reverse; }
  .bubble-avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: var(--bg-raised);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
    flex-shrink: 0;
  }
  .bubble-content {
    max-width: 75%;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 12px 16px;
  }
  .bubble-user .bubble-content {
    background: var(--accent-bg);
  }
  .bubble-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
  }
  .bubble-role {
    font-size: 12px;
    font-weight: 600;
    color: var(--accent);
  }
  .bubble-agent .bubble-role { color: var(--green); }
  .bubble-time {
    font-size: 11px;
    color: var(--text-dim);
  }
</style>
