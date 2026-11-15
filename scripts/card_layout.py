"""Visual row ordering and visit-local identity; a name is never a unique ID."""
def ordered(cards, tolerance=18):
    rows=[]
    for card in sorted(cards,key=lambda c:(c['bounds']['y'],c['bounds']['x'])):
        if not rows or card['bounds']['y']-rows[-1][0]['bounds']['y'] > tolerance:
            rows.append([card])
        else:rows[-1].append(card)
    return [card for row in rows for card in sorted(row,key=lambda c:c['bounds']['x'])]


def choose(cards, processed):
    history=[p for p in processed if isinstance(p,dict)]
    legacy={p for p in processed if isinstance(p,str)}
    for card in ordered(cards):
        if card['card_runtime'] in legacy:continue
        done=False
        for old in history:
            if card.get('business_id') and card['business_id']==old.get('business_id'):
                done=True;break
            if card['card_runtime']==old.get('card_runtime') and card.get('summary')==old.get('summary'):
                done=True;break
            # Rebuilt controls can only be correlated inside the same viewport
            # at the same position. Never deduplicate by name/summary alone.
            if (not card.get('business_id') and card.get('summary')==old.get('summary')
                and card.get('scroll_percent')==old.get('scroll_percent')
                and abs(card['bounds']['x']-old.get('bounds',{}).get('x',-9999))<3
                and abs(card['bounds']['y']-old.get('bounds',{}).get('y',-9999))<3):
                done=True;break
        if not done:return card
    return None


def receipt(card):
    return {key:card.get(key) for key in ('card_runtime','business_id','summary','bounds','scroll_percent')}
