"""Complete a card-local visual colleague check when UIA exposes an opaque icon."""
import argparse
import json
import re
from pathlib import Path


def complete(observation,state,evidence,image):
    if state not in ('present','absent') or not evidence.strip():
        raise ValueError('real_visual_state_and_evidence_required')
    if not Path(image).is_file(): raise ValueError('card_image_missing')
    result=dict(observation);card=dict(result.get('card',{}))
    card['coworker_contact']=dict(state=state,lookup_completed=True,evidence=evidence,source='local_card_visual',image=str(Path(image).resolve()))
    card.update(advantage='',expectation='')
    if state=='absent':
        raw=result.get('raw_text','')
        for field,label,stop in (('advantage','优势','期望'),('expectation','期望','优势|打招呼|继续沟通')):
            match=re.search(label+r'[：:\s]*(.*?)(?='+stop+r'|$)',raw,re.S)
            if match:card[field]=match.group(1).strip()
    result['card']=card
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,required=True);p.add_argument('--image',type=Path,required=True)
    p.add_argument('--visual-state',choices=('present','absent'),required=True);p.add_argument('--evidence',required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=complete(json.loads(a.input.read_text(encoding='utf-8-sig')),a.visual_state,a.evidence,a.image)
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result['card']['coworker_contact'],ensure_ascii=False))


if __name__=='__main__':main()
