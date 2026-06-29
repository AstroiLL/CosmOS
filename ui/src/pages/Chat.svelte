<script>
  import { onMount } from 'svelte';
  import { marked } from 'marked';
  import ChatBubble from '../lib/ChatBubble.svelte';
  import { createTask } from '../api.js';

  let { agentName = 'hermes', navigate } = $props();

  // ── Options state ────────────────────────────────────
  let optOpen = $state(false);
  let optWorkdir = $state('');
  let optHost = $state('');
  let optModel = $state('');
  let optInstructions = $state('');

  // ── Chat state ────────────────────────────────────────
  let messages = $state([]);
  let inputText = $state('');
  let running = $state(false);
  let bottomPad = $state(0);

  // Load saved options per agent
  function loadOptions() {
    try {
      const saved = JSON.parse(localStorage.getItem(`cosmos_agent_${agentName}`) || '{}');
      optWorkdir = saved.workdir || '';
      optHost = saved.host || '';
      optModel = saved.model || '';
      optInstructions = saved.instructions || '';
    } catch { /* ignore */ }
  }

  function saveOptions() {
    try {
      localStorage.setItem(`cosmos_agent_${agentName}`, JSON.stringify({
        workdir: optWorkdir,
        host: optHost,
        model: optModel,
        instructions: optInstructions,
      }));
    } catch { /* ignore */ }
  }

  onMount(() => {
    loadOptions();
    const vv = window.visualViewport;
    if (vv) {
      bottomPad = Math.max(0, window.innerHeight - vv.height - 16);
    } else {
      bottomPad = 12;
    }
  });

  // ── Computed: CLI preview ───────────────────────────
  // Remote agents always show --host automatically
  const defaultHost = $derived(agentName.includes('/') ? agentName.split('/')[0] : '');

  const cliParts = $derived(() => {
    const parts = [];
    // Always show --agent (who is being called)
    parts.push(`--agent ${agentName}`);
    // Always show --host for remote agents
    const host = optHost || defaultHost;
    if (host) parts.push(`--host ${host}`);
    if (optWorkdir) parts.push(`--workdir ${optWorkdir}`);
    if (optModel) parts.push(`--model ${optModel}`);
    if (optInstructions) parts.push(`--instructions "${optInstructions.slice(0, 40)}${optInstructions.length > 40 ? '…' : ''}"`);
    return parts;
  });

  // ── Messages ─────────────────────────────────────────
  function addMessage(role, content) {
    messages = [...messages, {
      role,
      content,
      timestamp: new Date().toLocaleTimeString(),
    }];
  }

  async function send() {
    const text = inputText.trim();
    if (!text || running) return;

    inputText = '';
    addMessage('user', text);

    running = true;
    addMessage('agent', '_Processing..._');

    try {
      const task = await createTask(
        text,
        agentName,
        optHost || null,
        optWorkdir || null,
        optModel || null,
        optInstructions || null,
      );
      const resultText = task.result || task.error || 'No output';
      const status = task.status === 'completed' ? '✅' : '❌';
      const duration = task.duration_sec ? `\n\n*Duration: ${task.duration_sec.toFixed(1)}s*` : '';

      messages = messages.slice(0, -1);
      addMessage('agent', `${status} **${task.description}**\n\n\`\`\`\n${resultText.slice(0, 2000)}\n\`\`\`${duration}`);
    } catch (e) {
      messages = messages.slice(0, -1);
      addMessage('agent', `❌ *Error:* ${e.message}`);
    } finally {
      running = false;
    }
  }

  function handleKeydown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  function toggleOpts() {
    if (running) return;
    optOpen = !optOpen;
  }

  function closeOpts() {
    saveOptions();
    optOpen = false;
  }

  const isRemote = $derived(agentName.includes('/'));
</script>

<div class="page">
  <div class="chat-header">
    <button class="btn-ghost" onclick={() => navigate('mission-control')}>← Dashboard</button>
    <span class="chat-agent">🤖 {agentName}</span>
    <span class="status-online">● Online</span>
  </div>

  <div class="messages">
    {#if messages.length === 0}
      <div class="welcome">
        <p>Send a task to <strong>{agentName}</strong>.</p>
        <p class="hint">Examples:</p>
        <div class="examples">
          <button class="btn-outline example-btn" onclick={() => { inputText = 'Check disk space'; }}>
            Check disk space
          </button>
          <button class="btn-outline example-btn" onclick={() => { inputText = `What's the uptime?`; }}>
            What's the uptime?
          </button>
        </div>
      </div>
    {:else}
      {#each messages as msg}
        <ChatBubble role={msg.role} content={msg.content} timestamp={msg.timestamp} />
      {/each}
    {/if}
  </div>

  {#if optOpen}
    <!-- ── Options editor panel ──────────────────── -->
    <div class="opts-panel">
      <div class="opts-row">
        <label class="opts-label">Workdir</label>
        <input class="opts-input" type="text" bind:value={optWorkdir} placeholder="Default (~)" />
      </div>
      <div class="opts-row">
        <label class="opts-label">Host</label>
        <input class="opts-input" type="text" bind:value={optHost} placeholder={defaultHost || 'auto'} disabled={agentName.includes('/')} />
      </div>
      <div class="opts-row">
        <label class="opts-label">Model</label>
        <input class="opts-input" type="text" bind:value={optModel} placeholder="Default" />
      </div>
      <div class="opts-row opts-row-textarea">
        <label class="opts-label">Instructions</label>
        <textarea class="opts-textarea" bind:value={optInstructions} placeholder="Extra context or system instructions…" rows="2"></textarea>
      </div>
      <div class="opts-actions">
        <button class="btn-primary opts-apply" onclick={closeOpts}>✓ Apply</button>
      </div>
    </div>
  {:else}
    <!-- ── CLI preview bar (always visible) ──────── -->
    <div class="cli-bar">
      <button class="btn-ghost cli-gear" onclick={toggleOpts} disabled={running} title="Edit options">
        ⚙
      </button>
      <code class="cli-cmd">cosmos task {cliParts().join(' ')}</code>
    </div>
  {/if}

  <div class="input-area" style="padding-bottom: {bottomPad}px">
    <textarea
      bind:value={inputText}
      onkeydown={handleKeydown}
      placeholder={`Send a task to ${agentName}...`}
      rows="2"
      disabled={running}
    ></textarea>
    <button class="btn-primary send-btn" onclick={send} disabled={running || !inputText.trim()}>
      {running ? '⏳' : '→'}
    </button>
  </div>
</div>

<style>
  .page {
    display: flex;
    flex-direction: column;
    height: 100%;
    max-width: 800px;
    margin: 0 auto;
  }
  .chat-header {
    display: flex;
    align-items: center;
    gap: 10px;
    padding-bottom: 16px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 16px;
  }
  .chat-agent {
    font-weight: 600;
    font-size: 16px;
    flex: 1;
  }
  .messages {
    flex: 1;
    overflow-y: auto;
    padding: 8px 0;
  }
  .welcome {
    text-align: center;
    padding: 40px 20px;
    color: var(--text-dim);
  }
  .welcome strong { color: var(--text-bright); }
  .hint { margin-top: 16px; font-size: 12px; }
  .examples {
    display: flex;
    gap: 8px;
    justify-content: center;
    margin-top: 8px;
    flex-wrap: wrap;
  }
  .example-btn { font-size: 12px; }

  /* ── Options editor panel ─────────────────────── */
  .opts-panel {
    background: var(--bg-raised);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 12px 16px;
    margin-bottom: 8px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .opts-row {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .opts-row-textarea {
    flex-direction: column;
    align-items: stretch;
  }
  .opts-label {
    font-size: 11px;
    font-weight: 600;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    min-width: 80px;
  }
  .opts-input {
    flex: 1;
    padding: 6px 10px;
    font-size: 13px;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    color: var(--text-bright);
    font-family: inherit;
  }
  .opts-input:disabled { opacity: 0.5; }
  .opts-textarea {
    padding: 6px 10px;
    font-size: 13px;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    color: var(--text-bright);
    font-family: inherit;
    resize: vertical;
  }
  .opts-actions {
    display: flex;
    justify-content: flex-end;
  }
  .opts-apply {
    font-size: 12px;
    padding: 4px 16px;
  }

  /* ── CLI preview bar ──────────────────────────── */
  .cli-bar {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 12px;
    margin-bottom: 8px;
    background: var(--bg-raised);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    overflow: hidden;
  }
  .cli-gear {
    font-size: 14px;
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    cursor: pointer;
    transition: opacity 0.15s;
  }
  .cli-gear:disabled {
    opacity: 0.3;
    cursor: not-allowed;
  }
  .cli-gear-inline {
    font-size: 16px;
    width: 36px;
    height: 36px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    align-self: flex-end;
    margin-bottom: 2px;
    cursor: pointer;
    transition: opacity 0.15s;
  }
  .cli-gear-inline:disabled {
    opacity: 0.3;
    cursor: not-allowed;
  }
  .cli-cmd {
    font-size: 12px;
    color: var(--text-dim);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', monospace;
  }

  /* ── Input area ────────────────────────────────── */
  .input-area {
    display: flex;
    gap: 8px;
    padding-top: 12px;
    border-top: 1px solid var(--border);
    background: var(--bg);
  }
  .input-area textarea {
    flex: 1;
    resize: none;
    padding: 10px 14px;
    font-family: inherit;
    line-height: 1.4;
  }
  .send-btn {
    width: 44px;
    height: 44px;
    padding: 0;
    font-size: 18px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    align-self: flex-end;
  }
</style>
