"""Synthetic receipt and isolated providers used by the browser settlement check."""
import io
from PIL import Image, ImageDraw, ImageFont
from demo_data import make_image


def receipt():
    image = Image.open(io.BytesIO(make_image('SAMPLE STATIONERY', '2026-11-10', '30.00', '2.40', '30.40')))
    ImageDraw.Draw(image).text((64, 550), 'Discount: -$2.00', font=ImageFont.load_default(size=20), fill='#404b5b')
    output = io.BytesIO()
    image.save(output, format='PNG')
    return output.getvalue()


def serve(port):
    import uvicorn
    import api
    from test_workflow import FakeSandbox
    pp = FakeSandbox()
    api.paypal_or_503 = lambda: pp

    def extract(raw, mime, record):
        import json
        from ai_engine import ExtractedReceipt
        assert raw == receipt()
        reading = ExtractedReceipt(merchant='SAMPLE STATIONERY', date='2026-11-10', currency=None,
                                   subtotal='30.00', tax='2.40', adjustments=[dict(label='Discount',kind='discount',effect='subtract',amount='2.00')], total='30.40', line_items=None).model_dump()
        for number in (1,2):
            record(number,dict(raw=json.dumps(reading if number==1 else dict(reading,total='30.00')),model='test fixture',time=api.now(),response_id=None))
        return reading, dict(reading,total='30.00')

    api.read_receipt = extract
    uvicorn.run(api.app, host='127.0.0.1', port=port, access_log=False)
