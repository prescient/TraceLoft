import unittest
from unittest.mock import patch
from tests import test_sql_analytics
from recalculation import calculate
from shot_schema import evidence_manifest


class RecalculationTests(unittest.TestCase):
    setUp=test_sql_analytics.SQLAnalyticsTests.setUp

    def stage(self,family='flight',**kw):return self.store.stage_calculations(family,dict(mode='demo'),**kw)

    def publish(self,b):return self.store.publish_calculations(b['batch_id'],b['selection_token'])

    def test_preview_publish_history_and_historical_pins(self):
        original=self.store.load_session(self.sid);evidence=evidence_manifest(self.store.connection)
        old_median=self.store.analysis(dict(mode='demo',basis='flight'))['selected']['total']['median']
        def changed(*args):
            art,vals=calculate(*args);vals['total_distance_yd']+=10;return art,vals
        with patch('recalculation.calculate',side_effect=changed):b=self.stage()
        self.assertTrue(b['publishable']);self.assertEqual(b['coverage']['ready'],5)
        self.assertEqual(self.store.load_session(self.sid),original)
        self.assertTrue(all(d['changes']['total_distance_yd']['after']-d['changes']['total_distance_yd']['before']==10 for d in b['differences']))
        self.publish(b);self.assertEqual(self.store.load_session(self.sid),original)
        after_evidence=evidence_manifest(self.store.connection)
        self.assertEqual({k:v for k,v in after_evidence.items() if k!='audit_events'},{k:v for k,v in evidence.items() if k!='audit_events'})
        after=self.store.analysis(dict(mode='demo',basis='flight'))
        self.assertAlmostEqual(after['selected']['total']['median'],old_median+10)
        h=self.store.calculation_history(b['differences'][0]['shot_id']);self.assertTrue(any(r['batch_id']==b['batch_id'] and r['selected_for_analysis'] for r in h))
        self.assertTrue(all(r['code_hash'] for r in h if r['batch_id']))
        self.assertIn('equipment_context_id',self.store.calculation_history_csv())
        self.assertEqual(self.store.connection.execute('PRAGMA foreign_key_check').fetchall(),[])

    def test_interruption_resume_is_idempotent(self):
        count=0
        def interrupt(*args):
            nonlocal count
            count+=1
            if count==2:raise KeyboardInterrupt()
            return calculate(*args)
        with patch('recalculation.calculate',side_effect=interrupt):
            with self.assertRaises(KeyboardInterrupt):self.stage()
        b=self.store.calculation_batches()[0];self.assertEqual(b['status'],'staging')
        partial=self.store.calculation_snapshot(b['batch_id']);self.assertEqual(partial['processed'],1)
        with self.assertRaises(ValueError):self.publish(partial)
        done=self.store.resume_calculations(b['batch_id']);self.assertTrue(done['publishable'])
        count=self.store.connection.execute('SELECT count(*) FROM shot_derived_metrics').fetchone()[0]
        self.assertEqual(self.store.resume_calculations(b['batch_id']),done);self.assertEqual(self.store.connection.execute('SELECT count(*) FROM shot_derived_metrics').fetchone()[0],count)

    def test_missing_inputs_or_errors_cannot_replace_selection(self):
        before=list(self.store.connection.execute('SELECT * FROM derived_metric_selection'))
        with patch('recalculation.calculate',return_value=(dict(status='unavailable',reason='Missing spin'),{})):b=self.stage()
        self.assertEqual(b['coverage']['unavailable'],5);self.assertFalse(b['publishable'])
        with self.assertRaises(ValueError):self.publish(b)
        with patch('recalculation.calculate',side_effect=RuntimeError('failed model')):bad=self.stage()
        self.assertEqual(bad['status'],'error')
        with self.assertRaises(ValueError):self.publish(bad)
        self.assertEqual(list(self.store.connection.execute('SELECT * FROM derived_metric_selection')),before)

    def test_stale_cleanup_owner_and_selection_token_guards(self):
        b=self.stage();other=self.stage('source_features');self.publish(other)
        # A competing flight publication invalidates a previously reviewed token.
        with patch('recalculation.calculate',return_value=(dict(status='ready'),dict(total_distance_yd=200))):new=self.stage()
        self.publish(new)
        with self.assertRaises(ValueError):self.publish(b)
        fresh=self.store.calculation_snapshot(b['batch_id']);self.publish(fresh)
        shot=self.service.practice.data['shots'][0]
        self.client.post(f'/api/range/{self.sid}/cleanup',json=dict(action='exclude',keys=[shot['key']],revision=0,reason='Warmup'))
        stale=self.store.calculation_snapshot(b['batch_id']);self.assertGreater(stale['stale'],0)
        with self.assertRaises(ValueError):self.publish(stale)
        uid=self.store.create_user('Other');self.store.select_user(uid)
        with self.assertRaises(ValueError):self.store.calculation_snapshot(b['batch_id'])

    def test_putting_method_change_preserves_review(self):
        self.client.post(f'/api/practice/{self.sid}/finish',json={})
        r=self.client.post('/api/practice',json=dict(drill='Pace consistency',target_mode='distance',demo=True))
        self.assertEqual(r.status_code,200,r.text)
        sid=self.service.practice.data['id']
        # Use the same public shot ingestion path as putting tests.
        self.assertTrue(self.service.practice.add(dict(session_id='demo',seq=1,result='validated',vals=dict(ball_speed=3,launch_dir=0,launch_ang=0))))
        self.service.practice.save();original=self.store.load_session(sid)
        from putting_distance import MODEL_ID
        b=self.store.stage_calculations('putting',dict(mode='real',kind='putting',sessions=sid),MODEL_ID)
        self.assertTrue(b['publishable']);self.publish(b)
        self.assertEqual(self.store.load_session(sid),original)
        self.assertTrue(any(d['changes'].get('estimated_distance_ft') for d in b['differences']))

    def test_source_selection_survives_save_and_cancel_cannot_publish(self):
        with patch('recalculation.calculate',return_value=(dict(status='ready'),dict(source_rollout_yd=123))):b=self.stage('source_features')
        self.publish(b)
        self.service.practice.save()
        self.assertEqual(self.store.analysis(dict(mode='demo',basis='flight',metric='source_rollout_yd'))['selected']['source_rollout_yd']['median'],123)
        from recalculation import cancel
        pending=self.stage('source_features');cancelled=cancel(self.store,pending['batch_id'])
        self.assertEqual(cancelled['status'],'cancelled')
        with self.assertRaises(ValueError):self.publish(cancelled)
        self.assertEqual(self.store.connection.execute('PRAGMA foreign_key_check').fetchall(),[])


if __name__=='__main__':unittest.main()
