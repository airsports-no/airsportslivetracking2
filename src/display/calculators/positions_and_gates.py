import logging
from datetime import timedelta, datetime
from typing import Tuple, List, Optional

import dateutil

from display.convert_flightcontest_gpx import Waypoint
from display.coordinate_utilities import line_intersect, fraction_of_leg, calculate_bearing
from display.models import bearing_difference

logger = logging.getLogger(__name__)


class Position:
    def __init__(self, time, latitude, longitude, altitude, speed, course, battery_level):
        self.time = dateutil.parser.parse(time)
        self.latitude = latitude
        self.longitude = longitude
        self.altitude = altitude
        self.speed = speed
        self.course = course
        self.battery_level = battery_level


class Gate:
    def __init__(self, gate: Waypoint, expected_time,
                 gate_line_extended: Tuple[Tuple[float, float], Tuple[float, float]]):
        self.name = gate.name
        self.gate_line = gate.gate_line
        self.gate_line_infinite = gate.gate_line_infinite
        self.gate_line_extended = gate_line_extended

        self.type = gate.type
        self.latitude = gate.latitude
        self.longitude = gate.longitude
        self.inside_distance = gate.inside_distance
        self.outside_distance = gate.outside_distance
        self.gate_check = gate.gate_check
        self.time_check = gate.time_check
        self.distance = gate.distance_next
        self.bearing = gate.bearing_next
        self.is_procedure_turn = gate.is_procedure_turn
        self.passing_time = None
        self.extended_passing_time = None
        self.missed = False
        self.maybe_missed_time = None
        self.expected_time = expected_time

    def __str__(self):
        return self.name

    def has_been_passed(self):
        return self.missed or self.passing_time is not None

    def has_extended_been_passed(self):
        return self.extended_passing_time is not None

    def is_passed_in_correct_direction_bearing(self, track_bearing) -> bool:
        return abs(bearing_difference(track_bearing, self.bearing)) < 90

    def is_passed_in_correct_direction_track(self, track) -> bool:
        if len(track) > 1:
            return self.is_passed_in_correct_direction_bearing(
                calculate_bearing((track[-2].latitude, track[-2].longitude), (track[-1].latitude, track[-1].longitude)))
        return False

    def get_gate_intersection_time(self, track: List[Position]) -> Optional[datetime]:
        if len(track) > 1:
            return get_intersect_time(track[-2], track[-1], self.gate_line[0], self.gate_line[1])
        return None

    def get_gate_infinite_intersection_time(self, track: List[Position]) -> Optional[datetime]:
        if len(track) > 1:
            return get_intersect_time(track[-2], track[-1], self.gate_line_infinite[0], self.gate_line_infinite[1])
        return None

    def get_gate_extended_intersection_time(self, track: List[Position]) -> Optional[datetime]:
        if len(track) > 1 and self.gate_line_extended:
            return get_intersect_time(track[-2], track[-1], self.gate_line_extended[0], self.gate_line_extended[1])
        return None


def get_intersect_time(track_segment_start: Position, track_segment_finish: Position, gate_start, gate_finish) -> \
        Optional[datetime]:
    intersection = line_intersect(track_segment_start.longitude, track_segment_start.latitude,
                                  track_segment_finish.longitude,
                                  track_segment_finish.latitude, gate_start[1], gate_start[0], gate_finish[1],
                                  gate_finish[0])

    if intersection:
        fraction = fraction_of_leg(track_segment_start.longitude, track_segment_start.latitude,
                                   track_segment_finish.longitude,
                                   track_segment_finish.latitude, intersection[0], intersection[1])
        time_difference = (track_segment_finish.time - track_segment_start.time).total_seconds()
        return track_segment_start.time + timedelta(seconds=fraction * time_difference)
    return None
