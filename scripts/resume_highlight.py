"""Draw only scored keyword spans using native OCR character geometry."""
import hashlib
import json
from pathlib import Path
import re


def spans(text, hits, negative=False):
    result=[]
    for hit in hits:
        word=hit.get('word') or hit.get('company')
        quote=hit.get('quote','')
        if not word or not quote:
            continue
        for context in re.finditer(re.escape(quote), text):
            for term in re.finditer(re.escape(word),quote,re.I):
                prefix=quote[max(0,term.start()-14):term.start()]
                suffix=quote[term.end():term.end()+8]
                # Never paint an explicitly negated occurrence merely because
                # another occurrence of the same word contributed to the score.
                if re.search(r'(?i)\b(?:no|not|never|without)\b|没(?:有|做过|干过|接触过)?|未曾?|不(?:曾|做|想|考虑|接受|愿意|会|熟悉|负责|涉及|从事)|无|缺乏|拒绝',prefix):
                    continue
                if re.match(r'(?:工作)?(?:经验)?(?:没有|不足|为零|不具备|无经验)',suffix):
                    continue
                result.append(dict(word=word,start=context.start()+term.start(),end=context.start()+term.end(),negative=negative))
    return result


def geometry(ocr, targets):
    text='\n'.join(line['text'] for line in ocr['lines'])
    offsets={};start=0
    for line in ocr['lines']:
        chars=line.get('characters',[])
        compact=''.join(c['text'] for c in chars)
        original=line['text']
        if re.sub(r'\s+','',compact).casefold() == re.sub(r'\s+','',original).casefold():
            indices=[i for i,c in enumerate(original) if not c.isspace()]
            cursor=0
            for char in chars:
                for letter in char['text']:
                    if letter.isspace():continue
                    if cursor < len(indices) and char.get('score',0) >= .8:
                        offsets[start+indices[cursor]]=char['box']
                    cursor+=1
        start+=len(original)+1
    located=[];missing=[]
    for item in targets:
        needed=[i for i in range(item['start'],item['end']) if not text[i].isspace()]
        if not needed or any(i not in offsets for i in needed):
            missing.append(dict(item,reason='无法精确定位'))
            continue
        # Separate boxes across wrapped lines instead of painting the page.
        boxes=[]
        for i in needed:
            box=offsets[i]
            if boxes and abs(boxes[-1][1]-box[1]) < max(3,(box[3]-box[1])/2):
                old=boxes[-1];boxes[-1]=[min(old[0],box[0]),min(old[1],box[1]),max(old[2],box[2]),max(old[3],box[3])]
            else:boxes.append(list(box))
        located.append(dict(item,boxes=boxes))
    return located,missing


def create(evidence, result):
    from PIL import Image,ImageDraw,ImageFont
    source=Path(evidence['image']);data=Path(evidence['ocr_json'])
    ocr=json.loads(data.read_text(encoding='utf-8-sig'))
    text='\n'.join(line['text'] for line in ocr['lines'])
    targets=spans(text,result.get('hits',[]))+spans(text,result.get('negative_hits',[]),True)
    located,missing=geometry(ocr,targets)
    # A missing quote is also visible in the legend rather than silently lost.
    found={t['word'] for t in targets}
    for negative,key in ((False,'hits'),(True,'negative_hits')):
        for h in result.get(key,[]):
            word=h.get('word') or h.get('company')
            if word and word not in found:missing.append(dict(word=word,negative=negative,reason='无法精确定位'))
    original=Image.open(source).convert('RGB')
    legend=list(dict.fromkeys((m['word'],m['negative']) for m in missing))
    canvas=Image.new('RGB',(original.width+380 if legend else original.width,max(original.height,50+32*len(legend))),'white')
    canvas.paste(original,(0,0));draw=ImageDraw.Draw(canvas)
    try:font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',18)
    except OSError:font=ImageFont.load_default()
    # Positive first: red remains visible if the two scored spans overlap.
    for item in sorted(located,key=lambda x:x['negative']):
        for box in item['boxes']:
            draw.rectangle(box,outline='#d62828' if item['negative'] else '#16803a',width=3)
    for n,(word,negative) in enumerate(legend):
        draw.text((original.width+12,16+n*32),word+'（无法精确定位）',fill='#d62828' if negative else '#16803a',font=font)
    target=source.with_name(source.stem+'-marked.png');canvas.save(target)
    meta=dict(schema='resume-highlights/v1',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
              ocr_sha256=hashlib.sha256(data.read_bytes()).hexdigest(),scoring=result,located=located,unlocated=missing)
    target.with_suffix('.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    return str(target)
