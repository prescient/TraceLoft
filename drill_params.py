"""Typed launch parameters for each scorer, and the API envelope derived from them.

Each scorer declares exactly the request fields it uses, with their bounds and defaults. Fields
shared by several scorers (equipment choice, demo, handedness, Stimp, distance metric) are
declared once in a mixin. `PracticeParams`, the body of POST /api/practice, is the union of
every scorer's fields with unknown keys rejected, so a new drill only declares its own model.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, create_model

from putting_distance import DEFAULT_MODEL_ID


class DrillParams(BaseModel):
    # The envelope rejects unknown keys; a scorer ignores the other scorers' fields.
    model_config = ConfigDict(extra='ignore')
    drill: str


class EquipmentChoice(BaseModel):
    range_bag_id: str = Field(default='', max_length=32)
    range_club_id: str = Field(default='', max_length=32)


class DemoChoice(BaseModel):
    demo: bool = False


class Handedness(BaseModel):
    handedness: str = 'right_handed'


class GreenSpeed(BaseModel):
    stimp: float = Field(default=10, ge=3, le=20, allow_inf_nan=False)


class DistanceMetric(BaseModel):
    range_metric: str = 'carry'


class PuttingParams(GreenSpeed, DrillParams):
    target: float = Field(default=4, gt=0, allow_inf_nan=False)
    speed_tolerance: float = Field(default=0.3, ge=0, allow_inf_nan=False)
    angle_tolerance: float = Field(default=1, ge=0, allow_inf_nan=False)
    repetitions: int = Field(default=10, ge=1, le=1000)
    random_pace: bool = False
    minimum: float = Field(default=3, allow_inf_nan=False)
    maximum: float = Field(default=6, allow_inf_nan=False)
    target_mode: str = 'speed'
    target_distance: float = Field(default=10, ge=0.5, le=300, allow_inf_nan=False)
    distance_tolerance: float = Field(default=2, ge=0, le=100, allow_inf_nan=False)
    ladder_start: float = Field(default=5, ge=0.5, le=300, allow_inf_nan=False)
    ladder_end: float = Field(default=25, ge=0.5, le=300, allow_inf_nan=False)
    ladder_step: float = Field(default=5, ge=0.5, le=300, allow_inf_nan=False)
    ladder_rounds: int = Field(default=2, ge=1, le=100)
    ladder_direction: str = 'ascending'
    distance_model: str = DEFAULT_MODEL_ID


class DistanceLadderParams(EquipmentChoice, DistanceMetric, DrillParams):
    range_start: float = Field(default=30, ge=1, le=600, allow_inf_nan=False)
    range_end: float = Field(default=100, ge=1, le=600, allow_inf_nan=False)
    range_step: float = Field(default=10, ge=1, le=600, allow_inf_nan=False)
    range_shots: int = Field(default=1, ge=1, le=100)
    range_rounds: int = Field(default=2, ge=1, le=100)
    range_tolerance: float = Field(default=5, ge=0, le=100, allow_inf_nan=False)
    range_order: str = 'ascending'
    range_category: str = 'wedges'
    range_club: str = Field(default='', max_length=80)


class TargetWindow(BaseModel):
    range_width: float = Field(default=30, ge=1, le=200, allow_inf_nan=False)
    range_depth: float = Field(default=20, ge=1, le=200, allow_inf_nan=False)


class RangeParams(EquipmentChoice, DemoChoice, Handedness, TargetWindow, DrillParams):
    range_target: float = Field(default=150, ge=0, le=450, allow_inf_nan=False)


class RandomDistanceParams(EquipmentChoice, DemoChoice, Handedness, TargetWindow, DrillParams):
    random_min: float = Field(default=60, ge=1, le=450, allow_inf_nan=False)
    random_max: float = Field(default=180, ge=1, le=450, allow_inf_nan=False)
    random_step: float = Field(default=5, ge=1, le=50, allow_inf_nan=False)
    random_gap: float = Field(default=15, ge=0, le=200, allow_inf_nan=False)
    random_count: int = Field(default=20, ge=1, le=200)


class CollectionParams(EquipmentChoice, DistanceMetric, DemoChoice, Handedness, DrillParams):
    swing_labels: list[str] = Field(
        default_factory=lambda: ['Half', 'Three-quarter', 'Full'], max_length=8
    )
    collection_clubs: list[str] = Field(default_factory=list, max_length=50)
    collection_samples: int = Field(default=5, ge=2, le=100)


class GolfParams(EquipmentChoice, DemoChoice, GreenSpeed, DrillParams):
    game_rough: float = Field(default=7, ge=0, le=60, allow_inf_nan=False)
    game_sand: float = Field(default=20, ge=0, le=80, allow_inf_nan=False)
    game_rollout_rough: float = Field(default=75, ge=0, le=100, allow_inf_nan=False)
    game_rollout_ob: float = Field(default=100, ge=0, le=100, allow_inf_nan=False)
    game_variation: float = Field(default=0, ge=0, le=10, allow_inf_nan=False)
    game_gimme: float = Field(default=3, ge=0, le=10, allow_inf_nan=False)
    game_course_id: str = Field(default='pebble-boulder-blue-v3', max_length=80)
    game_holes: Literal['full', 'front', 'back'] = 'full'
    game_geometry: str = 'downrange'
    game_acknowledged: bool = False


SCORER_PARAMS = (
    PuttingParams,
    DistanceLadderParams,
    RangeParams,
    RandomDistanceParams,
    CollectionParams,
    GolfParams,
)


def envelope(models, name='PracticeParams'):
    """Union of the models' fields, rejecting unknown keys.

    A field shared by several models must be declared identically (use a mixin); a conflicting
    redefinition is a programming error and fails at import time.
    """
    fields = {}
    for model in models:
        for field, info in model.model_fields.items():
            if field in fields:
                if repr(fields[field]) != repr(info):
                    raise TypeError(f'{model.__name__}.{field} conflicts with another drill.')
                continue
            fields[field] = info
    return create_model(
        name,
        __config__=ConfigDict(extra='forbid'),
        **{field: (info.annotation, info) for field, info in fields.items()},
    )


PracticeParams = envelope(SCORER_PARAMS)
