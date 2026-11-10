import React, {useEffect, useState} from 'react';
import {createRoot} from 'react-dom/client';
import { ArrowRight, Check, CheckCircle2, CircleDollarSign, ClipboardCheck, CreditCard, FileSearch,
  FileText, KeyRound, LoaderCircle, LockKeyhole, Plus, RefreshCw, ShieldCheck, Sparkles, UploadCloud,
  UserCheck, X, XCircle, ExternalLink, Info, ClipboardCopy, AlertTriangle } from 'lucide-react';
import evaluation from './evaluation.json';
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
 const status = batch.payment_status;
 const done = [batch.documents.length > 0, !!batch.paypal_authorization_id,
   batch.tasks.length > 0 && batch.tasks.every(t => ['ACCEPTED','SKIPPED'].includes(t.status)),
   ['CAPTURED','VOIDED'].includes(status)];
 return <div className="flow-row">{['Analyze receipts','Authorize budget','Decide on reviews','Settle fees'].map((label,i)=>
   <div className={'flow-step '+(done[i]?'active':'')} key={label}><span>{done[i]?<Check size={15}/>:i+1}</span><small>{label}</small></div>)}</div>;

}
function Status({status}) { const colors = {NOT_STARTED:'neutral',AWAITING_BUYER:'amber',AUTHORIZED:'blue',CAPTURED:'green',VOIDED:'neutral',PENDING:'amber',SUBMITTED:'blue',ACCEPTED:'green',SKIPPED:'neutral'}; return <Pill tone={colors[status]||'neutral'}>{status.replaceAll('_',' ')}</Pill> }
function ExtractValue({name, value}) {return <div className="extract-line"><span>{name}</span><strong>{value??'Unclear'}</strong></div>}
function Adjustments({items}) {
 if (!items) return 'Unknown';
 if (!items.length) return 'None observed';
 return items.map((item,i)=><div key={i}>{item.label} · {item.amount ?? 'Unreadable'} ({item.effect ?? 'unclear effect'})</div>);
}

function ReviewComparison({task, currency, reason, onReason}) {
 if (!task.reviewer_value) return null;
 return <div className="review-comparison">
   <dl><div><dt>Original AI total</dt><dd>{currency} {task.proposed_value ?? 'Unreadable'}</dd></div>
   <div><dt>Reviewer total</dt><dd>{currency} {task.reviewer_value}</dd></div></dl>
   {task.correction_warnings?.map(w=><p className="reason" key={w}><AlertTriangle size={16}/>{w}</p>)}
   {task.status==='SUBMITTED' && task.correction_warnings?.length>0 && <label>Reason for accepting this difference
     <textarea required maxLength={500} value={reason} onChange={e=>onReason(e.target.value)}/></label>}
   {task.acceptance_reason && <p>Requester’s reason: {task.acceptance_reason}</p>}
   {task.status==='ACCEPTED' && <p className="subtle">Requester accepted the service fee. Receipt accuracy is unconfirmed.</p>}
 </div>;
}
function Evaluation() {
 return <details className="panel benchmark"><summary>Synthetic evaluation · {evaluation.receipts} receipts</summary>
   <p>Both Gemini readings matched the labeled total on {evaluation.paired_matches} of {evaluation.receipts} receipts. The full-review baseline used AI-assisted visual readings; {evaluation.policies.find(row=>row.policy==='Full').abstentions} were unreadable. With zero initial errors, this run cannot measure an accuracy improvement.</p>
   <div className="table-scroll"><table className="reading-table"><thead><tr>
     {['Policy','Reviews','Errors detected','Corrected','Review cost¹','Corrected / review'].map(h=><th key={h}>{h}</th>)}
   </tr></thead><tbody>{evaluation.policies.map(row=><tr key={row.policy}><th scope="row">{row.policy}</th>
     <td>{row.reviews}</td><td>{row.errors_detected}</td><td>{row.errors_corrected}</td>
     <td>${row.estimated_spend_usd}</td><td>{row.corrected_per_review ?? '—'}</td></tr>)}</tbody></table></div>
   <p className="subtle">¹ Estimate at $0.75 per requested review, including unreadable submissions. Random review uses the same count as selective review. A dash indicates zero reviews.</p>
 </details>;
}
function DocumentItem({doc}) {
 const fields = ['merchant', 'date', 'currency', 'subtotal', 'adjustments', 'tax', 'total'];
 const readings = [doc.first, doc.second];
 return <article className="document-card">
   <a href={doc.image_url} target="_blank" rel="noreferrer"><img className="receipt-thumb" src={doc.image_url} alt="Open full receipt"/></a>
   <div className="doc-details"><div className="doc-title"><strong>{doc.filename}</strong>
     <Pill tone={doc.flagged ? 'amber' : 'neutral'}>{doc.flagged ? 'Review recommended' : 'No review recommended'}</Pill></div>
     <p className="subtle">{doc.mode === 'LIVE_GEMINI' ? 'Live Gemini extraction' : 'Scripted example'}{doc.mode === 'LIVE_GEMINI' && doc.first && !('adjustments' in doc.first) && ' · Historical readings did not extract discounts or fees.'}</p>
     <table className="reading-table"><thead><tr><th>Field</th><th>First reading</th><th>Second reading</th></tr></thead>
       <tbody>{fields.map(field => <tr key={field}><th scope="row">{field}</th>
         {readings.map((reading,i) => <td key={i}>{field === 'adjustments' ? <Adjustments items={reading?.adjustments}/> : (reading?.[field] ?? 'Unavailable')}</td>)}</tr>)}
         <tr><th scope="row">Line items</th>{readings.map((r,i) => <td key={i}>{r?.line_items?.length ?
           r.line_items.map((item,j) => <div key={j}>{item.description ?? 'Unnamed item'} · Qty {item.quantity ?? '—'} · {item.amount ?? '—'}</div>) : 'None read'}</td>)}</tr>
       </tbody></table>
     {doc.reasons?.length ? doc.reasons.map(r => <p className="reason" key={r}><AlertTriangle size={14}/>{r}</p>) :
       <p className="subtle">No rule flagged these readings. Agreement alone cannot establish correctness.</p>}
     {doc.passes?.length > 0 && <details><summary>Extraction details</summary>{doc.passes.map(p =>
       <p className="subtle" key={p.number}>Pass {p.number} · {p.model} · {p.time} · Attempt {p.attempt_id}</p>)}</details>}
   </div>
 </article>;
}
function Reviewer({id}) {
 const qs = new URLSearchParams(window.location.hash.slice(1) || window.location.search), token=qs.get('token')||'';
 const [task,setTask]=useState(null), [value,setValue]=useState(''),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 useEffect(() => {
   if (busy) return;
   let active = true, timer;
   async function refresh() {
     try {
       const t = await api(`/tasks/${id}`, {headers:{'X-Review-Token':token}});
       if (active) {
         setTask(t);
         setValue(previous => previous || t.reviewer_value || '');
       }
     } catch (err) { if (active) setError(err.message); }
     if (active) timer = setTimeout(refresh,3000);
   }
   refresh();
   return () => {active=false; clearTimeout(timer);};
 },[id,token,busy]);
 const locked = task && !['PENDING','REVISION_REQUESTED'].includes(task.status);
 async function submit(event) {
   event.preventDefault();
   if (busy || locked || !value.trim()) return;
   setBusy(true);
   setError('');
   try {
     const result = await post(`/tasks/${id}/submit`, {token, value, revision:task.revision});
     setTask({...task, status: result.status, check_status:result.check_status, reviewer_value: value.trim()});
   } catch (err) {
     setError(`Verification could not be submitted. ${err.message}`);
   } finally {
     setBusy(false);
   }
 }
 return <><Header/><main className="page reviewer-page"><div className="eyebrow">HUMAN VERIFICATION DESK</div><h1>A second opinion, exactly where it's needed.</h1><p className="lede">You are reviewing one uncertain field. Your response goes back to the requester for acceptance; it does not automatically trigger payment.</p>
 {error && <div className="alert" role="alert"><XCircle size={18}/>{error}</div>}
 {!task && !error && <div className="loading" role="status"><LoaderCircle className="spin"/> Loading review task…</div>}
 {task && <div className="review-grid">
   <Panel title="Receipt evidence" eyebrow="CROPPED RECEIPT REGION"><div className="receipt-preview"><img src={task.crop_url} alt="Bottom region of receipt; may contain sensitive data"/></div><p className="subtle">Check the total against the visible receipt. If it is unreadable, leave the task pending for the requester.</p></Panel>
   <Panel title="Verify the total" eyebrow="HUMAN REVIEWER">
     <div className="fieldbox"><small>AI's first reading</small><strong>{task.proposed_value || 'Unreadable'}</strong></div>
     <form onSubmit={submit} aria-busy={busy}>
       <label className="input-label" htmlFor="review-total">Correct receipt total</label>
       <input id="review-total" className="input" value={value} onChange={e=>setValue(e.target.value)}
         placeholder="e.g. 32.40" inputMode="decimal" required disabled={busy || locked}/>
       <div className="review-fee"><CircleDollarSign size={16}/> Verification fee if requester accepts: {fmt(task.fee_cents)}</div>
       <Button type="submit" disabled={busy || locked || !value.trim()} icon={CheckCircle2}>
         {busy ? 'Submitting…' : task.status === 'SUBMITTED' ? 'Submitted' : 'Submit verification'}
       </Button>
     </form>
     <div className="feedback" role="status">
       <Status status={task.status}/>{task.check_status && <p>CHECKS PASSED · Valid numeric format. Requester approval is separate.</p>}{task.status === 'REVISION_REQUESTED' && <p>Please check the receipt total again and resubmit.</p>}
       {task.status === 'SUBMITTED' && <p>You submitted {task.reviewer_value} for the requester to review.</p>}
     </div>
   </Panel>
 </div>}
 <div className="footer-note">HumanBridge · Sandbox proof of concept · No real payments</div></main></>
}
function ReceiptUpload({batchId, busy, run}) {
 const [file, setFile] = useState(null);
 const [analyzed, setAnalyzed] = useState('');
 const [error, setError] = useState('');

 async function upload(event) {
   event.preventDefault();
   if (!file || busy) return;
   const form = event.currentTarget;
   setError('');
   setAnalyzed('');
   await run('upload', async () => {
     const body = new FormData();
     body.append('file', file);
     try {
       const updated = await api(`/batches/${batchId}/documents`, {method: 'POST', body});
       form.reset();
       setFile(null);
       setAnalyzed(file.name);
       return updated;
     } catch (err) {
       setError(`Receipt analysis failed. ${err.message}`);
     }
   });
 }
 return <>
   <form onSubmit={upload} className="upload-row" aria-busy={busy === 'upload'}>
     <label className="upload-target">
       <UploadCloud size={19}/><span>{file?.name || 'Choose a receipt image'}</span>
       <input type="file" aria-label="Choose a receipt image" accept="image/png,image/jpeg,image/webp"
         disabled={!!busy} onChange={e => {setFile(e.target.files[0]); setError(''); setAnalyzed('');}}/>
     </label>
     <Button type="submit" disabled={!file || !!busy} icon={FileSearch}>
       {busy === 'upload' ? 'Analyzing…' : 'Analyze'}
     </Button>
   </form>
   {error && <div className="alert" role="alert"><XCircle size={18}/>{error}</div>}
   {analyzed && <p className="success-hint" role="status"><CheckCircle2 size={16}/>Analyzed {analyzed}.</p>}
 </>;
}
function Checkout({batch, busy, run}) {
 const params = new URLSearchParams(location.search);
 const callback = params.get('checkout');
 const returnedToken = params.get('token');
 const order = batch.paypal_order_id;
 const mismatch = callback && ((returnedToken && returnedToken !== order) || (callback === 'return' && !returnedToken));
 const [check,setCheck] = useState(0);
 const [status,setStatus] = useState('CHECKING');
 const [failure,setFailure] = useState('');
 useEffect(() => {
   if (mismatch) return;
   let active = true;
   setStatus('CHECKING');
   setFailure('');
   api(`/batches/${batch.id}/payment/approval?token=${encodeURIComponent(order)}`)
     .then(result => {if (active) setStatus(result.status);})
     .catch(err => {if (active) {setStatus('FAILED'); setFailure(err.message);}});
   return () => {active=false;};
 },[batch.id,order,check,mismatch]);
 if (mismatch) return <p className="alert" role="alert">The return link has a missing or incorrect order token. <a href="/">Return to your requester workspace</a></p>;
 const approved = ['APPROVED','AUTHORIZATION_FOUND'].includes(status);
 const waiting = ['CREATED','SAVED','PAYER_ACTION_REQUIRED'].includes(status);
 const unavailable = ['VOIDED','EXPIRED','UNAVAILABLE'].includes(status);
 const authorizing = busy === 'authorize';
 const messages = {
   CHECKING:'Checking approval with PayPal…',
   APPROVED:'Buyer approved. Authorize the $5.00 review budget.',
   AUTHORIZATION_FOUND:'PayPal has an authorization. Verify it to update this batch.',
   UNAVAILABLE:`PayPal cannot find order ${order}. Checkout is unavailable for this order.`,
   VOIDED:'PayPal reports that this order was voided.',
   EXPIRED:'PayPal reports that this order expired.',
   FAILED:'Payment verification failed. ' + failure,
 };
 let message = messages[status] || 'PayPal returned an unexpected order state. Check the order again.';
 if (waiting) message = callback === 'cancel' ? 'Buyer cancelled checkout. You can reopen this order.' :
   'Awaiting buyer approval. Sign in with the Sandbox buyer account and finish checkout on PayPal.';
 if (authorizing) message = 'Authorization in progress. Waiting for PayPal confirmation…';
 const authorize = () => run('authorize', async () => {
   try {return await post(`/batches/${batch.id}/payment/authorize?token=${encodeURIComponent(order)}`);}
   catch (err) {setStatus('FAILED'); setFailure(err.message);}
 });
 return <>
   <p role="status" className={status==='FAILED' || unavailable ? 'alert' : 'hint'}>{message}</p>
   {waiting && <a className="button outline" href={batch.paypal_approval_url}
     onClick={()=>sessionStorage.setItem('hb_checkout_'+order,batch.id)}>Open Sandbox checkout</a>}
   {approved && <Button icon={Check} disabled={!!busy} onClick={authorize}>
     {authorizing?'Authorizing…':'Authorize approved budget'}</Button>}
   <Button variant="ghost" disabled={!!busy || status==='CHECKING'} onClick={()=>setCheck(c=>c+1)}>Check approval status</Button>
 </>;
}
function App() {
 const [batch,setBatch]=useState(null), [config,setConfig]=useState(null),[busy,setBusy]=useState(''),[error,setError]=useState(''),[showEvents,setShowEvents]=useState(false);
 const [reasons,setReasons] = useState({});
 const batchId = batch?.id;
 useEffect(()=>{api('/config').then(setConfig).catch(()=>{}); const query=new URLSearchParams(location.search);
 const callback=query.has('checkout');
 const saved=(callback && (query.get('batch') || sessionStorage.getItem('hb_checkout_'+query.get('token')))) || localStorage.getItem('humanbridge_last_batch');
 if(callback && !saved) setError('Open the original requester workspace in the browser that began checkout.');if(saved)api(`/batches/${saved}`).then(setBatch).catch(e=>setError(e.message))},[]);
 useEffect(() => {
   if (!batchId || busy) return;
   let active=true, timer;
   async function refresh() {
     try {
       const latest=await api(`/batches/${batchId}`);
       if(active) setBatch(latest);
     } catch(err) { if(active) setError(err.message); }
     if(active) timer=setTimeout(refresh,3000);
   }
   timer=setTimeout(refresh,3000);
   return () => {active=false; clearTimeout(timer);};
 },[batchId,busy]);
 const update = async id => { const b=await api(`/batches/${id||batchId}`);setBatch(b);localStorage.setItem('humanbridge_last_batch',b.id);return b; };
 const run = async (action,fn) => {setError('');setBusy(action);try {const b=await fn();if(b?.id){setBatch(b);localStorage.setItem('humanbridge_last_batch',b.id);}} catch(e){setError(e.message)} finally{setBusy('')}};
 const newDemo=()=>run('demo',()=>post('/batches/demo'));
 const newEmpty=()=>run('new',()=>post('/batches'));
 const payCreate=()=>run('payCreate',async()=>{await post(`/batches/${batchId}/payment/create`);return update()});
 const settle=()=>window.confirm('Settle the accepted service fees with PayPal Sandbox?') && run('settle',()=>post(`/batches/${batchId}/payment/settle`));
 const decide=(task,action)=>run('decide:'+task.id,()=>post(`/batches/${batchId}/tasks/${task.id}/${action}?revision=${task.revision || 0}`,action==='accept'?{reason:reasons[task.id+':'+task.revision] || ''}:null));
 const tasks=batch?.tasks||[], docs=batch?.documents||[];
 const ready=tasks.length>0 && tasks.every(t=>['ACCEPTED','SKIPPED'].includes(t.status));
 const accepted=batch?.accepted_cents ?? tasks.reduce((sum,t)=>sum+(t.status==='ACCEPTED'?t.fee_cents:0),0);
 const paid=batch?.captured_cents||0;
 const status=batch?.payment_status;
 return <><Header/><main className="page"><div className="hero"><div className="eyebrow"><Sparkles size={14}/> RECEIPT REVIEW WORKSPACE</div><h1>Review the receipts <em>that need a second look.</em></h1><p>Compare two Gemini readings, inspect the flagged amounts, and pay only for reviews you accept through PayPal Sandbox.</p><div className="hero-actions"><Button onClick={newEmpty} disabled={!!busy} icon={Plus}>{busy==='new'?'Creating batch…':'New live batch'}</Button><Button variant="outline" onClick={newDemo} disabled={!!busy} icon={Sparkles}>{busy==='demo'?'Loading examples…':'Load scripted demo'}</Button>{batch&&<Button variant="ghost" onClick={()=>run('refresh',()=>update())} disabled={!!busy} icon={RefreshCw}>Refresh</Button>}</div></div>
 {error&&<div className="alert" role="alert"><XCircle size={18}/><span>{error}</span><button aria-label="Dismiss error" onClick={()=>setError('')}><X size={16}/></button></div>}
 {batch ? <>
   <FlowHeader batch={batch}/>
   <div className="metrics"><div className="metric"><span>Documents</span><strong>{docs.length}</strong><small>Processed receipts</small></div><div className="metric"><span>Flagged for review</span><strong>{tasks.length}</strong><small>{docs.length?Math.round(tasks.length/docs.length*100):0}% of batch</small></div><div className="metric"><span>Budget</span><strong>{fmt(batch.budget_cents)}</strong><small>Authorized after buyer approval</small></div><div className="metric"><span>Approved service cost</span><strong>{fmt(accepted)}</strong><small>Captured only at settlement</small></div></div>
   <div className="main-grid"><div className="stack"><Panel title="Document intelligence" eyebrow="01 / ANALYZE" extra={<Pill tone={batch.data_mode==='scripted_demo'?'amber':'blue'}>{batch.data_mode==='scripted_demo'?'SCRIPTED EXAMPLE':'LIVE GEMINI BATCH'}</Pill>}>
     <p className="subtle">Compare the printed amounts with both readings. A flagged receipt shows which checks need a second look.</p>
     {status==='NOT_STARTED' && batch.data_mode !== 'scripted_demo' && <ReceiptUpload key={batchId} batchId={batchId} busy={busy} run={run}/>}
     {!config?.gemini_enabled && status==='NOT_STARTED' &&<p className="hint"><Info size={14}/> Add GEMINI_API_KEY to backend/.env to analyze real uploads. Scripted Demo Batch remains available.</p>}
     {docs.length?docs.map(d=><DocumentItem key={d.id} doc={d}/>):<div className="empty"><FileText size={27}/><p>No receipts yet. Upload a non-sensitive receipt or download the <a href="/api/sample-receipt" download="sample-stationery.png">synthetic sample receipt</a> to try Gemini.</p></div>}
   </Panel></div>
   <div className="stack"><Panel title="Payment budget" eyebrow="02 / PAYPAL SANDBOX" extra={status!=='AWAITING_BUYER' && <Status status={status}/>}>
      <div className="budget-amount"><span>Approved budget ceiling</span><strong>{fmt(batch.budget_cents)}</strong></div><div className="budget-meter"><div style={{width:`${Math.min(100,paid/batch.budget_cents*100)}%`}}/></div><div className="budget-numbers">{status==='SETTLING' ? <span>PayPal read-back pending</span> : <><span>Captured {fmt(paid)}</span><span>Not captured {fmt(batch.budget_cents-paid)}</span></>}</div>
      <p className="subtle">The app enforces the budget ceiling. PayPal supplies authorization and final capture; uncaptured does not mean an immediately released hold.</p>
      {status==='NOT_STARTED'&&<Button disabled={tasks.length===0||!!busy} icon={CreditCard} onClick={payCreate}>{busy==='payCreate'?'Creating order…':'Create $5 authorization order'}</Button>}
      {status==='AWAITING_BUYER' && <Checkout key={batch.paypal_order_id} batch={batch} busy={busy} run={run}/>}
      {status==='AUTHORIZED'&&<><div className="success-hint"><ShieldCheck size={18}/> Sandbox authorization verified. Human reviews can now be accepted.</div><Button disabled={!ready || !!busy} icon={CircleDollarSign} onClick={settle}>{busy==='settle'?'Verifying settlement…':accepted?'Capture '+fmt(accepted)+' (final)':'Void unused authorization'}</Button>{!ready&&<p className="hint">Accept or skip every review task before settlement.</p>}</>}
      {status==='SETTLING' && <><p role="status">Settlement awaits PayPal confirmation.</p><Button disabled={!!busy} onClick={settle}>{busy==='settle'?'Checking PayPal…':'Reconcile settlement'}</Button></>}
      {batch.verified_cents != null && <p className="subtle">Authorization verified for {fmt(batch.verified_cents)} {batch.auth_currency}.</p>}
      {status==='CAPTURED'&&<div className="success-hint" role="status"><CheckCircle2 size={17}/> PayPal confirmed the capture of {fmt(batch.captured_cents)}.</div>}
      {status==='VOIDED'&&<div className="success-hint"><CheckCircle2 size={17}/> PayPal confirmed this authorization was voided.</div>}
      {batch.paypal_order_id&&<div className="ledger"><ExtractValue name="Order" value={batch.paypal_order_id}/><ExtractValue name="Authorization" value={batch.paypal_authorization_id||'Waiting'}/><ExtractValue name="Capture" value={batch.paypal_capture_id||'Not captured'}/></div>}
   </Panel>
   <Panel title="Human verification queue" eyebrow="03 / REVIEW & ACCEPT" extra={<Pill>{tasks.length} tasks</Pill>}>
      {tasks.length===0?<div className="empty"><UserCheck size={25}/><p>No review needed yet.</p></div>:tasks.map((t,i)=>{const d=docs.find(x=>x.id===t.document_id);const link=`/review/${t.id}#token=${encodeURIComponent(t.review_token)}`;return <div className="task" key={t.id}><div className="task-top"><div><small>Verification #{i+1}</small><strong>{d?.first?.merchant||'Receipt'} · total</strong></div><Status status={t.status}/></div><p className="reason"><AlertTriangle size={14}/> {d?.reasons.join(' · ')}</p><ReviewComparison task={t} currency={d?.first?.currency} reason={reasons[t.id+':'+t.revision] || ''} onReason={v=>setReasons(prev=>({...prev,[t.id+':'+t.revision]:v}))}/><a className="doclink" href={d?.image_url} target="_blank" rel="noreferrer">Inspect receipt evidence</a><div className="task-actions"><Button variant="outline" icon={ExternalLink} onClick={()=>window.open(link,'_blank','noopener,noreferrer')}>Open reviewer</Button>{t.status==='SUBMITTED'&&<Button icon={Check} disabled={status!=='AUTHORIZED'||!!busy||(t.correction_warnings?.length>0 && !reasons[t.id+':'+t.revision]?.trim())} onClick={()=>decide(t,'accept')}>Accept {t.reviewer_value}</Button>}{t.status==='SUBMITTED' && <Button variant="outline" disabled={!!busy} onClick={()=>decide(t,'revise')}>Request revision</Button>}{['PENDING','SUBMITTED','REVISION_REQUESTED'].includes(t.status)&&<Button variant="ghost" disabled={!!busy} onClick={()=>decide(t,'skip')}>Skip</Button>}</div>{t.status==='SUBMITTED'&&status!=='AUTHORIZED'&&<p className="hint">Requester acceptance becomes available after payment authorization.</p>}</div>})}
   </Panel></div></div>
   <Panel title="Audit trail" eyebrow="BATCH ACTIVITY" extra={<Button variant="ghost" icon={showEvents?X:ClipboardCheck} onClick={()=>setShowEvents(!showEvents)}>{showEvents?'Hide':'Show events'}</Button>}>
      <div className="audit-summary"><div><CheckCircle2 size={20}/><strong>Deterministic checks</strong><small>Amount consistency and disagreements</small></div><div><LockKeyhole size={20}/><strong>Server-side budget</strong><small>Capture only requester-accepted work</small></div><div><CreditCard size={20}/><strong>PayPal settlement</strong><small>{status==='CAPTURED'?'Capture confirmed by identifier':status==='VOIDED'?'Void confirmed by identifier':'Awaiting verified settlement'}</small></div></div>
      {showEvents&&<div className="events">{batch.events.map((e,i)=><div key={i}><small>{new Date(e.time).toLocaleString()}</small><strong>{e.kind.toLowerCase().replaceAll('_',' ')}</strong><small>{e.details.capture_id || e.details.authorization_id || e.details.order_id || e.details.reason || ''}</small></div>)}</div>}
   </Panel>
 </> : <Panel title="How a receipt moves through review"><div className="intro-grid">
   <div><FileSearch/><h3>Read the receipt</h3><p>Upload a non-sensitive PNG, JPEG or WebP. Compare two Gemini readings alongside the original.</p></div>
   <div><UserCheck/><h3>Decide on a correction</h3><p>Reviewers inspect flagged totals. Compare their answer with the printed amounts before accepting a fee.</p></div>
   <div><CreditCard/><h3>Settle accepted work</h3><p>Authorize a $5.00 Sandbox budget. Each accepted review costs $0.75, paid to the verification service.</p></div>
 </div></Panel>}
 <Evaluation/>
 <div className="footer-note"><ShieldCheck size={15}/> Sandbox-only prototype. Scripted demo readings are not real AI. No payment or review work happens without explicit user actions.</div></main></>;
}
const reviewerId = window.location.pathname.match(/^\/review\/([^/]+)/)?.[1];
createRoot(document.getElementById('root')).render(reviewerId ? <Reviewer id={reviewerId}/> : <App/>);
