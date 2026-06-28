<script>
  import { marked } from 'marked';
  import ChatBubble from '../lib/ChatBubble.svelte';
  import { createTask } from '../api.js';

  let { agentName = 'hermes', navigate } = $props();

  let messages = $state([]);
  let inputText = $state('');
  let running = $state(false);

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

    // If first message and no agent message yet, add welcome
    if (messages.length <= 1) {
      // Show agent name in header
    }

    running = true;
    addMessage('agent', '_Processing..._');

    try {
      const task = await createTask(text, agentName);
      // Update last message with real result
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

  <div class="input-area">
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
