function api(method, args) {
  var opts = {method:'GET'};
  if (args !== undefined) { opts.method='POST'; opts.headers={'Content-Type':'application/json'}; opts.body=JSON.stringify(args); }
  return fetch('/api/'+method, opts).then(function(r){return r.json()});
}

function addLog(msg, level) {
  var el = document.getElementById('log-content');
  var colors = {INFO:'#333',SUCCESS:'#52c41a',WARNING:'#ff9800',ERROR:'#f44336'};
  var c = colors[level]||'#333', ts=new Date().toLocaleTimeString('zh-CN',{hour12:false});
  el.innerHTML += '<span style="color:'+c+'">['+ts+'] '+esc(msg)+'</span><br>';
  el.scrollTop = el.scrollHeight;
}
function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}
function clearLog(){document.getElementById('log-content').innerHTML=''}

function startAll(){api('startGame',['zenless_zone_zero']);api('startGame',['endfield'])}
function stopAll(){api('stopGame',['zenless_zone_zero']);api('stopGame',['endfield'])}

// Buttons use inline onclick -> api(...)
window.startAll=startAll;window.stopAll=stopAll;window.clearLog=clearLog;
window.openConfig=openConfig;window.closeConfig=closeConfig;
window.switchTab=switchTab;window.saveConfig=saveConfig;
window.checkUpdate=checkUpdate;window.closeUpdate=closeUpdate;

document.addEventListener('DOMContentLoaded',function(){
  api('getConfig').then(function(cfg){
    document.getElementById('cfg-od-path').value=cfg.onedragon_path;
    document.getElementById('cfg-od-python').value=cfg.onedragon_python;
    document.getElementById('cfg-ma-path').value=cfg.maaend_path;
    renderSequence(cfg.sequence);
    var radios=document.querySelectorAll('input[name=\"post_action\"]');
    for(var i=0;i<radios.length;i++){if(radios[i].value===cfg.post_action)radios[i].checked=true}
  });
  api('getVersion').then(function(v){document.getElementById('ver-label').textContent='v'+v});
});

function openConfig(){document.getElementById('config-overlay').style.display='flex'}
function closeConfig(){document.getElementById('config-overlay').style.display='none'}
function switchTab(btn){
  document.querySelectorAll('.tab-btn').forEach(function(b){b.classList.remove('active')});
  document.querySelectorAll('.tab-content').forEach(function(t){t.classList.remove('active')});
  btn.classList.add('active');document.getElementById(btn.dataset.tab).classList.add('active');
}
function saveConfig(){
  api('savePaths',[document.getElementById('cfg-od-path').value,document.getElementById('cfg-od-python').value,document.getElementById('cfg-ma-path').value]);
  var seq=[];document.querySelectorAll('.seq-item').forEach(function(el){var cb=el.querySelector('input[type=\"checkbox\"]');if(cb.checked)seq.push(el.dataset.key)});
  api('saveSequence',[seq]);
  var a=document.querySelector('input[name=\"post_action\"]:checked');if(a)api('savePostAction',[a.value]);
  closeConfig();addLog('配置已保存','SUCCESS');
}
function renderSequence(seq){
  var labels={onedragon:'OneDragon（绝区零无头模式）',maaend:'MaaEnd（终末地）'};
  var el=document.getElementById('seq-list');el.innerHTML='';
  seq.forEach(function(key){
    var item=document.createElement('div');item.className='seq-item';item.dataset.key=key;item.draggable=true;
    item.innerHTML='<input type=\"checkbox\" checked> <span class=\"seq-name\">'+(labels[key]||key)+'</span><span class="seq-move" onclick="moveSeqItem(this,-1)">▲</span><span class="seq-move" onclick="moveSeqItem(this,1)">▼</span>';
    item.addEventListener('dragstart',function(e){e.dataTransfer.setData('text/plain',key);this.classList.add('dragging')});
    item.addEventListener('dragend',function(){this.classList.remove('dragging')});
    item.addEventListener('dragover',function(e){e.preventDefault()});
    item.addEventListener('drop',function(e){
      e.preventDefault();var fk=e.dataTransfer.getData('text/plain'),tk=this.dataset.key;if(fk!==tk)swapSeqItems(fk,tk);
    });
    el.appendChild(item);
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
function checkUpdate(){
  var btn=document.getElementById('btn-update');btn.disabled=true;btn.textContent='检查中...';
  api('checkUpdate').then(function(r){
    btn.disabled=false;btn.textContent='检查更新';
    var body=document.getElementById('update-body');
    if(r.latest!==r.current){
      body.innerHTML='<p>当前版本：<span style="color:#999">v'+r.current+'</span></p><p>最新版本：<span style="color:#52c41a;font-weight:bold">v'+r.latest+'</span></p><button class="dlg-btn dlg-ok" style="margin-top:12px" onclick="doUpdate()">立即更新</button>';
    }else{
      body.innerHTML='<p>当前版本：<span style="color:#999">v'+r.current+'</span></p><p>最新版本：<span style="color:#52c41a;font-weight:bold">v'+r.current+'</span></p><p style="margin-top:12px;font-size:14px;color:#52c41a;font-weight:bold">✓ 已是最新版本</p>';
    }
  });
}
function doUpdate(){addLog('更新功能需要在 Electron 中运行','WARNING')}
function closeUpdate(){}
