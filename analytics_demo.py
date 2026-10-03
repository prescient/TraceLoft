"""Idempotent, explicitly invented historical sessions for Analyze development."""
import copy
import json
import random
import uuid
from datetime import datetime, timedelta

from collection import CollectionSession
from driving_range import DrivingRangeSession
from equipment import new_bag, selection

KEY = 'analytics_demo_pack.v1'
CLUBS = {
    'Driver': (230, 145, 13, 2700), '5 iron': (180, 121, 17, 4700),
    '7 iron': (160, 110, 20, 6200), '9 iron': (138, 97, 25, 7900),
    'PW': (123, 89, 29, 8900), 'SW': (85, 72, 34, 9700),
}


def sample(session, eq, week, bag_index, seq, captured, swing=None):
    rng = random.Random(f'{KEY}:{week}:{bag_index}:{seq}:{swing}')
    carry, speed, launch, spin = CLUBS[eq['club_label']]
    factor = {None: 1, 'Half': .55, 'Three-quarter': .78, 'Full': 1}[swing]
    # Deliberate test trends; no claim about a player's progress or club fitting.
    center = carry * factor * (1 + week*.003 + bag_index*.02)
    spread = (7-week*.4) * factor
    mishit = seq % 11 == 0
    distance = max(5, center + rng.gauss(0, spread) - (center*.25 if mishit else 0))
    vals = dict(carry=round(distance,1), total=round(distance+(16 if carry>200 else 5)*factor,1),
                offline=round(rng.gauss(5-week*.6-bag_index*3,spread*1.6)+(22 if mishit else 0),1),
                ball_speed=round(speed*factor**.6*(.8 if mishit else 1)+rng.gauss(0,1.5),1),
                launch_ang=round(launch+rng.gauss(0,1.2),1), launch_dir=round(rng.gauss(.5,1.2),1),
                total_spin=round(spin*factor**.4+rng.gauss(0,250)),spin_axis=round(rng.gauss(3,7),1),
                peak_height=round(85*factor+rng.gauss(0,5),1),
                descent_ang=round(37+(launch-13)*.7+rng.gauss(0,1.5),1),hang_time=round(5*factor+rng.gauss(0,.2),1))
    if seq % 7 == 0:
        vals['descent_ang'] = None
        vals['peak_height'] = None
    if seq % 13 == 0:
        vals['offline'] = None
    if seq % 17 == 0:
        vals['carry'] = round(center*1.5,1)
        vals['total'] = vals['carry']+5
    return dict(kind='record',session_id=KEY+':'+session.data['id'],seq=seq,receipt_id=uuid.uuid4().hex,
                producer_id=KEY,result='validated',captured_at=captured.isoformat(),simulated=True,
                practice_session_id=session.data['id'],equipment_selection=copy.deepcopy(eq),
                collection_context=dict(swing_label=swing),vals=vals,
                source_configuration=dict(acquisition='synthetic_demo',generator=KEY,
                                          assumptions='Invented distances, trends, mishits and missing readings; not measured or Tour data.'),
                note='SIMULATED analytics development sample; all values and trends are invented.')


def install(service, anchor=None):
    """Atomic pack; never replaces an existing bag, active session or capture owner."""
    store=service.store
    if not store:
        raise ValueError('SQLite storage is required.')
    anchor=(anchor or datetime.now().astimezone()-timedelta(days=1)).replace(hour=17,minute=0,second=0,microsecond=0)
    with store.transaction():
        previous=store.connection.execute('SELECT value FROM metadata WHERE key=?',(KEY,)).fetchone()
        if previous:
            return dict(json.loads(previous[0]),already_loaded=True)
        catalog=copy.deepcopy(service.equipment)
        if len(catalog['bags'])>48:
            raise ValueError('Two free bag slots are required.')
        bags=[]
        for letter in ('A','B'):
            bag=new_bag(f'Analytics lab {letter} · DEMO')
            bag['clubs']=[dict(id=uuid.uuid4().hex,label=label) for label in CLUBS]
            bags.append(bag)
        catalog['bags'].extend(bags)
        catalog['revision']+=1
        store.save_equipment_catalog(catalog)
        ids=[];shot_count=0;excluded=0;removed=0;retagged=0
        for week in range(8):
            plans=[(0,False),(1,False)] + ([(week//2%2,True)] if week%2 else [])
            for bag_index,wedge in plans:
                bag=bags[bag_index]
                clubs=bag['clubs'][-2:] if wedge else bag['clubs']
                if wedge:
                    session=CollectionSession(service.root/'practice_sessions',catalog,bag['id'],
                        [c['id'] for c in clubs],samples=6,demo=True,store=store,
                        swing_labels=['Half','Three-quarter','Full'])
                else:
                    session=DrivingRangeSession(service.root/'practice_sessions',store=store,demo=True,
                        equipment_selection=selection(catalog,bag['id'],clubs[0]['id']))
                started=anchor-timedelta(days=(7-week)*7,hours=bag_index*2+(1 if wedge else 0))
                session.data.update(started=started.isoformat(),demo_reference=dict(id=KEY,week=week+1,
                    assumptions='Invented analytics test history; changing spread is scripted, not evidence of improvement.'))
                for club in clubs:
                    eq=selection(catalog,bag['id'],club['id'])
                    for swing in (['Half','Three-quarter','Full'] if wedge else [None]):
                        for _ in range(6 if wedge else 5):
                            seq=len(session.data['shots'])+1
                            event=sample(session,eq,week,bag_index,seq,started+timedelta(seconds=seq*45),swing)
                            # A deliberate forgotten club selection, corrected below through normal cleanup.
                            if not wedge and seq==1:
                                event['equipment_selection']=selection(catalog,bag['id'],bag['clubs'][1]['id'])
                            store.ingest(event,provenance='synthetic_demo')
                            if not session.add(event):
                                raise ValueError('Synthetic sample was not accepted.')
                shots=session.data['shots']
                def cleanup(action, keys, reason, equipment=None):
                    session.cleanup(action,keys,session.data['cleanup_revision'],reason,equipment)
                    store._audit(session.data['id'],'range_cleanup',session.data['cleanup_history'][-1])
                bad=[s['key'] for i,s in enumerate(shots,1) if i%17==0]
                cleanup('exclude',bad,'DEMO fixture: simulated distance-reading error, not a mishit.')
                excluded+=len(bad)
                if not wedge:
                    cleanup('retag',[shots[0]['key']],'DEMO fixture: forgotten club selection corrected to Driver.',
                            selection(catalog,bag['id'],bag['clubs'][0]['id']))
                    retagged+=1
                    if week%3==0:
                        cleanup('remove',[shots[-1]['key']],'DEMO fixture: recoverable warm-up removal.')
                        removed+=1
                session.data['ended']=(started+timedelta(seconds=(len(shots)+1)*45)).isoformat()
                session.save()
                ids.append(session.data['id']);shot_count+=len(shots)
        result=dict(bag_ids=[b['id'] for b in bags],session_ids=ids,shot_count=shot_count,
                    date_from=(anchor-timedelta(days=49,hours=2)).date().isoformat(),date_to=anchor.date().isoformat(),
                    excluded=excluded,removed=removed,retagged=retagged)
        store.connection.execute('INSERT INTO metadata VALUES(?,?)',(KEY,json.dumps(result)))
    service.equipment=catalog
    service.sessions_revision+=1
    return dict(result,already_loaded=False)
