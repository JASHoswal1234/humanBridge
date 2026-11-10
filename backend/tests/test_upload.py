import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from google import genai

import api
from ai_engine import analyze
from demo_data import make_image


@pytest.fixture
def upload(tmp_path, monkeypatch):
    monkeypatch.setattr(api, 'DB', tmp_path / 'receipts.db')
    monkeypatch.setattr(api, 'STORAGE', tmp_path)
    api.init_database()
    monkeypatch.setenv('GEMINI_API_KEY', 'test-only')
    client = TestClient(api.app)
    model = MagicMock()
    monkeypatch.setattr(genai, 'Client', model)
    generate = model.return_value.__enter__.return_value.models.generate_content
    batch = client.post('/api/batches').json()['id']
    url = f'/api/batches/{batch}'
    image = make_image('Sample', '2026-11-10', '10.00', '1.00', '11.00')

    def submit(content=image):
        return client.post(url + '/documents', files={'file': ('receipt.png', content, 'image/png')})
    return submit, generate, lambda: client.get(url).json(), image


def result(total='11.00'):
    data = dict(merchant='Sample', date='2026-11-10', subtotal='10.00', tax='1.00',
                currency=None, adjustments=[], total=total, line_items=[dict(description='Goods', quantity=None, amount='10.00')])
    return SimpleNamespace(text=json.dumps(data), model_version='test-model', response_id='test-response')


@pytest.mark.parametrize('second,reason', [('11.00', None), (None, 'Missing or unreadable total'),
                                           ('12.00', 'Two AI readings disagree on total')])
def test_two_pass_upload_and_refresh(upload, second, reason):
    submit, generate, reload, image = upload
    responses = [result(), result(second)]
    generate.side_effect = responses
    batch = submit().json()
    doc, = batch['documents']
    assert [doc['first'], doc['second']] == [json.loads(r.text) for r in responses]
    calls = [c.kwargs['contents'] for c in generate.call_args_list]
    assert calls[0][0] != calls[1][0]
    assert all(parts[1].inline_data.data == image for parts in calls)
    assert [p['number'] for p in doc['passes']] == [1, 2]
    assert analyze(doc['first'], doc['second']) == (doc['flagged'], doc['reasons'])
    if reason:
        assert reason in doc['reasons']
    assert len(batch['tasks']) == int(bool(reason))
    assert reload() == submit().json() == batch
    assert generate.call_count == 2


@pytest.mark.parametrize('failure', [TimeoutError('private details'), RuntimeError('private details'),
                                      SimpleNamespace(text='{', model_version='test', response_id='bad'),
                                      SimpleNamespace(text='{}', model_version='test', response_id='bad')])
def test_failed_second_pass_can_retry(upload, failure):
    submit, generate, reload, _ = upload
    generate.side_effect = [result(), failure, result(), result()]
    failed = submit()
    assert failed.status_code == 502 and 'private details' not in failed.text
    assert reload()['documents'] == reload()['tasks'] == []
    assert len(submit().json()['documents']) == 1
    assert len(submit().json()['documents']) == 1
    assert generate.call_count == 4


def test_invalid_and_oversized_upload(upload):
    submit, generate, reload, _ = upload
    assert submit(b'invalid').status_code == 400
    assert submit(bytes(5 * 1024 * 1024 + 1)).status_code == 413
    assert reload()['documents'] == []
    generate.assert_not_called()


def test_duplicate_while_first_request_is_processing(upload):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    submit, generate, reload, _ = upload
    started, release = Event(), Event()

    def generate_response(**kwargs):
        started.set()
        assert release.wait(10)
        return result()

    generate.side_effect = generate_response
    with ThreadPoolExecutor(max_workers=1) as pool:
        first = pool.submit(submit)
        try:
            assert started.wait(10)
            assert submit().status_code == 409
        finally:
            release.set()
        assert first.result().status_code == 200
    assert len(reload()['documents']) == 1
    assert generate.call_count == 2


def test_rules_check_both_readings():
    first = json.loads(result().text)
    second = dict(first, merchant='Different shop', tax='2.00', currency='EUR')
    flagged, reasons = analyze(first, second)
    assert flagged
    assert set(reasons) == {'Two AI readings disagree on merchant', 'Two AI readings disagree on tax',
                            'Two AI readings disagree on currency', 'Subtotal + tax does not equal total'}
