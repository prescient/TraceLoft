"""Read-only, paired mapping endpoints for the game's historical club preview."""
import math
from analysis import robust
from driving_range import effective_equipment
from flight_model import MODEL, finite


def build_preview(sessions, game):
    equipment = game.get('equipment_selection') or {}
    bag, club = equipment.get('bag_id'), equipment.get('club_id')
    result = dict(equipment=equipment, demo=bool(game.get('demo')), profiles=[], model=MODEL,
                  geometry=game['game_settings']['geometry'])
    if not bag or not club:
        return result
    groups = {}
    for session in sessions:
        kind = session.get('collection_kind')
        if kind not in ('bag', 'wedge') or bool(session.get('demo')) != result['demo'] or session.get('deleted'):
            continue
        for shot in session.get('shots', []):
            eq = effective_equipment(shot)
            if eq.get('bag_id') != bag or eq.get('club_id') != club:
                continue
            swing = shot.get('swing_label') or ''
            key = (kind, swing)
            if key not in groups:
                groups[key] = dict(id=kind+':'+swing, label=('Bag mapping' if kind=='bag' else 'Wedge matrix') +
                    (' / '+swing if swing else ' / unspecified swing'), excluded=0, removed=0, included=0,
                    views={v:dict(points=[], dates=[]) for v in ('reported_total','model_total','model_carry')})
            group = groups[key]
            if shot.get('removed'):
                group['removed'] += 1
                continue
            if shot.get('excluded'):
                group['excluded'] += 1
                continue
            group['included'] += 1
            vals = shot.get('vals', {})
            total, right = vals.get('total'), vals.get('offline')
            endpoints = {}
            if finite(total) and total >= 0 and finite(right):
                if result['geometry'] == 'downrange':
                    endpoints['reported_total'] = dict(forward=total, right=right)
                elif abs(right) <= total:
                    endpoints['reported_total'] = dict(forward=math.sqrt(total*total-right*right), right=right)
            flight = shot.get('flight') or {}
            if flight.get('status') == 'ready' and flight.get('model') == MODEL:
                for metric in ('carry', 'total'):
                    point = flight.get(metric+'_point_yd') or {}
                    if finite(point.get('forward')) and finite(point.get('right')) and point['forward'] >= 0:
                        endpoints['model_'+metric] = dict(forward=point['forward'], right=point['right'])
            for name, point in endpoints.items():
                group['views'][name]['points'].append(point)
                group['views'][name]['dates'].append(str(shot.get('captured') or session.get('started') or '')[:10])
    for group in groups.values():
        for view in group['views'].values():
            dates = sorted(d for d in view.pop('dates') if d)
            view.update(distance=robust(p['forward'] for p in view['points']),
                        date_from=dates[0] if dates else None, date_to=dates[-1] if dates else None,
                        missing=group['included']-len(view['points']))
        result['profiles'].append(group)
    result['profiles'].sort(key=lambda p:p['id'])
    return result
