"""Read-only, source-value analysis over saved session attempts; no inferred measurements."""
import csv
import io
import math
from datetime import date
from collections import defaultdict
from driving_range import effective_equipment

METRICS = {
    'carry': ('Carry','yd'), 'total': ('Total','yd'), 'absolute_offline': ('Absolute offline','yd'),
    'offline': ('Signed offline','yd'), 'ball_speed': ('Ball speed','mph'),
    'launch_ang': ('Launch angle','°'), 'launch_dir': ('Start line','°'),
    'total_spin': ('Total spin','rpm'), 'descent_ang': ('Descent angle','°'),
    'peak_height': ('Apex','ft'), 'hang_time': ('Hang time','s'),
}


def value(shot, metric):
    v=shot.get('vals',{}).get('offline' if metric=='absolute_offline' else metric)
    if v is None and metric=='descent_ang' and shot.get('simulated'):
        v=shot.get('vals',{}).get('descent')
    if type(v) not in (int,float) or not math.isfinite(v):
        return None
    return abs(v) if metric=='absolute_offline' else v


def robust(values):
    vals=sorted(v for v in values if type(v) in (int,float) and math.isfinite(v));n=len(vals)
    def q(p):
        i=(n-1)*p;lo=int(i)
        return vals[lo]+(i-lo)*(vals[min(lo+1,n-1)]-vals[lo])
    return dict(count=n,median=q(.5) if n else None,q1=q(.25) if n>1 else None,
                q3=q(.75) if n>1 else None,iqr=q(.75)-q(.25) if n>1 else None)


def build_report(sessions, params):
    f={k:params.get(k,'') for k in ('date_from','date_to','bag','club','swing','sessions')}
    f.update(mode=params.get('mode','real'),kind=params.get('kind','full_swing'),metric=params.get('metric','carry'),
             inclusion=params.get('inclusion','included'))
    if f['mode'] not in ('real','demo') or f['kind'] not in ('full_swing','putting','all','game') or f['metric'] not in METRICS or f['inclusion'] not in ('included','all'):
        raise ValueError('Choose valid analysis filters.')
    for key in ('date_from','date_to'):
        if f[key]:date.fromisoformat(f[key])
    if f['date_from'] and f['date_to'] and f['date_from']>f['date_to']:
        raise ValueError('Start date must precede end date.')
    selected_ids=set(filter(None,f['sessions'].split(',')))
    available=[s for s in sessions if bool(s.get('demo'))==(f['mode']=='demo')]
    options=dict(bags={},clubs={},swings=set(),sessions=[])
    rows=[];removed=0
    for s in available:
        kind='game' if s.get('session_kind')=='golf_sim' else s.get('practice_type','putting')
        if f['kind']!='all' and f['kind']!=kind:continue
        options['sessions'].append(dict(id=s['id'],started=s['started'],drill=s['drill']))
        for shot in s.get('shots',[]):
            eq=effective_equipment(shot)
            if eq.get('bag_id'):options['bags'][eq['bag_id']]=eq.get('bag_name','Unnamed bag')
            if eq.get('club_id'):options['clubs'][eq['club_id']]=dict(label=eq.get('club_label','Unnamed club'),bag=eq.get('bag_id',''))
            if shot.get('swing_label'):options['swings'].add(shot['swing_label'])
            day=s['started'][:10]
            if f['date_from'] and day<f['date_from'] or f['date_to'] and day>f['date_to']:continue
            if selected_ids and s['id'] not in selected_ids:continue
            if f['bag'] and eq.get('bag_id')!=f['bag'] or f['club'] and eq.get('club_id')!=f['club']:continue
            if f['swing'] and (shot.get('swing_label') or '__unspecified')!=f['swing']:continue
            if shot.get('removed'):removed+=1;continue
            rows.append(dict(session_id=s['id'],session_started=s['started'],drill=s['drill'],
                key=shot['key'],receipt_id=shot.get('receipt_id'),captured=shot.get('captured'),
                bag_id=eq.get('bag_id',''),bag_name=eq.get('bag_name','No bag'),club_id=eq.get('club_id',''),
                club_label=eq.get('club_label') or 'Untagged',swing_label=shot.get('swing_label') or '',
                excluded=bool(shot.get('excluded')),simulated=bool(s.get('demo')),values={m:value(shot,m) for m in METRICS}))
    chosen=[r for r in rows if f['inclusion']=='all' or not r['excluded']]
    groups=defaultdict(list);by_session=defaultdict(list)
    for r in chosen:
        groups[(r['bag_id'],r['club_id'],r['swing_label'])].append(r)
        by_session[r['session_id']].append(r)
    def summary(rs):return {m:robust(r['values'][m] for r in rs) for m in METRICS}
    group_rows=[]
    for (bag,club,swing),rs in groups.items():
        group_rows.append(dict(bag_id=bag,club_id=club,swing_label=swing,bag_name=rs[0]['bag_name'],
            club_label=rs[0]['club_label'],count=len(rs),metrics=summary(rs)))
    group_rows.sort(key=lambda g:(g['bag_name'],g['swing_label'],-(g['metrics'][f['metric']]['median'] or 0)))
    trend=[]
    for sid,rs in by_session.items():
        baseline=[r for r in rows if r['session_id']==sid]
        trend.append(dict(id=sid,started=rs[0]['session_started'],drill=rs[0]['drill'],count=len(rs),
            metrics=summary(rs),excluded=sum(r['excluded'] for r in baseline),eligible=len(baseline)))
    trend.sort(key=lambda s:(s['started'],s['id']))
    options['swings']=sorted(options['swings'])
    return dict(filters=f,metrics={k:dict(label=v[0],unit=v[1]) for k,v in METRICS.items()},options=options,
        selected=summary(chosen),all_recorded=summary(rows),count=len(chosen),eligible=len(rows),removed=removed,
        excluded=sum(r['excluded'] for r in rows),groups=group_rows,trend=trend,rows=chosen,
        counting='Session attempts; exclusions are session-scoped. A shot reused in multiple sessions can appear once per session.',
        method='Source values; median and type-7 IQR. Missing values omitted per metric; no automatic outlier removal.')


def report_csv(report):
    stream=io.StringIO(newline='');writer=csv.writer(stream)
    fields=['session_id','session_started','key','captured','bag_name','club_label','swing_label','excluded','simulated']
    writer.writerow(fields+[f'{m} ({METRICS[m][1]})' for m in METRICS])
    def safe(v):
        if isinstance(v,str) and v.lstrip().startswith(('=','+','-','@')):return "'"+v
        return v
    for r in report['rows']:writer.writerow([safe(r.get(k)) for k in fields]+[r['values'][m] for m in METRICS])
    return '\ufeff'+stream.getvalue()
