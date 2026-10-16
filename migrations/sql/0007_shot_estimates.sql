
ALTER TABLE shot_derived_metrics ADD COLUMN face_angle_deg REAL;
ALTER TABLE shot_derived_metrics ADD COLUMN face_to_path_deg REAL;
ALTER TABLE shot_derived_metrics ADD COLUMN dynamic_loft_deg REAL;
ALTER TABLE shot_derived_metrics ADD COLUMN spin_loft_deg REAL;
ALTER TABLE shot_derived_metrics ADD COLUMN face_to_path_from_spin_deg REAL;
DROP VIEW v_shots_analysis;
CREATE VIEW v_shots_analysis AS
 SELECT s.*,
 sf.result_id source_features_result_id,sf.absolute_offline_yd,sf.calculated_smash_factor,sf.source_rollout_yd,
 fl.result_id flight_result_id,fl.status flight_status,fl.reason flight_reason,
 fl.carry_distance_yd model_carry_distance_yd,fl.total_distance_yd model_total_distance_yd,
 fl.offline_distance_yd model_offline_distance_yd,fl.apex_ft model_apex_ft,
 fl.descent_angle_deg model_descent_angle_deg,fl.hang_time_s model_hang_time_s,fl.flight_shape,
 cd.result_id club_result_id,cd.status club_estimate_status,cd.reason club_estimate_reason,
 cd.face_angle_deg est_face_angle_deg,cd.face_to_path_deg est_face_to_path_deg,
 cd.dynamic_loft_deg est_dynamic_loft_deg,cd.spin_loft_deg est_spin_loft_deg,
 cd.face_to_path_from_spin_deg est_face_to_path_from_spin_deg
 FROM v_shots_source s
 LEFT JOIN derived_metric_selection psf ON psf.shot_id=s.shot_id AND psf.model_family='source_features' AND psf.context_id='shot'
 LEFT JOIN shot_derived_metrics sf ON sf.result_id=psf.result_id
 LEFT JOIN derived_metric_selection pfl ON pfl.shot_id=s.shot_id AND pfl.model_family='flight' AND pfl.context_id='shot'
 LEFT JOIN shot_derived_metrics fl ON fl.result_id=pfl.result_id
 LEFT JOIN derived_metric_selection pcd ON pcd.shot_id=s.shot_id AND pcd.model_family='club_delivery' AND pcd.context_id='shot'
 LEFT JOIN shot_derived_metrics cd ON cd.result_id=pcd.result_id;
