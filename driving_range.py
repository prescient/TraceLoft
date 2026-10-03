"""Open-ended range, immutable flight predictions and session-scoped recoverable cleanup."""
import copy
import math
import random
import statistics
import uuid
from collections import Counter
from pathlib import Path

from putting import PuttingSession, timestamp
from distance_ladder import numeric
from flight_model import predict

DRIVING_FIELDS = ('range_target', 'range_width', 'range_depth', 'handedness', 'demo')
EDIT_FIELDS = ('excluded', 'removed', 'corrected_equipment', 'cleanup_reason')


def effective_equipment(shot):
    return shot.get('corrected_equipment') or {k: shot.get(k, '') for k in
        ('bag_id','bag_name','club_id','club_label','catalog_revision','selection_mode')}


def stats(shots, field):
    values = [s['vals'][field] for s in shots if numeric(s['vals'].get(field), -10000, 20000)]
    return dict(count=len(values), mean=statistics.mean(values) if values else None,
                median=statistics.median(values) if values else None, sd=statistics.pstdev(values) if values else None)


class DrivingRangeSession(PuttingSession):
    def __init__(self, folder, store=None, equipment_selection=None, range_target=150,
                 range_width=30, range_depth=20, handedness='right_handed', demo=False):
        if not numeric(range_target, 0, 450) or not numeric(range_width, 1, 200) or not numeric(range_depth, 1, 200):
            raise ValueError('Target must be 0–450 yd; target width/depth must be 1–200 yd.')
        if handedness not in ('right_handed','left_handed') or not isinstance(demo, bool):
            raise ValueError('Choose a valid handedness and range mode.')
        self.folder, self.store = Path(folder), store
        self.data = dict(id=uuid.uuid4().hex, started=timestamp(), ended=None, drill='Driving range',
            practice_type='full_swing', session_kind='driving_range', random_pace=False, target=range_target,
            range_target=range_target, range_width=range_width, range_depth=range_depth, handedness=handedness,
            demo=demo, equipment_selection=equipment_selection, shots=[], cleanup_revision=0, cleanup_history=[])
        self.save()

    def add(self, event):
        if self.data['ended'] or event.get('result') not in ('sent','validated'):
            return False
        if bool(event.get('simulated')) != self.data['demo']:
            return False
        key = f"{event['session_id']}:{event['seq']}"
        vals = event.get('vals', {})
        if any(s['key']==key for s in self.data['shots']):
            return False
        if not (numeric(vals.get('ball_speed'),1,220) and numeric(vals.get('launch_ang'),-10,70)
                and numeric(vals.get('launch_dir'),-45,45)):
            return False
        equipment = copy.deepcopy(event.get('equipment_selection', self.data.get('equipment_selection')) or {})
        context = event.get('range_context') or {k:self.data[k] for k in ('range_target','range_width','range_depth')}
        target=context['range_target']
        carry=vals.get('carry')
        scored=target>0 and numeric(carry,0,450)
        shot=dict(key=key, captured=event.get('captured_at') or timestamp(), vals=copy.deepcopy(vals),
                  receipt_id=event.get('receipt_id'), target=target, target_distance_yd=target,
                  target_width_yd=context['range_width'], target_depth_yd=context['range_depth'],
                  distance_metric='carry', distance_yd=carry if numeric(carry,0,450) else None,
                  distance_error_yd=carry-target if scored else None, scored=scored,
                  success=bool(scored and abs(carry-target)<=context['range_depth']/2),
                  excluded=False, removed=False, simulated=self.data['demo'], **equipment)
        shot['flight'] = copy.deepcopy(event.get('_demo_flight')) if event.get('_demo_flight') else predict(vals,self.data['handedness'])
        self.data['shots'].append(shot)
        self.save()
        return True

    def summary(self):
        all_shots=self.data['shots']
        included=[s for s in all_shots if not s.get('excluded') and not s.get('removed')]
        clubs={}
        for s in included:
            eq=effective_equipment(s); key=eq.get('bag_id','')+':'+eq.get('club_id','')
            clubs.setdefault(key, dict(bag=eq.get('bag_name',''), club=eq.get('club_label','') or 'Untagged', shots=[]))['shots'].append(s)
        return dict(count=len(included), recorded=len(all_shots), successes=sum(s['success'] for s in included),
            scored=sum(s['scored'] for s in included), excluded=sum(s.get('excluded',False) and not s.get('removed') for s in all_shots),
            removed=sum(s.get('removed',False) for s in all_shots),
            carry=stats(included,'carry'), total=stats(included,'total'), offline=stats(included,'offline'),
            all_recorded_carry=stats(all_shots,'carry'),
            shapes=dict(Counter(s.get('flight',{}).get('shape','Unavailable') for s in included)),
            clubs=[dict(bag=c['bag'],club=c['club'],count=len(c['shots']),carry=stats(c['shots'],'carry'),
                        total=stats(c['shots'],'total'),offline=stats(c['shots'],'offline')) for c in clubs.values()])

    def cleanup(self, action, keys, revision, reason, equipment=None, batch_id=None):
        if revision != self.data['cleanup_revision']:
            raise ValueError('Shot cleanup changed on another screen. Refresh and select again.')
        if not isinstance(reason,str) or not 1<=len(reason.strip())<=240:
            raise ValueError('Enter a cleanup reason (1–240 characters).')
        if action == 'undo':
            batches=[b for b in self.data['cleanup_history'] if b['action']!='undo' and not b.get('undone')]
            if not batches or batches[-1]['id']!=batch_id:
                raise ValueError('Only the latest remaining cleanup can be undone. Refresh the range.')
            prior=batches[-1]; keys=[item['key'] for item in prior['items']]
        elif action not in ('exclude','include','remove','restore','retag'):
            raise ValueError('Unknown shot cleanup action.')
        if not keys or len(keys)>1000 or len(set(keys))!=len(keys):
            raise ValueError('Select 1–1000 distinct shots.')
        by_key={s['key']:s for s in self.data['shots']}
        if any(k not in by_key for k in keys):
            raise ValueError('Selection contains a shot outside this session; nothing changed.')
        if action=='retag' and not equipment:
            raise ValueError('Choose a valid bag/club for the correction.')
        items=[]
        for key in keys:
            s=by_key[key]; before={k:copy.deepcopy(s.get(k)) for k in EDIT_FIELDS}
            if action=='undo':
                original=next(i['before'] for i in prior['items'] if i['key']==key)
                s.update(copy.deepcopy(original))
            else:
                if action in ('include','exclude'): s['excluded']=action=='exclude'
                if action in ('remove','restore'): s['removed']=action=='remove'
                if action=='retag': s['corrected_equipment']=copy.deepcopy(equipment)
                s['cleanup_reason']=reason.strip()
            items.append(dict(key=key,before=before,after={k:copy.deepcopy(s.get(k)) for k in EDIT_FIELDS}))
        if action=='undo': prior['undone']=True
        batch=dict(id=uuid.uuid4().hex,action=action,reason=reason.strip(),at=timestamp(),items=items,
                   undo_of=batch_id if action=='undo' else None)
        self.data['cleanup_history'].append(batch)
        self.data['cleanup_revision']+=1
        self.save()
        return batch['id']


def demo_event(session, seq):
    """Repeatable diverse flight inputs; never hardware capture or GSPro delivery."""
    rng=random.Random(session.data['id']+str(seq))
    eq=session.data.get('equipment_selection') or {}
    label=eq.get('club_label','').lower()
    speed,launch,spin = (145,13,2700) if 'driver' in label or 'wood' in label else (75,30,8500) if any(x in label for x in ('wedge','pw','gw','sw','lw','°')) else (112,20,5500)
    if session.data.get('collection_kind')=='wedge':
        labels=session.data['swing_labels'];speed *= .55 + .45*(labels.index(session.data['swing_label'])+1)/len(labels)
    if seq%9==0: speed*=.68; launch=7
    axis=[-18,-8,-2,0,2,8,19][seq%7]
    vals=dict(ball_speed=round(speed+rng.uniform(-7,7),1),launch_ang=round(launch+rng.uniform(-3,3),1),
              launch_dir=round(rng.uniform(-5,5),1),total_spin=round(spin+rng.uniform(-600,600)),spin_axis=axis)
    flight=predict(vals,session.data['handedness'])
    metrics=flight.get('metrics',{})
    vals.update(carry=round(metrics['carry_yd'],1) if metrics.get('carry_yd') is not None else None,
                total=round(metrics['total_yd'],1) if metrics.get('total_yd') is not None else None,
                offline=round(flight['total_point_yd']['right'],1) if flight.get('total_point_yd') else None,
                peak_height=metrics.get('apex_ft'),descent_ang=metrics.get('descent_deg'),hang_time=metrics.get('hang_time_s'))
    return dict(kind='record',session_id='demo-'+session.data['id'],seq=seq,receipt_id=uuid.uuid4().hex,
                producer_id='golfdata-demo-v1',result='validated',captured_at=timestamp(),simulated=True,
                source_configuration={'acquisition':'synthetic_demo','generator':'golfdata-demo-v1'},
                practice_session_id=session.data['id'],equipment_selection=copy.deepcopy(eq),vals=vals,
                _demo_flight=flight,note='SIMULATED DATA: generated launch inputs; all distances are model estimates.')
