"""GSPro Open Connect v1 JSON framing and validation; no acquisition dependencies."""
import codecs
import copy
import json
import math

LIMIT = 262144
BALL = {'Speed':'ball_speed','VLA':'launch_ang','HLA':'launch_dir','TotalSpin':'total_spin',
        'SpinAxis':'spin_axis','BackSpin':'back_spin','SideSpin':'side_spin','CarryDistance':'carry'}
CLUB = {'Speed':'club_speed','AngleOfAttack':'attack_angle','FaceToTarget':'face_angle',
        'Lie':'dynamic_lie','Loft':'dynamic_loft','Path':'club_path','ClosureRate':'closure_rate',
        'VerticalFaceImpact':'impact_vertical','HorizontalFaceImpact':'impact_horizontal'}

def reject_constant(value):
    raise ValueError('Non-finite JSON number: '+value)

def object_pairs(pairs):
    result = {}
    for key,value in pairs:
        if key in result: raise ValueError('Duplicate JSON field: '+key)
        result[key] = value
    return result

class Frames:
    """Bounded raw JSON framing, including concatenation and split UTF-8 sequences."""
    def __init__(self):
        self.utf8 = codecs.getincrementaldecoder('utf-8')()
        self.pending = ''
        self.decoder = json.JSONDecoder(parse_constant=reject_constant, object_pairs_hook=object_pairs)

    def feed(self, data):
        self.pending += self.utf8.decode(data)
        if len(self.pending.encode('utf-8')) > LIMIT: raise ValueError('Packet exceeds 256 KiB.')
        result = []
        while self.pending.strip():
            self.pending = self.pending.lstrip()
            if not self.pending.startswith('{'): raise ValueError('Expected a JSON object.')
            try: value,end = self.decoder.raw_decode(self.pending)
            except json.JSONDecodeError: break  # Incomplete input is bounded by size and idle timeout.
            result.append(value)
            self.pending = self.pending[end:]
        return result

def wire(packet):
    return json.dumps(packet,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode('utf-8')

def numeric(data,key,low,high,required=False):
    value=data.get(key)
    if value is None and not required:return
    if type(value) not in (int,float) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError('Invalid or missing '+key)

def validate_packet(packet):
    if not isinstance(packet,dict):raise ValueError('Expected a JSON object.')
    if not isinstance(packet.get('DeviceID'),str) or not 1<=len(packet['DeviceID'])<=100:
        raise ValueError('DeviceID is required (1-100 characters).')
    if packet.get('APIversion')!='1':raise ValueError('APIversion must be "1".')
    if packet.get('Units','Yards')!='Yards':raise ValueError('This adapter expects Yards (speed in mph).')
    if type(packet.get('ShotNumber')) is not int or not 0<=packet['ShotNumber']<=2147483647:
        raise ValueError('ShotNumber must be a nonnegative integer.')
    options=packet.get('ShotDataOptions')
    if not isinstance(options,dict):raise ValueError('ShotDataOptions is required.')
    for key in ('ContainsBallData','ContainsClubData'):
        if type(options.get(key)) is not bool:raise ValueError(key+' must be boolean.')
    for key in ('IsHeartBeat','LaunchMonitorIsReady','LaunchMonitorBallDetected'):
        if key in options and type(options[key]) is not bool:raise ValueError(key+' must be boolean.')
    if options.get('IsHeartBeat') and (options['ContainsBallData'] or options['ContainsClubData']):
        raise ValueError('Heartbeat cannot contain shot data.')
    if options['ContainsClubData']:
        if not options['ContainsBallData']:raise ValueError('Club-only shot packets are not supported.')
        club=packet.get('ClubData')
        if not isinstance(club,dict):raise ValueError('ClubData object required.')
        for key in (*CLUB,'SpeedAtImpact'):
            numeric(club,key,0 if key in ('Speed','SpeedAtImpact') else -10000,10000)
    if not options['ContainsBallData']:return {}
    ball=packet.get('BallData')
    if not isinstance(ball,dict):raise ValueError('BallData object required.')
    for key,low,high in [('Speed',0,250),('HLA',-90,90),('VLA',-90,90)]:numeric(ball,key,low,high,True)
    for key,low,high in [('TotalSpin',0,50000),('SpinAxis',-180,180),('BackSpin',-50000,50000),('SideSpin',-50000,50000),('CarryDistance',0,1000)]:numeric(ball,key,low,high)
    total_pair=ball.get('TotalSpin') is not None and ball.get('SpinAxis') is not None
    component_pair=ball.get('BackSpin') is not None and ball.get('SideSpin') is not None
    if not total_pair and not component_pair:raise ValueError('Send TotalSpin + SpinAxis or BackSpin + SideSpin.')
    vals={field:ball[key] for key,field in BALL.items() if ball.get(key) is not None}
    if options['ContainsClubData']:
        vals.update({field:packet['ClubData'][key] for key,field in CLUB.items() if packet['ClubData'].get(key) is not None and key not in ('VerticalFaceImpact','HorizontalFaceImpact','ClosureRate')})
    return vals

def simulator_packet(packet,number):
    """Documented fields only; private extensions remain in SQLite, not simulator output."""
    options=packet['ShotDataOptions']
    result={key:copy.deepcopy(packet[key]) for key in ('DeviceID','APIversion')}
    result.update(Units='Yards',ShotNumber=number,ShotDataOptions={key:options[key] for key in
        ('ContainsBallData','ContainsClubData','IsHeartBeat','LaunchMonitorIsReady','LaunchMonitorBallDetected') if key in options})
    if options['ContainsBallData']:result['BallData']={key:packet['BallData'][key] for key in BALL if packet['BallData'].get(key) is not None}
    if options['ContainsClubData']:result['ClubData']={key:packet['ClubData'][key] for key in (*CLUB,'SpeedAtImpact') if packet['ClubData'].get(key) is not None}
    return result

def heartbeat(ready=False,number=0):
    return dict(DeviceID='TraceLoft',Units='Yards',ShotNumber=number,APIversion='1',
        ShotDataOptions=dict(ContainsBallData=False,ContainsClubData=False,IsHeartBeat=True,
            LaunchMonitorIsReady=bool(ready),LaunchMonitorBallDetected=bool(ready)))
