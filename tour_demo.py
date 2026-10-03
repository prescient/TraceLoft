"""Opt-in, repeatable test data anchored to published averages; never player measurements."""
import copy
import json
import random
import uuid
from pathlib import Path
from collection import CollectionSession
from equipment import new_bag, selection
from putting import timestamp

KEY = 'tour_demo_pack.v1'
SOURCE = json.loads((Path(__file__).parent/'data/tour_averages.v1.json').read_text('utf-8'))
SAMPLES = 12


def profiles():
    result = {r['club']: dict(r, basis='published_average') for r in SOURCE['clubs']}
    for label, carry, speed, launch, spin in [('GW',125,95,27,9600),('SW',108,85,31,9800),('LW',92,75,35,10000)]:
        result[label] = dict(club=label, carry_yd=carry, ball_speed_mph=speed, launch_deg=launch,
                             spin_rpm=spin, apex_yd=29, descent_deg=54, basis='illustrative_wedge')
    return result


def sample_event(session, eq, profile, seq, intent=None):
    rng=random.Random(f'{KEY}:{eq["club_label"]}:{intent}:{seq}')
    factor={None:1,'Full':1,'Three-quarter':.78,'Half':.55}[intent]
    carry=profile['carry_yd']*factor
    actual=max(5,carry+rng.gauss(0,max(2,carry*.035)))
    # Test-only variation and rollout. Neither is a published Tour statistic.
    roll=18 if eq['club_label']=='Driver' else 10 if carry>210 else 5 if carry>150 else 2
    vals=dict(carry=round(actual,1),total=round(actual+max(0,roll+rng.gauss(0,1)),1),
        offline=round(rng.gauss(0,max(2,carry*.035)),1),
        ball_speed=round(profile['ball_speed_mph']*factor**.6+rng.gauss(0,1.5),1),
        launch_ang=round(profile['launch_deg']+rng.gauss(0,1),1),launch_dir=round(rng.gauss(0,1),1),
        total_spin=round(profile['spin_rpm']*factor**.35+rng.gauss(0,150)),spin_axis=round(rng.gauss(0,3),1),
        peak_height=round(profile['apex_yd']*3*factor+rng.gauss(0,2),1),
        descent_ang=round(profile['descent_deg']+rng.gauss(0,1),1))
    return dict(kind='record',session_id='tour-demo-'+session.data['id'],seq=seq,receipt_id=uuid.uuid4().hex,
        producer_id=KEY,result='validated',captured_at=timestamp(),simulated=True,
        practice_session_id=session.data['id'],equipment_selection=copy.deepcopy(eq),
        collection_context={'swing_label':intent},vals=vals,
        source_configuration=dict(acquisition='synthetic_demo',generator=KEY,reference=SOURCE['id'],
            basis=profile['basis'] if intent in (None,'Full') else 'illustrative_partial_wedge',
            source=SOURCE['source'],dispersion='invented test variation',total='invented rollout'),
        note='SIMULATED: Tour averages anchor full swings; dispersion, rollout and partial wedges are invented.')


def install(service):
    """One atomic pack. Never takes capture ownership or changes an active selection."""
    store=service.store
    if not store: raise ValueError('SQLite storage is required.')
    with store.transaction():
        previous=store.connection.execute('SELECT value FROM metadata WHERE key=?',(KEY,)).fetchone()
        if previous: return dict(json.loads(previous[0]),already_loaded=True)
        catalog=copy.deepcopy(service.equipment)
        if len(catalog['bags'])>=50: raise ValueError('The bag catalog is full.')
        bag=new_bag('Tour reference · DEMO')
        refs=profiles()
        bag['clubs']=[dict(id=uuid.uuid4().hex,label=label) for label in refs]+[dict(id=uuid.uuid4().hex,label='Putter')]
        catalog['bags'].append(bag);catalog['revision']+=1
        store.save_equipment_catalog(catalog)
        ids=[]
        for wedge in (False,True):
            clubs=[c for c in bag['clubs'] if c['label'] in refs and (not wedge or c['label'] in ('PW','GW','SW','LW'))]
            session=CollectionSession(service.root/'practice_sessions',catalog,bag['id'],[c['id'] for c in clubs],
                samples=SAMPLES,demo=True,store=store,swing_labels=['Half','Three-quarter','Full'] if wedge else None)
            session.data['demo_reference']=dict(id=KEY,reference=SOURCE,assumptions='Synthetic variation/rollout; partial carry factors .55/.78/1. Not player or Tour dispersion.')
            for club in clubs:
                eq=selection(catalog,bag['id'],club['id'])
                for intent in (['Half','Three-quarter','Full'] if wedge else [None]):
                    for _ in range(SAMPLES):
                        event=sample_event(session,eq,refs[club['label']],len(session.data['shots'])+1,intent)
                        store.ingest(event,provenance='synthetic_demo')
                        if not session.add(event): raise ValueError('Demo sample was not accepted.')
            session.finish();ids.append(session.data['id'])
        result=dict(bag_id=bag['id'],session_ids=ids,shot_count=(len(refs)+12)*SAMPLES,source=SOURCE['source'])
        store.connection.execute('INSERT INTO metadata VALUES(?,?)',(KEY,json.dumps(result)))
    service.equipment=catalog
    service.sessions_revision+=1
    return dict(result,already_loaded=False)
