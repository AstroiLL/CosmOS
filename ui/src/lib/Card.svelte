<script>
  let { title, value, icon = '◆', status = 'neutral' } = $props();
</script>

<div class="card" class:card-{status}>
  <div class="card-icon">{icon}</div>
  <div class="card-body">
    <div class="card-title">{title}</div>
    <div class="card-value">{value}</div>
  </div>
</div>

<style>
  .card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px;
    display: flex;
    align-items: center;
    gap: 12px;
    transition: border-color 0.15s;
  }
  .card:hover { border-color: var(--border-hover); }
  .card-online { border-left: 3px solid var(--green); }
  .card-offline { border-left: 3px solid var(--red); }
  .card-neutral { border-left: 3px solid var(--border); }
  .card-icon {
    font-size: 24px;
    width: 40px;
    height: 40px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg-raised);
    border-radius: var(--radius-sm);
  }
  .card-body { flex: 1; min-width: 0; }
  .card-title {
    font-size: 12px;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  .card-value {
    font-size: 18px;
    font-weight: 600;
    color: var(--text-bright);
    margin-top: 2px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
</style>
