<script>
  import { marked } from 'marked';
  import { memorySearch } from '../api.js';

  let query = $state('');
  let results = $state([]);
  let loading = $state(false);

  async function search() {
    if (!query.trim()) return;
    loading = true;
    try {
      const res = await memorySearch(query);
      results = res.results || [];
    } catch (e) {
      console.error('Search failed', e);
    } finally {
      loading = false;
    }
  }
</script>

<div class="page">
  <h1 class="page-title">Memory</h1>

  <div class="search-bar">
    <input
      type="text"
      placeholder="Search across SQLite and Obsidian..."
      bind:value={query}
      onkeydown={(e) => e.key === 'Enter' && search()}
    />
    <button class="btn-primary" onclick={search} disabled={loading}>
      {loading ? '⏳' : '🔍'} Search
    </button>
  </div>

  {#if results.length > 0}
    <div class="results-count">{results.length} result(s)</div>
    <div class="results">
      {#each results as item}
        <div class="result-item">
          <div class="result-header">
            <span class="result-key">{item.key}</span>
            <span class="result-source">[{item.source}]</span>
            {#if item.tags}
              {#each item.tags as tag}
                <span class="result-tag">{tag}</span>
              {/each}
            {/if}
          </div>
          <div class="result-content markdown">{@html marked.parse((item.content || '').slice(0, 500))}</div>
        </div>
      {/each}
    </div>
  {:else if query && !loading}
    <p class="empty">No results found.</p>
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
  .search-bar {
    display: flex;
    gap: 8px;
    margin-bottom: 20px;
  }
  .search-bar input { flex: 1; }
  .empty { color: var(--text-dim); text-align: center; padding: 40px; }
  .results-count {
    font-size: 12px;
    color: var(--text-dim);
    margin-bottom: 12px;
  }
  .results { display: flex; flex-direction: column; gap: 12px; }
  .result-item {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px;
  }
  .result-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
    flex-wrap: wrap;
  }
  .result-key {
    font-weight: 600;
    font-size: 13px;
    color: var(--accent);
  }
  .result-source {
    font-size: 11px;
    color: var(--text-dim);
  }
  .result-tag {
    font-size: 10px;
    padding: 1px 6px;
    background: var(--bg-raised);
    border: 1px solid var(--border);
    border-radius: 8px;
    color: var(--text-dim);
  }
  .result-content {
    font-size: 13px;
    line-height: 1.6;
    color: var(--text);
  }
</style>
