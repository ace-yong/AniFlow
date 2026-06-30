// event dispatcher
window._on = function(event, args) {
  if (event === 'addLog') addLog(args[0], args[1] || 'INFO');
  else if (event === 'onStatus') onStatus(args[0], args[1]);
  else if (event === 'onToolOutput') onToolOutput(args[0], args[1]);
};

// log
function addLog(msg, level) {
  var el = document.getElementById('log-content');
  var colors = {INFO:'#333', SUCCESS:'#52c41a', WARNING:'#ff9800', ERROR:'#f44336'};
  var c = colors[level] || '#333';
  var ts = new Date().toLocaleTimeString('zh-CN', {hour12:false});
  el.innerHTML += '<span style="color:'+c+'">['+ts+'] '+esc(msg)+'</span><br>';
  el.scrollTop = el.scrollHeight;
}

function esc(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

function clearLog() { document.getElementById('log-content').innerHTML = ''; }

// status
function onStatus(gt, st) {
  var prefix = gt === 'zenless_zone_zero' ? 'od' : gt === 'endfield' ? 'ma' : null;
  if (!prefix) return;
  var ind = document.getElementById(prefix+'-indicator');
  var txt = document.getElementById(prefix+'-status');
  var start = document.getElementById(prefix+'-start');
  var stop = document.getElementById(prefix+'-stop');
  if (st === 'running') {
    ind.className = 'indicator running'; ind.textContent = '●';
    txt.textContent = '运行中'; txt.className = 'status-text running';
    start.disabled = true; stop.disabled = false;
  } else if (st === 'stopped') {
    ind.className = 'indicator idle'; ind.textContent = '●';
    txt.textContent = '已停止'; txt.className = 'status-text idle';
    start.disabled = false; stop.disabled = true;
  } else if (st === 'failed') {
    ind.className = 'indicator error'; ind.textContent = '✗';
    txt.textContent = '启动失败'; txt.className = 'status-text error';
    start.disabled = false; stop.disabled = true;
  }
}

function onToolOutput(src, line) {
  var labels = {zenless_zone_zero:'绝区零', endfield:'终末地', onedragon:'OneDragon', maaend:'MaaEnd'};
  addLog('['+(labels[src]||src)+'] '+line, 'INFO');
}

// tool controls
function startAll() {
  api.startGame('zenless_zone_zero');
  api.startGame('endfield');
}
function stopAll() {
  api.stopGame('zenless_zone_zero');
  api.stopGame('endfield');
}

// init
document.addEventListener('DOMContentLoaded', function() {
  // populate drive selects
  var drives = [];
  for (var c = 67; c <= 90; c++) {
    var letter = String.fromCharCode(c);
    drives.push(letter+':\\');
  }
  ['od-drive','ma-drive'].forEach(function(id) {
    var sel = document.getElementById(id);
    drives.forEach(function(d) { var o = document.createElement('option'); o.value = d; o.textContent = d; sel.appendChild(o); });
  });
  // load config
  api.getConfig().then(function(cfg) {
    document.getElementById('cfg-od-path').value = cfg.onedragon_path;
    document.getElementById('cfg-od-python').value = cfg.onedragon_python;
    document.getElementById('cfg-ma-path').value = cfg.maaend_path;
    // sequence
    renderSequence(cfg.sequence);
    // post action
    var radios = document.querySelectorAll('input[name="post_action"]');
    for (var i = 0; i < radios.length; i++) { if (radios[i].value === cfg.post_action) radios[i].checked = true; }
    // version
    api.getVersion().then(function(v) { document.getElementById('ver-label').textContent = 'v'+v; });
  });
});

// config dialog
function openConfig() { document.getElementById('config-overlay').style.display = 'flex'; }
function closeConfig() { document.getElementById('config-overlay').style.display = 'none'; }

function switchTab(btn) {
  document.querySelectorAll('.tab-btn').forEach(function(b) { b.classList.remove('active'); });
  document.querySelectorAll('.tab-content').forEach(function(t) { t.classList.remove('active'); });
  btn.classList.add('active');
  document.getElementById(btn.dataset.tab).classList.add('active');
}

function scanTool(tool) {
  var driveId = tool === 'onedragon' ? 'od-drive' : 'ma-drive';
  var drive = document.getElementById(driveId).value;
  addLog('正在扫描 '+tool+' ('+(drive||'全部盘符')+')...', 'INFO');
  api.scanTool(tool, drive).then(function(r) {
    var res = JSON.parse(r);
    if (tool === 'onedragon') {
      if (res.path) { document.getElementById('cfg-od-path').value = res.path; }
      if (res.python) { document.getElementById('cfg-od-python').value = res.python; }
    } else {
      if (res.path) { document.getElementById('cfg-ma-path').value = res.path; }
    }
    addLog((res.path?'已找到 '+tool:'未找到 '+tool), res.path?'SUCCESS':'WARNING');
  });
}

function downloadTool(tool) {
  addLog('开始下载 '+tool+'...', 'INFO');
  api.downloadTool(tool).then(function(r) {
    var res = JSON.parse(r);
    if (res.path) {
      if (tool === 'onedragon') {
        document.getElementById('cfg-od-path').value = res.path;
        if (res.python) document.getElementById('cfg-od-python').value = res.python;
      } else {
        document.getElementById('cfg-ma-path').value = res.path;
      }
      addLog(tool+' 下载安装完成', 'SUCCESS');
    } else if (res.error) {
      addLog(tool+' 下载失败: '+res.error, 'ERROR');
    }
  });
}

function saveConfig() {
  var odPath = document.getElementById('cfg-od-path').value;
  var odPy = document.getElementById('cfg-od-python').value;
  var maPath = document.getElementById('cfg-ma-path').value;
  api.savePaths(odPath, odPy, maPath);

  var seq = [];
  document.querySelectorAll('.seq-item').forEach(function(el) {
    var cb = el.querySelector('input[type="checkbox"]');
    seq.push({key: el.dataset.key, enabled: cb.checked});
  });
  api.saveSequence(seq.filter(function(s) { return s.enabled; }).map(function(s) { return s.key; }));

  var action = document.querySelector('input[name="post_action"]:checked');
  if (action) api.savePostAction(action.value);

  closeConfig();
  addLog('配置已保存', 'SUCCESS');
}

function renderSequence(seq) {
  var labels = {onedragon:'OneDragon（绝区零无头模式）', maaend:'MaaEnd（终末地）'};
  var el = document.getElementById('seq-list');
  el.innerHTML = '';
  seq.forEach(function(key) {
    var item = document.createElement('div');
    item.className = 'seq-item';
    item.dataset.key = key;
    item.draggable = true;
    item.innerHTML = '<input type="checkbox" checked> <span class="seq-name">'+(labels[key]||key)+'</span>'
      + '<span class="seq-move" onclick="moveSeqItem(this,-1)">▲</span>'
      + '<span class="seq-move" onclick="moveSeqItem(this,1)">▼</span>';
    // drag events
    item.addEventListener('dragstart', function(e) { e.dataTransfer.setData('text/plain', key); this.classList.add('dragging'); });
    item.addEventListener('dragend', function() { this.classList.remove('dragging'); });
    item.addEventListener('dragover', function(e) { e.preventDefault(); });
    item.addEventListener('drop', function(e) {
      e.preventDefault();
      var fromKey = e.dataTransfer.getData('text/plain');
      var toKey = this.dataset.key;
      if (fromKey !== toKey) swapSeqItems(fromKey, toKey);
    });
    el.appendChild(item);
  });
}

function moveSeqItem(btn, dir) {
  var item = btn.parentElement;
  var list = item.parentElement;
  var idx = Array.prototype.indexOf.call(list.children, item);
  var target = idx + dir;
  if (target < 0 || target >= list.children.length) return;
  if (dir < 0) list.insertBefore(item, list.children[target]);
  else list.insertBefore(item, list.children[target + 1]);
}

function swapSeqItems(a, b) {
  var list = document.getElementById('seq-list');
  var items = list.children;
  var ai = -1, bi = -1;
  for (var i = 0; i < items.length; i++) {
    if (items[i].dataset.key === a) ai = i;
    if (items[i].dataset.key === b) bi = i;
  }
  if (ai < 0 || bi < 0) return;
  if (ai < bi) list.insertBefore(items[ai], items[bi + 1]);
  else list.insertBefore(items[ai], items[bi]);
}

// update
function checkUpdate() {
  document.getElementById('btn-update').disabled = true;
  document.getElementById('btn-update').textContent = '检查中...';
  api.checkUpdate().then(function(r) {
    document.getElementById('btn-update').disabled = false;
    document.getElementById('btn-update').textContent = '检查更新';
    var data = JSON.parse(r);
    var body = document.getElementById('update-body');
    if (data.latest !== data.current) {
      body.innerHTML = '<p>当前版本：<span style="color:#999">v'+data.current+'</span></p>'
        + '<p>最新版本：<span style="color:#52c41a;font-weight:bold">v'+data.latest+'</span></p>'
        + '<p style="margin-top:10px;font-size:12px;color:#666">'+(data.notes||'')+'</p>'
        + '<button class="dlg-btn dlg-ok" style="margin-top:12px" onclick="doUpdate()">立即更新</button>';
    } else {
      body.innerHTML = '<p>当前版本：<span style="color:#999">v'+data.current+'</span></p>'
        + '<p>最新版本：<span style="color:#52c41a;font-weight:bold">v'+data.current+'</span></p>'
        + '<p style="margin-top:12px;font-size:14px;color:#52c41a;font-weight:bold">✓ 已是最新版本</p>';
    }
    document.getElementById('update-overlay').style.display = 'flex';
  });
}

function doUpdate() {
  document.querySelector('#update-body .dlg-ok').textContent = '下载中...';
  addLog('正在下载更新...', 'INFO');
  api.downloadUpdate().then(function(err) {
    if (err) addLog('更新失败: '+err, 'ERROR');
  });
}

function closeUpdate() { document.getElementById('update-overlay').style.display = 'none'; }

function openLogFolder() {
  // this would need a python bridge call
  addLog('日志目录: 在 exe 同级的 AniFlow/logs/ 下', 'INFO');
}
