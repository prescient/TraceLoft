"""Shared polygon semantics for versioned original and imported courses (yards)."""
import math


def in_ring(point, ring):
    x,y=point; result=False
    for a,b in zip(ring,ring[1:]+ring[:1]):
        dx,dy=b[0]-a[0],b[1]-a[1]
        cross=(x-a[0])*dy-(y-a[1])*dx
        if abs(cross)<=1e-8 and min(a[0],b[0])-1e-8<=x<=max(a[0],b[0])+1e-8 and min(a[1],b[1])-1e-8<=y<=max(a[1],b[1])+1e-8:
            return True
        if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:result=not result
    return result


def in_polygon(point, polygon):
    return in_ring(point,polygon['outer']) and not any(in_ring(point,h) for h in polygon.get('holes',[]))


def on_surface(point, course, name):
    if 'surfaces' in course:
        return any(in_polygon(point,p) for p in course['surfaces'].get(name,[]))
    if name=='fairway':return in_ring(point,course['fairway'])
    if name=='green':return math.dist(point,course['pin'])<=course['green_radius']
    if name=='tee':return math.dist(point,course['tee'])<=4
    if name=='nature':return abs(point[0])>60
    return any(math.dist(point,h['center'])<=h['radius'] for h in course.get(name,[]))


def classify(point, course):
    x,y=point;left,right,near,far=course['bounds']
    if not(left<=x<=right and near<=y<=far) or (course.get('boundary') and not in_polygon(point,course['boundary'])):
        return 'out of bounds'
    for name in ('water','sand','green','tee','fairway','nature'):
        if on_surface(point,course,name):return name
    return 'rough'
