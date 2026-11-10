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

def test_line_amounts_ignore_decorative_rows_order_and_formatting():
    a = {'total':'12.00','merchant':'A & B','date':'2026-11-10','line_items':[{'description':'Tea','amount':'12.0'}]}
    b = dict(a,merchant='A B', date='2026/11/10', line_items=[{'description':'Goods'}, {'description':'TEA','amount':'12.00'}])
    assert analyze(a,b) == (False,[])
    b['line_items'][1]['amount'] = '13.00'
    assert 'priced items' in analyze(a,b)[1][0]

def discount_reading(**changes):
    reading = dict(subtotal='245.00', tax='39.69', total='260.19', date='2026-11-10',
                   adjustments=[dict(label='Discount', kind='discount', effect='subtract', amount='24.50')])
    return {**reading, **changes}


def test_discount_receipt_matches_to_minor_unit():
    reading = discount_reading()
    assert analyze(reading, reading) == (False, [])


def test_receipt_explicitly_without_discount():
    reading = discount_reading(adjustments=[], total='284.69')
    assert analyze(reading, reading) == (False, [])


def test_one_cent_error_despite_discount():
    reading = discount_reading(total='260.18')
    assert '260.19' in analyze(reading, reading)[1][0]


def test_missing_discount_amount_is_unresolved():
    reading = discount_reading()
    reading['adjustments'][0]['amount'] = None
    assert analyze(reading, reading) == (True,['Unclear amount or direction for Discount'])


def test_post_discount_tax_and_already_net_subtotal():
    reading = discount_reading(subtotal='220.50')
    reading['adjustments'][0]['effect'] = 'included'
    assert analyze(reading, reading) == (False, [])


def test_equivalent_dates():
    assert analyze(discount_reading(), discount_reading(date='10 Nov 2026')) == (False, [])


def test_review_one_cent_conflict_and_rounding():
    from ai_engine import correction_warnings
    assert decimal_value('1.005') == Decimal('1.01')
    warnings = correction_warnings(discount_reading(),discount_reading(),'260.18')
    assert any('260.19' in w and '260.18' in w for w in warnings)
    assert not correction_warnings(discount_reading(),discount_reading(),'260.19')
