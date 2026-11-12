import React, {useEffect, useState} from 'react';
import {createRoot} from 'react-dom/client';
import { ArrowRight, Check, CheckCircle2, CircleDollarSign, ClipboardCheck, CreditCard, FileSearch,
  FileText, LoaderCircle, LockKeyhole, Plus, RefreshCw, ShieldCheck, UploadCloud,
  UserCheck, X, XCircle, ExternalLink, Info, AlertTriangle } from 'lucide-react';
import foldedReceipt from '../../evaluation/challenge/fold.png';
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
function Header() {
 return <header className="topbar"><div className="brandmark"><span className="brandicon" aria-hidden="true"><i/><i/><i/></span><strong>HumanBridge</strong></div>
   <span className="desk-name">The Evidence Desk</span><span className="sandbox">PayPal Sandbox</span></header>;
}

const steps = ['Inspect','Review','Accept','Settle'];
function FlowHeader({batch}) {
 const tasks = batch.tasks;
 const settled = ['CAPTURED','VOIDED'].includes(batch.payment_status);
 let stage = 0;
 if (settled || (tasks.length > 0 && tasks.every(t=>['ACCEPTED','SKIPPED'].includes(t.status)))) stage = 3;
 else if (tasks.some(t=>t.status==='SUBMITTED')) stage = 2;
 else if (tasks.length) stage = 1;
 return <nav className="flow-row" aria-label="Batch workflow">{steps.map((label,i)=>
   <a href={'#'+['inspect','decisions','decisions','payment'][i]} key={label}
     aria-current={i===stage?'step':undefined} className={i===stage?'current':''}>
     <span>{i===stage ? '●' : '○'}</span>{label}{i<3 && <ArrowRight size={14}/>}</a>)}</nav>;
}

function Specimen() {
 return <figure className="specimen"><div className="specimen-caption">Synthetic source <span>PNG</span></div>
   <div className="specimen-mat"><a href={foldedReceipt} target="_blank" rel="noreferrer" aria-label="Inspect the synthetic folded receipt">
     <img src={foldedReceipt} alt="Synthetic receipt with a fold across the printed amounts"/></a></div>
   <figcaption>Folded receipt <a href={foldedReceipt} download="synthetic-fold.png">Download sample ↓</a></figcaption></figure>;
}
function Status({status}) { const colors = {NOT_STARTED:'neutral',AWAITING_BUYER:'amber',AUTHORIZED:'blue',CAPTURED:'green',VOIDED:'neutral',PENDING:'amber',SUBMITTED:'blue',ACCEPTED:'green',SKIPPED:'neutral'}; return <Pill tone={colors[status]||'neutral'}>{status.replaceAll('_',' ')}</Pill> }
function ExtractValue({name, value}) {return <div className="extract-line"><span>{name}</span><strong>{value??'Unclear'}</strong></div>}
function Adjustments({items}) {
 if (!items) return 'Unknown';
 if (!items.length) return 'None observed';
 return items.map((item,i)=><div key={i}>{item.label} · {item.amount ?? 'Unreadable'} ({item.effect ?? 'unclear effect'})</div>);
}

function ReviewComparison({task, currency, reason, onReason}) {

 return <div className="review-comparison">
   <dl><div><dt>Original AI total</dt><dd>{currency} {task.proposed_value ?? 'Unreadable'}</dd></div>
   <div><dt>Reviewer total</dt><dd>{task.reviewer_value ? [currency,task.reviewer_value].filter(Boolean).join(' ') : 'Awaiting review'}</dd></div></dl>
   {task.check_status==='CHECKS_PASSED' && <p className="subtle">Numeric format checked</p>}
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
   <a className="source-sheet" href={doc.image_url} target="_blank" rel="noreferrer"><span>Source image <ExternalLink size={13}/></span><img src={doc.image_url} alt={'Original receipt · '+doc.filename}/><small>Open full receipt ↗</small></a>
   <div className="doc-details"><div className="doc-title"><strong>{doc.filename}</strong>
     <Pill tone={doc.flagged ? 'amber' : 'neutral'}>{doc.flagged ? 'Review recommended' : 'No review recommended'}</Pill></div>
     <p className="subtle">{doc.mode === 'LIVE_GEMINI' ? 'Live Gemini extraction' : 'Scripted example'}{doc.mode === 'LIVE_GEMINI' && doc.first && !('adjustments' in doc.first) && ' · Historical readings did not extract discounts or fees.'}</p>
     <table className="reading-table"><thead><tr><th>Field</th><th>First reading</th><th>Second reading</th></tr></thead>
       <tbody>{fields.map(field => <tr key={field} className={doc.reasons?.some(r=>r.toLowerCase().split(/[^a-z]+/).includes(field)) ? 'flagged-field' : ''}><th scope="row">{field}</th>
         {readings.map((reading,i) => <td key={i}>{field === 'adjustments' ? <Adjustments items={reading?.adjustments}/> : (reading?.[field] ?? 'Unavailable')}</td>)}</tr>)}
         <tr className={doc.reasons?.some(r=>r.includes('priced items'))?'flagged-field':''}><th scope="row">Line items</th>{readings.map((r,i) => <td key={i}>{r?.line_items?.length ?
           r.line_items.map((item,j) => <div key={j}>{item.description ?? 'Unnamed item'} · Qty {item.quantity ?? '—'} · {item.amount ?? '—'}</div>) : 'None read'}</td>)}</tr>
       </tbody></table>
     {doc.reasons?.length ? doc.reasons.map(r => <p className="reason" key={r}><AlertTriangle size={14}/>{r}</p>) :
       <p className="subtle">No rule flagged these readings. Agreement alone cannot establish correctness.</p>}
     {doc.passes?.length > 0 && <details><summary>Extraction details</summary>{doc.passes.map(p =>
       <p className="subtle" key={p.number}>Pass {p.number} · {p.model} · {p.time} · Attempt {p.attempt_id}</p>)}</details>}
   </div>
 </article>;
}
function Evidence({documents}) {
 const [selection,setSelection] = useState('');
 const current = documents.find(d=>d.id===selection) || documents.find(d=>d.flagged) || documents[0];
 return <>{documents.length>1 && <label className="document-picker">Receipt
   <select value={current.id} onChange={e=>setSelection(e.target.value)}>{documents.map((d,i)=><option key={d.id} value={d.id}>{i+1} / {documents.length} · {d.filename}</option>)}</select>
 </label>}<DocumentItem doc={current}/></>;
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
 return <><Header/><main className="page reviewer-page"><div className="eyebrow">Reviewer desk</div><h1>Read the printed total.</h1><p className="lede">Inspect the assigned crop and submit one value for the requester to consider.</p>
 {error && <div className="alert" role="alert"><XCircle size={18}/>{error}</div>}
 {!task && !error && <div className="loading" role="status"><LoaderCircle className="spin"/> Loading review task…</div>}
 {task && <div className="review-grid">
   <Panel title="Receipt evidence" eyebrow="Assigned crop"><div className="receipt-preview"><img src={task.crop_url} alt="Assigned lower region of the receipt"/></div><p className="subtle">Check the total against the visible receipt. If it is unreadable, leave the task pending for the requester.</p></Panel>
   <Panel title="Verify the total" eyebrow="Your decision">
     <div className="fieldbox"><small>First AI reading</small><strong>{task.proposed_value || 'Unreadable'}</strong></div>
     <form onSubmit={submit} aria-busy={busy}>
       <label className="input-label" htmlFor="review-total">Correct receipt total</label>
       <input id="review-total" className="input" value={value} onChange={e=>setValue(e.target.value)}
         placeholder="Enter the printed total" inputMode="decimal" required disabled={busy || locked}/>
       <div className="review-fee"><CircleDollarSign size={16}/> Verification fee if requester accepts: {fmt(task.fee_cents)}</div>
       <Button type="submit" disabled={busy || locked || !value.trim()} icon={CheckCircle2}>
         {busy ? 'Submitting…' : task.status === 'SUBMITTED' ? 'Submitted' : 'Submit verification'}
       </Button>
     </form>
     <div className="feedback" role="status">
       <Status status={task.status}/>{task.check_status==='CHECKS_PASSED' && <p>CHECKS PASSED · Valid numeric format. Requester approval is separate.</p>}{task.status === 'REVISION_REQUESTED' && <p>Please check the receipt total again and resubmit.</p>}
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
   APPROVED:`Buyer approved. Authorize the ${fmt(batch.budget_cents)} review budget.`,
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
 return <><Header/><main className={'page '+(batch?'workspace':'landing')}>
   <div className={batch?'batch-head':'cover'}><div className="cover-copy">
   <div className="eyebrow">{batch?'Requester desk':'Receipt verification'}</div>
   <h1>{batch?'Evidence workspace':<>Know when <br/>to <em>ask.</em></>}</h1>
   {!batch && <p>Two Gemini readings. A human opinion when the evidence calls for one. PayPal settles the reviews you accept.</p>}
   <div className="hero-actions"><Button onClick={newEmpty} disabled={!!busy} icon={Plus}>{busy==='new'?'Creating batch…':'New live batch'}</Button>
   <Button variant="outline" onClick={newDemo} disabled={!!busy} icon={FileText}>{busy==='demo'?'Loading examples…':'Load scripted demo'}</Button>
   {batch && <Button variant="ghost" onClick={()=>run('refresh',()=>update())} disabled={!!busy} icon={RefreshCw}>{busy==='refresh'?'Refreshing…':'Refresh'}</Button>}</div></div>
   {!batch && <Specimen/>}</div>
 {error&&<div className="alert" role="alert"><XCircle size={18}/><span>{error}</span><button aria-label="Dismiss error" onClick={()=>setError('')}><X size={16}/></button></div>}
 {batch ? <>
   <FlowHeader batch={batch}/>
   <div className="main-grid"><div className="stack" id="inspect"><Panel title="Receipt evidence" eyebrow="Inspect" extra={<Pill tone={batch.data_mode==='scripted_demo'?'amber':'blue'}>{batch.data_mode==='scripted_demo'?'SCRIPTED EXAMPLE':'LIVE GEMINI BATCH'}</Pill>}>
     <p className="subtle">Compare the printed amounts with both readings. A flagged receipt shows which checks need a second look.</p>
     {status==='NOT_STARTED' && batch.data_mode !== 'scripted_demo' && <ReceiptUpload key={batchId} batchId={batchId} busy={busy} run={run}/>}
     {config?.gemini_enabled===false && status==='NOT_STARTED' &&<p className="hint"><Info size={14}/> Add GEMINI_API_KEY to backend/.env to analyze real uploads. Scripted Demo Batch remains available.</p>}
     {docs.length?<Evidence key={batchId} documents={docs}/>:<div className="empty"><FileText size={27}/><p>No receipts yet. Upload a non-sensitive receipt or download the <a href="/api/sample-receipt" download="sample-stationery.png">synthetic sample receipt</a> to try Gemini.</p></div>}
   </Panel></div>
   <div className="stack side-desk"><div id="payment"><Panel title="Settlement ledger" eyebrow="PayPal Sandbox" extra={<Status status={status}/>}>
      <div className="budget-amount"><span>Approved budget ceiling</span><strong>{fmt(batch.budget_cents)}</strong></div><div className="extract-line"><span>Accepted service fees</span><strong>{fmt(accepted)}</strong></div><div className="budget-numbers">{status==='SETTLING' ? <span>PayPal read-back pending</span> : <><span>Captured {fmt(paid)}</span><span>Not captured {fmt(batch.budget_cents-paid)}</span></>}</div>
      <p className="subtle">PayPal determines when an unused hold clears.</p>
      {status==='NOT_STARTED'&&<Button disabled={tasks.length===0||!!busy} icon={CreditCard} onClick={payCreate}>{busy==='payCreate'?'Creating order…':'Create $'+(batch.budget_cents/100)+' authorization order'}</Button>}
      {status==='AWAITING_BUYER' && <Checkout key={batch.paypal_order_id} batch={batch} busy={busy} run={run}/>}
      {status==='AUTHORIZED'&&<><div className="success-hint"><ShieldCheck size={18}/> Sandbox authorization verified. Human reviews can now be accepted.</div><Button disabled={!ready || !!busy} icon={CircleDollarSign} onClick={settle}>{busy==='settle'?'Verifying settlement…':accepted?'Capture '+fmt(accepted)+' (final)':'Void unused authorization'}</Button>{!ready&&<p className="hint">Accept or skip every review task before settlement.</p>}</>}
      {status==='SETTLING' && <><p role="status">Settlement awaits PayPal confirmation.</p><Button disabled={!!busy} onClick={settle}>{busy==='settle'?'Checking PayPal…':'Reconcile settlement'}</Button></>}
      {batch.verified_cents != null && <p className="subtle">Authorization verified for {fmt(batch.verified_cents)} {batch.auth_currency}.</p>}
      {status==='CAPTURED'&&<div className="success-hint" role="status"><CheckCircle2 size={17}/> PayPal confirmed the capture of {fmt(batch.captured_cents)}.</div>}
      {status==='VOIDED'&&<div className="success-hint"><CheckCircle2 size={17}/> PayPal confirmed this authorization was voided.</div>}
      {batch.paypal_order_id&&<div className="ledger"><ExtractValue name="Order" value={batch.paypal_order_id}/><ExtractValue name="Authorization" value={batch.paypal_authorization_id||'Waiting'}/><ExtractValue name="Capture" value={batch.paypal_capture_id||'Not captured'}/></div>}
   </Panel></div>
   <div id="decisions"><Panel title="Review decisions" eyebrow="Review & accept" extra={<Pill>{tasks.length} tasks</Pill>}>
      {tasks.length===0?<div className="empty"><UserCheck size={25}/><p>No review needed yet.</p></div>:tasks.map((t,i)=>{const d=docs.find(x=>x.id===t.document_id);const link=`/review/${t.id}#token=${encodeURIComponent(t.review_token)}`;return <div className="task" key={t.id}><div className="task-top"><div><small>Review {i+1} · {fmt(t.fee_cents)}</small><strong>{d?.first?.merchant||'Receipt'} · total</strong></div><Status status={t.status}/></div><p className="reason"><AlertTriangle size={14}/> {d?.reasons.join(' · ')}</p><ReviewComparison task={t} currency={d?.first?.currency} reason={reasons[t.id+':'+t.revision] || ''} onReason={v=>setReasons(prev=>({...prev,[t.id+':'+t.revision]:v}))}/><a className="doclink" href={d?.image_url} target="_blank" rel="noreferrer">Inspect receipt evidence</a><div className="task-actions"><Button variant="outline" icon={ExternalLink} onClick={()=>window.open(link,'_blank','noopener,noreferrer')}>Open reviewer</Button>{t.status==='SUBMITTED'&&<Button icon={Check} disabled={status!=='AUTHORIZED'||!!busy||(t.correction_warnings?.length>0 && !reasons[t.id+':'+t.revision]?.trim())} onClick={()=>decide(t,'accept')}>{busy==='decide:'+t.id?'Saving decision…':'Accept '+t.reviewer_value}</Button>}{t.status==='SUBMITTED' && <Button variant="outline" disabled={!!busy} onClick={()=>decide(t,'revise')}>Request revision</Button>}{['PENDING','SUBMITTED','REVISION_REQUESTED'].includes(t.status)&&<Button variant="ghost" disabled={!!busy} onClick={()=>decide(t,'skip')}>Skip</Button>}</div>{t.status==='SUBMITTED'&&status!=='AUTHORIZED'&&<p className="hint">Requester acceptance becomes available after payment authorization.</p>}</div>})}
   </Panel></div></div></div>
   <Panel title="Audit trail" eyebrow="Batch activity" extra={<Button variant="ghost" icon={showEvents?X:ClipboardCheck} onClick={()=>setShowEvents(!showEvents)}>{showEvents?'Hide':'Show events'}</Button>}>
      {showEvents&&<div className="events">{batch.events.map((e,i)=><div key={i}><small>{new Date(e.time).toLocaleString()}</small><strong>{e.kind.toLowerCase().replaceAll('_',' ')}</strong><small>{e.details.capture_id || e.details.authorization_id || e.details.order_id || e.details.reason || ''}</small></div>)}</div>}
   </Panel>
 </> : <section className="method"><h2>How the desk works</h2><ol>{[
   ['Inspect','Compare the source receipt with two Gemini readings.'],
   ['Review','Send a flagged total to a reviewer with its evidence crop.'],
   ['Accept','Compare the submitted value and approve or request a revision.'],
   ['Settle','Capture accepted service fees against a buyer-approved budget.'],
 ].map(([title,description])=><li key={title}><h3>{title}</h3><p>{description}</p></li>)}</ol></section>}
 <Evaluation/>
 <div className="footer-note"><LockKeyhole size={15}/> HumanBridge · Verification-service payments use PayPal Sandbox.</div></main></>;
}
const reviewerId = window.location.pathname.match(/^\/review\/([^/]+)/)?.[1];
createRoot(document.getElementById('root')).render(reviewerId ? <Reviewer id={reviewerId}/> : <App/>);
