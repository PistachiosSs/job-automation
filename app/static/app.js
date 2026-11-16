'use strict';
const token = document.querySelector('meta[name="job-apply-token"]').content;
const state = {page:'new',app:null,apps:[],kind:'cv',dirty:false,hasPdf:false};
const $ = id => document.getElementById(id);
const statuses = {draft:'Draft',compiled:'Compiled',approved:'Approved',missing_template:'Missing template',not_requested:'Not requested'};
let toastTimer;

async function api(path, data) {
  const options = data === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json','X-Job-Apply-Token':token},body:JSON.stringify(data)};
  const response = await fetch(path,options);
  const result = await response.json();
  if (!response.ok || result.ok===false) throw new Error(result.message || 'Something went wrong');
  return result.result === undefined ? result : result.result;
}
function toast(message, bad=false){const box=$('toast');box.textContent=message;box.classList.toggle('error',bad);box.style.display='block';clearTimeout(toastTimer);toastTimer=setTimeout(()=>box.style.display='none',5000)}
function showPage(page){
  state.page=page;
  document.querySelectorAll('.page').forEach(el=>el.classList.toggle('active',el.id==='page-'+page));
  document.querySelectorAll('.nav[data-section]').forEach(el=>el.classList.toggle('active',el.dataset.section===page));
  $('active-location').textContent = ({new:'New application',documents:'Document studio',tracker:'Application tracker',templates:'Templates & prompts'})[page];
  if (page==='tracker') renderTracker();
  if (page==='templates'){refreshHealth();loadPromptSettings();}
}
function statusText(s){return statuses[s] || s || 'Not requested'}
function shortDate(iso){return iso ? iso.slice(0,10) : '—'}
function addCell(tr,value,className){const td=document.createElement('td');td.textContent=value;if(className)td.className=className;tr.appendChild(td);return td}
async function refreshHealth(){
  const h=await api('/api/health');
  $('cv-health').textContent=h.cv_template?'Template loaded':'Missing';
  $('cover-health').textContent=h.cover_template?'Template loaded':'Missing';
  $('cv-hint').textContent=h.cv_missing_assets.length ? 'Missing required asset(s): '+h.cv_missing_assets.join(', ') : 'CV source and referenced image assets found';
  $('cover-hint').textContent=h.cover_template?'Cover letter LaTeX source is available':'Upload the cover letter LaTeX project to enable this option';
  const warnings=[];
  if(h.engine!=='pdflatex')warnings.push('PDF compiler not detected: install MacTeX or BasicTeX.');
  if(h.cv_missing_assets.length)warnings.push('CV requires missing asset: '+h.cv_missing_assets.join(', ')+'.');
  if(!h.cover_template)warnings.push('Cover letter template has not been added.');
  $('setup-alert').style.display=warnings.length?'block':'none';
  $('setup-alert').textContent=warnings.length?'Setup notice: '+warnings.join(' ') : '';
  return h;
}
async function refreshApps(){
  const data=await api('/api/applications');
  state.apps=data.items;
  const selector=$('app-selector');
  const selected=state.app && state.app.id;
  selector.replaceChildren();
  const blank=new Option('Select an application','');selector.add(blank);
  for (const a of state.apps)selector.add(new Option(`${a.company} · ${a.job_title} · ${a.status}`,a.id));
  if(selected)selector.value=selected;
  $('tracker-count').textContent=state.apps.length+' application'+(state.apps.length===1?'':'s');
}
async function loadApp(appId){
  if(!appId){state.app=null;state.hasPdf=false;renderDocEmpty();return;}
  const result=await api('/api/application?id='+encodeURIComponent(appId));
  state.app=result.item;
  state.dirty=false;
  $('app-selector').value=state.app.id;
  renderDocEmpty();
  await loadDocument();
}
function renderDocEmpty(){
  const exists=Boolean(state.app);
  $('doc-empty').classList.toggle('hidden',exists);
  $('doc-panel').classList.toggle('hidden',!exists);
  if(!exists)return;
  $('app-status').textContent=state.app.status;
  for (const kind of ['cv','cover-letter']){
    const span=$(kind==='cv'?'cv-badge':'cover-badge');
    span.textContent=statusText(state.app.documents[kind].status);
  }
  const requested=Object.entries(state.app.documents).filter(([,d])=>d.requested);
  const pending=requested.filter(([,d])=>d.status!=='approved');
  $('readiness-text').textContent=pending.length?'Still awaiting approval: '+pending.map(([k])=>k==='cv'?'CV':'Cover letter').join(', '):'All requested documents approved. You can mark this application Prepared.';
  $('mark-prepared').disabled=Boolean(pending.length)||Boolean(state.app.prepared_at);
  $('mark-prepared').textContent=state.app.prepared_at?'Prepared ✓':'Mark as Prepared →';
}
async function loadDocument(){
  if(!state.app)return;
  const kind=state.kind;
  document.querySelectorAll('.tab').forEach(t=>t.classList.toggle('active',t.dataset.kind===kind));
  $('editor-heading').textContent=(kind==='cv'?'CV':'Cover letter')+' source — main.tex';
  const doc=state.app.documents[kind];
  const result=await api('/api/document?id='+encodeURIComponent(state.app.id)+'&kind='+kind);
  $('tex-editor').value=result.tex;
  $('tex-editor').disabled=!doc.requested;
  $('dirty-indicator').textContent=!doc.requested?'Not requested for this application':(result.tex?'Source loaded from working copy':'Template not available');
  $('generate-prompt').disabled=!doc.requested||!result.tex;
  $('save-source').disabled=!doc.requested;
  $('compile-button').disabled=!doc.requested||!result.tex;
  $('approve-document').disabled=doc.status!=='compiled';
  $('approve-document').textContent=doc.status==='approved'?'Approved ✓':'Approve document ✓';
  $('compile-badge').textContent=statusText(doc.status);
  $('compile-errors').classList.add('hidden');
  state.dirty=false;
  showPdf(doc.status==='compiled'||doc.status==='approved');
}
function showPdf(hasPdf){
  if(!state.app)return;
  state.hasPdf=hasPdf;
  $('pdf-frame').classList.toggle('hidden',!hasPdf);
  $('preview-fallback').classList.toggle('hidden',hasPdf);
  if(hasPdf)$('pdf-frame').src='/api/pdf?id='+encodeURIComponent(state.app.id)+'&kind='+state.kind+'&t='+Date.now();
  else $('pdf-frame').removeAttribute('src');
  $('download-pdf').disabled=!hasPdf||state.app.documents[state.kind].status!=='approved';
  $('download-tex').disabled=!$('tex-editor').value.trim();
}
async function saveSource(){
  if(!state.app)return;
  let tex=$('tex-editor').value;
  const fence=tex.match(/^\s*```(?:tex|latex)?\s*\n([\s\S]*?)\n```\s*$/i);
  if(fence){tex=fence[1];$('tex-editor').value=tex;}
  const entry=await api('/api/save-document',{id:state.app.id,kind:state.kind,tex});
  state.app=entry;
  state.dirty=false;
  $('dirty-indicator').textContent='Saved to this application (master unchanged)';
  renderDocEmpty();
  showPdf(false);
  $('approve-document').disabled=true;
  $('compile-badge').textContent='Draft';
  return entry;
}
async function compileSource(){
  try{
    $('compile-button').disabled=true;
    if(state.dirty)await saveSource();
    const result=await api('/api/compile',{id:state.app.id,kind:state.kind});
    if(!result.ok){
      $('compile-errors').textContent=result.message+(result.log?'\n'+result.log:'');
      $('compile-errors').classList.remove('hidden');
      showPdf(false);
      toast(result.message,true);
      return;
    }
    $('compile-errors').classList.add('hidden');
    state.app=(await api('/api/application?id='+encodeURIComponent(state.app.id))).item;
    renderDocEmpty();
    $('compile-badge').textContent='Compiled';
    $('approve-document').disabled=false;
    showPdf(true);
    toast('PDF compiled successfully. Review the preview before approving.');
  }catch(e){toast(e.message,true)}finally{$('compile-button').disabled=false}
}
async function generatePrompt(){
  try{
    if(state.dirty)await saveSource();
    const result=await api('/api/generate-prompt',{id:state.app.id,kind:state.kind});
    $('prompt-output').value=result.prompt;
    $('prompt-modal').classList.remove('hidden');
  }catch(e){toast(e.message,true)}
}
async function clipboard(text){
  try{await navigator.clipboard.writeText(text);toast('Copied to clipboard. Paste into ChatGPT.');}
  catch(e){toast('Clipboard access unavailable. Select all text in the dialog and copy manually.',true)}
}
async function createApp(event){
  event.preventDefault();
  try{
    const form=new FormData($('new-form'));
    const p=Object.fromEntries(form.entries());
    p.include_cv=$('new-form').querySelector('[name=include_cv]').checked;
    p.include_cover=$('new-form').querySelector('[name=include_cover]').checked;
    const item=await api('/api/create',p);
    state.app=item;
    state.kind=p.include_cv?'cv':'cover-letter';
    await refreshApps();
    showPage('documents');
    await loadApp(item.id);
    toast('Application created. Your master template was copied, not changed.');
  }catch(e){toast(e.message,true)}
}
function renderTracker(){
  const tbody=$('tracker-rows');tbody.replaceChildren();
  if(!state.apps.length){const tr=document.createElement('tr');const td=addCell(tr,'No applications yet.','muted');td.colSpan=6;tbody.appendChild(tr);return;}
  for(const a of state.apps){
    const tr=document.createElement('tr');
    addCell(tr,a.company,'cell-strong');addCell(tr,a.job_title);addCell(tr,a.category);addCell(tr,shortDate(a.created_at));addCell(tr,a.status);
    const td=document.createElement('td');
    const btn=document.createElement('button');btn.className='inline-action';
    if(a.status==='Prepared'){btn.textContent='Mark Applied';btn.addEventListener('click',async()=>{try{await api('/api/apply',{id:a.id});await refreshApps();if(state.app&&state.app.id===a.id)await loadApp(a.id);renderTracker();toast('Application marked Applied and logged locally.')}catch(e){toast(e.message,true)}});}
    else{btn.textContent='Open';btn.addEventListener('click',async()=>{showPage('documents');await loadApp(a.id)})}
    td.appendChild(btn);tr.appendChild(td);tbody.appendChild(tr);
  }
}
async function loadPromptSettings(){
  try{const kind=$('prompt-kind').value;const result=await api('/api/prompt-settings?kind='+kind);$('prompt-editor').value=result.prompt;}
  catch(e){toast(e.message,true)}
}
function toBase64(file){return new Promise((resolve,reject)=>{const reader=new FileReader();reader.onerror=reject;reader.onload=()=>resolve(String(reader.result).split(',')[1]);reader.readAsDataURL(file)});}
async function uploadFiles(kind,inputId){
  const files=Array.from($(inputId).files);
  if(!files.length){toast('Select a .tex, asset, or .zip file first.',true);return;}
  try{
    for(const file of files){
      toast('Importing '+file.name+' ...');
      await api('/api/upload-template',{kind,filename:file.name,data:await toBase64(file)});
    }
    await refreshHealth();
    toast('Template assets imported. New applications will use the updated master.');
  }catch(e){toast(e.message,true)}
}
async function act(fn){try{await fn()}catch(e){toast(e.message,true)}}
function init(){
  document.querySelectorAll('[data-section]').forEach(b=>b.addEventListener('click',()=>showPage(b.dataset.section)));
  $('new-form').addEventListener('submit',createApp);
  $('app-selector').addEventListener('change',e=>act(()=>loadApp(e.target.value)));
  document.querySelectorAll('.tab').forEach(tab=>tab.addEventListener('click',async()=>{
    if(state.dirty&&!confirm('The current LaTeX source has unsaved changes. Switch documents without saving?'))return;
    state.kind=tab.dataset.kind;await act(loadDocument);
  }));
  $('tex-editor').addEventListener('input',()=>{state.dirty=true;$('dirty-indicator').textContent='Unsaved changes';$('approve-document').disabled=true;showPdf(false)});
  $('save-source').addEventListener('click',()=>act(async()=>{await saveSource();toast('LaTeX source saved in this application.')}));
  $('review-diff').addEventListener('click',()=>act(async()=>{
    if(state.dirty)await saveSource();
    const r=await api('/api/diff?id='+encodeURIComponent(state.app.id)+'&kind='+state.kind);
    $('diff-output').value=r.diff; $('diff-modal').classList.remove('hidden');
  }));
  for(const id of ['close-diff','dismiss-diff'])$(id).addEventListener('click',()=>$('diff-modal').classList.add('hidden'));
  $('diff-modal').addEventListener('click',e=>{if(e.target===$('diff-modal'))$('diff-modal').classList.add('hidden')});
  $('compile-button').addEventListener('click',()=>act(compileSource));
  $('generate-prompt').addEventListener('click',()=>act(generatePrompt));
  $('close-modal').addEventListener('click',()=>$('prompt-modal').classList.add('hidden'));
  $('prompt-modal').addEventListener('click',e=>{if(e.target===$('prompt-modal'))$('prompt-modal').classList.add('hidden')});
  $('copy-prompt').addEventListener('click',()=>clipboard($('prompt-output').value));
  $('approve-document').addEventListener('click',()=>act(async()=>{
    state.app=await api('/api/approve',{id:state.app.id,kind:state.kind});
    renderDocEmpty();await loadDocument();toast('Document approved.');
  }));
  $('mark-prepared').addEventListener('click',()=>act(async()=>{
    state.app=await api('/api/prepare',{id:state.app.id});renderDocEmpty();await refreshApps();toast('Application marked Prepared. This does not mean you have applied.');
  }));
  $('download-pdf').addEventListener('click',()=>{if(state.hasPdf&&state.app.documents[state.kind].status==='approved')window.location.href='/api/download?id='+encodeURIComponent(state.app.id)+'&kind='+state.kind+'&format=pdf'});
  $('download-tex').addEventListener('click',()=>{if(state.app)window.location.href='/api/download?id='+encodeURIComponent(state.app.id)+'&kind='+state.kind+'&format=tex'});
  $('upload-cv').addEventListener('click',()=>act(()=>uploadFiles('cv','cv-files')));
  $('upload-cover').addEventListener('click',()=>act(()=>uploadFiles('cover-letter','cover-files')));
  $('prompt-kind').addEventListener('change',loadPromptSettings);
  $('save-prompt').addEventListener('click',()=>act(async()=>{await api('/api/save-prompt',{kind:$('prompt-kind').value,prompt:$('prompt-editor').value});toast('Prompt saved locally.')}));
  window.addEventListener('beforeunload',e=>{if(state.dirty){e.preventDefault();e.returnValue='';}});
}
init();
(async()=>{try{await refreshHealth();await refreshApps()}catch(e){toast('Could not connect to local server: '+e.message,true)}})();
