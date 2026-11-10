"""PayPal *Sandbox-only* REST client, modeled after the smoke test that passed."""
import os
import uuid
from decimal import Decimal
from typing import Any

import requests

BASE = 'https://api-m.sandbox.paypal.com'


class PayPalError(RuntimeError):
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


def sandbox_request(method, url, **kwargs):
    try:
        return requests.request(method, url, allow_redirects=False, **kwargs)
    except requests.RequestException:
        raise PayPalError('PayPal Sandbox did not respond. Retry to check the payment status.') from None


class PayPalSandbox:
    def __init__(self):
        self.client_id = os.getenv('PAYPAL_CLIENT_ID', '').strip()
        self.client_secret = os.getenv('PAYPAL_CLIENT_SECRET', '').strip()
        if not self.client_id or not self.client_secret:
            raise PayPalError('Missing PAYPAL_CLIENT_ID or PAYPAL_CLIENT_SECRET in backend/.env')

    @staticmethod
    def _check(response: requests.Response, operation: str) -> dict:
        if not 200 <= response.status_code < 300:
            try:
                raw = response.json()
                extra = ', '.join(f"{d.get('issue', '')}: {d.get('description', '')}" for d in raw.get('details', []))
                message = f"{raw.get('name', 'ERROR')}: {raw.get('message', '')} {extra} (debug_id={raw.get('debug_id','n/a')})"
            except ValueError:
                message = f'HTTP {response.status_code}'
            raise PayPalError(f'{operation} failed: {message}', response.status_code)
        if not response.content:
            return {}
        try:
            return response.json()
        except ValueError:
            return {}

    def token(self) -> str:
        response = sandbox_request('POST',
            f'{BASE}/v1/oauth2/token',
            auth=(self.client_id, self.client_secret),
            data={'grant_type': 'client_credentials'}, timeout=25,
        )
        return self._check(response, 'OAuth token')['access_token']

    def request(self, method: str, path: str, *, data: dict | None = None, request_id: str | None = None) -> dict:
        if not path.startswith('/') or '://' in path:
            raise PayPalError('Invalid PayPal Sandbox path')
        headers = {
            'Authorization': f'Bearer {self.token()}',
            'Content-Type': 'application/json',
            'Prefer': 'return=representation',
        }
        if request_id:
            headers['PayPal-Request-Id'] = request_id
        response = sandbox_request(method, f'{BASE}{path}', headers=headers, json=data, timeout=30)
        return self._check(response, f'{method} {path}')

    def create_order(self, *, batch_id: str, dollars: str, request_id: str, public_url: str) -> dict:
        amount = f'{Decimal(dollars):.2f}'
        payload = {
            'intent': 'AUTHORIZE',
            'purchase_units': [{
                'reference_id': batch_id,
                'custom_id': batch_id[:90],
                'amount': {'currency_code': 'USD', 'value': amount},
                'description': 'HumanBridge human-verification service budget (Sandbox)',
            }],
            'payment_source': {'paypal': {'experience_context': {
                'return_url': public_url.rstrip('/') + f'/?checkout=return&batch={batch_id}',
                'cancel_url': public_url.rstrip('/') + f'/?checkout=cancel&batch={batch_id}',
                'shipping_preference': 'NO_SHIPPING',
                'user_action': 'CONTINUE',
            }}},
        }
        return self.request('POST', '/v2/checkout/orders', data=payload, request_id=request_id)

    def show_order(self, order_id: str) -> dict:
        return self.request('GET', f'/v2/checkout/orders/{order_id}')

    def authorize(self, order_id: str, request_id: str) -> dict:
        return self.request('POST', f'/v2/checkout/orders/{order_id}/authorize', data={}, request_id=request_id)

    def show_authorization(self, auth_id: str) -> dict:
        return self.request('GET', f'/v2/payments/authorizations/{auth_id}')

    def capture(self, auth_id: str, cents: int, request_id: str) -> dict:
        if cents <= 0:
            raise PayPalError('Cannot capture zero or negative dollars')
        return self.request('POST', f'/v2/payments/authorizations/{auth_id}/capture', data={
            'amount': {'currency_code': 'USD', 'value': f'{Decimal(cents) / 100:.2f}'},
            'invoice_id': request_id,
            'final_capture': True,
        }, request_id=request_id)

    def show_capture(self, capture_id: str) -> dict:
        return self.request('GET', f'/v2/payments/captures/{capture_id}')

    def void(self, auth_id: str, request_id: str) -> dict:
        return self.request('POST', f'/v2/payments/authorizations/{auth_id}/void', data={}, request_id=request_id)


def stable_id() -> str:
    return str(uuid.uuid4())
