from decimal import Decimal

from ai_engine import analyze, decimal_value


def test_consistent_receipt_does_not_escalate():
    receipt = {'subtotal': '10.00', 'tax': '1.00', 'total': '11.00'}
    assert analyze(receipt, receipt) == (False, [])


def test_disagreement_flags_receipt():
    first = {'subtotal': '20', 'tax': '2', 'total': '21'}
    second = {'subtotal': '20', 'tax': '2', 'total': '22'}
    flagged, reasons = analyze(first, second)
    assert flagged
    assert 'Two AI readings disagree on total' in reasons
    assert 'Subtotal + tax does not equal total' in reasons


def test_missing_amount_flags_receipt():
    first = {'total': None}
    second = {'total': '18.45'}
    flagged, reasons = analyze(first, second)
    assert flagged
    assert 'Missing or unreadable total' in reasons


def test_decimal_cleanup():
    assert decimal_value('USD $1,250.45') == Decimal('1250.45')
