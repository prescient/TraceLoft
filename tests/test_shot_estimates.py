"""Per-shot flight and club delivery estimates for every non-putt shot (D71)."""

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import migrations.v0007_shot_estimates as v0007
from shot_schema import is_putt
from storage import Store

# rēlā/LPi chip, 2026-10-16 (rela.log shot 7): slow, but it spins and launches.
CHIP = dict(ball_speed=11.11, launch_ang=27.36, launch_dir=-8.25, total_spin=999.52, spin_axis=17.17,
            back_spin=955, side_spin=295, club_speed=10.79, attack_angle=-6.63, club_path=-13.05)
PUTT = dict(ball_speed=4.29, launch_ang=0.2, launch_dir=-11.07, total_spin=None, spin_axis=None,
            back_spin=None, side_spin=None)


class ShotEstimateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / 'golfdata.sqlite3')
        self.c = self.store.connection
        self.seq = 0

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def ingest(self, vals, club=''):
        self.seq += 1
        event = dict(kind='record', receipt_id=f'r{self.seq}', producer_id='p', session_id='s',
                     seq=self.seq, result='validated', vals=vals, club=club,
                     captured_at=datetime.now(timezone.utc).isoformat(),
                     source_configuration=dict(acquisition='test'), mapping_id='traceloft.normalized.v1')
        self.store.ingest(event)
        return self.c.execute('SELECT id FROM shots WHERE event_id=?', (f'r{self.seq}',)).fetchone()[0]

    def selected(self, shot_id):
        return {
            row['model_family']: row
            for row in self.c.execute(
                "SELECT d.* FROM derived_metric_selection s JOIN shot_derived_metrics d USING(result_id) "
                "WHERE s.shot_id=? AND s.context_id='shot'",
                (shot_id,),
            )
        }

    def test_a_chip_outside_any_session_gets_flight_and_club_estimates(self):
        results = self.selected(self.ingest(CHIP))
        self.assertEqual(set(results), {'source_features', 'flight', 'club_delivery'})
        flight, club = results['flight'], results['club_delivery']
        self.assertEqual(flight['status'], 'ready')
        self.assertGreater(flight['carry_distance_yd'], 1)
        self.assertLess(flight['carry_distance_yd'], 5)
        self.assertEqual(club['status'], 'ready')
        # Iron weights (k 0.75, a 0.78), not the putter weights the < 25 mph rule would pick.
        self.assertAlmostEqual(club['face_angle_deg'], (-8.25 - 0.25 * -13.05) / 0.75)
        self.assertAlmostEqual(club['dynamic_loft_deg'], (27.36 - 0.22 * -6.63) / 0.78)
        self.assertIn('default_non_putt', club['artifact_json'])
        # Never written into the measurements.
        report = self.c.execute('SELECT * FROM shot_source_metrics').fetchone()
        self.assertIsNone(report['carry_distance_yd'])
        # The readable per-shot view: one row, source columns beside the estimates.
        row, = self.c.execute('SELECT * FROM v_shots_analysis').fetchall()
        self.assertIsNone(row['carry_distance_yd'])
        self.assertEqual(row['model_carry_distance_yd'], flight['carry_distance_yd'])
        self.assertEqual(row['est_face_angle_deg'], club['face_angle_deg'])
        self.assertAlmostEqual(row['calculated_smash_factor'], 11.11 / 10.79)

    def test_putts_get_no_estimates(self):
        self.assertTrue(is_putt(PUTT))
        self.assertTrue(is_putt(dict(CHIP), 'PT'))                # tagged putter
        self.assertTrue(is_putt(dict(CHIP, total_spin=0, back_spin=0, side_spin=0)))
        self.assertFalse(is_putt(CHIP))
        self.assertEqual(set(self.selected(self.ingest(PUTT))), {'source_features'})

    def test_club_estimate_without_club_data_is_stored_as_unavailable(self):
        vals = {k: v for k, v in CHIP.items() if k not in ('club_speed', 'attack_angle', 'club_path')}
        club = self.selected(self.ingest(vals))['club_delivery']
        self.assertEqual(club['status'], 'unavailable')
        self.assertIsNone(club['face_angle_deg'])

    def test_a_failing_estimate_never_loses_the_shot(self):
        with patch('shot_schema.shot_estimates', side_effect=ValueError('boom')):
            shot_id = self.ingest(CHIP)
        self.assertEqual(self.store.count('shots'), 1)
        self.assertEqual(set(self.selected(shot_id)), {'source_features'})

    def test_upgrade_backfill_estimates_existing_shots_once(self):
        chip, putt = self.ingest(CHIP), self.ingest(PUTT)
        for table, where in (
            ('derived_metric_selection', "context_id='shot' AND model_family!='source_features'"),
            ('calculation_inputs', "result_id IN (SELECT result_id FROM shot_derived_metrics WHERE "
                                   "model_family IN ('flight','club_delivery'))"),
            ('shot_trajectories', "result_id IN (SELECT result_id FROM shot_derived_metrics WHERE "
                                  "model_family='flight')"),
            ('shot_derived_metrics', "model_family IN ('flight','club_delivery')"),
        ):
            self.c.execute(f'DELETE FROM {table} WHERE {where}')
        self.assertEqual(v0007.backfill(self.c), dict(shots=2, estimated=1))
        self.assertEqual(set(self.selected(chip)), {'source_features', 'flight', 'club_delivery'})
        self.assertEqual(set(self.selected(putt)), {'source_features'})
        before = self.c.execute('SELECT count(*) FROM shot_derived_metrics').fetchone()[0]
        v0007.backfill(self.c)  # idempotent: same inputs give the same result identities
        self.assertEqual(self.c.execute('SELECT count(*) FROM shot_derived_metrics').fetchone()[0], before)


if __name__ == '__main__':
    unittest.main()
