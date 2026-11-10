"""HumanBridge demo API. Sandbox funds only. NOT production-secure or multi-tenant."""
import json
import os
import secrets
import sqlite3
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).with_name('.env'))

from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from PIL import Image, UnidentifiedImageError
import io

from ai_engine import analyze, crop_receipt, read_receipt
from demo_data import DEMO, make_image
from paypal_client import PayPalSandbox, PayPalError, stable_id

ROOT = Path(__file__).resolve().parent
STORAGE = ROOT / 'data' / 'uploads'
STORAGE.mkdir(parents=True, exist_ok=True)
DB = Path(os.getenv('DB_PATH', str(ROOT / 'data' / 'humanbridge.db'))).resolve()
DB.parent.mkdir(parents=True, exist_ok=True)
BUDGET_CENTS = 500
REVIEW_CENTS = 75
app = FastAPI(title='HumanBridge Sandbox MVP', version='0.1.0')
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'], allow_credentials=False, allow_methods=['*'], allow_headers=['*'])
app.mount('/uploads', StaticFiles(directory=STORAGE), name='uploads')


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
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, batch_id TEXT NOT NULL,
            created_at TEXT NOT NULL, kind TEXT NOT NULL, details_json TEXT NOT NULL
        );
        ''')


init_database()


def require_batch(db, batch_id):
    batch = db.execute('SELECT * FROM batches WHERE id=?', (batch_id,)).fetchone()
    if not batch:
        raise HTTPException(404, 'Batch not found')
    return batch


def log_event(db, batch_id, kind, detail=None):
    db.execute('INSERT INTO events(batch_id,created_at,kind,details_json) VALUES(?,?,?,?)',
               (batch_id, now(), kind, json.dumps(detail or {})))


def new_batch(mode='live'):
    batch_id = uuid.uuid4().hex[:16]
    with connect() as db:
        db.execute('INSERT INTO batches(id,created_at,data_mode) VALUES(?,?,?)', (batch_id, now(), mode))
        log_event(db, batch_id, 'BATCH_CREATED', {'mode': mode})
    return batch_id


def add_document(batch_id, filename, raw, first, second, mode):
    doc_id = uuid.uuid4().hex[:16]
    image_path = STORAGE / f'{doc_id}.png'
    crop_path = STORAGE / f'{doc_id}-crop.png'
    with Image.open(io.BytesIO(raw)) as img:
        img.convert('RGB').save(image_path, format='PNG')
    crop_path.write_bytes(crop_receipt(raw))
    flagged, reasons = analyze(first, second)
    with connect() as db:
        require_batch(db, batch_id)
        db.execute('''INSERT INTO documents(id,batch_id,filename,image_path,crop_path,first_json,second_json,flagged,reasons_json,data_mode)
                      VALUES(?,?,?,?,?,?,?,?,?,?)''',
                   (doc_id, batch_id, filename, str(image_path), str(crop_path), json.dumps(first), json.dumps(second),
                    1 if flagged else 0, json.dumps(reasons), mode))
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
        events = db.execute('SELECT created_at,kind,details_json FROM events WHERE batch_id=? ORDER BY id DESC LIMIT 20', (batch_id,)).fetchall()
    def public_doc(d):
        return {
            'id': d['id'], 'filename': d['filename'], 'flagged': bool(d['flagged']),
            'reasons': json.loads(d['reasons_json']), 'first': json.loads(d['first_json']),
            'second': json.loads(d['second_json']), 'mode': d['data_mode'],
            'image_url': f"/uploads/{d['id']}.png", 'crop_url': f"/uploads/{d['id']}-crop.png",
        }
    return {
        'id': batch['id'], 'created_at': batch['created_at'], 'data_mode': batch['data_mode'],
        'payment_status': batch['payment_status'], 'budget_cents': batch['authorized_cents'],
        'captured_cents': batch['captured_cents'], 'paypal_order_id': batch['paypal_order_id'],
        'paypal_approval_url': batch['paypal_approval_url'],
        'paypal_authorization_id': batch['paypal_authorization_id'],
        'paypal_capture_id': batch['paypal_capture_id'],
        'documents': [public_doc(d) for d in docs],
        'tasks': [{k: t[k] for k in ('id','document_id','review_token','field','proposed_value','reviewer_value','status','fee_cents')} for t in tasks],
        'events': [{'time': e['created_at'], 'kind': e['kind'], 'details': json.loads(e['details_json'])} for e in events],
    }


@app.get('/api/health')
def health():
    return {'ok': True, 'sandbox_only': True}


@app.get('/api/config')
def config():
    return {'sandbox_only': True, 'gemini_enabled': bool(os.getenv('GEMINI_API_KEY')),
            'paypal_enabled': bool(os.getenv('PAYPAL_CLIENT_ID') and os.getenv('PAYPAL_CLIENT_SECRET')),
            'budget_cents': BUDGET_CENTS, 'fee_cents': REVIEW_CENTS}


@app.post('/api/batches')
def create_batch():
    return get_batch_state(new_batch())


@app.post('/api/batches/demo')
def demo_batch():
    batch_id = new_batch('scripted_demo')
    for name, date, subtotal, tax, actual, reading1, reading2 in DEMO:
        raw = make_image(name, date, subtotal, tax, actual)
        first = {'merchant': name, 'date': date, 'subtotal': subtotal, 'tax': tax, 'total': reading1 or None}
        second = {'merchant': name, 'date': date, 'subtotal': subtotal, 'tax': tax, 'total': reading2 or None}
        add_document(batch_id, f'{name.lower().replace(" ", "-")}.png', raw, first, second, 'SCRIPTED_SIMULATION')
    return get_batch_state(batch_id)


@app.get('/api/batches/{batch_id}')
def batch_state(batch_id: str):
    return get_batch_state(batch_id)


@app.post('/api/batches/{batch_id}/documents')
async def upload_document(batch_id: str, file: UploadFile = File(...)):
    with connect() as db:
        batch = require_batch(db, batch_id)
        if batch['payment_status'] != 'NOT_STARTED':
            raise HTTPException(409, 'Cannot upload after payment authorization flow begins')
    raw = await file.read()
    if len(raw) > 5 * 1024 * 1024:
        raise HTTPException(413, 'Image exceeds 5 MB limit')
    try:
        with Image.open(io.BytesIO(raw)) as im:
            fmt = im.format
            im.verify()
    except (UnidentifiedImageError, OSError):
        raise HTTPException(400, 'Upload a valid PNG, JPEG or WebP image')
    if fmt not in ('PNG', 'JPEG', 'WEBP'):
        raise HTTPException(400, 'Only PNG, JPEG and WebP images supported')
    mimetype = {'PNG': 'image/png', 'JPEG': 'image/jpeg', 'WEBP': 'image/webp'}[fmt]
    try:
        first, second = read_receipt(raw, mimetype)
    except Exception as err:
        # Avoid leaking image bytes or API key in error messages; use a generic failure.
        raise HTTPException(502, f'Gemini extraction failed: {type(err).__name__}. Check model/key and backend logs.')
    add_document(batch_id, file.filename or 'receipt', raw, first, second, 'LIVE_GEMINI')
    return get_batch_state(batch_id)


def paypal_or_503():
    try:
        return PayPalSandbox()
    except PayPalError as err:
        raise HTTPException(503, str(err))


def api_error(err):
    raise HTTPException(502, str(err))


@app.post('/api/batches/{batch_id}/payment/create')
def payment_create(batch_id: str):
    with connect() as db:
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
        order = paypal_or_503().create_order(batch_id=batch_id, dollars='5.00', request_id=request_id)
    except PayPalError as err:
        api_error(err)
    approval_url = next((link['href'] for link in order.get('links', []) if link.get('rel') in ('approve','payer-action')), None)
    with connect() as db:
        db.execute("UPDATE batches SET paypal_order_id=?, paypal_approval_url=?, payment_status='AWAITING_BUYER' WHERE id=? AND paypal_order_id IS NULL",
                   (order['id'], approval_url, batch_id))
        log_event(db, batch_id, 'ORDER_CREATED', {'order_id': order['id']})
    return {'order_id': order['id'], 'approval_url': approval_url, 'payment_status': 'AWAITING_BUYER'}


@app.post('/api/batches/{batch_id}/payment/authorize')
def payment_authorize(batch_id: str):
    with connect() as db:
        batch = require_batch(db, batch_id)
        if batch['payment_status'] == 'AUTHORIZED':
            return get_batch_state(batch_id)
        if batch['payment_status'] != 'AWAITING_BUYER' or not batch['paypal_order_id']:
            raise HTTPException(409, 'Create an order before authorizing it')
        order_id = batch['paypal_order_id']
        request_id = batch['authorize_request_id'] or stable_id()
        db.execute('UPDATE batches SET authorize_request_id=? WHERE id=?', (request_id, batch_id))
    client = paypal_or_503()
    try:
        order = client.show_order(order_id)
        if order.get('status') != 'APPROVED':
            raise HTTPException(409, f'PayPal order is {order.get("status")}; buyer must approve first')
        # Verify order amount, not simply the status.
        units = order.get('purchase_units') or []
        if not units or units[0].get('amount', {}).get('value') != '5.00' or units[0].get('amount', {}).get('currency_code') != 'USD':
            raise HTTPException(409, 'PayPal approved order amount/currency mismatch')
        response = client.authorize(order_id, request_id)
        authorizations = (response.get('purchase_units') or [{}])[0].get('payments', {}).get('authorizations', [])
        if not authorizations:
            raise HTTPException(502, 'PayPal authorization response lacks authorization ID')
        auth_id = authorizations[0]['id']
    except PayPalError as err:
        api_error(err)
    with connect() as db:
        db.execute("UPDATE batches SET paypal_authorization_id=?, payment_status='AUTHORIZED' WHERE id=? AND payment_status='AWAITING_BUYER'", (auth_id, batch_id))
        log_event(db, batch_id, 'BUDGET_AUTHORIZED', {'authorization_id': auth_id})
    return get_batch_state(batch_id)


@app.get('/api/tasks/{task_id}')
def get_task(task_id: str, token: str = Query(...)):
    with connect() as db:
        task = db.execute('SELECT * FROM review_tasks WHERE id=?', (task_id,)).fetchone()
        if not task or not secrets.compare_digest(token, task['review_token']):
            raise HTTPException(404, 'Review task not found')
        doc = db.execute('SELECT * FROM documents WHERE id=?', (task['document_id'],)).fetchone()
    return {'id': task_id, 'batch_id': task['batch_id'], 'field': task['field'],
            'proposed_value': task['proposed_value'], 'reviewer_value': task['reviewer_value'],
            'status': task['status'], 'fee_cents': task['fee_cents'],
            'crop_url': f"/uploads/{doc['id']}-crop.png", 'mode': doc['data_mode']}


class ReviewResponse(BaseModel):
    token: str
    value: str


@app.post('/api/tasks/{task_id}/submit')
def submit_review(task_id: str, response: ReviewResponse):
    from ai_engine import decimal_value
    if decimal_value(response.value) is None:
        raise HTTPException(400, 'Enter a valid numeric total')
    with connect() as db:
        task = db.execute('SELECT * FROM review_tasks WHERE id=?', (task_id,)).fetchone()
        if not task or not secrets.compare_digest(response.token, task['review_token']):
            raise HTTPException(404, 'Review task not found')
        if task['status'] not in ('PENDING', 'SUBMITTED'):
            raise HTTPException(409, 'Review task is already decided')
        db.execute("UPDATE review_tasks SET reviewer_value=?, status='SUBMITTED' WHERE id=?", (response.value.strip(), task_id))
        log_event(db, task['batch_id'], 'REVIEW_SUBMITTED', {'task_id': task_id})
    return {'ok': True, 'status': 'SUBMITTED'}


@app.post('/api/batches/{batch_id}/tasks/{task_id}/accept')
def accept_task(batch_id: str, task_id: str):
    with connect() as db:
        batch = require_batch(db, batch_id)
        if batch['payment_status'] != 'AUTHORIZED':
            raise HTTPException(409, 'Requester must authorize review budget before accepting paid tasks')
        task = db.execute('SELECT * FROM review_tasks WHERE id=? AND batch_id=?', (task_id, batch_id)).fetchone()
        if not task:
            raise HTTPException(404, 'Review task not found')
        if task['status'] != 'SUBMITTED':
            raise HTTPException(409, 'Only submitted work can be accepted')
        db.execute("UPDATE review_tasks SET status='ACCEPTED' WHERE id=?", (task_id,))
        log_event(db, batch_id, 'REVIEW_ACCEPTED', {'task_id': task_id})
    return get_batch_state(batch_id)


@app.post('/api/batches/{batch_id}/tasks/{task_id}/skip')
def skip_task(batch_id: str, task_id: str):
    with connect() as db:
        batch = require_batch(db, batch_id)
        if batch['payment_status'] not in ('AUTHORIZED','NOT_STARTED','AWAITING_BUYER'):
            raise HTTPException(409, 'Payment already completed')
        task = db.execute('SELECT * FROM review_tasks WHERE id=? AND batch_id=?', (task_id, batch_id)).fetchone()
        if not task:
            raise HTTPException(404, 'Review task not found')
        if task['status'] not in ('PENDING','SUBMITTED'):
            raise HTTPException(409, 'Task already decided')
        db.execute("UPDATE review_tasks SET status='SKIPPED' WHERE id=?", (task_id,))
        log_event(db, batch_id, 'REVIEW_SKIPPED', {'task_id': task_id})
    return get_batch_state(batch_id)


@app.post('/api/batches/{batch_id}/payment/settle')
def settle_payment(batch_id: str):
    with connect() as db:
        batch = require_batch(db, batch_id)
        if batch['payment_status'] in ('CAPTURED', 'VOIDED'):
            return get_batch_state(batch_id)
        if batch['payment_status'] != 'AUTHORIZED' or not batch['paypal_authorization_id']:
            raise HTTPException(409, 'Budget is not authorized')
        tasks = db.execute('SELECT status,fee_cents FROM review_tasks WHERE batch_id=?', (batch_id,)).fetchall()
        if any(t['status'] not in ('ACCEPTED','SKIPPED') for t in tasks):
            raise HTTPException(409, 'All tasks must be accepted or skipped before settlement')
        amount = sum(t['fee_cents'] for t in tasks if t['status'] == 'ACCEPTED')
        if amount > batch['authorized_cents']:
            raise HTTPException(409, 'Application-enforced budget exceeded. No capture attempted.')
        auth_id = batch['paypal_authorization_id']
        request_id = batch['capture_request_id'] if amount > 0 else batch['void_request_id']
        request_id = request_id or stable_id()
        if amount > 0:
            db.execute('UPDATE batches SET capture_request_id=? WHERE id=?', (request_id, batch_id))
        else:
            db.execute('UPDATE batches SET void_request_id=? WHERE id=?', (request_id, batch_id))
    client = paypal_or_503()
    try:
        if amount:
            receipt = client.capture(auth_id, amount, request_id)
            capture_id = receipt.get('id')
            if not capture_id:
                raise HTTPException(502, 'PayPal did not return a capture ID')
            verified = client.show_capture(capture_id)
            if verified.get('status') != 'COMPLETED' or verified.get('amount', {}).get('currency_code') != 'USD' or verified.get('amount', {}).get('value') != f'{Decimal(amount)/100:.2f}':
                raise HTTPException(502, 'Capture not verified as COMPLETED with expected amount')
            with connect() as db:
                db.execute("UPDATE batches SET paypal_capture_id=?, captured_cents=?, payment_status='CAPTURED' WHERE id=?", (capture_id, amount, batch_id))
                log_event(db, batch_id, 'FINAL_CAPTURE_COMPLETED', {'capture_id': capture_id, 'cents': amount})
        else:
            client.void(auth_id, request_id)
            verified = client.show_authorization(auth_id)
            if verified.get('status') != 'VOIDED':
                raise HTTPException(502, 'Authorization was not verified as VOIDED')
            with connect() as db:
                db.execute("UPDATE batches SET payment_status='VOIDED' WHERE id=?", (batch_id,))
                log_event(db, batch_id, 'AUTHORIZATION_VOIDED')
    except PayPalError as err:
        api_error(err)
    return get_batch_state(batch_id)


FRONTEND_BUILD = ROOT.parent / 'frontend' / 'dist'
if FRONTEND_BUILD.is_dir():
    app.mount('/assets', StaticFiles(directory=FRONTEND_BUILD / 'assets'), name='frontend_assets')
    @app.get('/')
    def index():
        return FileResponse(FRONTEND_BUILD / 'index.html')
    @app.get('/review/{path:path}')
    def review_page(path: str):
        return FileResponse(FRONTEND_BUILD / 'index.html')
