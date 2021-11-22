from multiprocessing.queues import Queue

from django.core.cache import cache

from display.calculators.anr_corridor_calculator import AnrCorridorCalculator
from display.calculators.backtracking_and_procedure_turns import BacktrackingAndProcedureTurnsCalculator
from display.calculators.gatekeeper import Gatekeeper
from display.calculators.gatekeeper_landing import GatekeeperLanding
from display.calculators.gatekeeper_poker import GatekeeperPoker
from display.calculators.gatekeeper_route import GatekeeperRoute
from display.calculators.penalty_zone_calculator import PenaltyZoneCalculator
from display.calculators.prohibited_zone_calculator import ProhibitedZoneCalculator

from display.models import Contestant, Scorecard


def calculator_factory(contestant: "Contestant", live_processing: bool = True) -> "Gatekeeper":
    cache.delete(contestant.termination_request_key)
    if contestant.navigation_task.scorecard.calculator == Scorecard.PRECISION:
        return GatekeeperRoute(contestant,
                               [BacktrackingAndProcedureTurnsCalculator, ProhibitedZoneCalculator,
                                PenaltyZoneCalculator],
                               live_processing=live_processing)
    if contestant.navigation_task.scorecard.calculator in (Scorecard.ANR_CORRIDOR, Scorecard.AIRSPORTS):
        return GatekeeperRoute(contestant,
                               [BacktrackingAndProcedureTurnsCalculator, AnrCorridorCalculator,
                                ProhibitedZoneCalculator, PenaltyZoneCalculator],
                               live_processing=live_processing)
    if contestant.navigation_task.scorecard.calculator == Scorecard.LANDING:
        return GatekeeperLanding(contestant, [], live_processing=live_processing)
    if contestant.navigation_task.scorecard.calculator == Scorecard.POKER:
        return GatekeeperPoker(contestant, [], live_processing=live_processing)
    return GatekeeperRoute(contestant, [], live_processing=live_processing)
