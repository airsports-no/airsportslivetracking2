#
import datetime

from display.utilities.clone_object import simple_clone
from display.models import (
    GateScore,
    Scorecard,
    NavigationTask,
    TURNPOINT,
    TAKEOFF_GATE,
    LANDING_GATE,
    SECRETPOINT,
    FINISHPOINT,
    STARTINGPOINT,
    DUMMY,
    UNKNOWN_LEG,
)


def get_default_scorecard():
    Scorecard.objects.filter(name="Airsports Challenge 2023").update(name="Air Sport Challenge 2023")
    scorecard, created = Scorecard.objects.update_or_create(
        name="Air Sport Challenge 2023",
        defaults={
            "shortcut_name": "Air Sport  Challenge",
            "valid_from": datetime.datetime(2022, 1, 1, tzinfo=datetime.timezone.utc),
            "backtracking_penalty": 10,
            "backtracking_grace_time_seconds": 5,
            "backtracking_maximum_penalty": 100,
            "use_procedure_turns": False,
            "task_type": [NavigationTask.AIRSPORT_CHALLENGE],
            "calculator": NavigationTask.AIRSPORT_CHALLENGE,
            "corridor_maximum_penalty": -1,  # verified
            "corridor_outside_penalty": 1,  # verified
            "corridor_grace_time": 5,  # verified
            "below_minimum_altitude_penalty": 500,  # verified
            "below_minimum_altitude_maximum_penalty": 500,  # verified
            "prohibited_zone_penalty": 200,
            "prohibited_zone_grace_time": 5,
            "penalty_zone_grace_time": 5,
            "penalty_zone_penalty_per_second": 3,
            "penalty_zone_maximum": 100,
            "included_fields": [
                [
                    "Corridor penalties",
                    "corridor_grace_time",
                    "backtracking_penalty",
                    "corridor_outside_penalty",
                ],
                [
                    "Prohibited zone",
                    "prohibited_zone_grace_time",
                    "prohibited_zone_penalty",
                ],
                [
                    "Penalty zone",
                    "penalty_zone_grace_time",
                    "penalty_zone_penalty_per_second",
                    "penalty_zone_maximum",
                ],
            ],
        },
    )

    regular_gate_score = GateScore.objects.update_or_create(
        scorecard=scorecard,
        gate_type=TURNPOINT,
        defaults={
            "extended_gate_width": 0,
            "bad_crossing_extended_gate_penalty": 0,
            "graceperiod_before": 2,
            "graceperiod_after": 2,
            "maximum_penalty": 200,
            "penalty_per_second": 2,
            "missed_penalty": 100,
            "backtracking_after_steep_gate_grace_period_seconds": 0,
            "backtracking_before_gate_grace_period_nm": 0.5,
            "backtracking_after_gate_grace_period_nm": 0.5,
            "missed_procedure_turn_penalty": 0,
            "included_fields": [
                [
                    "Penalties",
                    "penalty_per_second",
                    "maximum_penalty",
                    "missed_penalty",
                ],
                ["Time limits", "graceperiod_before", "graceperiod_after"],
            ],
        },
    )[0]

    GateScore.objects.update_or_create(
        scorecard=scorecard,
        gate_type=SECRETPOINT,
        defaults={
            "extended_gate_width": 0,
            "bad_crossing_extended_gate_penalty": 0,
            "graceperiod_before": 2,
            "graceperiod_after": 2,
            "maximum_penalty": 200,
            "penalty_per_second": 1,
            "missed_penalty": 100,
            "backtracking_after_steep_gate_grace_period_seconds": 0,
            "backtracking_before_gate_grace_period_nm": 0.5,
            "backtracking_after_gate_grace_period_nm": 0.5,
            "missed_procedure_turn_penalty": 0,
            "included_fields": [
                [
                    "Penalties",
                    "penalty_per_second",
                    "maximum_penalty",
                    "missed_penalty",
                ],
                ["Time limits", "graceperiod_before", "graceperiod_after"],
            ],
        },
    )

    GateScore.objects.update_or_create(
        scorecard=scorecard,
        gate_type=TAKEOFF_GATE,
        defaults={
            "extended_gate_width": 0,
            "bad_crossing_extended_gate_penalty": 0,
            "graceperiod_after": 60,  # verified
            "graceperiod_before": 3,  # verified
            "maximum_penalty": 200,  # verified
            "backtracking_after_steep_gate_grace_period_seconds": 0,
            "backtracking_after_gate_grace_period_nm": 0.5,
            "penalty_per_second": 200,  # verified
            "missed_penalty": 0,
            "missed_procedure_turn_penalty": 0,
            "included_fields": [
                ["Penalties", "maximum_penalty", "missed_penalty"],
                ["Time limits", "graceperiod_before", "graceperiod_after"],
            ],
        },
    )

    GateScore.objects.update_or_create(
        scorecard=scorecard,
        gate_type=LANDING_GATE,
        defaults={
            "extended_gate_width": 0,
            "bad_crossing_extended_gate_penalty": 0,
            "graceperiod_before": 9999999999,
            "graceperiod_after": 0,
            "backtracking_after_steep_gate_grace_period_seconds": 0,
            "backtracking_after_gate_grace_period_nm": 0.5,
            "maximum_penalty": 0,
            "penalty_per_second": 0,
            "missed_penalty": 0,
            "missed_procedure_turn_penalty": 0,
            "included_fields": [["Penalties", "maximum_penalty", "missed_penalty"]],
        },
    )

    GateScore.objects.update_or_create(
        scorecard=scorecard,
        gate_type=STARTINGPOINT,
        defaults={
            "extended_gate_width": 0.6,  # verified
            "bad_crossing_extended_gate_penalty": 0,
            "graceperiod_before": 2,  # verified
            "graceperiod_after": 2,  # verified
            "backtracking_after_steep_gate_grace_period_seconds": 0,
            "backtracking_after_gate_grace_period_nm": 0.5,
            "maximum_penalty": 200,  # verified
            "penalty_per_second": 2,  # verified
            "missed_penalty": 100,  # verified
            "missed_procedure_turn_penalty": 0,
            "included_fields": [
                [
                    "Penalties",
                    "penalty_per_second",
                    "maximum_penalty",
                    "missed_penalty",
                    "bad_crossing_extended_gate_penalty",
                ],
                ["Time limits", "graceperiod_before", "graceperiod_after"],
            ],
        },
    )
    scorecard.gatescore_set.filter(gate_type__in=(FINISHPOINT,)).delete()
    simple_clone(regular_gate_score, {"gate_type": FINISHPOINT})
    scorecard.gatescore_set.filter(gate_type__in=(DUMMY, UNKNOWN_LEG)).delete()
    simple_clone(regular_gate_score, {"gate_type": DUMMY})
    simple_clone(regular_gate_score, {"gate_type": UNKNOWN_LEG})

    return scorecard
