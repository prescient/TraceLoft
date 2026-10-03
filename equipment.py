"""Small versioned bag catalog; captured selections are immutable name snapshots."""
import copy
import uuid

COMMON_CLUBS = ('Driver', '3 wood', '5 wood', '4 hybrid', '4 iron', '5 iron', '6 iron',
                '7 iron', '8 iron', '9 iron', 'PW', 'GW', 'SW', 'LW', 'Putter')
CATALOG_KEY = 'equipment_catalog.v1'


def text(value, label):
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > 80:
        raise ValueError(f'{label} must be 1–80 characters.')
    return value.strip()


def new_bag(name):
    return dict(id=uuid.uuid4().hex, name=text(name, 'Bag name'),
                clubs=[dict(id=uuid.uuid4().hex, label=label) for label in COMMON_CLUBS])


def default_catalog():
    return dict(version=1, revision=1, bags=[new_bag('My bag')])


def edit_catalog(catalog, revision, name, bag_id=None, clubs=None):
    if revision != catalog['revision']:
        raise ValueError('Bags changed in another browser. Close and reopen Manage bags to refresh.')
    updated = copy.deepcopy(catalog)
    name = text(name, 'Bag name')
    if any(b['name'].casefold() == name.casefold() and b['id'] != bag_id for b in updated['bags']):
        raise ValueError('Choose a different bag name.')
    if bag_id is None:
        if len(updated['bags']) >= 50:
            raise ValueError('At most 50 bags are supported.')
        bag = new_bag(name)
        updated['bags'].append(bag)
    else:
        bag = next((b for b in updated['bags'] if b['id'] == bag_id), None)
        if not bag:
            raise ValueError('Bag not found. Refresh your bags.')
        if not isinstance(clubs, list) or not 1 <= len(clubs) <= 50:
            raise ValueError('Keep 1–50 clubs in each bag.')
        allowed = {c['id'] for c in bag['clubs']}
        result, ids, labels = [], set(), set()
        for c in clubs:
            cid = c.get('id') or uuid.uuid4().hex
            label = text(c.get('label'), 'Club name')
            if c.get('id') and cid not in allowed:
                raise ValueError('Club does not belong to this bag.')
            if cid in ids or label.casefold() in labels:
                raise ValueError('Use distinct club names and identities within a bag.')
            ids.add(cid); labels.add(label.casefold())
            result.append(dict(id=cid, label=label))
        bag.update(name=name, clubs=result)
    updated['revision'] += 1
    return updated, bag['id']


def selection(catalog, bag_id='', club_id=''):
    if not bag_id:
        if club_id:
            raise ValueError('Choose a bag before choosing a club.')
        return None
    bag = next((b for b in catalog['bags'] if b['id'] == bag_id), None)
    if not bag:
        raise ValueError('Bag not found. Refresh your bags.')
    club = next((c for c in bag['clubs'] if c['id'] == club_id), None) if club_id else None
    if club_id and not club:
        raise ValueError('Club does not belong to this bag. Choose it again.')
    return dict(bag_id=bag_id, bag_name=bag['name'], club_id=club_id,
                club_label=club['label'] if club else '', catalog_revision=catalog['revision'],
                selection_mode='manual')
