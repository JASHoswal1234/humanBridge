import React, {useEffect, useState} from 'react';
import {createRoot} from 'react-dom/client';
import { ArrowRight, Check, CheckCircle2, CircleDollarSign, ClipboardCheck, CreditCard, FileSearch,
  FileText, KeyRound, LoaderCircle, LockKeyhole, Plus, RefreshCw, ShieldCheck, Sparkles, UploadCloud,
  UserCheck, X, XCircle, ExternalLink, Info, ClipboardCopy, AlertTriangle } from 'lucide-react';
import './styles.css';

const fmt = c => '$' + (c / 100).toFixed(2);
const api = async (path, options={}) => {
  const response = await fetch('/api'+path, options);
  let data; try { data = await response.json(); } catch { data = null; }
  if (!response.ok) throw new Error(data?.detail || `HTTP ${response.status}`);
  return data;
};
const post = (path, body=null) => api(path, {method:'POST', ...(body ? {headers:{'Content-Type':'application/json'},body:JSON.stringify(body)} : {})});
function Pill({children, tone='plain'}) { return <span className={'pill '+tone}>{children}</span> }
function Panel({children, title, eyebrow, extra, className=''}) {return <section className={'panel '+className}>
  {(title||eyebrow) && <div className="panel-heading"><div>{eyebrow&&<div className="eyebrow">{eyebrow}</div>}{title&&<h2>{title}</h2>}</div>{extra}</div>}{children}
  </section>}
function Button({children, onClick, variant='primary', disabled, icon:Icon, type='button'}) {
  return <button type={type} className={'button '+variant} disabled={disabled} onClick={onClick}>{Icon&&<Icon size={16}/>} {children}</button>
}
function Header() { return <header className="topbar"><div className="brandmark"><span className="brandicon"><ShieldCheck size={24}/></span><span><strong>HumanBridge</strong><small>Decision-aware verification</small></span></div><div className="righthead"><Pill tone="blue">PayPal Sandbox only</Pill><a href="https://developer.paypal.com/" target="_blank" rel="noreferrer" className="doclink">Developer docs <ExternalLink size={13}/></a></div></header>}
function FlowHeader({batch}) {
 const stage = !batch ? 0 : batch.payment_status === 'NOT_STARTED' ? 1 : batch.payment_status === 'AWAITING_BUYER' ? 2 : batch.payment_status === 'AUTHORIZED' ? 3 : 4;
 return <div className="flow-row">{[['01','Analyze receipts'],['02','Authorize budget'],['03','Human verifies'],['04','Pay for accepted work']].map(([num,label],i)=><div className={'flow-step '+(i<stage?'active':'')} key={num}><span>{i<stage?<Check size={15}/>:num}</span><small>{label}</small></div>)}</div>
}
function Status({status}) { const colors = {NOT_STARTED:'neutral',AWAITING_BUYER:'amber',AUTHORIZED:'blue',CAPTURED:'green',VOIDED:'neutral',PENDING:'amber',SUBMITTED:'blue',ACCEPTED:'green',SKIPPED:'neutral'}; return <Pill tone={colors[status]||'neutral'}>{status.replaceAll('_',' ')}</Pill> }
function ExtractValue({name, value}) {return <div className="extract-line"><span>{name}</span><strong>{value??'Unclear'}</strong></div>}
function DocumentItem({doc}) {return <div className="document-card"><img src={doc.image_url} alt="Uploaded receipt preview"/><div className="doc-details"><div className="doc-title"><strong>{doc.first?.merchant || doc.filename}</strong><Pill tone={doc.flagged?'amber':'green'}>{doc.flagged?'Needs review':'Accepted'}</Pill></div><p className="subtle">{doc.mode === 'LIVE_GEMINI'?'Two live Gemini readings':'Scripted demonstration — not live AI'}</p><div className="doc-readings"><div><small>First reading</small><strong>{doc.first?.total || '—'}</strong></div><div><small>Second reading</small><strong>{doc.second?.total || '—'}</strong></div></div>{doc.reasons?.map((r,i)=><p className="reason" key={i}><AlertTriangle size={14}/> {r}</p>)}</div></div>}
function Reviewer({id}) {
 const qs = new URLSearchParams(window.location.search), token=qs.get('token')||'';
 const [task,setTask]=useState(null), [value,setValue]=useState(''),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 useEffect(()=>{api(`/tasks/${id}?token=${encodeURIComponent(token)}`).then(t=>{setTask(t);setValue(t.reviewer_value||'')}).catch(e=>setError(e.message))},[id,token]);
 async function submit(e){e.preventDefault();setBusy(true);setError('');try { await post(`/tasks/${id}/submit`,{token,value});const t=await api(`/tasks/${id}?token=${encodeURIComponent(token)}`);setTask(t);}catch(err){setError(err.message)}finally{setBusy(false)}}
 return <><Header/><main className="page reviewer-page"><div className="eyebrow">HUMAN VERIFICATION DESK</div><h1>A second opinion, exactly where it's needed.</h1><p className="lede">You are reviewing one uncertain field. Your response goes back to the requester for acceptance; it does not automatically trigger payment.</p>{error&&<div className="alert"><XCircle size={18}/>{error}</div>}{!task&&!error&&<div className="loading"><LoaderCircle className="spin"/> Loading review task…</div>}
 {task&&<div className="review-grid"><Panel title="Receipt evidence" eyebrow="CROPPED REGION — DEMONSTRATION"><div className="receipt-preview"><img src={task.crop_url} alt="Bottom region of receipt; may contain sensitive data"/></div><p className="subtle">This is a bottom-region heuristic crop, not guaranteed PII removal or guaranteed field localization.</p></Panel><Panel title="Verify the total" eyebrow="HUMAN REVIEWER"><div className="fieldbox"><small>AI's first reading</small><strong>{task.proposed_value || 'Unreadable'}</strong></div><form onSubmit={submit}><label className="input-label">Correct total (USD)</label><input className="input" value={value} onChange={e=>setValue(e.target.value)} placeholder="e.g. 32.40" disabled={task.status==='ACCEPTED'||task.status==='SKIPPED'}/><div className="review-fee"><CircleDollarSign size={16}/> Verification fee if requester accepts: {fmt(task.fee_cents)}</div><Button disabled={busy || task.status==='ACCEPTED'||task.status==='SKIPPED'} icon={CheckCircle2}>{busy?'Submitting…':task.status==='SUBMITTED'?'Update submitted answer':'Submit verification'}</Button></form><div className="feedback"><Status status={task.status}/>{task.status==='SUBMITTED'&&<p>Submitted. The requester now decides whether to accept your answer.</p>}</div></Panel></div>}
 <div className="footer-note">HumanBridge · Sandbox proof of concept · No real payments</div></main></>
}
function App() {
 const [batch,setBatch]=useState(null), [config,setConfig]=useState(null),[busy,setBusy]=useState(''),[error,setError]=useState(''),[file,setFile]=useState(null),[showEvents,setShowEvents]=useState(false);
 const batchId = batch?.id;
 useEffect(()=>{api('/config').then(setConfig).catch(()=>{}); const saved=localStorage.getItem('humanbridge_last_batch');if(saved)api(`/batches/${saved}`).then(setBatch).catch(()=>localStorage.removeItem('humanbridge_last_batch'))},[]);
 const update = async id => { const b=await api(`/batches/${id||batchId}`);setBatch(b);localStorage.setItem('humanbridge_last_batch',b.id);return b; };
 const run = async (action,fn) => {setError('');setBusy(action);try {const b=await fn();if(b?.id){setBatch(b);localStorage.setItem('humanbridge_last_batch',b.id);}} catch(e){setError(e.message)} finally{setBusy('')}};
 const newDemo=()=>run('demo',()=>post('/batches/demo'));
 const newEmpty=()=>run('new',()=>post('/batches'));
 const upload=async e=>{e.preventDefault();if(!file||!batch)return;await run('upload',async()=>{const fd=new FormData();fd.append('file',file);return api(`/batches/${batch.id}/documents`,{method:'POST',body:fd})});setFile(null)};
 const payCreate=()=>run('payCreate',async()=>{const o=await post(`/batches/${batchId}/payment/create`); const b=await update();if(o.approval_url)window.open(o.approval_url,'_blank','noopener,noreferrer');return b});
 const authorize=()=>run('authorize',()=>post(`/batches/${batchId}/payment/authorize`));
 const settle=()=>run('settle',()=>post(`/batches/${batchId}/payment/settle`));
 const decide=(task,accept)=>run('decide:'+task.id,()=>post(`/batches/${batchId}/tasks/${task.id}/${accept?'accept':'skip'}`));
 const tasks=batch?.tasks||[], docs=batch?.documents||[];
 const ready=tasks.length>0 && tasks.every(t=>['ACCEPTED','SKIPPED'].includes(t.status));
 const accepted=tasks.filter(t=>t.status==='ACCEPTED').reduce((s,t)=>s+t.fee_cents,0);
 const paid=batch?.captured_cents||0;
 const status=batch?.payment_status;
 return <><Header/><main className="page"><div className="hero"><div className="eyebrow"><Sparkles size={14}/> AI + HUMAN JUDGMENT + PAYPAL</div><h1>When AI is uncertain, <em>buy certainty.</em></h1><p>Only escalate receipts that need a second opinion. Requester-approved human verification, settled through PayPal's authorize-and-capture flow.</p><div className="hero-actions"><Button onClick={newDemo} disabled={!!busy} icon={Sparkles}>Load scripted demo</Button><Button variant="outline" onClick={newEmpty} disabled={!!busy} icon={Plus}>New live batch</Button>{batch&&<Button variant="ghost" onClick={()=>run('refresh',()=>update())} disabled={!!busy} icon={RefreshCw}>Refresh</Button>}</div></div>
 {error&&<div className="alert"><XCircle size={18}/><span>{error}</span><button onClick={()=>setError('')}><X size={16}/></button></div>}
 {batch ? <>
   <FlowHeader batch={batch}/>
   <div className="metrics"><div className="metric"><span>Documents</span><strong>{docs.length}</strong><small>Processed receipts</small></div><div className="metric"><span>Flagged for review</span><strong>{tasks.length}</strong><small>{docs.length?Math.round(tasks.length/docs.length*100):0}% of batch</small></div><div className="metric"><span>Budget</span><strong>{fmt(batch.budget_cents)}</strong><small>Authorized after buyer approval</small></div><div className="metric"><span>Approved service cost</span><strong>{fmt(accepted)}</strong><small>Captured only at settlement</small></div></div>
   <div className="main-grid"><div className="stack"><Panel title="Document intelligence" eyebrow="01 / ANALYZE" extra={<Pill tone={batch.data_mode==='scripted_demo'?'amber':'blue'}>{batch.data_mode==='scripted_demo'?'SIMULATED READINGS':'LIVE GEMINI BATCH'}</Pill>}>
     <p className="subtle">The AI reads twice; deterministic checks flag disagreements and arithmetic errors. No probabilistic calibration is claimed.</p>
     {status==='NOT_STARTED'&&<form onSubmit={upload} className="upload-row"><label className="upload-target"><UploadCloud size={19}/><span>{file?.name||'Choose a receipt image'}</span><input type="file" accept="image/png,image/jpeg,image/webp" onChange={e=>setFile(e.target.files?.[0])}/></label><Button disabled={!file||!!busy} icon={FileSearch}>{busy==='upload'?'Analyzing…':'Analyze'}</Button></form>}
     {!config?.gemini_enabled && status==='NOT_STARTED' &&<p className="hint"><Info size={14}/> Add GEMINI_API_KEY to backend/.env to analyze real uploads. Scripted Demo Batch remains available.</p>}
     {docs.length?docs.map(d=><DocumentItem key={d.id} doc={d}/>):<div className="empty"><FileText size={27}/><p>No receipts yet. Upload a real image or load scripted examples.</p></div>}
   </Panel></div>
   <div className="stack"><Panel title="Payment budget" eyebrow="02 / PAYPAL SANDBOX" extra={<Status status={status}/>}>
      <div className="budget-amount"><span>Approved budget ceiling</span><strong>{fmt(batch.budget_cents)}</strong></div><div className="budget-meter"><div style={{width:`${Math.min(100,paid/batch.budget_cents*100)}%`}}/></div><div className="budget-numbers"><span>Captured {fmt(paid)}</span><span>Not captured {fmt(batch.budget_cents-paid)}</span></div>
      <p className="subtle">The app enforces the budget ceiling. PayPal supplies authorization and final capture; uncaptured does not mean an immediately released hold.</p>
      {status==='NOT_STARTED'&&<Button disabled={tasks.length===0||!!busy} icon={CreditCard} onClick={payCreate}>Create $5 authorization order</Button>}
      {status==='AWAITING_BUYER'&&<><Button variant="outline" icon={ExternalLink} onClick={()=>window.open(batch.paypal_approval_url,'_blank','noopener,noreferrer')}>Open Sandbox checkout</Button><Button icon={Check} disabled={!!busy} onClick={authorize}>{busy==='authorize'?'Confirming…':"I've approved — verify & authorize"}</Button></>}
      {status==='AUTHORIZED'&&<><div className="success-hint"><ShieldCheck size={18}/> Sandbox authorization verified. Human reviews can now be accepted.</div><Button disabled={!ready || !!busy} icon={CircleDollarSign} onClick={settle}>{accepted?'Capture '+fmt(accepted)+' (final)':'Void unused authorization'}</Button>{!ready&&<p className="hint">Accept or skip every review task before settlement.</p>}</>}
      {status==='CAPTURED'&&<div className="success-hint"><CheckCircle2 size={17}/> PayPal confirmed the capture of {fmt(batch.captured_cents)}.</div>}
      {status==='VOIDED'&&<div className="success-hint"><CheckCircle2 size={17}/> PayPal confirmed this authorization was voided.</div>}
      {batch.paypal_order_id&&<div className="ledger"><ExtractValue name="Order" value={batch.paypal_order_id}/><ExtractValue name="Authorization" value={batch.paypal_authorization_id||'Waiting'}/><ExtractValue name="Capture" value={batch.paypal_capture_id||'Not captured'}/></div>}
   </Panel>
   <Panel title="Human verification queue" eyebrow="03 / REVIEW & ACCEPT" extra={<Pill>{tasks.length} tasks</Pill>}>
      {tasks.length===0?<div className="empty"><UserCheck size={25}/><p>No review needed yet.</p></div>:tasks.map((t,i)=>{const d=docs.find(x=>x.id===t.document_id);const link=`/review/${t.id}?token=${encodeURIComponent(t.review_token)}`;return <div className="task" key={t.id}><div className="task-top"><div><small>Verification #{i+1}</small><strong>{d?.first?.merchant||'Receipt'} · total</strong></div><Status status={t.status}/></div><p className="reason"><AlertTriangle size={14}/> {d?.reasons.join(' · ')}</p><div className="task-actions"><Button variant="outline" icon={ExternalLink} onClick={()=>window.open(link,'_blank','noopener,noreferrer')}>Open reviewer</Button>{t.status==='SUBMITTED'&&<Button icon={Check} disabled={status!=='AUTHORIZED'||!!busy} onClick={()=>decide(t,true)}>Accept {t.reviewer_value}</Button>}{['PENDING','SUBMITTED'].includes(t.status)&&<Button variant="ghost" disabled={!!busy} onClick={()=>decide(t,false)}>Skip</Button>}</div>{t.status==='SUBMITTED'&&status!=='AUTHORIZED'&&<p className="hint">Requester acceptance becomes available after payment authorization.</p>}</div>})}
   </Panel></div></div>
   <Panel title="Audit trail" eyebrow="04 / PROOF, NOT PROMISE" extra={<Button variant="ghost" icon={showEvents?X:ClipboardCheck} onClick={()=>setShowEvents(!showEvents)}>{showEvents?'Hide':'Show events'}</Button>}>
      <div className="audit-summary"><div><CheckCircle2 size={20}/><strong>Deterministic checks</strong><small>Amount consistency and disagreements</small></div><div><LockKeyhole size={20}/><strong>Server-side budget</strong><small>Capture only requester-accepted work</small></div><div><CreditCard size={20}/><strong>Verified PayPal outcome</strong><small>Capture read back by identifier</small></div></div>
      {showEvents&&<div className="events">{batch.events.map((e,i)=><div key={i}><small>{new Date(e.time).toLocaleString()}</small><strong>{e.kind}</strong></div>)}</div>}
   </Panel>
 </> : <Panel title="Create your first batch" eyebrow="GET STARTED"><div className="empty splash"><FileSearch size={33}/><p>Load a scripted demo to see how the decisions and payments connect, or start a live Gemini batch.</p></div></Panel>}
 <div className="footer-note"><ShieldCheck size={15}/> Sandbox-only prototype. Scripted demo readings are not real AI. No payment or review work happens without explicit user actions.</div></main></>;
}
const reviewerId = window.location.pathname.match(/^\/review\/([^/]+)/)?.[1];
createRoot(document.getElementById('root')).render(reviewerId ? <Reviewer id={reviewerId}/> : <App/>);
