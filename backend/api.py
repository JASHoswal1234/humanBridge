"""HumanBridge demo API. Sandbox funds only. NOT production-secure or multi-tenant."""
import re
import hashlib
import time
import json
import os
import secrets
import sqlite3
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

from dotenv import load_dotenv
load_dotenv(Path(__file__).with_name('.env'))

from fastapi import FastAPI, HTTPException, UploadFile, File, Query, Request, Response, Depends, APIRouter, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from PIL import Image, UnidentifiedImageError
import io

from ai_engine import correction_warnings, analyze, crop_receipt, read_receipt
from demo_data import DEMO, make_image
from paypal_client import PayPalSandbox, PayPalError, stable_id

def free_preview():
    return os.getenv('RENDER') == 'true' or os.getenv('HUMANBRIDGE_FREE_PREVIEW', '0') != '0'


def require_payment_mode():
    if free_preview():
        raise HTTPException(403, 'Payments are disabled in this temporary free preview.')


def public_origin():
    return (os.getenv('APP_PUBLIC_URL') or os.getenv('RENDER_EXTERNAL_URL') or '').rstrip('/')


ROOT = Path(__file__).resolve().parent
STORAGE = Path(os.getenv('UPLOAD_DIR') or ROOT / 'data' / 'uploads')
STORAGE.mkdir(parents=True, exist_ok=True)
DB = Path(os.getenv('DB_PATH', str(ROOT / 'data' / 'humanbridge.db'))).resolve()
DB.parent.mkdir(parents=True, exist_ok=True)
BUDGET_CENTS = 500
REVIEW_CENTS = 75
app = FastAPI(title='HumanBridge Sandbox MVP', version='0.1.0')
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'], allow_credentials=False, allow_methods=['*'], allow_headers=['*'])



@app.middleware('http')
async def protect_browser_requests(request: Request, call_next):
    if request.method == 'POST' and request.headers.get('sec-fetch-site') in ('cross-site','same-site'):
        return Response('Open HumanBridge on its own origin',status_code=403)
    response = await call_next(request)
    response.headers['Referrer-Policy'] = 'no-referrer'
    if request.url.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'private, no-store'
    return response


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect():
    db = sqlite3.connect(DB, timeout=20)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    return db


def init_database():
    with connect() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS batches (
            id TEXT PRIMARY KEY, created_at TEXT NOT NULL, data_mode TEXT NOT NULL,
            payment_status TEXT NOT NULL DEFAULT 'NOT_STARTED',
            paypal_order_id TEXT, paypal_approval_url TEXT,
            paypal_authorization_id TEXT, paypal_capture_id TEXT,
            authorized_cents INTEGER NOT NULL DEFAULT 500, captured_cents INTEGER NOT NULL DEFAULT 0,
            order_request_id TEXT, authorize_request_id TEXT, capture_request_id TEXT, void_request_id TEXT
        );
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY, batch_id TEXT NOT NULL REFERENCES batches(id),
            filename TEXT NOT NULL, image_path TEXT NOT NULL, crop_path TEXT NOT NULL,
            first_json TEXT NOT NULL, second_json TEXT NOT NULL, flagged INTEGER NOT NULL,
            reasons_json TEXT NOT NULL, data_mode TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS review_tasks (
            id TEXT PRIMARY KEY, batch_id TEXT NOT NULL REFERENCES batches(id),
            document_id TEXT NOT NULL REFERENCES documents(id),
            review_token TEXT NOT NULL, field TEXT NOT NULL DEFAULT 'total',
            proposed_value TEXT, reviewer_value TEXT,
            status TEXT NOT NULL DEFAULT 'PENDING', fee_cents INTEGER NOT NULL DEFAULT 75
        );
        CREATE TABLE IF NOT EXISTS extraction_attempts (
            id TEXT PRIMARY KEY, batch_id TEXT NOT NULL REFERENCES batches(id), digest TEXT NOT NULL,
            started REAL NOT NULL, state TEXT NOT NULL, error TEXT, document_id TEXT REFERENCES documents(id)
        );
        CREATE INDEX IF NOT EXISTS attempts_image ON extraction_attempts(batch_id,digest);
        CREATE TABLE IF NOT EXISTS extraction_passes (
            attempt_id TEXT NOT NULL REFERENCES extraction_attempts(id), number INTEGER NOT NULL,
            evidence TEXT NOT NULL, PRIMARY KEY(attempt_id,number)
        );
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, batch_id TEXT NOT NULL,
            created_at TEXT NOT NULL, kind TEXT NOT NULL, details_json TEXT NOT NULL
        );
        ''')

        additions = {'batches': {'owner_hash':'TEXT', 'auth_currency':'TEXT', 'auth_status':'TEXT',
                                 'verified_cents':'INTEGER', 'settle_started':'REAL', 'pending_capture':'TEXT', 'authorize_started':'REAL'},
                     'review_tasks': {'revision':'INTEGER NOT NULL DEFAULT 0', 'check_status':'TEXT', 'acceptance_reason':'TEXT'}}
        for table, columns in additions.items():
            existing = {r['name'] for r in db.execute(f'PRAGMA table_info({table})')}
            for name, definition in columns.items():
                if name not in existing:
                    db.execute(f'ALTER TABLE {table} ADD COLUMN {name} {definition}')


init_database()


def require_batch(db, batch_id):
    batch = db.execute('SELECT * FROM batches WHERE id=?', (batch_id,)).fetchone()
    if not batch:
        raise HTTPException(404, 'Batch not found')
    return batch


def log_event(db, batch_id, kind, detail=None):
    db.execute('INSERT INTO events(batch_id,created_at,kind,details_json) VALUES(?,?,?,?)',
               (batch_id, now(), kind, json.dumps(detail or {})))


def require_owner(batch_id: str, request: Request):
    token = request.cookies.get('hb_owner', '')
    with connect() as db:
        batch = require_batch(db, batch_id)
    if not secrets.compare_digest(batch['owner_hash'] or '-', hashlib.sha256(token.encode()).hexdigest()):
        raise HTTPException(403, 'Open this batch in the browser that created it')


owner = APIRouter(dependencies=[Depends(require_owner)])


def private_image(doc_id, crop=False):
    if not re.fullmatch('[0-9a-f]{16}', doc_id):
        raise HTTPException(404)
    path = (STORAGE / (doc_id + ('-crop.png' if crop else '.png'))).resolve()
    if path.parent != STORAGE.resolve() or not path.is_file():
        raise HTTPException(404)
    return FileResponse(path, media_type='image/png', headers={'Cache-Control':'private, no-store'})


@owner.get('/api/batches/{batch_id}/images/{doc_id}')
def requester_image(batch_id: str, doc_id: str):
    with connect() as db:
        if not db.execute('SELECT 1 FROM documents WHERE id=? AND batch_id=?', (doc_id,batch_id)).fetchone():
            raise HTTPException(404)
    return private_image(doc_id)


@app.get('/api/tasks/{task_id}/receipt-crop.png')
def reviewer_image(task_id: str, request: Request):
    with connect() as db:
        task = db.execute('SELECT * FROM review_tasks WHERE id=?', (task_id,)).fetchone()
    if not task or not secrets.compare_digest(request.cookies.get('hb_review',''),task['review_token']):
        raise HTTPException(404)
    return private_image(task['document_id'], crop=True)


def new_batch(response, mode='live'):
    capability = secrets.token_urlsafe(32)
    batch_id = uuid.uuid4().hex[:16]
    with connect() as db:
        db.execute('INSERT INTO batches(id,created_at,data_mode,owner_hash) VALUES(?,?,?,?)',
                   (batch_id, now(), mode, hashlib.sha256(capability.encode()).hexdigest()))
        response.set_cookie('hb_owner', capability, path=f'/api/batches/{batch_id}', httponly=True, secure=public_origin().startswith('https://'), samesite='strict', max_age=86400*7)
        log_event(db, batch_id, 'BATCH_CREATED', {'mode': mode})
    return batch_id


def add_document(batch_id, filename, raw, first, second, mode, attempt=None):
    doc_id = uuid.uuid4().hex[:16]
    image_path = STORAGE / f'{doc_id}.png'
    crop_path = STORAGE / f'{doc_id}-crop.png'
    flagged, reasons = analyze(first, second)
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        batch = require_batch(db, batch_id)
        if attempt and batch['payment_status'] != 'NOT_STARTED':
            raise HTTPException(409, 'Batch closed during analysis')
        if attempt and not db.execute("SELECT 1 FROM extraction_attempts WHERE id=? AND state='running'", (attempt,)).fetchone():
            raise HTTPException(409, 'Extraction attempt expired')
        with Image.open(io.BytesIO(raw)) as img:
            img.convert('RGB').save(image_path, format='PNG')
        crop_path.write_bytes(crop_receipt(raw))
        db.execute('''INSERT INTO documents(id,batch_id,filename,image_path,crop_path,first_json,second_json,flagged,reasons_json,data_mode)
                      VALUES(?,?,?,?,?,?,?,?,?,?)''',
                   (doc_id, batch_id, filename, str(image_path), str(crop_path), json.dumps(first), json.dumps(second),
                    1 if flagged else 0, json.dumps(reasons), mode))
        if attempt:
            (STORAGE / f'{doc_id}.original').write_bytes(raw)
            db.execute("UPDATE extraction_attempts SET state='complete', document_id=? WHERE id=?", (doc_id, attempt))
        if flagged:
            task_id = uuid.uuid4().hex[:16]
            db.execute('''INSERT INTO review_tasks(id,batch_id,document_id,review_token,proposed_value,fee_cents)
                          VALUES(?,?,?,?,?,?)''',
                       (task_id, batch_id, doc_id, secrets.token_urlsafe(18), first.get('total'), REVIEW_CENTS))
        log_event(db, batch_id, 'DOCUMENT_ANALYZED', {'document_id': doc_id, 'flagged': flagged, 'mode': mode})
    return doc_id


def get_batch_state(batch_id):
    with connect() as db:
        batch = require_batch(db, batch_id)
        docs = db.execute('SELECT * FROM documents WHERE batch_id=? ORDER BY rowid', (batch_id,)).fetchall()
        tasks = db.execute('SELECT * FROM review_tasks WHERE batch_id=? ORDER BY rowid', (batch_id,)).fetchall()
        events = db.execute('SELECT created_at,kind,details_json FROM events WHERE batch_id=? ORDER BY id DESC', (batch_id,)).fetchall()
        passes = {}
        for row in db.execute("""SELECT a.document_id,a.id,p.number,p.evidence FROM extraction_attempts a
                                 JOIN extraction_passes p ON a.id=p.attempt_id
                                 WHERE a.batch_id=? AND a.state='complete' ORDER BY p.number""", (batch_id,)):
            evidence = json.loads(row['evidence'])
            passes.setdefault(row['document_id'], []).append({
                'attempt_id': row['id'], 'number': row['number'], 'model': evidence['model'],
                'time': evidence['time'], 'response_id': evidence['response_id']})
    def public_doc(d):
        return {
            'passes': passes.get(d['id'], []), 'id': d['id'], 'filename': d['filename'], 'flagged': bool(d['flagged']),
            'reasons': json.loads(d['reasons_json']), 'first': json.loads(d['first_json']),
            'second': json.loads(d['second_json']), 'mode': d['data_mode'],
            'image_url': f"/api/batches/{batch_id}/images/{d['id']}",
        }
    readings = {d['id']:(json.loads(d['first_json']),json.loads(d['second_json'])) for d in docs}
    def public_task(t):
        fields = ('id','document_id','review_token','field','proposed_value','reviewer_value',
                  'status','fee_cents','revision','check_status','acceptance_reason')
        return {**{k:t[k] for k in fields},
                'correction_warnings':correction_warnings(*readings[t['document_id']], t['reviewer_value'])}
    return {
        'id': batch['id'], 'created_at': batch['created_at'], 'data_mode': batch['data_mode'],
        'payment_status': batch['payment_status'], 'budget_cents': BUDGET_CENTS, 'verified_cents':batch['verified_cents'], 'auth_currency':batch['auth_currency'], 'auth_status':batch['auth_status'],
        'free_preview': free_preview(), 'accepted_cents': sum(t['fee_cents'] for t in tasks if t['status']=='ACCEPTED'),
        'captured_cents': batch['captured_cents'], 'paypal_order_id': batch['paypal_order_id'],
        'paypal_approval_url': batch['paypal_approval_url'],
        'paypal_authorization_id': batch['paypal_authorization_id'],
        'paypal_capture_id': batch['paypal_capture_id'],
        'documents': [public_doc(d) for d in docs],
        'tasks': [public_task(t) for t in tasks],
        'events': [{'time': e['created_at'], 'kind': e['kind'], 'details': json.loads(e['details_json'])} for e in events],
    }


@app.get('/api/health')
def health():
    return {'ok': True, 'sandbox_only': True}


@app.get('/api/config')
def config():
    return {'sandbox_only': True, 'gemini_enabled': bool(os.getenv('GEMINI_API_KEY')),
            'free_preview': free_preview(), 'paypal_enabled': not free_preview() and bool(os.getenv('PAYPAL_CLIENT_ID') and os.getenv('PAYPAL_CLIENT_SECRET')),
            'budget_cents': BUDGET_CENTS, 'fee_cents': REVIEW_CENTS}


@app.post('/api/batches')
def create_batch(response: Response):
    return get_batch_state(new_batch(response))


@app.get('/api/sample-receipt')
def sample_receipt():
    from fastapi.responses import Response
    image = make_image('SAMPLE STATIONERY', '2026-11-10', '30.00', '2.40', '32.40')
    return Response(content=image, media_type='image/png')


@app.post('/api/batches/demo')
def demo_batch(response: Response):
    batch_id = new_batch(response, 'scripted_demo')
    for name, date, subtotal, tax, actual, reading1, reading2 in DEMO:
        raw = make_image(name, date, subtotal, tax, actual)
        first = {'merchant': name, 'date': date, 'subtotal': subtotal, 'tax': tax, 'total': reading1 or None}
        second = {'merchant': name, 'date': date, 'subtotal': subtotal, 'tax': tax, 'total': reading2 or None}
        add_document(batch_id, f'{name.lower().replace(" ", "-")}.png', raw, first, second, 'SCRIPTED_SIMULATION')
    return get_batch_state(batch_id)


@owner.get('/api/batches/{batch_id}')
def batch_state(batch_id: str):
    return get_batch_state(batch_id)


@owner.post('/api/batches/{batch_id}/documents')
def upload_document(batch_id: str, file: UploadFile = File(...)):
    with connect() as db:
        batch = require_batch(db, batch_id)
        if batch['data_mode'] == 'scripted_demo':
            raise HTTPException(409, 'Start a live batch to upload a receipt')
        if batch['payment_status'] != 'NOT_STARTED':
            raise HTTPException(409, 'Cannot upload after payment authorization flow begins')
    raw = file.file.read(5 * 1024 * 1024 + 1)
    if len(raw) > 5 * 1024 * 1024:
        raise HTTPException(413, 'Image exceeds 5 MB limit')
    try:
        with Image.open(io.BytesIO(raw)) as im:
            fmt = im.format
            if im.width * im.height > 16000000:
                raise HTTPException(413, 'Image exceeds 16 megapixels')
            im.verify()
        with Image.open(io.BytesIO(raw)) as im:
            im.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, SyntaxError):
        raise HTTPException(400, 'Upload a valid PNG, JPEG or WebP image')
    if fmt not in ('PNG', 'JPEG', 'WEBP'):
        raise HTTPException(400, 'Only PNG, JPEG and WebP images supported')
    mimetype = {'PNG': 'image/png', 'JPEG': 'image/jpeg', 'WEBP': 'image/webp'}[fmt]
    digest = hashlib.sha256(raw).hexdigest()
    attempt = uuid.uuid4().hex
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        previous = db.execute("""SELECT state,started FROM extraction_attempts WHERE batch_id=? AND digest=?
                                 ORDER BY started DESC LIMIT 1""", (batch_id, digest)).fetchone()
        if previous and previous['state'] == 'complete':
            return get_batch_state(batch_id)
        if previous and previous['state'] == 'running':
            if time.time() - previous['started'] < 300:
                raise HTTPException(409, 'This receipt is being analyzed. Refresh the batch shortly.')
            db.execute("UPDATE extraction_attempts SET state='expired' WHERE batch_id=? AND digest=? AND state='running'",
                       (batch_id, digest))
        db.execute("INSERT INTO extraction_attempts(id,batch_id,digest,started,state) VALUES(?,?,?,?,'running')",
                   (attempt, batch_id, digest, time.time()))

    def record_pass(number, evidence):
        with connect() as db:
            db.execute('INSERT INTO extraction_passes VALUES(?,?,?)', (attempt, number, json.dumps(evidence)))

    try:
        first, second = read_receipt(raw, mimetype, record_pass)
        add_document(batch_id, file.filename or 'receipt', raw, first, second, 'LIVE_GEMINI', attempt)
    except Exception as err:
        kind = type(err).__name__
        code = getattr(err, 'code', None)
        detail = f'{kind} (HTTP {code})' if isinstance(code, int) else kind
        with connect() as db:
            db.execute("UPDATE extraction_attempts SET state='failed',error=? WHERE id=?", (detail, attempt))
        if isinstance(err, HTTPException):
            raise
        if code in (500, 502, 503, 504):
            raise HTTPException(502, f'Gemini is temporarily unavailable (HTTP {code}). Retry this receipt shortly.') from None
        raise HTTPException(502, f'Gemini analysis failed: {detail}. Check model, key and quota before retrying.') from None
    return get_batch_state(batch_id)


def paypal_or_503():
    try:
        return PayPalSandbox()
    except PayPalError as err:
        raise HTTPException(503, str(err))


def api_error(err):
    raise HTTPException(502, str(err))


def order_unit(order, batch):
    units = order.get('purchase_units', [])
    if (order.get('id') != batch['paypal_order_id'] or order.get('intent') != 'AUTHORIZE'
            or len(units) != 1 or units[0].get('reference_id') != batch['id']
            or units[0].get('amount',{}).get('currency_code') != 'USD'
            or units[0].get('amount',{}).get('value') != f'{Decimal(BUDGET_CENTS)/100:.2f}'):
        raise HTTPException(409,'PayPal order does not match this batch and budget')
    return units[0]


def verify_authorization(auth, auth_id, unit):
    amount = auth.get('amount', {})
    if auth.get('id') != auth_id or any(amount.get(k) != unit['amount'][k] for k in ('currency_code','value')):
        raise HTTPException(409,'PayPal authorization ID, amount or currency mismatch')


@owner.post('/api/batches/{batch_id}/payment/create', dependencies=[Depends(require_payment_mode)])
def payment_create(batch_id: str, request: Request):
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        batch = require_batch(db, batch_id)
        task_count = db.execute('SELECT COUNT(*) FROM review_tasks WHERE batch_id=?', (batch_id,)).fetchone()[0]
        if not task_count:
            raise HTTPException(409, 'No uncertain documents to review: no paid task is needed')
        if batch['paypal_order_id']:
            return {'order_id': batch['paypal_order_id'], 'approval_url': batch['paypal_approval_url'], 'payment_status': batch['payment_status']}
        if batch['payment_status'] != 'NOT_STARTED':
            raise HTTPException(409, 'Cannot create new order in this payment state')
        request_id = batch['order_request_id'] or stable_id()
        db.execute('UPDATE batches SET order_request_id=? WHERE id=?', (request_id, batch_id))
    try:
        public_url = public_origin()
        if not public_url:
            origin = urlsplit(request.headers.get('origin') or str(request.base_url))
            if origin.scheme in ('http','https') and origin.hostname in ('127.0.0.1','localhost','::1'):
                public_url = f'{origin.scheme}://{origin.netloc}'
        order = paypal_or_503().create_order(batch_id=batch_id, dollars='5.00', request_id=request_id,
                                            public_url=public_url or 'http://127.0.0.1:5173')
    except PayPalError as err:
        api_error(err)
    approval_url = next((link['href'] for link in order.get('links', []) if link.get('rel') in ('approve','payer-action')), None)
    if (not order.get('id') or not approval_url or not approval_url.startswith('https://www.sandbox.paypal.com/')
            or parse_qs(urlsplit(approval_url).query).get('token') != [order['id']]):
        raise HTTPException(502,'Sandbox order lacks an approval link or identifier')
    with connect() as db:
        db.execute("UPDATE batches SET paypal_order_id=?, paypal_approval_url=?, payment_status='AWAITING_BUYER' WHERE id=? AND paypal_order_id IS NULL",
                   (order['id'], approval_url, batch_id))
        log_event(db, batch_id, 'ORDER_CREATED', {'order_id': order['id']})
    return {'order_id': order['id'], 'approval_url': approval_url, 'payment_status': 'AWAITING_BUYER'}


@owner.get('/api/batches/{batch_id}/payment/approval', dependencies=[Depends(require_payment_mode)])
def payment_approval(batch_id: str, token: str):
    with connect() as db:
        batch = require_batch(db, batch_id)
    if not token or token != batch['paypal_order_id']:
        raise HTTPException(409, 'Checkout token does not match this batch order')
    try:
        order = paypal_or_503().show_order(token)
    except PayPalError as err:
        if err.status_code == 404:
            return {'status':'UNAVAILABLE'}
        api_error(err)
    unit = order_unit(order, batch)
    status = order.get('status')
    if status == 'COMPLETED' and unit.get('payments',{}).get('authorizations'):
        return {'status':'AUTHORIZATION_FOUND'}
    return {'status':status}


@owner.post('/api/batches/{batch_id}/payment/authorize', dependencies=[Depends(require_payment_mode)])
def payment_authorize(batch_id: str, token: str | None = None):
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        batch = require_batch(db, batch_id)
        if token is not None and token != batch['paypal_order_id']:
            raise HTTPException(409,'Checkout token does not match this batch order')
        if batch['payment_status'] == 'AUTHORIZED':
            return get_batch_state(batch_id)
        if batch['payment_status'] != 'AWAITING_BUYER' or not batch['paypal_order_id']:
            raise HTTPException(409, 'Create an order before authorizing it')
        order_id = batch['paypal_order_id']
        request_id = batch['authorize_request_id'] or stable_id()
        started = time.time()
        if batch['authorize_started'] and started - batch['authorize_started'] < 240:
            raise HTTPException(409,'Authorization check is already in progress. Check again shortly.')
        db.execute('UPDATE batches SET authorize_request_id=?,authorize_started=? WHERE id=?',(request_id,started,batch_id))
    try:
        return finish_authorization(batch, request_id)
    finally:
        with connect() as db:
            db.execute('UPDATE batches SET authorize_started=NULL WHERE id=? AND authorize_started=?',(batch_id,started))


def finish_authorization(batch, request_id):
    batch_id, order_id = batch['id'], batch['paypal_order_id']
    client = paypal_or_503()
    try:
        order = client.show_order(order_id)
        unit = order_unit(order,batch)
        auths = unit.get('payments',{}).get('authorizations',[])
        if not auths:
            if order.get('status') != 'APPROVED':
                raise HTTPException(409,'Buyer approval is still required in PayPal Sandbox')
            client.authorize(order_id,request_id)
            unit = order_unit(client.show_order(order_id),batch)
            auths = unit.get('payments',{}).get('authorizations',[])
        if len(auths) != 1 or not auths[0].get('id'):
            raise HTTPException(502,'Expected one authorization for this order')
        auth_id = auths[0]['id']
        verified = client.show_authorization(auth_id)
        verify_authorization(verified,auth_id,unit)
        if verified.get('status') != 'CREATED':
            raise HTTPException(409,'Authorization is not available for capture')
    except PayPalError as err:
        api_error(err)
    with connect() as db:
        db.execute("UPDATE batches SET paypal_authorization_id=?, auth_status=?,auth_currency=?,verified_cents=?, payment_status='AUTHORIZED' WHERE id=? AND payment_status='AWAITING_BUYER'", (auth_id, verified['status'],verified['amount']['currency_code'],BUDGET_CENTS,batch_id))
        log_event(db, batch_id, 'BUDGET_AUTHORIZED', {'authorization_id': auth_id,'currency':'USD','verified_cents':BUDGET_CENTS,'status':verified['status']})
    return get_batch_state(batch_id)


@app.get('/api/tasks/{task_id}')
def get_task(task_id: str, response: Response, token: str = Query(''), x_review_token: str = Header('')):
    token = x_review_token or token
    with connect() as db:
        task = db.execute('SELECT * FROM review_tasks WHERE id=?', (task_id,)).fetchone()
        if not task or not secrets.compare_digest(token, task['review_token']):
            raise HTTPException(404, 'Review task not found')
        doc = db.execute('SELECT * FROM documents WHERE id=?', (task['document_id'],)).fetchone()
    response.set_cookie('hb_review',token,path=f'/api/tasks/{task_id}/',httponly=True,secure=public_origin().startswith('https://'),samesite='strict')
    response.headers['Cache-Control'] = 'no-store'
    return {'id': task_id, 'free_preview':free_preview(), 'revision':task['revision'], 'check_status':task['check_status'], 'field': task['field'],
            'proposed_value': task['proposed_value'], 'reviewer_value': task['reviewer_value'],
            'status': task['status'], 'fee_cents': task['fee_cents'],
            'crop_url': f"/api/tasks/{task_id}/receipt-crop.png", 'mode': doc['data_mode']}


class ReviewResponse(BaseModel):
    token: str
    value: str
    revision: int = 0


@app.post('/api/tasks/{task_id}/submit')
def submit_review(task_id: str, response: ReviewResponse):
    if not re.fullmatch(r'[0-9]{1,10}(?:\.[0-9]{1,2})?',response.value.strip()):
        raise HTTPException(400, 'Enter a valid numeric total')
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        task = db.execute('SELECT * FROM review_tasks WHERE id=?', (task_id,)).fetchone()
        if not task or not secrets.compare_digest(response.token, task['review_token']):
            raise HTTPException(404, 'Review task not found')
        if task['revision'] != response.revision:
            raise HTTPException(409,'The task has changed. Reload before submitting.')
        if task['status'] == 'SUBMITTED' and task['reviewer_value'] == response.value.strip():
            return {'ok':True,'status':'SUBMITTED','check_status':'CHECKS_PASSED'}
        if task['status'] not in ('PENDING', 'REVISION_REQUESTED'):
            raise HTTPException(409, 'Review task is already decided')
        db.execute("UPDATE review_tasks SET reviewer_value=?, status='SUBMITTED', check_status='CHECKS_PASSED' WHERE id=?", (response.value.strip(), task_id))
        log_event(db, task['batch_id'], 'REVIEW_SUBMITTED', {'task_id': task_id})
    return {'ok': True, 'status': 'SUBMITTED', 'check_status':'CHECKS_PASSED'}


class Acceptance(BaseModel):
    reason: str = ''


@owner.post('/api/batches/{batch_id}/tasks/{task_id}/accept', dependencies=[Depends(require_payment_mode)])
def accept_task(batch_id: str, task_id: str, revision: int = 0, decision: Acceptance | None = None):
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        batch = require_batch(db, batch_id)
        if batch['payment_status'] != 'AUTHORIZED':
            raise HTTPException(409, 'Requester must authorize review budget before accepting paid tasks')
        task = db.execute('SELECT * FROM review_tasks WHERE id=? AND batch_id=?', (task_id, batch_id)).fetchone()
        if not task:
            raise HTTPException(404, 'Review task not found')
        if task['status'] != 'SUBMITTED' or task['revision'] != revision or task['check_status'] != 'CHECKS_PASSED':
            raise HTTPException(409, 'Only submitted work can be accepted')
        existing = db.execute("SELECT COALESCE(SUM(fee_cents),0) FROM review_tasks WHERE batch_id=? AND status='ACCEPTED'",(batch_id,)).fetchone()[0]
        if task['fee_cents'] <= 0 or existing + task['fee_cents'] > min(BUDGET_CENTS,batch['verified_cents'] or 0):
            raise HTTPException(409,'Accepting this review would exceed the authorized budget')
        doc = db.execute('SELECT first_json,second_json FROM documents WHERE id=?',(task['document_id'],)).fetchone()
        warnings = correction_warnings(json.loads(doc['first_json']),json.loads(doc['second_json']),task['reviewer_value'])
        reason = decision.reason.strip() if decision else ''
        if len(reason)>500 or (warnings and not reason):
            raise HTTPException(422,'Explain why you accept this correction in 1 to 500 characters.')
        db.execute("UPDATE review_tasks SET status='ACCEPTED',acceptance_reason=? WHERE id=?", (reason or None,task_id))
        log_event(db, batch_id, 'REVIEW_ACCEPTED', {'task_id': task_id,'reviewer_value':task['reviewer_value'],'warnings':warnings,'reason':reason or None})
    return get_batch_state(batch_id)


@owner.post('/api/batches/{batch_id}/tasks/{task_id}/revise')
def revise_task(batch_id: str, task_id: str, revision: int = 0):
    with connect() as db:
        updated = db.execute("""UPDATE review_tasks SET status='REVISION_REQUESTED', revision=revision+1, check_status=NULL
                                WHERE id=? AND batch_id=? AND status='SUBMITTED' AND revision=?""",(task_id,batch_id,revision))
        if not updated.rowcount:
            raise HTTPException(409,'This submission is no longer awaiting a decision')
        log_event(db,batch_id,'REVISION_REQUESTED',{'task_id':task_id,'revision':revision})
    return get_batch_state(batch_id)


@owner.post('/api/batches/{batch_id}/tasks/{task_id}/skip')
def skip_task(batch_id: str, task_id: str):
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        batch = require_batch(db, batch_id)
        if batch['payment_status'] not in ('AUTHORIZED','NOT_STARTED','AWAITING_BUYER'):
            raise HTTPException(409, 'Payment already completed')
        task = db.execute('SELECT * FROM review_tasks WHERE id=? AND batch_id=?', (task_id, batch_id)).fetchone()
        if not task:
            raise HTTPException(404, 'Review task not found')
        if task['status'] not in ('PENDING','SUBMITTED','REVISION_REQUESTED'):
            raise HTTPException(409, 'Task already decided')
        db.execute("UPDATE review_tasks SET status='SKIPPED' WHERE id=?", (task_id,))
        log_event(db, batch_id, 'REVIEW_SKIPPED', {'task_id': task_id})
    return get_batch_state(batch_id)


@owner.post('/api/batches/{batch_id}/payment/settle', dependencies=[Depends(require_payment_mode)])
def settle_payment(batch_id: str):
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        batch = require_batch(db, batch_id)
        if batch['payment_status'] in ('CAPTURED', 'VOIDED'):
            return get_batch_state(batch_id)
        if batch['payment_status'] not in ('AUTHORIZED','SETTLING') or not batch['paypal_authorization_id']:
            raise HTTPException(409, 'Budget is not authorized')
        tasks = db.execute('SELECT status,fee_cents FROM review_tasks WHERE batch_id=?', (batch_id,)).fetchall()
        if any(t['status'] not in ('ACCEPTED','SKIPPED') for t in tasks):
            raise HTTPException(409, 'All tasks must be accepted or skipped before settlement')
        amount = sum(t['fee_cents'] for t in tasks if t['status'] == 'ACCEPTED')
        if (batch['captured_cents'] != 0 or any(t['fee_cents'] <= 0 for t in tasks)
                or amount > min(BUDGET_CENTS,batch['verified_cents'] or 0)):
            raise HTTPException(409, 'Application-enforced budget exceeded. No capture attempted.')
        auth_id = batch['paypal_authorization_id']
        request_id = batch['capture_request_id'] if amount > 0 else batch['void_request_id']
        request_id = request_id or stable_id()
        key_field = 'capture_request_id' if amount else 'void_request_id'
        started = batch['settle_started'] or time.time()
        db.execute(f"UPDATE batches SET {key_field}=?,settle_started=?,payment_status='SETTLING' WHERE id=?",
                   (request_id,started,batch_id))
        if batch['payment_status'] == 'AUTHORIZED':
            log_event(db,batch_id,'SETTLEMENT_REQUESTED',{'authorization_id':auth_id,'cents':amount,'request_id':request_id})
    client = paypal_or_503()
    try:
        unit = order_unit(client.show_order(batch['paypal_order_id']),batch)
        payments = unit.get('payments',{})
        if [a.get('id') for a in payments.get('authorizations',[])] != [auth_id]:
            raise HTTPException(409,'Authorization is not linked to this batch order')
        auth = client.show_authorization(auth_id)
        verify_authorization(auth,auth_id,unit)
        captures = payments.get('captures',[])
        if len(captures) > 1 or (captures and batch['payment_status'] != 'SETTLING'):
            raise HTTPException(409,'Unexpected captures on this order require reconciliation')
        if amount:
            capture_id = batch['pending_capture'] or (captures[0]['id'] if captures else None)
            if not capture_id:
                if auth.get('status') not in ('CREATED','CAPTURED','PARTIALLY_CAPTURED') or time.time()-started > 300:
                    raise HTTPException(409,'Cannot safely replay capture. Reconcile the Sandbox authorization.')
                if auth['status'] != 'CREATED' and batch['payment_status'] != 'SETTLING':
                    raise HTTPException(409,'Authorization already used outside this settlement')
                receipt = client.capture(auth_id,amount,request_id)
                capture_id = receipt.get('id')
                if not capture_id:
                    raise HTTPException(502,'PayPal did not return a capture ID')
                with connect() as db:
                    db.execute('UPDATE batches SET pending_capture=? WHERE id=?',(capture_id,batch_id))
            verified = client.show_capture(capture_id)
            related = verified.get('supplementary_data',{}).get('related_ids',{})
            if (verified.get('id') != capture_id or verified.get('status') != 'COMPLETED'
                    or verified.get('invoice_id') != request_id
                    or related.get('order_id',batch['paypal_order_id']) != batch['paypal_order_id']
                    or related.get('authorization_id',auth_id) != auth_id
                    or verified.get('amount',{}).get('currency_code') != 'USD'
                    or verified.get('amount',{}).get('value') != f'{Decimal(amount)/100:.2f}'):
                raise HTTPException(502,'Capture not verified as completed for the expected USD amount')
            with connect() as db:
                updated = db.execute("""UPDATE batches SET paypal_capture_id=?,captured_cents=?,payment_status='CAPTURED'
                                        WHERE id=? AND payment_status='SETTLING'""",(capture_id,amount,batch_id))
                if updated.rowcount:
                    log_event(db,batch_id,'FINAL_CAPTURE_COMPLETED',{'capture_id':capture_id,'cents':amount,'status':'COMPLETED'})
        else:
            if captures or auth['status'] not in ('CREATED','VOIDED'):
                raise HTTPException(409,'Authorization cannot be voided safely')
            if auth['status'] != 'VOIDED':
                client.void(auth_id,request_id)
                auth = client.show_authorization(auth_id)
                verify_authorization(auth,auth_id,unit)
            if auth['status'] != 'VOIDED':
                raise HTTPException(502,'PayPal has not confirmed the void')
            with connect() as db:
                updated = db.execute("UPDATE batches SET payment_status='VOIDED' WHERE id=? AND payment_status='SETTLING'",(batch_id,))
                if updated.rowcount:
                    log_event(db,batch_id,'AUTHORIZATION_VOIDED',{'authorization_id':auth_id})
    except (PayPalError,HTTPException) as err:
        with connect() as db:
            log_event(db,batch_id,'SETTLEMENT_UNCONFIRMED',{'request_id':request_id,'reason':str(err)})
        if isinstance(err,HTTPException):
            raise
        api_error(err)
    return get_batch_state(batch_id)


app.include_router(owner)

FRONTEND_BUILD = ROOT.parent / 'frontend' / 'dist'
if FRONTEND_BUILD.is_dir():
    app.mount('/assets', StaticFiles(directory=FRONTEND_BUILD / 'assets'), name='frontend_assets')
    @app.get('/')
    def index():
        return FileResponse(FRONTEND_BUILD / 'index.html')
    @app.get('/review/{path:path}')
    def review_page(path: str):
        return FileResponse(FRONTEND_BUILD / 'index.html')
