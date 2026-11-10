"""Separate fixed acquisition challenge. Run once in a clean directory to collect all cases."""
from hashlib import sha256
from pathlib import Path
import json

from PIL import Image, ImageFilter, ImageDraw
from benchmark import ROOT, analyze, load_dotenv, read_receipt, receipt, save

OUT = ROOT / 'challenge'
CASES = [
    ('blur', ['Subtotal USD 18.00', 'Tax 1.44', 'TOTAL USD 19.44'], '19.44'),
    ('cropped', ['Subtotal USD 47.50', 'Tax 3.80', 'TOTAL USD 51.30'], '51.30'),
    ('fold', ['Subtotal USD 62.00', 'Discount -6.20', 'Tax 4.46', 'TOTAL USD 60.26'], '60.26'),
]


def main():
    load_dotenv(ROOT.parent / 'backend' / '.env')
    OUT.mkdir(exist_ok=True)
    saved = OUT / 'results.json'
    results = json.loads(saved.read_text()) if saved.exists() else {}
    for name, lines, label in CASES:
        image = receipt(name.title(), lines)
        if name == 'blur':
            image = image.resize((180, 130), Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(0.8))
        elif name == 'cropped':
            image = image.crop((0, 0, 360, 131))
        else:
            ImageDraw.Draw(image).polygon([(135, 65), (161, 65), (191, 259), (162, 259)], fill='#dedbd5')
        path = OUT / (name + '.png')
        image.save(path)
        raw = path.read_bytes()
        digest = sha256(raw).hexdigest()
        if name in results:
            assert results[name]['sha256'] == digest
            continue
        evidence = []
        readings = read_receipt(raw, 'image/png', lambda n, e: evidence.append(
            {k: e[k] for k in ('response_id', 'model', 'time', 'prompt')}))
        selected, reasons = analyze(*readings)[:2]
        results[name] = dict(label=label, sha256=digest, readings=readings, passes=evidence,
                             selected=bool(selected), findings=reasons)
        save(saved, results)
        print(name, [r['total'] for r in readings], selected, reasons, flush=True)


if __name__ == '__main__':
    main()
