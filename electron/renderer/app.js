// ---------- API helper ----------
function api(method, args) {
  var opts = {method:'GET'};
  if (args !== undefined) { opts.method='POST'; opts.headers={'Content-Type':'application/json'}; opts.body=JSON.stringify(args); }
  return fetch('/api/'+method, opts).then(function(r){return r.json()});
}

// ---------- log ----------
function addLog(msg, level) {
  var el = document.getElementById('log-content');
  var colors = {INFO:'#333',SUCCESS:'#52c41a',WARNING:'#ff9800',ERROR:'#f44336'};
  var c = colors[level]||'#333', ts=new Date().toLocaleTimeString('zh-CN',{hour12:false});
  el.innerHTML += '<span style="color:'+c+'">['+ts+'] '+esc(msg)+'</span><br>';
  el.scrollTop = el.scrollHeight;
}
function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}
function clearLog(){document.getElementById('log-content').innerHTML=''}
function openLogFolder(){api('openLogFolder')}

// ---------- status bar ----------
function setStatus(msg, state) {
  state = state || 'idle';
  document.getElementById('statusbar-msg').textContent = msg;
  var ind = document.getElementById('statusbar-indicator');
  ind.className = state;
}

var _gameLabels = { zenless_zone_zero: '绝区零', endfield: '终末地' };
var _seqRunning = false;

// ---------- SSE real-time events ----------
function connectSSE() {
  var es = new EventSource('/api/events');
  es.addEventListener('status', function(e) {
    var d = JSON.parse(e.data);
    var gt = d.game_type, st = d.status;
    if (gt === 'pipeline') {
      if (st === 'seq_completed') {
        document.getElementById('seq-status').textContent = '全部任务完成 ✓';
        document.getElementById('seq-status').style.cssText = 'color:#4CAF50;font-size:12px;padding:0 8px;font-weight:bold';
        document.getElementById('btn-run').disabled = false;
        document.getElementById('btn-stop').disabled = true;
        setStatus('全部任务完成', 'idle');
        _seqRunning = false;
      } else if (st.indexOf('seq_') === 0 && st.indexOf('_running') > 0) {
        var key = st.substring(4, st.length - 8);
        var labels = {onedragon:'OneDragon',maaend:'MaaEnd'};
        document.getElementById('seq-status').textContent = '正在执行 ' + (labels[key]||key) + '...';
        document.getElementById('seq-status').style.cssText = 'color:#FF9800;font-size:12px;padding:0 8px;font-weight:bold';
        document.getElementById('btn-run').disabled = true;
        document.getElementById('btn-stop').disabled = false;
        setStatus('正在执行 ' + (labels[key]||key) + '...', 'running');
      }
      return;
    }
    var label = _gameLabels[gt] || gt;
    if (st === 'running') {
      addLog(label + ' ● 启动成功', 'SUCCESS');
      setStatus('运行中...', 'running');
    } else if (st === 'closing') {
      addLog(label + ' ● 正在关闭...', 'INFO');
    } else if (st === 'stopped') {
      addLog(label + ' ○ 已停止', 'WARNING');
      setStatus('就绪', 'idle');
    } else if (st === 'failed') {
      addLog(label + ' ✗ 启动失败，请检查工具路径', 'ERROR');
      setStatus('启动失败', 'error');
    }
  });
  es.addEventListener('output', function(e) {
    var d = JSON.parse(e.data);
    var labels = {zenless_zone_zero:'绝区零',endfield:'终末地',onedragon:'OneDragon',maaend:'MaaEnd'};
    addLog('[' + (labels[d.source]||d.source) + '] ' + d.line, 'INFO');
  });
  es.addEventListener('download_status', function(e) {
    var d = JSON.parse(e.data);
    if (d.done) {
      _dlInProgress = false;
      var btn = document.getElementById('btn-dl-' + (d.name === 'OneDragon' ? 'od' : 'ma'));
      btn.disabled = false; btn.textContent = '⬇ 下载安装 ' + d.name;
      if (d.error) {
        setDlStatus(d.msg, true);
      } else {
        setDlStatus(d.name + ' 下载完成！');
        if (d.path) {
          if (d.name === 'OneDragon') { document.getElementById('cfg-od-path').value = d.path; }
          if (d.name === 'MaaEnd') { document.getElementById('cfg-ma-path').value = d.path; }
        }
        if (d.python_path) { document.getElementById('cfg-od-python').value = d.python_path; }
      }
    } else {
      setDlStatus(d.msg);
    }
    addLog(d.msg, d.error ? 'ERROR' : 'INFO');
  });
  es.onerror = function() {
    setTimeout(connectSSE, 3000);
  };
}

// ---------- start / stop ----------
function startAll(){
  for (var gt in _gameLabels) { api('startGame',[gt]); }
  addLog('正在打开所有工具...','INFO');
}
function stopAll(){
  for (var gt in _gameLabels) { api('stopGame',[gt]); }
  addLog('正在关闭所有工具...','INFO');
}
function startSequence(){
  if (_seqRunning) return;
  api('getConfig').then(function(cfg){
    var hasAny=cfg.sequence&&cfg.sequence.some(function(item){return item.enabled!==false});
    if (!hasAny) {
      addLog('没有可运行的工具，请在配置-执行顺序中勾选', 'WARNING');
      return;
    }
    _seqRunning = true;
    api('startSequence');
    document.getElementById('btn-run').disabled = true;
    document.getElementById('btn-stop').disabled = false;
    document.getElementById('seq-status').textContent = '执行中...';
    document.getElementById('seq-status').style.cssText = 'color:#FF9800;font-size:12px;padding:0 8px;font-weight:bold';
    setStatus('执行中...', 'running');
  });
}
function stopSequence(){
  api('stopSequence');
  document.getElementById('btn-run').disabled = false;
  document.getElementById('btn-stop').disabled = true;
  document.getElementById('seq-status').textContent = '已停止';
  document.getElementById('seq-status').style.cssText = 'color:#f44336;font-size:12px;padding:0 8px';
  setStatus('已停止', 'idle');
  _seqRunning = false;
}
// ---------- wallpaper ----------
function setWallpaper() {
  var img = new Image();
  img.onload = function() {
    document.getElementById('app').style.backgroundImage = 'url(/wallpaper.jpg)';
    document.getElementById('app').style.backgroundSize = 'cover';
    document.getElementById('app').style.backgroundPosition = 'center';
    document.getElementById('app').style.backgroundAttachment = 'fixed';
  };
  img.onerror = function() {
    document.getElementById('app').style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
  };
  img.src = '/wallpaper.jpg';
}

// ---------- scan tools ----------
function setDlStatus(msg, isError) {
  var el = document.getElementById('dl-status');
  if (!msg) { el.style.display = 'none'; return; }
  el.style.display = 'block';
  el.style.background = isError ? '#fff2f0' : '#fffbe6';
  el.style.borderColor = isError ? '#ffccc7' : '#ffe58f';
  el.style.color = isError ? '#cf1322' : '#ad8b00';
  el.textContent = msg;
}

function scanOD(btn) {
  btn.disabled = true; btn.textContent = '⏳ 扫描中...';
  api('scanOD').then(function(r){
    if (r.path) { document.getElementById('cfg-od-path').value = r.path; }
    if (r.python_path) { document.getElementById('cfg-od-python').value = r.python_path; }
    btn.disabled = false; btn.textContent = '🔍 自动检测';
    setDlStatus(r.path ? '已找到 OneDragon' : '未扫描到 OneDragon', !r.path);
  });
}

function scanMaa(btn) {
  btn.disabled = true; btn.textContent = '⏳ 扫描中...';
  api('scanMaa').then(function(r){
    if (r.path) { document.getElementById('cfg-ma-path').value = r.path; }
    btn.disabled = false; btn.textContent = '🔍 自动检测';
    setDlStatus(r.path ? '已找到 MaaEnd' : '未扫描到 MaaEnd', !r.path);
  });
}

// ---------- download tools ----------
var _dlInProgress = false;

function downloadTool(name) {
  if (_dlInProgress) { setDlStatus('已有下载任务进行中', true); return; }
  _dlInProgress = true;
  var btn = document.getElementById('btn-dl-' + (name === 'OneDragon' ? 'od' : 'ma'));
  btn.disabled = true; btn.textContent = '⏳ 下载中...';
  setDlStatus('正在下载 ' + name + '...');
  api('downloadTool', [name]);
}

window.startAll=startAll;window.stopAll=stopAll;window.clearLog=clearLog;
window.openConfig=openConfig;window.closeConfig=closeConfig;
window.switchTab=switchTab;window.saveConfig=saveConfig;
window.checkUpdate=checkUpdate;window.closeUpdate=closeUpdate;
window.openLogFolder=openLogFolder;
window.startSequence=startSequence;window.stopSequence=stopSequence;
window.scanOD=scanOD;window.scanMaa=scanMaa;window.downloadTool=downloadTool;


// ---------- config dialog ----------
document.addEventListener('DOMContentLoaded',function(){
  api('getConfig').then(function(cfg){
    document.getElementById('cfg-od-path').value=cfg.onedragon_path||'';
    document.getElementById('cfg-od-python').value=cfg.onedragon_python||'';
    document.getElementById('cfg-ma-path').value=cfg.maaend_path||'';
    renderSequence(cfg.sequence);
    var radios=document.querySelectorAll('input[name="post_action"]');
    for(var i=0;i<radios.length;i++){if(radios[i].value===cfg.post_action)radios[i].checked=true}
    if (cfg.exec_timeout !== undefined) document.getElementById('cfg-exec-timeout').value = cfg.exec_timeout;
    if (cfg.exec_retry !== undefined) document.getElementById('cfg-exec-retry').value = cfg.exec_retry;
    if (cfg.exec_switch_delay !== undefined) document.getElementById('cfg-exec-switch').value = cfg.exec_switch_delay;
  });
  api('getVersion').then(function(v){document.getElementById('ver-label').textContent='v'+v});
  setWallpaper();
  connectSSE();
});

function openConfig(){
  document.getElementById('config-overlay').style.display='flex';
  api('getConfig').then(function(cfg){
    document.getElementById('cfg-od-path').value=cfg.onedragon_path||'';
    document.getElementById('cfg-od-python').value=cfg.onedragon_python||'';
    document.getElementById('cfg-ma-path').value=cfg.maaend_path||'';
    renderSequence(cfg.sequence);
    var radios=document.querySelectorAll('input[name="post_action"]');
    for(var i=0;i<radios.length;i++){if(radios[i].value===cfg.post_action)radios[i].checked=true}
    if (cfg.exec_timeout !== undefined) document.getElementById('cfg-exec-timeout').value = cfg.exec_timeout;
    if (cfg.exec_retry !== undefined) document.getElementById('cfg-exec-retry').value = cfg.exec_retry;
    if (cfg.exec_switch_delay !== undefined) document.getElementById('cfg-exec-switch').value = cfg.exec_switch_delay;
  });
}
function closeConfig(){document.getElementById('config-overlay').style.display='none'}
function switchTab(btn){
  document.querySelectorAll('.tab-btn').forEach(function(b){b.classList.remove('active')});
  document.querySelectorAll('.tab-content').forEach(function(t){t.classList.remove('active')});
  btn.classList.add('active');document.getElementById(btn.dataset.tab).classList.add('active');
}

function saveConfig(){
  var a=document.querySelector('input[name="post_action"]:checked');
  var seq=[].map.call(document.querySelectorAll('.seq-item'),function(el){return{name:el.dataset.key,enabled:!!(el.querySelector('input[type="checkbox"]')||{}).checked}});
  api('saveConfig',[{
    onedragon_path: document.getElementById('cfg-od-path').value,
    onedragon_python: document.getElementById('cfg-od-python').value,
    maaend_path: document.getElementById('cfg-ma-path').value,
    sequence: seq,
    post_action: a?a.value:'close_game',
    exec_timeout: parseInt(document.getElementById('cfg-exec-timeout').value)||7200,
    exec_retry: parseInt(document.getElementById('cfg-exec-retry').value)||3,
    exec_switch_delay: parseInt(document.getElementById('cfg-exec-switch').value)||10
  }]).then(function(){
    addLog('配置已保存','SUCCESS');
    closeConfig();
  },function(){
    addLog('配置保存失败','ERROR');
  });
}

function renderSequence(seq){
  var labels={onedragon:'OneDragon（绝区零无头模式）',maaend:'MaaEnd（终末地）'};
  var el=document.getElementById('seq-list');el.innerHTML='';
  var allKeys=Object.keys(labels);
  var items=[];
  // convert old string-array format to {name,enabled}
  if (!seq||!seq.length) {
    allKeys.forEach(function(k){items.push({name:k,enabled:true})});
  } else if (typeof seq[0]=='string') {
    var raw={}; seq.forEach(function(k){raw[k.replace(/^~/,'')]=!k.startsWith('~')});
    seq.forEach(function(k){var n=k.replace(/^~/,'');if(allKeys.indexOf(n)>=0)items.push({name:n,enabled:raw[n]})});
    allKeys.forEach(function(k){if(!items.some(function(i){return i.name===k}))items.push({name:k,enabled:false})});
  } else {
    items=seq.slice();
    allKeys.forEach(function(k){if(!items.some(function(i){return i.name===k}))items.push({name:k,enabled:false})});
  }
  items.forEach(function(item){
    var d=document.createElement('div');d.className='seq-item';d.dataset.key=item.name;d.draggable=true;
    d.innerHTML='<input type=\"checkbox\"'+(item.enabled?' checked':'')+'> <span class=\"seq-name\">'+(labels[item.name]||item.name)+'</span><span class="seq-move" onclick="moveSeqItem(this,-1)">▲</span><span class="seq-move" onclick="moveSeqItem(this,1)">▼</span>';
    d.addEventListener('dragstart',function(e){e.dataTransfer.setData('text/plain',item.name);this.classList.add('dragging')});
    d.addEventListener('dragend',function(){this.classList.remove('dragging')});
    d.addEventListener('dragover',function(e){e.preventDefault()});
    d.addEventListener('drop',function(e){
      e.preventDefault();var fk=e.dataTransfer.getData('text/plain'),tk=this.dataset.key;if(fk!==tk)swapSeqItems(fk,tk);
    });
    el.appendChild(d);
  });
}
function moveSeqItem(btn,dir){
  var item=btn.parentElement,list=item.parentElement,idx=Array.prototype.indexOf.call(list.children,item),t=idx+dir;
  if(t<0||t>=list.children.length)return;
  if(dir<0)list.insertBefore(item,list.children[t]);else list.insertBefore(item,list.children[t+1]);
}
function swapSeqItems(a,b){
  var list=document.getElementById('seq-list'),items=list.children,ai=-1,bi=-1;
  for(var i=0;i<items.length;i++){if(items[i].dataset.key===a)ai=i;if(items[i].dataset.key===b)bi=i}
  if(ai<0||bi<0)return;
  if(ai<bi)list.insertBefore(items[ai],items[bi+1]);else list.insertBefore(items[ai],items[bi]);
}



// ---------- update ----------
function checkUpdate(){
  var btn=document.getElementById('btn-update');btn.disabled=true;btn.textContent='检查中...';
  api('checkUpdate').then(function(r){
    btn.disabled=false;btn.textContent='检查更新';
    var body=document.getElementById('update-body');
    if(r.current && r.latest && r.latest!==r.current){
      body.innerHTML='<p>当前版本：<span style="color:#999">v'+r.current+'</span></p><p>最新版本：<span style="color:#52c41a;font-weight:bold">v'+r.latest+'</span></p><p style="margin-top:8px;font-size:12px;color:#666;text-align:left;max-height:120px;overflow-y:auto">'+(r.notes||'')+'</p><button class="dlg-btn dlg-ok" style="margin-top:12px" onclick="doUpdate()">立即更新</button>';
    }else{
      body.innerHTML='<p>当前版本：<span style="color:#999">v'+(r.current||'')+'</span></p><p>最新版本：<span style="color:#52c41a;font-weight:bold">v'+(r.latest||r.current||'')+'</span></p><p style="margin-top:12px;font-size:14px;color:#52c41a;font-weight:bold">✓ 已是最新版本</p>';
    }
    document.getElementById('update-overlay').style.display='flex';
  });
}
function doUpdate(){addLog('请前往 https://github.com/ace-yong/AniFlow/releases 下载更新','WARNING')}
function closeUpdate(){document.getElementById('update-overlay').style.display='none'}
