class HK37xxRemoteCard extends HTMLElement {
  set hass(hass) {
    const entry = hass.config_entries?.find(e => e.domain === 'hk37xx');
    if (!entry) { this.innerHTML = '<div style="padding:16px;color:#999">No hk37xx integration found</div>'; return; }
    const prefix = entry.title ? entry.title.toLowerCase().replace(/\s+/g, '_') : 'hk_3770';
    const entities = {
      media: `media_player.${prefix}`,
      volume_up: `button.${prefix}_volume_up`,
      volume_down: `button.${prefix}_volume_down`,
      mute: `media_player.${prefix}`,
      source: `select.${prefix}_source`,
      nav_up: `button.${prefix}_nav_up`,
      nav_down: `button.${prefix}_nav_down`,
      nav_exit: `button.${prefix}_nav_exit`,
      tune_up: `button.${prefix}_tune_up`,
      tune_down: `button.${prefix}_tune_down`,
      direct: `button.${prefix}_tuner_direct_entry`,
      mem: `button.${prefix}_tuner_store_preset`,
      rds: `button.${prefix}_rds`,
      speaker_a: `button.${prefix}_speaker_a`,
      speaker_b: `button.${prefix}_speaker_b`,
      harman_vol: `button.${prefix}_harman_volume`,
      auto_preset: `button.${prefix}_auto_preset`,
      tone: `button.${prefix}_tone_control`,
      dim: `button.${prefix}_dim_display`,
      menu: `button.${prefix}_menu`,
      tuner_freq: `number.${prefix}_tuner_frequency`,
    };
    const states = Object.fromEntries(Object.entries(entities).map(([k, e]) => [k, hass.states[e]?.state || 'unknown']));
    const attrs = Object.fromEntries(Object.entries(entities).map(([k, e]) => [k, hass.states[e]?.attributes || {}]));

    const playerState = attrs.media;
    const isOn = playerState.state === 'on' || states.media === 'on';

    this.innerHTML = `
      <ha-card header="${entry.title || 'Harman Kardon HK 37xx'}" style="font-family:sans-serif;background:#1a1a2e;color:#eee;">
        <style>
          .hk37xx-grid { display:grid; grid-template-columns:1fr 1fr; gap:8px; padding:12px; }
          .hk37xx-row { grid-column:span 2; }
          .hk37xx-btn { border:none; border-radius:8px; padding:14px; font-size:14px; background:#2a2a40; color:#ccc; cursor:pointer; transition:background .15s; text-align:center; }
          .hk37xx-btn:hover { background:#3a3a60; }
          .hk37xx-btn.active { background:#4caf50; color:#fff; }
          .hk37xx-btn.disabled { opacity:.35; pointer-events:none; }
          input[type="number"] { width:100%; padding:8px; border-radius:8px; border:none; background:#2a2a40; color:#eee; font-size:16px; box-sizing:border-box; }
          .hk37xx-header { display:flex; justify-content:space-between; align-items:center; padding:0 4px 8px; font-size:12px; opacity:.7; }
          select { width:100%; padding:8px; border-radius:8px; border:none; background:#2a2a40; color:#eee; }
        </style>
        <div class="hk37xx-header">
          <span>IR Tunnel · DLNA Readback</span>
          <span>${isOn ? '● ON' : '○ STANDBY'}</span>
        </div>
        <div class="hk37xx-grid">
          <div class="hk37xx-row">
            <select onchange="this.dispatchEvent(new CustomEvent('action', {bubbles:true, composed:true, detail:{action:'select_source', value:this.value}}))" aria-label="Source">
              ${(() => { const src = attrs.source?.current_source || 'Unknown'; const opts = ['FM','AM','Analog','Digital','USB','CD','Phono','Bluetooth','vTuner','Home Network','Cable Sat','STB','TV']; return opts.map(s => `<option value="${s}" ${s===src ? 'selected' : ''}>${s}</option>`).join(''); })()}
            </select>
          </div>
          <div class="hk37xx-row" style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;">
            <button class="hk37xx-btn" onclick="this.dispatchEvent(new CustomEvent('action', {bubbles:true, composed:true, detail:{action:'volume_up'}}))">VOL +</button>
            <button class="hk37xx-btn" onclick="this.dispatchEvent(new CustomEvent('action', {bubbles:true, composed:true, detail:{action:'volume_down'}}))">VOL −</button>
            <button class="hk37xx-btn" onclick="this.dispatchEvent(new CustomEvent('action', {bubbles:true, composed:true, detail:{action:'mute_toggle'}}))">MUTE</button>
            <button class="hk37xx-btn ${!isOn ? 'disabled' : ''}" onclick="this.dispatchEvent(new CustomEvent('action', {bubbles:true, composed:true, detail:{action:'power_off'}}))">PWR OFF</button>
          </div>
          <div class="hk37xx-row">
            <input type="number" step="0.1" min="87.5" max="108" value="${attrs.tuner_frequency?.native_value || 101.5}" aria-label="Tuner frequency (MHz)" placeholder="FM frequency (MHz)" onkeydown="if(event.key==='Enter'){this.dispatchEvent(new CustomEvent('action',{bubbles:true,composed:true,detail:{action:'tune_direct',value:this.valueAsNumber}}));this.blur();}"></input>
          </div>
          <div class="hk37xx-row" style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;">
            <button class="hk37xx-btn ${!isOn ? 'disabled' : ''}" onclick="this.dispatchEvent(new CustomEvent('action',{bubbles:true,composed:true,detail:{action:'tuner_direct'}}))">DIRECT</button>
            <button class="hk37xx-btn ${!isOn ? 'disabled' : ''}" onclick="this.dispatchEvent(new CustomEvent('action',{bubbles:true,composed:true,detail:{action:'tuner_mem'}}))">MEM</button>
            <button class="hk37xx-btn ${!isOn ? 'disabled' : ''}" onclick="this.dispatchEvent(new CustomEvent('action',{bubbles:true,composed:true,detail:{action:'auto_preset'}}))">AUTO</button>
            <button class="hk37xx-btn ${!isOn ? 'disabled' : ''}" onclick="this.dispatchEvent(new CustomEvent('action',{bubbles:true,composed:true,detail:{action:'clear_entry'}}))">CLEAR</button>
          </div>
          <div class="hk37xx-row" style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;">
            <button class="hk37xx-btn ${!isOn ? 'disabled' : ''}" onclick="this.dispatchEvent(new CustomEvent('action',{bubbles:true,composed:true,detail:{action:'rds'}}))">RDS</button>
            <button class="hk37xx-btn ${!isOn ? 'disabled' : ''}" onclick="this.dispatchEvent(new CustomEvent('action',{bubbles:true,composed:true,detail:{action:'speaker_a'}}))">A</button>
            <button class="hk37xx-btn ${!isOn ? 'disabled' : ''}" onclick="this.dispatchEvent(new CustomEvent('action',{bubbles:true,composed:true,detail:{action:'speaker_b'}}))">B</button>
            <button class="hk37xx-btn ${!isOn ? 'disabled' : ''}" onclick="this.dispatchEvent(new CustomEvent('action',{bubbles:true,composed:true,detail:{action:'top_menu'}}))">MENU</button>
          </div>
          <div class="hk37xx-row" style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;">
            <button class="hk37xx-btn ${!isOn ? 'disabled' : ''}" onclick="this.dispatchEvent(new CustomEvent('action',{bubbles:true,composed:true,detail:{action:'tune_up'}}))">▲</button>
            <button class="hk37xx-btn ${!isOn ? 'disabled' : ''}" onclick="this.dispatchEvent(new CustomEvent('action',{bubbles:true,composed:true,detail:{action:'tune_down'}}))">▼</button>
            <button class="hk37xx-btn ${!isOn ? 'disabled' : ''}" onclick="this.dispatchEvent(new CustomEvent('action',{bubbles:true,composed:true,detail:{action:'nav_up'}}))">▲ MEN</button>
            <button class="hk37xx-btn ${!isOn ? 'disabled' : ''}" onclick="this.dispatchEvent(new CustomEvent('action',{bubbles:true,composed:true,detail:{action:'nav_down'}}))">▼ MEN</button>
          </div>
          <div class="hk37xx-row" style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;">
            <button class="hk37xx-btn ${!isOn ? 'disabled' : ''}" onclick="this.dispatchEvent(new CustomEvent('action',{bubbles:true,composed:true,detail:{action:'nav_exit'}}))">EXIT</button>
            <button class="hk37xx-btn ${!isOn ? 'disabled' : ''}" onclick="this.dispatchEvent(new CustomEvent('action',{bubbles:true,composed:true,detail:{action:'harman_volume'}}))">VOL EQ</button>
            <button class="hk37xx-btn ${!isOn ? 'disabled' : ''}" onclick="this.dispatchEvent(new CustomEvent('action',{bubbles:true,composed:true,detail:{action:'tone_control'}}))">TONE</button>
            <button class="hk37xx-btn ${!isOn ? 'disabled' : ''}" onclick="this.dispatchEvent(new CustomEvent('action',{bubbles:true,composed:true,detail:{action:'dim_display'}}))">DIM</button>
          </div>
        </div>
      </ha-card>`;
  }
}
customElements.define('hk37xx-remote-card', HK37xxRemoteCard);
