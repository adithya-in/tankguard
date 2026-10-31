// Controller page served by the C1 firmware at http://<ip>/
// Same origin as the API, so it works with no internet, no CORS and no build step.
#pragma once

static const char UI_HTML[] PROGMEM = R"HTML(<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark">
<title>TankGuard C1</title>
<style>
:root{--bg:#0e1218;--panel:#151b24;--line:#242e3b;--ink:#e9eef5;--dim:#8a97a8;--accent:#4da3ff;--good:#2fbf71;--warn:#e0a32e;--bad:#e5484d}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
header{display:flex;flex-wrap:wrap;align-items:center;gap:10px;padding:14px 18px;border-bottom:1px solid var(--line)}
h1{margin:0;font-size:17px;font-weight:650}
.badge{padding:3px 9px;border-radius:999px;font-size:11px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;background:#222c39;color:var(--dim)}
.badge.run{background:rgba(77,163,255,.16);color:var(--accent)}
.badge.ok{background:rgba(47,191,113,.16);color:var(--good)}
.badge.bad{background:rgba(229,72,77,.18);color:var(--bad)}
main{max-width:960px;margin:0 auto;padding:16px;display:grid;gap:14px}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
h2{margin:0 0 10px;font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--dim);font-weight:700}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:12px}
.k{font-size:11px;color:var(--dim);letter-spacing:.04em;text-transform:uppercase}
.v{font-size:20px;font-variant-numeric:tabular-nums}
.bar{height:8px;background:#222c39;border-radius:99px;overflow:hidden;margin-top:12px}
.bar>i{display:block;height:100%;width:0;background:var(--accent);transition:width .4s}
.btns{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px;align-items:center}
button{font:inherit;font-weight:600;color:var(--ink);background:#1d2632;border:1px solid var(--line);border-radius:9px;padding:10px 14px;cursor:pointer}
button:hover{border-color:#39485c}
button.primary{background:var(--accent);border-color:var(--accent);color:#08111c}
button.danger{background:transparent;border-color:var(--bad);color:var(--bad)}
button:disabled{opacity:.4;cursor:not-allowed}
select,input{font:inherit;color:var(--ink);background:#1d2632;border:1px solid var(--line);border-radius:9px;padding:9px 10px}
.row{display:flex;flex-wrap:wrap;gap:12px;align-items:end}
label{display:grid;gap:4px;font-size:12px;color:var(--dim)}
label.inline{display:flex;align-items:center;gap:8px;font-size:13px}
.warn{border-color:rgba(224,163,46,.4);background:rgba(224,163,46,.07);color:#e8c98a;font-size:13px}
#log{min-height:22px;font-size:13px;color:var(--dim);padding:0 4px}
.dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px;background:#3a4757}
.dot.g{background:var(--good)}
.dot.r{background:var(--bad)}
</style>
</head>
<body>
<header>
  <h1>TankGuard C1</h1>
  <span id="phase" class="badge">connecting</span>
  <span id="fault" class="badge bad" hidden>fault</span>
  <span id="net" class="k" style="margin-left:auto"></span>
</header>
<main>
  <section class="panel">
    <h2>Status</h2>
    <div class="grid">
      <div><div class="k">Ring / arc</div><div class="v" id="ring">&ndash;</div></div>
      <div><div class="k">Shoulder</div><div class="v" id="t1">&ndash;</div></div>
      <div><div class="k">Elbow</div><div class="v" id="t2">&ndash;</div></div>
      <div><div class="k">Level</div><div class="v" id="level">&ndash;</div></div>
      <div><div class="k">Bursts</div><div class="v" id="bursts">&ndash;</div></div>
      <div><div class="k">Last move</div><div class="v" id="last">&ndash;</div></div>
    </div>
    <div class="bar"><i id="prog"></i></div>
    <div class="btns">
      <span class="k"><span id="dotLid" class="dot"></span>lid</span>
      <span class="k"><span id="dotEstop" class="dot"></span>e-stop</span>
      <span class="k"><span id="dotHome1" class="dot"></span>home 1</span>
      <span class="k"><span id="dotHome2" class="dot"></span>home 2</span>
      <span class="k" id="progressText" style="margin-left:auto"></span>
    </div>
  </section>

  <section class="panel">
    <h2>Run</h2>
    <div class="row">
      <label>Rings
        <select id="rings">
          <option>1</option>
          <option>2</option>
          <option selected>3</option>
        </select>
      </label>
      <label class="inline"><input type="checkbox" id="force"> Skip level check (bench)</label>
    </div>
    <div class="btns">
      <button id="bCheck">Check</button>
      <button id="bHome">Home</button>
      <button id="bStart" class="primary">Start</button>
      <button id="bStop" class="danger">Stop</button>
      <button id="bReset">Reset</button>
    </div>
  </section>

  <section class="panel">
    <h2>Jog for calibration</h2>
    <div class="row">
      <label>Joint
        <select id="joint">
          <option value="sh">Shoulder</option>
          <option value="el">Elbow</option>
        </select>
      </label>
      <label>Direction
        <select id="dir">
          <option value="1">Forward</option>
          <option value="-1">Back</option>
        </select>
      </label>
      <label>Bursts
        <input id="bursts" type="number" min="1" max="20" value="5">
      </label>
      <button id="bJog">Jog</button>
    </div>
  </section>

  <section class="panel warn">
    Standalone build: join the <b>TankGuard-C1</b> hotspot and open <b>192.168.4.1</b>. The angles are estimates and there is no stall detection, so keep the e-stop within reach.
  </section>
  <div id="log"></div>
</main>
<script>
const $ = s => document.querySelector(s);
const get = async path => {
  const r = await fetch(path, { cache: 'no-store' });
  return r.json();
};
function badge(el, text, cls) {
  el.textContent = text;
  el.className = 'badge' + (cls ? ' ' + cls : '');
}
function dot(id, ok) {
  document.getElementById(id).className = 'dot ' + (ok ? 'g' : 'r');
}
function log(text) { $('#log').textContent = text; }
function setBusy(running) {
  ['bCheck', 'bHome', 'bStart', 'bReset', 'bJog'].forEach(id => {
    document.getElementById(id).disabled = running;
  });
}
function render(j) {
  const running = j.phase === 'running' || j.phase === 'homing' || j.phase === 'parking';
  badge($('#phase'), j.phase, running ? 'run' : (j.phase === 'fault' ? 'bad' : 'ok'));
  $('#fault').hidden = !j.fault;
  if (j.fault) $('#fault').textContent = j.fault;
  $('#ring').textContent = j.ring ? j.ring + ' / ' + j.arc : '\u2013';
  $('#t1').textContent = j.t1 == null ? '\u2013' : j.t1.toFixed(1) + '\u00b0';
  $('#t2').textContent = j.t2 == null ? '\u2013' : j.t2.toFixed(1) + '\u00b0';
  $('#level').textContent = j.level < 0 ? '\u2013' : j.level.toFixed(0) + '%';
  $('#bursts').textContent = j.bursts;
  $('#last').textContent = (j.lastMoveMs / 1000).toFixed(1) + 's';
  $('#prog').style.width = (j.progress || 0) + '%';
  $('#progressText').textContent = (j.arcsDone || 0) + ' / ' + j.arcCount + ' arcs';
  dot('dotLid', j.lid === 1);
  dot('dotEstop', j.estop === 0);
  dot('dotHome1', j.home1 === 1);
  dot('dotHome2', j.home2 === 1);
  $('#net').textContent = j.mode === 'ap' ? 'hotspot \u00b7 192.168.4.1' : '';
  setBusy(running);
}
async function refresh() {
  try {
    render(await get('/clean'));
  } catch (e) {
    badge($('#phase'), 'offline', 'bad');
  }
}
async function act(path, label) {
  try {
    const r = await get(path);
    let msg = label + ': ' + (r.ok === false ? 'refused, ' + (r.reason || 'error') : 'ok');
    if (r.reason === 'level stale') msg += ' \u2014 tick "Skip level check" for a bench run';
    log(msg);
  } catch (e) {
    log(label + ': no response');
  }
  refresh();
}
$('#bCheck').onclick = () => act('/clean?mode=check', 'Check');
$('#bHome').onclick = () => act('/clean?mode=home', 'Home');
$('#bReset').onclick = () => act('/clean?mode=reset', 'Reset');
$('#bStop').onclick = () => act('/clean?mode=stop', 'Stop');
$('#bStart').onclick = () => {
  const rings = $('#rings').value;
  const force = $('#force').checked ? '&force=1' : '';
  act('/clean?mode=start&rings=' + rings + force, 'Start');
};
$('#bJog').onclick = () => {
  const joint = $('#joint').value;
  const dir = $('#dir').value;
  const n = Math.max(1, Math.min(20, Number($('#bursts').value) || 1));
  act('/jog?joint=' + joint + '&dir=' + dir + '&bursts=' + n, 'Jog');
};
refresh();
setInterval(refresh, 1000);
</script>
</body>
</html>)HTML";
