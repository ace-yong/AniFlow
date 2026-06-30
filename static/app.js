// REST API bridge
function api(method, args) {
  var opts = {method:'GET'};
  if (args !== undefined) {
    opts.method = 'POST';
    opts.headers = {'Content-Type':'application/json'};
    opts.body = JSON.stringify(args);
  }
  return fetch('/api/'+method, opts).then(function(r){return r.json()});
}

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

// tool controls
function scanTool(tool) {
  var driveId = tool === 'onedragon' ? 'od-drive' : 'ma-drive';
  var drive = document.getElementById(driveId).value;
  addLog('正在扫描 '+tool+' ('+(drive||'全部盘符')+')...', 'INFO');
  api('scanTool', [tool, drive]).then(function(res) {
    if (tool === 'onedragon') {
      if (res.path) document.getElementById('cfg-od-path').value = res.path;
      if (res.python) document.getElementById('cfg-od-python').value = res.python;
    } else {
      if (res.path) document.getElementById('cfg-ma-path').value = res.path;
    }
    addLog(res.path ? '已找到 '+tool : '未找到 '+tool, res.path ? 'SUCCESS' : 'WARNING');
  });
}

function downloadTool(tool) {
  addLog('开始下载 '+tool+'...', 'INFO');
  api('downloadTool', [tool]).then(function(res) {
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

function startAll() {
  api('startGame', ['zenless_zone_zero']);
  api('startGame', ['endfield']);
}

function stopAll() {
  api('stopGame', ['zenless_zone_zero']);
  api('stopGame', ['endfield']);
}

// init
document.addEventListener('DOMContentLoaded', function() {
  ['od-drive','ma-drive'].forEach(function(id) {
    var sel = document.getElementById(id);
    for (var c = 67; c <= 90; c++) {
      var letter = String.fromCharCode(c);
      var o = document.createElement('option');
      o.value = letter+':\\'; o.textContent = letter+':\\';
      sel.appendChild(o);
    }
  });

  api('getConfig').then(function(cfg) {
    document.getElementById('cfg-od-path').value = cfg.onedragon_path;
    document.getElementById('cfg-od-python').value = cfg.onedragon_python;
    document.getElementById('cfg-ma-path').value = cfg.maaend_path;
    renderSequence(cfg.sequence);
    var radios = document.querySelectorAll('input[name="post_action"]');
    for (var i = 0; i < radios.length; i++) {
      if (radios[i].value === cfg.post_action) radios[i].checked = true;
    }
  });
  api('getVersion').then(function(v) { document.getElementById('ver-label').textContent = 'v'+v; });
});

// buttons in HTML use inline onclick, so they call api('startGame', ['type']) etc.
// We override the window-level api function to handle direct calls from HTML
window.startAll = startAll;
window.stopAll = stopAll;
window.scanTool = scanTool;
window.downloadTool = downloadTool;
window.clearLog = clearLog;
window.openLogFolder = function(){api('openLogFolder')};
window.checkUpdate = checkUpdate;

function checkUpdate() {
  document.getElementById('btn-update').disabled = true;
  document.getElementById('btn-update').textContent = '检查中...';
  api('checkUpdate').then(function(r) {
    document.getElementById('btn-update').disabled = false;
    document.getElementById('btn-update').textContent = '检查更新';
    var body = document.getElementById('update-body');
    if (r.latest !== r.current) {
      body.innerHTML = '<p>当前版本：<span style="color:#999">v'+r.current+'</span></p>'
        + '<p>最新版本：<span style="color:#52c41a;font-weight:bold">v'+r.latest+'</span></p>'
        + '<p style="margin-top:10px;font-size:12px;color:#666">'+(r.notes||'')+'</p>'
        + '<button class="dlg-btn dlg-ok" style="margin-top:12px" onclick="doUpdate()">立即更新</button>';
    } else {
      body.innerHTML = '<p>当前版本：<span style="color:#999">v'+r.current+'</span></p>'
        + '<p>最新版本：<span style="color:#52c41a;font-weight:bold">v'+r.current+'</span></p>'
        + '<p style="margin-top:12px;font-size:14px;color:#52c41a;font-weight:bold">✓ 已是最新版本</p>';
    }
    document.getElementById('update-overlay').style.display = 'flex';
  });
}

function doUpdate() {
  document.querySelector('#update-body .dlg-ok').textContent = '下载中...';
  addLog('正在下载更新...', 'INFO');
  api('downloadUpdate').then(function(err) {
    if (err && err.error) addLog('更新失败: '+err.error, 'ERROR');
  });
}

function closeUpdate() { document.getElementById('update-overlay').style.display = 'none'; }

// Config dialog
function openConfig() { document.getElementById('config-overlay').style.display = 'flex'; }
function closeConfig() { document.getElementById('config-overlay').style.display = 'none'; }

function switchTab(btn) {
  document.querySelectorAll('.tab-btn').forEach(function(b) { b.classList.remove('active'); });
  document.querySelectorAll('.tab-content').forEach(function(t) { t.classList.remove('active'); });
  btn.classList.add('active');
  document.getElementById(btn.dataset.tab).classList.add('active');
}

function saveConfig() {
  api('savePaths', [
    document.getElementById('cfg-od-path').value,
    document.getElementById('cfg-od-python').value,
    document.getElementById('cfg-ma-path').value
  ]);
  var seq = [];
  document.querySelectorAll('.seq-item').forEach(function(el) {
    var cb = el.querySelector('input[type="checkbox"]');
    if (cb.checked) seq.push(el.dataset.key);
  });
  api('saveSequence', [seq]);
  var action = document.querySelector('input[name="post_action"]:checked');
  if (action) api('savePostAction', [action.value]);
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
