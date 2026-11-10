import pytest
import api
from paypal_client import PayPalError
from fastapi.testclient import TestClient

from api import app

client = TestClient(app)


def test_demo_batch_and_reviewer_submission():
    response = client.post('/api/batches/demo')
    assert response.status_code == 200, response.text
    data = response.json()
    assert data['data_mode'] == 'scripted_demo'
    assert len(data['documents']) == 4
    assert len(data['tasks']) == 3
    assert data['payment_status'] == 'NOT_STARTED'
    assert data['paypal_approval_url'] is None
    first = data['tasks'][0]
    task_id, token = first['id'], first['review_token']
    unauthorized = client.get(f'/api/tasks/{task_id}', params={'token': 'wrong'})
    assert unauthorized.status_code == 404
    details = client.get(f'/api/tasks/{task_id}', params={'token': token}).json()
    assert details['crop_url'].endswith('-crop.png')
    assert client.post(f'/api/tasks/{task_id}/submit', json={'token': token, 'value': '32.40'}).status_code == 200
    updated = client.get(f'/api/tasks/{task_id}', params={'token': token}).json()
    assert updated['status'] == 'SUBMITTED'
    # Requester may not mark submitted work accepted until the funding authorization is verified.
    assert client.post(f"/api/batches/{data['id']}/tasks/{task_id}/accept").status_code == 409
    # Not yet funded => no settlement.
    assert client.post(f"/api/batches/{data['id']}/payment/settle").status_code == 409

class FakeSandbox:
    """Mock PayPal at API boundary; does not prove an external Sandbox integration."""
    def create_order(self, *, batch_id, dollars, request_id, public_url):
        self.batch_id = batch_id
        self.auth_status = None
        self.capture_calls = 0
        assert dollars == '5.00' and request_id
        return {'id': 'ORDER-MOCK', 'links': [{'rel':'approve', 'href':'https://www.sandbox.paypal.com/checkoutnow?token=ORDER-MOCK'}]}
    def show_order(self, order_id):
        assert order_id == 'ORDER-MOCK'
        return {'id':order_id,'intent':'AUTHORIZE','status':'COMPLETED' if self.auth_status else 'APPROVED',
                'purchase_units':[{'reference_id':self.batch_id,'amount':{'currency_code':'USD','value':'5.00'},
                                   'payments':{'authorizations':[{'id':'AUTH-MOCK'}] if self.auth_status else []}}]}
    def authorize(self, order_id, request_id):
        assert request_id
        self.auth_status = 'CREATED'
        return self.show_order(order_id)
    def capture(self, auth_id, cents, request_id):
        assert auth_id == 'AUTH-MOCK' and request_id and cents > 0
        self.capture_calls += 1
        self.invoice_id = request_id
        self.amount = cents
        self.auth_status = 'CAPTURED'
        return {'id':'CAPTURE-MOCK','status':'COMPLETED'}
    def show_capture(self, capture_id):
        assert capture_id == 'CAPTURE-MOCK'
        return {'id':capture_id,'invoice_id':self.invoice_id,'status':'COMPLETED','amount':{'currency_code':'USD','value':f'{self.amount//100}.{self.amount%100:02d}'}}
    def void(self, auth_id, request_id):
        assert auth_id == 'AUTH-MOCK' and request_id
        self.auth_status = 'VOIDED'
        return {}
    def show_authorization(self, auth_id):
        return {'id':auth_id,'status':self.auth_status,'amount':{'currency_code':'USD','value':'5.00'}}


def test_end_to_end_funded_and_captured(monkeypatch):
    import api as app_module
    sandbox = FakeSandbox()
    monkeypatch.setattr(app_module, 'paypal_or_503', lambda: sandbox)
    data=client.post('/api/batches/demo').json()
    bid=data['id']
    order=client.post(f'/api/batches/{bid}/payment/create')
    assert order.status_code == 200 and order.json()['order_id'] == 'ORDER-MOCK'
    authorized=client.post(f'/api/batches/{bid}/payment/authorize')
    assert authorized.status_code == 200, authorized.text
    assert authorized.json()['payment_status']=='AUTHORIZED'
    for i,task in enumerate(data['tasks']):
        t=task['id']
        submitted=client.post(f'/api/tasks/{t}/submit', json={'token':task['review_token'], 'value':f'{20+i}.00'})
        assert submitted.status_code==200
        assert client.post(f'/api/batches/{bid}/tasks/{t}/accept',json={'reason':'Reviewed printed total'}).status_code==200
    completed=client.post(f'/api/batches/{bid}/payment/settle')
    assert completed.status_code==200, completed.text
    assert completed.json()['captured_cents']==225
    assert completed.json()['paypal_capture_id']=='CAPTURE-MOCK'
    # The API's terminal state prevents a second capture request.
    assert client.post(f'/api/batches/{bid}/payment/settle').json()['captured_cents']==225


def test_end_to_end_authorization_void(monkeypatch):
    import api as app_module
    sandbox = FakeSandbox()
    monkeypatch.setattr(app_module, 'paypal_or_503', lambda: sandbox)
    data=client.post('/api/batches/demo').json()
    bid=data['id']
    client.post(f'/api/batches/{bid}/payment/create')
    client.post(f'/api/batches/{bid}/payment/authorize')
    for t in data['tasks']:
        result=client.post(f'/api/batches/{bid}/tasks/{t["id"]}/skip')
        assert result.status_code==200, result.text
    finished=client.post(f'/api/batches/{bid}/payment/settle')
    assert finished.status_code==200, finished.text
    assert finished.json()['payment_status']=='VOIDED'
    assert finished.json()['captured_cents']==0

def test_scoped_access_and_revision(monkeypatch):
    data = client.post('/api/batches/demo').json()
    bid = data['id']
    task, other = data['tasks'][:2]
    url = f"/api/tasks/{task['id']}"
    decision = f"/api/batches/{bid}/tasks/{task['id']}"
    outsider = TestClient(app)
    full = data['documents'][0]['image_url']
    assert client.get(full).status_code == 200
    assert outsider.get(full).status_code == outsider.get(f'/api/batches/{bid}').status_code == 403
    assert outsider.post(decision+'/accept').status_code == 403
    assert outsider.get('/uploads/'+data['documents'][0]['id']+'.png').status_code == 404
    assert outsider.get(url+'/receipt-crop.png').status_code == 404
    detail = outsider.get(url, headers={'X-Review-Token':task['review_token']}).json()
    assert 'batch_id' not in detail
    assert outsider.get(detail['crop_url']).status_code == 200
    assert outsider.get(f"/api/tasks/{other['id']}/receipt-crop.png").status_code == 404
    assert client.get(f'/api/batches/{bid}/images/%2e%2e%2f.env').status_code != 200
    body = {'token':task['review_token'],'value':'32.40'}
    for invalid in ('NaN','1e3','-1','3.999'):
        assert outsider.post(url+'/submit',json=dict(body,value=invalid)).status_code == 400
    assert client.post(decision+'/revise').status_code == 409
    for _ in range(2):
        assert outsider.post(url+'/submit',json=body).json()['check_status'] == 'CHECKS_PASSED'
    assert client.post(decision+'/revise').status_code == 200
    assert outsider.post(url+'/submit',json=body).status_code == 409
    assert outsider.post(url+'/submit',json=dict(body,revision=1)).status_code == 200
    assert client.post(decision+'/skip').status_code == 200
    assert outsider.post(url+'/submit',json=dict(body,revision=1)).status_code == 409


@pytest.fixture
def funded(monkeypatch):
    pp = FakeSandbox()
    monkeypatch.setattr(api,'paypal_or_503',lambda:pp)
    batch = client.post('/api/batches/demo').json()
    base = '/api/batches/'+batch['id']
    assert client.post(base+'/payment/create').status_code == 200
    assert client.post(base+'/payment/authorize').status_code == 200
    for t in batch['tasks']:
        assert client.post('/api/tasks/'+t['id']+'/submit',json={'token':t['review_token'],'value':'1.00'}).status_code == 200
        path = base+'/tasks/'+t['id']+'/accept'
        assert client.post(path).status_code == 422
        result = client.post(path,json={'reason':'Inspected source receipt'})
        assert result.status_code == 200
        saved = next(task for task in client.get(base).json()['tasks'] if task['id'] == t['id'])
        assert saved['acceptance_reason'] == 'Inspected source receipt' and saved['correction_warnings']
        event = next(e for e in result.json()['events'] if e['kind']=='REVIEW_ACCEPTED')
        assert event['details']['reason'] == saved['acceptance_reason']
        assert event['details']['warnings'] == saved['correction_warnings']
        assert client.post(path).status_code == 409
    return pp,base,batch


def test_capture_readback_retry(funded,monkeypatch):
    pp,base,_ = funded
    read = pp.show_capture
    def unavailable(_):
        raise PayPalError('Sandbox temporarily unavailable')
    monkeypatch.setattr(pp,'show_capture',unavailable)
    assert client.post(base+'/payment/settle').status_code == 502
    state = client.get(base).json()
    assert state['payment_status'] == 'SETTLING' and state['captured_cents'] == 0
    monkeypatch.setattr(pp,'show_capture',read)
    for _ in range(2):
        assert client.post(base+'/payment/settle').json()['captured_cents'] == 225
    assert pp.capture_calls == 1


def test_settlement_limits_and_authorization_binding(funded):
    pp,base,batch = funded
    with api.connect() as db:
        db.execute('UPDATE batches SET verified_cents=100 WHERE id=?',(batch['id'],))
    assert client.post(base+'/payment/settle').status_code == 409
    with api.connect() as db:
        db.execute("UPDATE batches SET verified_cents=500,paypal_authorization_id='UNRELATED' WHERE id=?",(batch['id'],))
    assert client.post(base+'/payment/settle').status_code == 409
    assert pp.capture_calls == 0

def test_uncertain_capture_reuses_key_and_reads_order(funded,monkeypatch):
    pp,base,_ = funded
    original_capture = pp.capture
    keys = []
    def delayed_response(auth_id,cents,request_id):
        keys.append(request_id)
        if len(keys)==1:
            original_capture(auth_id,cents,request_id)
            raise PayPalError('Response lost after capture')
        assert keys == [request_id,request_id]
        return {'id':'CAPTURE-MOCK'}
    monkeypatch.setattr(pp,'capture',delayed_response)
    assert client.post(base+'/payment/settle').status_code == 502
    assert client.post(base+'/payment/settle').json()['captured_cents'] == 225
    assert pp.capture_calls == 1


def test_wrong_capture_amount_never_becomes_settled(funded,monkeypatch):
    pp,base,_ = funded
    read=pp.show_capture
    def mismatch(cid):
        result=read(cid)
        result['amount']['value']='2.26'
        return result
    monkeypatch.setattr(pp,'show_capture',mismatch)
    for _ in range(2):
        assert client.post(base+'/payment/settle').status_code == 502
    assert client.get(base).json()['captured_cents']==0 and pp.capture_calls==1

def test_checkout_token_and_authorization_guard(monkeypatch):
    pp = FakeSandbox()
    monkeypatch.setattr(api,'paypal_or_503',lambda:pp)
    batch = client.post('/api/batches/demo').json()
    base = f"/api/batches/{batch['id']}/payment"
    assert client.post(base+'/create').status_code == 200
    assert client.get(base+'/approval?token=WRONG').status_code == 409
    assert client.post(base+'/authorize?token=WRONG').status_code == 409
    remote = pp.show_order
    monkeypatch.setattr(pp,'show_order',lambda oid:dict(remote(oid),status='PAYER_ACTION_REQUIRED'))
    assert client.get(base+'/approval?token=ORDER-MOCK').json()['status'] == 'PAYER_ACTION_REQUIRED'
    assert client.post(base+'/authorize').status_code == 409
    assert not pp.auth_status
    monkeypatch.setattr(pp,'show_order',remote)
    for _ in range(2):
        assert client.get(base+'/approval?token=ORDER-MOCK').json()['status'] == 'APPROVED'
    original = pp.authorize
    posts = []
    def overlapping(order_id,key):
        posts.append(key)
        assert client.post(base+'/authorize').status_code == 409
        return original(order_id,key)
    monkeypatch.setattr(pp,'authorize',overlapping)
    for _ in range(2):
        assert client.post(base+'/authorize?token=ORDER-MOCK').json()['payment_status'] == 'AUTHORIZED'
    assert len(posts) == 1

def test_missing_checkout_order_is_read_only(monkeypatch):
    pp = FakeSandbox()
    monkeypatch.setattr(api,'paypal_or_503',lambda:pp)
    batch = client.post('/api/batches/demo').json()
    base = f"/api/batches/{batch['id']}/payment"
    assert client.post(base+'/create').status_code == 200
    def missing(order_id):
        assert order_id == 'ORDER-MOCK'
        raise PayPalError('RESOURCE_NOT_FOUND',404)
    monkeypatch.setattr(pp,'show_order',missing)
    assert client.get(base+'/approval?token=ORDER-MOCK').json() == {'status':'UNAVAILABLE'}
    saved = client.get(f"/api/batches/{batch['id']}").json()
    assert saved['paypal_order_id'] == 'ORDER-MOCK'
    assert saved['paypal_authorization_id'] is None and saved['captured_cents'] == 0

def test_render_origin_secures_cookie_and_supplies_checkout_origin(monkeypatch):
    monkeypatch.delenv('APP_PUBLIC_URL', raising=False)
    monkeypatch.setenv('RENDER_EXTERNAL_URL', 'https://example.onrender.com')
    sandbox = FakeSandbox()
    observed = {}
    original = sandbox.create_order
    def create_order(**kwargs):
        observed.update(kwargs)
        return original(**kwargs)
    monkeypatch.setattr(sandbox, 'create_order', create_order)
    monkeypatch.setattr(api, 'paypal_or_503', lambda: sandbox)
    with TestClient(app, base_url='https://example.onrender.com') as browser:
        response = browser.post('/api/batches/demo')
        assert 'Secure' in response.headers['set-cookie']
        batch = response.json()['id']
        assert browser.post(f'/api/batches/{batch}/payment/create').status_code == 200
        assert observed['public_url'] == 'https://example.onrender.com'
    monkeypatch.setenv('APP_PUBLIC_URL', 'https://custom.example/')
    assert api.public_origin() == 'https://custom.example'
