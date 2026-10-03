"""Versioned endpoint golf game. Gameplay outcomes never replace source observations."""
import json
import copy
import hashlib
import math
import random
import uuid
from pathlib import Path

from course_geometry import classify
from bundled_courses import load_bundled
from putting import PuttingSession, timestamp
from putting_distance import distance_ft, required_speed_mph, model_context, DEFAULT_MODEL_ID
from distance_ladder import numeric

GAME_FIELDS = ('game_rough', 'game_sand', 'game_variation', 'game_gimme', 'game_geometry', 'game_acknowledged', 'game_course_id')
COURSE = dict(id='meadow-one-v1', name='Meadow One', par=4, yards=350, tee=[0,0], pin=[0,350],
    bounds=[-80,80,-15,385], green_radius=18,
    fairway=[[-18,0],[18,0],[22,140],[8,250],[10,335],[-15,335],[-32,240],[-25,130]],
    water=[dict(center=[-43,225],radius=20)],
    sand=[dict(center=[-25,332],radius=11),dict(center=[23,348],radius=10)])


def distance(a,b):
    return math.hypot(a[0]-b[0],a[1]-b[1])


def inside(point, polygon):
    x,y=point;result=False;j=len(polygon)-1
    for i,(xi,yi) in enumerate(polygon):
        xj,yj=polygon[j]
        if (yi>y)!=(yj>y) and x<(xj-xi)*(y-yi)/(yj-yi)+xi:result=not result
        j=i
    return result


def lie_at(point, course):
    return classify(point,course)


class GolfSimSession(PuttingSession):
    def __init__(self, folder, store=None, equipment_selection=None, demo=True, stimp=10,
                 game_rough=7, game_sand=20, game_variation=0, game_gimme=3,
                 game_geometry='downrange', game_acknowledged=False, game_course_id='meadow-one-v2', course=None):
        if any(not numeric(v,lo,hi) for v,lo,hi in ((game_rough,0,60),(game_sand,0,80),
            (game_variation,0,10),(game_gimme,0,10),(stimp,3,20))):
            raise ValueError('Choose valid lie, putting and variation settings.')
        if type(demo) is not bool or game_geometry not in ('downrange','radial'):
            raise ValueError('Choose a valid game mode and distance geometry.')
        if not demo and game_acknowledged is not True:
            raise ValueError('Acknowledge the unverified reported-distance geometry before live play.')
        if course is None:
            if game_course_id=='meadow-one-v1':course=COURSE
            else:course=load_bundled(game_course_id)
        self.folder,self.store=Path(folder),store
        self.data=dict(id=uuid.uuid4().hex,started=timestamp(),ended=None,drill='2D golf',
            practice_type='full_swing',session_kind='golf_sim',random_pace=False,target=0,demo=demo,
            equipment_selection=copy.deepcopy(equipment_selection),shots=[],course=copy.deepcopy(course),
            game_settings=dict(rough_percent=game_rough,sand_percent=game_sand,nature_percent=30,
                variation_degrees=game_variation,gimme_ft=game_gimme,geometry=game_geometry,
                acknowledged=game_acknowledged,putting=model_context(stimp)),
            game=dict(position=copy.deepcopy(course['tee']),aim=copy.deepcopy(course['pin']),lie='tee',turn=0,strokes=0,penalties=0,
                      concessions=0,holed=False,last_message='Aim, choose a club, then hit your first shot.'))
        self.save()

    def context(self):
        g=self.data['game']
        return {k:copy.deepcopy(g[k]) for k in ('turn','position','aim','lie')}

    def set_aim(self,x,y,turn):
        if self.data['ended'] or turn!=self.data['game']['turn']:
            raise ValueError('The round advanced or ended. Refresh before aiming.')
        left,right,near,far=self.data['course']['bounds']
        if not numeric(x,left,right) or not numeric(y,near,far) or distance([x,y],self.data['game']['position'])<.1:
            raise ValueError('Choose an aim point on the course, away from the ball.')
        self.data['game']['aim']=[x,y];self.save()

    def add(self,event):
        if self.data['ended'] or event.get('result') not in ('sent','validated') or bool(event.get('simulated'))!=self.data['demo']:
            return False
        key=f"{event['session_id']}:{event['seq']}"
        if any(s['key']==key or event.get('receipt_id') and s.get('receipt_id')==event['receipt_id'] for s in self.data['shots']):return False
        g=self.data['game'];settings=self.data['game_settings'];course=self.data['course'];vals=event.get('vals',{})
        before=copy.deepcopy(g);context=copy.deepcopy(event.get('game_context'))
        shot=dict(key=key,captured=event.get('captured_at') or timestamp(),receipt_id=event.get('receipt_id'),
            vals=copy.deepcopy(vals),excluded=False,success=False,scored=False,simulated=self.data['demo'],
            **copy.deepcopy(event.get('equipment_selection',self.data.get('equipment_selection')) or {}))
        outcome=dict(version='endpoint-golf-v1',course_id=course['id'],context=context,settings=copy.deepcopy(settings),
                     before=before,applied=False,penalty_strokes=0,conceded_strokes=0)
        reason=None;putting=g['lie']=='green'
        left,right,near,far=course['bounds']
        valid_context=(isinstance(context,dict) and all(context.get(k)==g[k] for k in ('turn','position','lie'))
            and isinstance(context.get('aim'),list) and len(context['aim'])==2
            and numeric(context['aim'][0],left,right) and numeric(context['aim'][1],near,far)
            and distance(context['aim'],g['position'])>=.1)
        if not valid_context:reason='Shot saved, ball unchanged: aim/turn context is missing or stale. Wait for the updated round before hitting.'
        elif putting and not (numeric(vals.get('ball_speed'),0,15) and numeric(vals.get('launch_dir'),-45,45)):
            reason='Shot saved, ball unchanged: putting needs speed 0–15 mph and start line.'
        elif not putting and not (numeric(vals.get('total'),0,600) and numeric(vals.get('offline'),-600,600)):
            reason='Shot saved, ball unchanged: full shots need reported total distance and signed offline.'
        elif not putting and settings['geometry']=='radial' and abs(vals['offline'])>vals['total']:
            reason='Shot saved, ball unchanged: offline exceeds radial total distance.'
        if reason:
            g['last_message']=reason;outcome['message']=reason
        else:
            aim=context['aim'];p=g['position'];angle=math.atan2(aim[0]-p[0],aim[1]-p[1])
            reduction=settings.get(g['lie']+'_percent',0)/100
            variation=settings['variation_degrees'] if g['lie'] in ('rough','sand','nature') else 0
            seed=hashlib.sha256((self.data['id']+key).encode()).hexdigest()
            draw=random.Random(seed).uniform(-variation,variation)
            angle+=math.radians(draw)
            if putting:
                travel=distance_ft(vals['ball_speed'],settings['putting']['stimp_ft'],settings['putting']['id'])/3
                lateral=travel*math.sin(math.radians(vals['launch_dir']))
                forward=travel*math.cos(math.radians(vals['launch_dir']))
            else:
                travel=vals['total']*(1-reduction);lateral=vals['offline']*(1-reduction)
                forward=math.sqrt(max(0,travel*travel-lateral*lateral)) if settings['geometry']=='radial' else travel
            end=[p[0]+forward*math.sin(angle)+lateral*math.cos(angle),
                 p[1]+forward*math.cos(angle)-lateral*math.sin(angle)]
            final_lie=lie_at(end,course);remaining=distance(end,course['pin'])
            outcome.update(applied=True,putting=putting,raw_total_yd=vals.get('total'),raw_offline_yd=vals.get('offline'),
                adjusted_forward_yd=forward,adjusted_right_yd=lateral,distance_factor=1-reduction,
                random_seed=seed,random_degrees=draw,endpoint=end,destination_lie=final_lie,
                remaining_at_endpoint_yd=remaining,aim_heading_degrees=math.degrees(angle)-draw)
            g['strokes']+=1;g['turn']+=1
            if final_lie in ('water','out of bounds'):
                g['strokes']+=1;g['penalties']+=1;outcome['penalty_strokes']=1
                message=f'{final_lie.capitalize()} · +1 penalty. Replay from the previous position.'
            else:
                g.update(position=end,lie=final_lie)
                holed=remaining*3<=.2
                conceded=not holed and final_lie=='green' and remaining*3<=settings['gimme_ft']
                if holed or conceded:
                    g['holed']=True;g['strokes']+=int(conceded);g['concessions']+=int(conceded)
                    outcome['conceded_strokes']=int(conceded);self.data['ended']=timestamp()
                    message='Hole complete · one conceded putt added.' if conceded else 'Hole complete · endpoint inside the simulated cup.'
                else:message=f'Green · {remaining*3:.1f} ft to the pin.' if final_lie=='green' else f'{final_lie.capitalize()} · {remaining:.1f} yd to the pin.'
                g['aim']=copy.deepcopy(course['pin'])
            g['last_message']=message;outcome['message']=message
            shot.update(scored=True,success=g['holed'])
        outcome['after']=copy.deepcopy(g);shot['game_outcome']=outcome
        self.data['shots'].append(shot);self.save();return True

    def summary(self):
        g=self.data['game'];shots=self.data['shots'];remaining=distance(g['position'],self.data['course']['pin'])
        putting=g['lie']=='green' and not g['holed']
        pace=required_speed_mph(max(.5,remaining*3),self.data['game_settings']['putting']['stimp_ft']) if putting and remaining*3<=300 else None
        return dict(count=sum(not s['excluded'] for s in shots),recorded=len(shots),successes=int(g['holed']),
            scored=sum(s['scored'] for s in shots),strokes=g['strokes'],penalties=g['penalties'],
            concessions=g['concessions'],remaining_yd=remaining,required_pace_mph=pace,holed=g['holed'])


def simulated_event(session, distance_yd, offline_yd=0):
    """Explicit deterministic test input, recorded as synthetic and isolated from live sessions."""
    if not session.data['demo'] or session.data['ended']:
        raise ValueError('Simulated shots require an active demo round.')
    if not numeric(distance_yd,.01,600) or not numeric(offline_yd,-200,200):
        raise ValueError('Choose a valid simulated distance and offline amount.')
    putting=session.data['game']['lie']=='green'
    if putting:
        travel=math.hypot(distance_yd,offline_yd)
        speed=required_speed_mph(travel*3,session.data['game_settings']['putting']['stimp_ft'])
        hla=math.degrees(math.atan2(offline_yd,distance_yd))
        if abs(hla)>45:raise ValueError('Simulated putting start line must stay within 45 degrees.')
        vals=dict(ball_speed=speed,launch_ang=0,launch_dir=hla,total_spin=0)
    else:
        vals=dict(ball_speed=max(1,min(200,distance_yd*.55)),launch_ang=18,launch_dir=0,
                  total=distance_yd,carry=distance_yd*.93,offline=offline_yd,total_spin=5500)
    return dict(kind='record',session_id='game-demo-'+session.data['id'],seq=len(session.data['shots'])+1,
        receipt_id=uuid.uuid4().hex,producer_id='golfdata-game-demo-v1',result='validated',simulated=True,
        captured_at=timestamp(),practice_session_id=session.data['id'],vals=vals,
        game_context=session.context(),equipment_selection=copy.deepcopy(session.data.get('equipment_selection')),
        source_configuration={'acquisition':'synthetic_demo','generator':'golfdata-game-demo-v1'})
