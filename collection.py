"""Guided equipment collection on the range's durable lifecycle and cleanup model."""
import copy
import uuid
from pathlib import Path
from driving_range import DrivingRangeSession
from equipment import selection
from putting import timestamp

COLLECTION_FIELDS = ('collection_clubs', 'collection_samples', 'swing_labels')


class CollectionSession(DrivingRangeSession):
    def __init__(self, folder, catalog, bag_id, club_ids, samples=5, metric='carry',
                 demo=False, handedness='right_handed', store=None, swing_labels=None):
        if not isinstance(club_ids, list) or not 1 <= len(club_ids) <= 50 or len(set(club_ids)) != len(club_ids):
            raise ValueError('Select 1–50 distinct clubs for this collection.')
        if type(samples) is not int or not 2 <= samples <= 100 or metric not in ('carry', 'total'):
            raise ValueError('Choose 2–100 readings per club and carry or total.')
        if type(demo) is not bool or handedness not in ('right_handed', 'left_handed'):
            raise ValueError('Choose valid collection settings.')
        if swing_labels is not None:
            if (not isinstance(swing_labels,list) or not 1 <= len(swing_labels) <= 8
                    or any(not isinstance(s,str) or not 1<=len(s.strip())<=40 for s in swing_labels)
                    or len({s.strip().casefold() for s in swing_labels}) != len(swing_labels)):
                raise ValueError('Enter 1–8 distinct swing labels, each 1–40 characters.')
            swing_labels=[s.strip() for s in swing_labels]
        plan = [selection(catalog, bag_id, cid) for cid in club_ids]
        if any(not p or not p['club_id'] for p in plan):
            raise ValueError('Every planned club must belong to the selected bag.')
        self.folder, self.store = Path(folder), store
        self.data = dict(id=uuid.uuid4().hex, started=timestamp(), ended=None, drill='Bag mapping',
            practice_type='full_swing', session_kind='driving_range', collection_kind='bag',
            collection_plan=plan, collection_samples=samples, range_metric=metric,
            random_pace=False, target=0, range_target=0, range_width=30, range_depth=20,
            handedness=handedness, demo=demo, equipment_selection=copy.deepcopy(plan[0]),
            shots=[], cleanup_revision=0, cleanup_history=[])
        if swing_labels:
            self.data.update(drill='Wedge matrix',collection_kind='wedge',swing_labels=swing_labels,
                             swing_label=swing_labels[0])
        self.save()

    def add(self,event):
        context=copy.deepcopy(event.get('collection_context',{'swing_label':self.data.get('swing_label')})) or {}
        if not super().add(event):
            return False
        if self.data['collection_kind']=='wedge':
            label=context.get('swing_label')
            self.data['shots'][-1]['swing_label']=label if label in self.data['swing_labels'] else None
            self.save()
        return True
