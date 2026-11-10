"""Clearly scripted/synthetic examples for local review/payment walkthroughs."""
import io
from PIL import Image, ImageDraw, ImageFont

DEMO = [
    ('COASTLINE COFFEE', '2026-11-10', '12.00', '1.20', '13.20', '13.20', '13.20'),
    ('NORTH STATIONERY', '2026-11-10', '30.00', '2.40', '32.40', '82.40', '32.40'),
    ('BLUE BICYCLE', '2026-11-10', '18.00', '1.80', '19.80', '19.30', '19.30'),
    ('HARBOUR GROCERY', '2026-11-10', '20.00', '2.00', '22.00', '', '22.00'),
]


def make_image(name, date, subtotal, tax, total) -> bytes:
    image = Image.new('RGB', (600, 810), '#f7f6f2')
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=26) if hasattr(ImageFont, 'load_default') else ImageFont.load_default()
    small = ImageFont.load_default(size=20) if hasattr(ImageFont, 'load_default') else ImageFont.load_default()
    draw.text((64, 95), name, fill='#202737', font=font)
    draw.text((64, 165), date, fill='#404b5b', font=small)
    draw.line((58, 225, 544, 225), fill='#b8bcc5', width=2)
    draw.text((64, 330), 'Goods / Services', fill='#202737', font=small)
    draw.text((64, 515), f'Subtotal: ${subtotal}', fill='#202737', font=small)
    draw.text((64, 590), f'Tax: ${tax}', fill='#202737', font=small)
    draw.text((64, 670), f'TOTAL: ${total}', fill='#202737', font=font)
    result = io.BytesIO()
    image.save(result, 'PNG')
    return result.getvalue()
