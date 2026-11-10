"""Fixed synthetic receipt benchmark. Run from any directory with backend requirements installed."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
import io
import json
from pathlib import Path
import random
import sys

from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / 'backend'))
from ai_engine import analyze, decimal_value, read_receipt

SEED = 4317
IDS = list('ABCDEF')
CENT = Decimal('.01')


def save(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf8')


def receipt(code, lines):
    image = Image.new('RGB', (360, 260), 'white')
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=19)
    draw.text((15, 10), f'Sample Shop {code}', fill='black', font=font)
    for index, line in enumerate(['10 Nov 2026', *lines]):
        draw.text((15, 43+index*31), line, fill='black', font=font)
    return image


def generate():
    rng = random.Random(SEED)
    sheet = Image.new('RGB',(1080,520),'white')
    labels = {}
    for i, code in enumerate(IDS):
        subtotal = Decimal(rng.randint(500, 9000))/100
        discount = (subtotal/10).quantize(CENT,ROUND_HALF_UP) if i % 2 else Decimal(0)
        tax = ((subtotal-discount)*Decimal('.08')).quantize(CENT,ROUND_HALF_UP)
        total = subtotal-discount+tax
        lines = [f'Subtotal   USD {subtotal:.2f}']
        if discount:
            lines.append(f'Discount      -{discount:.2f}')
        lines.extend([f'Tax             {tax:.2f}',f'TOTAL      USD {total:.2f}'])
        image = receipt(code,lines)
        if i in (2,5):  # Fixed partial occlusion. Labels remain the original printed totals.
            y=43+len(lines)*31
            ImageDraw.Draw(image).rectangle((143,y,166,y+26),fill='#666666')
        sheet.paste(image,(i%3*360,i//3*260))
        image.save(ROOT/f'{code}.png')
        labels[code]=f'{total:.2f}'
    sheet.save(ROOT/'review-sheet.png')
    save(ROOT/'labels.json',labels)


def extract(code):
    raw=(ROOT/f'{code}.png').read_bytes()
    evidence=[]
    readings=read_receipt(raw,'image/png',lambda n,e:evidence.append(e))
    return dict(image_sha256=sha256(raw).hexdigest(),readings=readings,
                passes=[{k:e[k] for k in ('model','time','response_id','prompt')} for e in evidence])


def collect():
    path=ROOT/'predictions.json'
    results=json.loads(path.read_text()) if path.exists() else {}
    for code,row in results.items():
        if sha256((ROOT/f'{code}.png').read_bytes()).hexdigest()!=row['image_sha256']:
            raise ValueError('Image differs from frozen prediction')
    missing=[c for c in IDS if c not in results]
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures={c:pool.submit(extract,c) for c in missing}
        for code,future in futures.items():
            try:
                results[code]=future.result()
            except Exception as err:
                print(code,'failed:',type(err).__name__,getattr(err,'code',''))
                continue
            save(path,results)
            print(code,'recorded',flush=True)
    if set(results)!=set(IDS):
        raise SystemExit('Incomplete collection. Retry to resume.')


def score(human_path, output):
    labels=json.loads((ROOT/'labels.json').read_text())
    predictions=json.loads((ROOT/'predictions.json').read_text())
    humans=json.loads(human_path.read_text()) if human_path else None
    if humans is not None and (set(humans)!=set(IDS) or any(v is not None and decimal_value(v) is None for v in humans.values())):
        raise ValueError('Provide one numeric total or null for each receipt A-F')
    readings={code:predictions[code]['readings'] for code in IDS}
    selected=[code for code in IDS if analyze(*readings[code])[0]]
    random_ids=random.Random(SEED).sample(IDS,len(selected))
    rows=[]
    for name,review in [('AI only',[]),('Random',random_ids),('Full',IDS),('Selective',selected)]:
        errors={c for c in IDS if decimal_value(readings[c][0]['total'])!=Decimal(labels[c])}
        detected=errors.intersection(review)
        corrected = sum(decimal_value(humans[c])==Decimal(labels[c]) for c in detected) if humans is not None or not detected else None
        introduced = (sum(humans[c] is not None and decimal_value(humans[c])!=Decimal(labels[c]) for c in set(review)-errors)
                      if humans is not None else (0 if not review else None))
        rows.append(dict(policy=name,cases=review,initial_errors=len(errors),errors_detected=len(detected),
                         errors_corrected=corrected,errors_introduced=introduced,reviews=len(review),
                         abstentions=sum(humans[c] is None for c in review) if humans is not None else None,
                         estimated_spend_usd=f'{Decimal(len(review))*Decimal(".75"):.2f}',
                         corrected_per_review=corrected/len(review) if review and corrected is not None else None))
    paired_matches=sum(all(decimal_value(r['total'])==Decimal(labels[c]) for r in readings[c]) for c in IDS)
    report=dict(receipts=len(IDS),paired_matches=paired_matches,seed=SEED,review_source='AI-assisted visual transcription',policies=rows)
    print(json.dumps(report,indent=2))
    if output:
        save(output,report)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['generate','collect','score','showcase'])
    parser.add_argument('--human',type=Path)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    load_dotenv(ROOT.parent/'backend'/'.env')
    if args.action=='generate': generate()
    elif args.action=='collect': collect()
    elif args.action=='score': score(args.human,args.output)
    else:
        buf=io.BytesIO()
        receipt('Showcase',['Subtotal   INR 245.00','Discount      -24.50','Tax             39.69','TOTAL      INR 260.19']).save(buf,format='PNG')
        readings=read_receipt(buf.getvalue(),'image/png',lambda n,e:print(n,e['model'],e['response_id']))
        print(json.dumps(readings),analyze(*readings))
