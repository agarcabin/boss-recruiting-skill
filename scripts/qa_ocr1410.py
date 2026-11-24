"""Isolated real-engine QA with synthetic resume text, never candidate data."""
import argparse
import json
from pathlib import Path
from types import SimpleNamespace
from PIL import Image,ImageDraw,ImageFont
import recruiting_rules
import resume_image_pipeline
import resume_highlight


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=True)
    source=a.output/'synthetic-resume.png'
    image=Image.new('RGB',(1100,400),'white');draw=ImageDraw.Draw(image)
    font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',38)
    for n,line in enumerate(('虚构简历测试','有组装工作经验。','工作时主管过喷漆。','本图仅用于软件验证。')):
        draw.text((30,25+n*85),line,font=font,fill='black')
    image.save(source)
    text=a.output/'resume.ocr.txt';detail=a.output/'resume.ocr.json'
    resume_image_pipeline.rapidocr(SimpleNamespace(image=source,text_output=text,json_output=detail,tile_height=1200,overlap=150))
    body=text.read_text(encoding='utf-8');data=json.loads(detail.read_text(encoding='utf-8'))
    result=dict(hits=recruiting_rules.positive_hits(body,['组装']),negative_hits=recruiting_rules.positive_hits(body,['主管']))
    if not result['hits'] or not result['negative_hits']:raise ValueError('synthetic_keywords_not_recognized')
    marked=resume_highlight.create(dict(image=str(source),ocr_json=str(detail)),result)
    meta=json.loads(Path(marked).with_suffix('.json').read_text(encoding='utf-8'))
    if len(meta['located'])!=2:raise ValueError('synthetic_character_boxes_not_verified')
    print(json.dumps(dict(state='verified',native_characters=sum(len(l.get('characters',[])) for l in data['lines']),marked=marked),ensure_ascii=False))


if __name__=='__main__':main()
