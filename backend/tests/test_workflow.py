import os
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
    def create_order(self, *, batch_id, dollars, request_id):
        assert dollars == '5.00' and request_id
        return {'id': 'ORDER-MOCK', 'links': [{'rel':'approve', 'href':'https://www.sandbox.paypal.com/checkoutnow?token=ORDER-MOCK'}]}
    def show_order(self, order_id):
        assert order_id == 'ORDER-MOCK'
        return {'status':'APPROVED','purchase_units':[{'amount':{'currency_code':'USD','value':'5.00'}}]}
    def authorize(self, order_id, request_id):
        assert request_id
        return {'purchase_units':[{'payments':{'authorizations':[{'id':'AUTH-MOCK'}]}}]}
    def capture(self, auth_id, cents, request_id):
        assert auth_id == 'AUTH-MOCK' and request_id and cents == 225
        return {'id':'CAPTURE-MOCK','status':'COMPLETED'}
    def show_capture(self, capture_id):
        assert capture_id == 'CAPTURE-MOCK'
        return {'status':'COMPLETED','amount':{'currency_code':'USD','value':'2.25'}}
    def void(self, auth_id, request_id):
        assert auth_id == 'AUTH-MOCK' and request_id
        return {}
    def show_authorization(self, auth_id):
        return {'status':'VOIDED'}


def test_end_to_end_funded_and_captured(monkeypatch):
    import api as app_module
    monkeypatch.setattr(app_module, 'paypal_or_503', lambda: FakeSandbox())
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
        assert client.post(f'/api/batches/{bid}/tasks/{t}/accept').status_code==200
    completed=client.post(f'/api/batches/{bid}/payment/settle')
    assert completed.status_code==200, completed.text
    assert completed.json()['captured_cents']==225
    assert completed.json()['paypal_capture_id']=='CAPTURE-MOCK'
    # The API's terminal state prevents a second capture request.
    assert client.post(f'/api/batches/{bid}/payment/settle').json()['captured_cents']==225


def test_end_to_end_authorization_void(monkeypatch):
    import api as app_module
    monkeypatch.setattr(app_module, 'paypal_or_503', lambda: FakeSandbox())
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
