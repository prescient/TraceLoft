"""Original Sheboygan Straits geometry. Optional Pillow creates image-generation guides.

Run python courses/build_sheboygan_straits.py [--guides]. Published Straits Blue
pars/yardages only; original routing and bunker complexes, not a geographic replica.
"""
import json
import math
import random
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from course_geometry import classify
from course_workbench import validate_edits

W,H=1536,768
YARDS=[405,533,180,451,563,378,205,470,412,376,563,138,389,360,464,545,223,487]
PARS=[4,5,3,4,5,4,3,4,4,4,5,3,4,4,4,5,3,4]
NAMES=['Dune Departure','Fescue Passage','Gull Shelf','Iron Shore','Serpent Marsh','Devils Pocket',
       'Wreckers Point','Bunker Coast','Homeward Hollow','Split Decision','Sand Cathedral','Little Cauldron',
       'Lakeside Ledge','Blind Bargain','Northwind','Temptation Bay','Needle Point','Straits Reckoning']
# Original left-to-right routing in the artwork plane; four interior changes create varied doglegs.
LINES=[[430,455,350,315,310],[400,320,280,390,435],[390,390,390,380,370],
       [360,300,280,340,370],[350,465,470,285,310],[420,455,390,270,285],
       [350,350,350,345,340],[420,350,410,320,300],[300,340,465,420,360],
       [400,340,250,300,380],[320,395,460,370,325],[380,380,380,390,400],
       [350,415,395,280,275],[420,460,380,280,345],[320,290,365,410,390],
       [390,445,400,285,315],[365,365,365,355,345],[400,300,265,420,390]]
TIPS=[
 'Favor the broad right half of the opening landing area; the left bunker chain crowds the shorter approach.',
 'A three-shot route leaves room between the staggered sand fields. The greenside pocket punishes a long second shot.',
 'Take enough club to carry the front bunker fan. The right collar offers the wider miss.',
 'A long two-shot test: favor the inland fairway before attacking the narrow lakeside green.',
 'Choose each landing area before hitting. Marsh water and alternating bunker clusters make a straight shortcut risky.',
 'The short route is tempting, but a broad sand complex guards the inside corner. Lay back for a full approach.',
 'The pin sits between pale sand and the lake. Aim for the middle of the green rather than the shoreline edge.',
 'A dense chain of sandy pockets squeezes the driving zone; favor the center and avoid chasing extra distance.',
 'The fairway bends around a bunker field before narrowing toward the green. A controlled approach matters more than length.',
 'The first landing zone is squeezed from both sides. Plan the second shot from the wider inside shelf.',
 'A long ribbon of sand follows the lay-up side. Choose a precise second-shot yardage before attacking the green.',
 'The shortest hole still needs commitment: a compact green sits inside a ring of separate sand pockets.',
 'The shoreline side leaves little room. Approach from inland and use the wider front entrance.',
 'Sand occupies the corner of this short dogleg. The longer fairway route leaves a more forgiving angle.',
 'A demanding long par four with offset landing areas and a tightly guarded approach.',
 'Two-shot ambition competes with bunker fields near the green. A shorter lay-up keeps a broad approach window.',
 'A long par three with a narrow landing shelf. The inland collar is the forgiving miss; the lake is not.',
 'A demanding finish: work around the cross-sand complex, then leave a clear angle into the final green.'
]
SOURCE='https://www.kohlerwisconsin.com/golf/whistling-straits/the-straits/the-straits-hole-by-hole'
SCORECARD='https://www.kohlerwisconsin.com/content/dam/kohler-destinations/pdf_resource/dk/golf/whistling-straits/scorecard-the-straits.pdf'

def lobed(cx,cy,rx,ry,phase,angle=0,n=40):
    result=[]
    for i in range(n):
        t=i*math.tau/n
        r=1+.18*math.sin(3*t+phase)+.09*math.cos(5*t-phase)
        x=rx*r*math.cos(t);y=ry*r*math.sin(t)
        result.append([cx+x*math.cos(angle)-y*math.sin(angle),cy+x*math.sin(angle)+y*math.cos(angle)])
    return result

def build(index):
    rng=random.Random(8010+index);number=index+1;par=PARS[index];yard=YARDS[index]
    xs=[110,430,760,1080,1390];ys=LINES[index]
    if par==3:ys=[ys[0]+(ys[-1]-ys[0])*i/4 for i in range(5)]
    route=[[x,y] for x,y in zip(xs,ys)]
    scale=yard/sum(math.dist(a,b) for a,b in zip(route,route[1:]));tx,ty=route[0]
    def world(p):return [round((p[1]-ty)*scale,6),round((p[0]-tx)*scale,6)]
    def poly(r,holes=()):return dict(outer=[world(p) for p in r],holes=[[world(p) for p in h] for h in holes])
    def center(x):
        j=min(3,max(0,next((i for i in range(4) if x<=xs[i+1]),3)))
        t=max(0,min(1,(x-xs[j])/(xs[j+1]-xs[j])))
        return ys[j]+(ys[j+1]-ys[j])*t
    def width(x):return (14.5+3.5*math.sin(x/130+index*.65))/scale
    samples=[110+k*1280/100 for k in range(101)]
    start=1060 if par==3 else 185
    grass=[x for x in samples if x>=start]
    fairway=[[x,center(x)-width(x)] for x in grass]+[[x,center(x)+width(x)] for x in reversed(grass)]
    green_rx=min(16/scale,113);green_ry=min((10.5 if index in (6,11,16) else 13)/scale,94)
    green=lobed(1390,ys[-1],green_rx,green_ry,index*.7,n=60)
    tee=lobed(110,ys[0],min(6/scale,47),min(4/scale,30),.2,n=28)
    # Grass corridor leaves recoverable rough between fairway and fescue.
    clearing=[[x,center(x)-width(x)-12/scale] for x in samples]+[[x,center(x)+width(x)+12/scale] for x in reversed(samples)]
    clearing[0][0]=35;clearing[-1][0]=35;clearing[100][0]=1520;clearing[101][0]=1520
    sand=[];bunker_centers=[]
    def bunker(x,y,rx,ry,angle=0):
        ring=lobed(x,y,rx,ry,rng.random()*math.tau,angle)
        if min(p[0] for p in ring)<15 or max(p[0] for p in ring)>1520 or min(p[1] for p in ring)<115 or max(p[1] for p in ring)>640:return
        # Protect a narrow conservative route and the tee/putting surface.
        if any(abs(p[1]-center(p[0]))<7/scale for p in ring if 110<=p[0]<=1390):return
        if any(((p[0]-1390)/green_rx)**2+((p[1]-ys[-1])/green_ry)**2<1.4 for p in ring):return
        sand.append(ring);bunker_centers.append([x,y])
    # Staggered irregular complexes near approach and realistic driving/lay-up distances.
    count=11 if par==3 else 20 if index in (7,10,17) else 16
    for j in range(count):
        x=(1000+440*(j/(count-1))) if par==3 else (390+940*j/(count-1))
        side=-1 if j%2 else 1
        rx=(rng.uniform(12,25)/scale) if par!=3 else rng.uniform(26,50)
        ry=(rng.uniform(4,7)/scale) if par!=3 else rng.uniform(15,30)
        y=center(x)+side*(width(x)+ry*.60+(j%3)*6/scale)
        bunker(x,y,rx,ry,side*rng.uniform(-.4,.4))
    # Four separate greenside hazards and rear escape pockets, outside putting surface.
    for angle in (-1.2,-.45,.7,1.55,2.35,3.4,4.1):
        x=1390+math.cos(angle)*(green_rx+24);y=ys[-1]+math.sin(angle)*(green_ry+35)
        bunker(x,y,rng.uniform(22,38),rng.uniform(13,23),angle+.5)
    # Satellite sand pockets in the dune shoulders: not a repeated grid or single ring.
    for j in range(10 if par!=3 else 4):
        x=rng.uniform(440,1280);side=-1 if j%2 else 1
        y=center(x)+side*rng.uniform(110,175)
        bunker(x,y,rng.uniform(14,29),rng.uniform(10,20),rng.random()*3)
    # Shoreline alternates sides; four inland holes replace the lake with dune country.
    edge=[[0,0],[W,0],[W,H],[0,H]];water=[]
    bottom=index%2==0
    if index not in (4,8,10,13):
        coast=[]
        for k in range(49):
            x=W*k/48
            y=(680+18*math.sin(k*.48+index)) if bottom else (80+20*math.sin(k*.43+index))
            coast.append([x,y])
        water.append(coast+([[W,H],[0,H]] if bottom else [[W,0],[0,0]]))
    elif index==4:
        water.append(lobed(730,150,200,67,1.2,n=64))
        water.append(lobed(1110,620,160,55,2.1,n=64))
    surfaces=dict(fairway=[poly(fairway)],green=[poly(green)],tee=[poly(tee)],
                  sand=[poly(r) for r in sand],water=[poly(r) for r in water],nature=[poly(edge,[clearing])])
    identity=f'sheboygan-straits-{number:02d}-v1'
    c=dict(id=identity,name=NAMES[index],hole_number=number,par=par,yards=yard,tee_label='Blue',
        description=TIPS[index],strategy=TIPS[index],bunker_count=len(sand),
        tee=world(route[0]),pin=world(route[-1]),playing_line=[world(p) for p in (route if par!=3 else [route[0],route[-1]])],
        hazard_test_points=dict(sand=[world(p) for p in bunker_centers]),
        bounds=[-ty*scale,(H-ty)*scale,-tx*scale,(W-tx)*scale],boundary=poly(edge),surfaces=surfaces,
        image=dict(href=f'/assets/art/{identity}.png',width=W,height=H,transform=[scale,0,0,scale,-tx*scale,-ty*scale]),
        provenance=dict(kind='original_generated',created='2026-10-03',geometry_review='straits_bunker_complexes_v1',
            route_yards=yard,straight_yards=round(math.dist(route[0],route[-1])*scale,1),
            attribution='Sheboygan Straits · original lakeside design · AI artwork',
            inspiration_source=SOURCE,yardage_source=SCORECARD,scorecard_edition='Official Straits Blue scorecard, accessed 2026-10-03'),
        warnings=['Original course inspired by Whistling Straits; not a geographic reconstruction.',
                  'Blue yardages follow the published Straits scorecard. Map distances are straight line.',
                  'Flat greens and endpoint scoring. Dune heights and bunker faces are scenery, not simulated elevation.',
                  'Sand reduces the next shot by your configured percentage; water/OB replay with +1 penalty.'])
    l,r,n,f=c['bounds'];c['viewbox']=[n,l,f-n,r-l]
    validate_edits({k:c[k] for k in ('surfaces','boundary','tee','pin')})
    assert classify(c['tee'],c)=='tee',(number,'tee')
    assert classify(c['pin'],c)=='green',(number,'green')
    for point in c['hazard_test_points']['sand']:assert classify(point,c)=='sand',(number,point)
    assert len(sand)>=10,(number,len(sand))
    return c,dict(edge=edge,clearing=clearing,fairway=fairway,green=green,tee=tee,sand=sand,water=water)

def guides(c,p):
    from PIL import Image,ImageDraw
    im=Image.new('RGB',(W,H),'#a28e58');d=ImageDraw.Draw(im)
    def draw(r,fill):d.polygon([tuple(v) for v in r],fill=fill)
    draw(p['clearing'],'#71834c');draw(p['fairway'],'#548542');draw(p['green'],'#a5c56c');draw(p['tee'],'#a5c56c')
    for r in p['sand']:draw(r,'#eddbb6')
    for r in p['water']:draw(r,'#285e79')
    folder=ROOT/'designs/sheboygan-straits';folder.mkdir(exist_ok=True)
    im.save(folder/f"{c['id']}-guide.png")

if __name__=='__main__':
    holes=[]
    for i in range(18):
        c,p=build(i);holes.append(c)
        if '--guides' in sys.argv:guides(c,p)
    package=dict(id='sheboygan-straits-blue-v1',name='Sheboygan Straits',tee_label='Blue',par=sum(PARS),yards=sum(YARDS),
        description='Eighteen demanding links holes. Lake Michigan atmosphere, fescue dunes and intricate bunker complexes.',
        holes=holes,version=1)
    (ROOT/'courses/sheboygan-straits-blue-v1.json').write_text(json.dumps(package,indent=2)+'\n',encoding='utf-8')
    print('Built',len(holes),'holes;',sum(YARDS),'yards; par',sum(PARS),'bunkers',[c['bunker_count'] for c in holes])
