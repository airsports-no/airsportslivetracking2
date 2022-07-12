#
from display.clone_object import simple_clone
from display.models import (
    GateScore,
    Scorecard,
    NavigationTask,
    TURNPOINT,
    TAKEOFF_GATE,
    LANDING_GATE,
    SECRETPOINT,
    FINISHPOINT,
    STARTINGPOINT, DUMMY, UNKNOWN_LEG,
)


# No procedure turn
# Extended starting gate 2NM
# No penalty for backtracking within 45 seconds for more than 90° turns


def get_default_scorecard():
    scorecard, created = Scorecard.objects.update_or_create(
        name="FAI Air Rally 2020",
        defaults={
            "shortcut_name": "FAI Air Rally",
            "backtracking_penalty": 100,
            "backtracking_grace_time_seconds": 5,
            "backtracking_maximum_penalty": 1000,
            "use_procedure_turns": False,
            "task_type": [NavigationTask.PRECISION],
            "calculator": Scorecard.PRECISION,
            "prohibited_zone_penalty": 0,
            "included_fields": [
                [
                    "Backtracking",
                    "backtracking_penalty",
                    "backtracking_grace_time_seconds",
                    "backtracking_maximum_penalty",
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

    regular_gate_score, created = GateScore.objects.update_or_create(
        scorecard=scorecard,
        gate_type=TURNPOINT,
        defaults={
            "extended_gate_width": 0.3,
            "bad_crossing_extended_gate_penalty": 0,
            "graceperiod_before": 2,
            "graceperiod_after": 2,
            "maximum_penalty": 100,
            "penalty_per_second": 3,
            "missed_penalty": 100,
            "missed_procedure_turn_penalty": 0,
            "backtracking_after_steep_gate_grace_period_seconds": 45,
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
            "graceperiod_before": 0,
            "graceperiod_after": 60,
            "maximum_penalty": 100,
            "penalty_per_second": 3,
            "missed_penalty": 0,
            "missed_procedure_turn_penalty": 0,
            "backtracking_after_steep_gate_grace_period_seconds": 0,
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
            "graceperiod_before": 0,
            "graceperiod_after": 60,
            "maximum_penalty": 0,
            "penalty_per_second": 0,
            "missed_penalty": 0,
            "missed_procedure_turn_penalty": 0,
            "backtracking_after_steep_gate_grace_period_seconds": 0,
            "included_fields": [["Penalties", "maximum_penalty", "missed_penalty"]],
        },
    )
    scorecard.gatescore_set.filter(
        gate_type__in=(SECRETPOINT, FINISHPOINT, STARTINGPOINT)
    ).delete()
    simple_clone(regular_gate_score, {"gate_type": SECRETPOINT})
    simple_clone(regular_gate_score, {"gate_type": FINISHPOINT})
    simple_clone(regular_gate_score, {"gate_type": STARTINGPOINT})
    scorecard.gatescore_set.filter(gate_type__in=(DUMMY, UNKNOWN_LEG)).delete()
    simple_clone(regular_gate_score, {"gate_type": DUMMY})
    simple_clone(regular_gate_score, {"gate_type": UNKNOWN_LEG})

    return scorecard
