import datetime
from typing import List, Tuple
from unittest.mock import Mock, patch

import dateutil
from django.test import TransactionTestCase

from display.calculators.anr_corridor_calculator import AnrCorridorCalculator
from display.calculators.calculator_factory import calculator_factory
from display.calculators.calculator_utilities import load_track_points_traccar_csv
from display.convert_flightcontest_gpx import create_anr_corridor_route_from_kml
from display.models import Aeroplane, NavigationTask, Contest, Crew, Person, Team, Contestant, ContestantTrack, \
    TrackScoreOverride


def load_traccar_track(track_file) -> List[Tuple[datetime.datetime, float, float]]:
    positions = []
    with open(track_file, "r") as i:
        for line in i.readlines():
            elements = line.split(",")
            positions.append((dateutil.parser.parse(elements[1]).replace(tzinfo=datetime.timezone.utc),
                              float(elements[2]), float(elements[3])))
    return positions


@patch("display.models.get_traccar_instance")
class TestANR(TransactionTestCase):
    @patch("display.models.get_traccar_instance")
    def setUp(self, p):
        with open("display/calculators/tests/eidsvoll.kml", "r") as file:
            route = create_anr_corridor_route_from_kml("test", file, 0.5, False)
        navigation_task_start_time = datetime.datetime(2021, 1, 27, 6, 0, 0, tzinfo=datetime.timezone.utc)
        navigation_task_finish_time = datetime.datetime(2021, 1, 27, 16, 0, 0, tzinfo=datetime.timezone.utc)
        self.aeroplane = Aeroplane.objects.create(registration="LN-YDB")
        from display.default_scorecards import default_scorecard_fai_anr_2017
        self.navigation_task = NavigationTask.objects.create(name="NM navigation_task",
                                                             route=route,
                                                             scorecard=default_scorecard_fai_anr_2017.get_default_scorecard(),
                                                             contest=Contest.objects.create(name="contest",
                                                                                            start_time=datetime.datetime.now(
                                                                                                datetime.timezone.utc),
                                                                                            finish_time=datetime.datetime.now(
                                                                                                datetime.timezone.utc),
                                                                                            time_zone="Europe/Oslo"),
                                                             start_time=navigation_task_start_time,
                                                             finish_time=navigation_task_finish_time)
        self.navigation_task.track_score_override = TrackScoreOverride.objects.create(corridor_width=0.5,
                                                                                      corridor_grace_time=5)
        crew = Crew.objects.create(member1=Person.objects.create(first_name="Mister", last_name="Pilot"))
        self.team = Team.objects.create(crew=crew, aeroplane=self.aeroplane)
        self.scorecard = default_scorecard_fai_anr_2017.get_default_scorecard()
        # Required to make the time zone save correctly
        self.navigation_task.refresh_from_db()

    def test_track(self, p):
        track = load_track_points_traccar_csv(
            load_traccar_track("display/calculators/tests/kolaf_eidsvoll_traccar.csv"))
        start_time, speed = datetime.datetime(2021, 1, 27, 6, 45, tzinfo=datetime.timezone.utc), 40
        self.contestant = Contestant.objects.create(navigation_task=self.navigation_task, team=self.team,
                                                    takeoff_time=start_time,
                                                    finished_by_time=start_time + datetime.timedelta(hours=2),
                                                    tracker_start_time=start_time - datetime.timedelta(minutes=30),
                                                    tracker_device_id="Test contestant", contestant_number=1,
                                                    minutes_to_starting_point=7,
                                                    air_speed=speed, wind_direction=160,
                                                    wind_speed=0)
        calculator = calculator_factory(self.contestant, Mock(), live_processing=False)
        calculator.start()
        calculator.add_positions(track)
        calculator.join()
        contestant_track = ContestantTrack.objects.get(contestant=self.contestant)
        self.assertEqual(496,  # 593,  # 2368,
                         contestant_track.score)
        strings = [item["string"] for item in contestant_track.score_log]
        self.assertTrue(
            "SP: 96.0 points passing gate (+33 s)\n(planned: 07:52:00 +0100, actual: 07:52:33 +0100)" in strings)

    def test_track_adaptive_start(self, p):
        track = load_track_points_traccar_csv(
            load_traccar_track("display/calculators/tests/kolaf_eidsvoll_traccar.csv"))
        start_time, speed = datetime.datetime(2021, 1, 27, 6, 45, tzinfo=datetime.timezone.utc), 40
        self.contestant = Contestant.objects.create(navigation_task=self.navigation_task, team=self.team,
                                                    adaptive_start=True,
                                                    takeoff_time=start_time,
                                                    finished_by_time=start_time + datetime.timedelta(hours=2),
                                                    tracker_start_time=start_time - datetime.timedelta(minutes=30),
                                                    tracker_device_id="Test contestant", contestant_number=1,
                                                    minutes_to_starting_point=7,
                                                    air_speed=speed, wind_direction=160,
                                                    wind_speed=0)
        calculator = calculator_factory(self.contestant, Mock(), live_processing=False)
        calculator.start()
        calculator.add_positions(track)
        calculator.join()
        contestant_track = ContestantTrack.objects.get(contestant=self.contestant)
        self.assertEqual(478,  # 575,  # 2350,
                         contestant_track.score)
        strings = [item["string"] for item in contestant_track.score_log]
        self.assertTrue(
            "SP: 78.0 points passing gate (-27 s)\n(planned: 07:53:00 +0100, actual: 07:52:33 +0100)" in strings)


class TestAnrCorridorCalculator(TransactionTestCase):
    @patch("display.models.get_traccar_instance")
    def setUp(self, p):
        with patch("display.convert_flightcontest_gpx.load_features_from_kml",
                   return_value={"route": [(60, 11), (60, 12), (61, 12), (61, 11)]}):
            self.route = create_anr_corridor_route_from_kml("test", Mock(), 0.5, False)
        from display.default_scorecards import default_scorecard_fai_anr_2017
        navigation_task_start_time = datetime.datetime(2021, 1, 27, 6, 0, 0, tzinfo=datetime.timezone.utc)
        navigation_task_finish_time = datetime.datetime(2021, 1, 27, 16, 0, 0, tzinfo=datetime.timezone.utc)

        self.navigation_task = NavigationTask.objects.create(name="NM navigation_task",
                                                             route=self.route,
                                                             scorecard=default_scorecard_fai_anr_2017.get_default_scorecard(),
                                                             contest=Contest.objects.create(name="123467",
                                                                                            start_time=datetime.datetime.now(
                                                                                                datetime.timezone.utc),
                                                                                            finish_time=datetime.datetime.now(
                                                                                                datetime.timezone.utc),
                                                                                            time_zone="Europe/Oslo"),
                                                             start_time=navigation_task_start_time,
                                                             finish_time=navigation_task_finish_time)
        self.navigation_task.track_score_override = TrackScoreOverride.objects.create(corridor_width=0.5,
                                                                                      corridor_grace_time=5)
        start_time, speed = datetime.datetime(2021, 1, 27, 6, 45, tzinfo=datetime.timezone.utc), 40
        self.aeroplane = Aeroplane.objects.create(registration="LN-YDB")
        crew = Crew.objects.create(member1=Person.objects.create(first_name="Mister", last_name="Pilot"))
        self.team = Team.objects.create(crew=crew, aeroplane=self.aeroplane)

        self.contestant = Contestant.objects.create(navigation_task=self.navigation_task, team=self.team,
                                                    takeoff_time=start_time,
                                                    finished_by_time=start_time + datetime.timedelta(hours=2),
                                                    tracker_start_time=start_time - datetime.timedelta(minutes=30),
                                                    tracker_device_id="Test contestant", contestant_number=1,
                                                    minutes_to_starting_point=7,
                                                    air_speed=speed, wind_direction=160,
                                                    wind_speed=0)
        self.update_score = Mock()
        self.calculator = AnrCorridorCalculator(self.contestant, self.navigation_task.scorecard, self.route.waypoints,
                                                self.route, self.update_score)

    def test_inside_20_seconds_enroute(self):
        position = Mock()
        position.latitude = 60
        position.longitude = 11.5
        position.time = datetime.datetime(2020, 1, 1, 0, 0)
        position2 = Mock()
        position2.latitude = 60
        position2.longitude = 11.5
        position2.time = datetime.datetime(2020, 1, 1, 0, 0, 20)

        gate = Mock()
        self.calculator.calculate_enroute([position], gate, gate)
        self.calculator.calculate_enroute([position2], gate, gate)
        self.update_score.assert_not_called()

    def test_outside_2_seconds_enroute(self):
        position = Mock()
        position.latitude = 60.5
        position.longitude = 11
        position.time = datetime.datetime(2020, 1, 1, 0, 0)
        position2 = Mock()
        position2.latitude = 60.5
        position2.longitude = 11
        position2.time = datetime.datetime(2020, 1, 1, 0, 0, 1)
        position3 = Mock()
        position3.latitude = 60
        position3.longitude = 11.5
        position3.time = datetime.datetime(2020, 1, 1, 0, 0, 3)

        gate = Mock()
        self.calculator.calculate_enroute([position], gate, gate)
        self.calculator.calculate_enroute([position2], gate, gate)
        self.calculator.calculate_enroute([position3], gate, gate)
        self.update_score.assert_not_called()

    def test_outside_20_seconds_enroute(self):
        position = Mock()
        position.latitude = 60.5
        position.longitude = 11
        position.time = datetime.datetime(2020, 1, 1, 0, 0)
        position2 = Mock()
        position2.latitude = 60.5
        position2.longitude = 11
        position2.time = datetime.datetime(2020, 1, 1, 0, 0, 1)
        position3 = Mock()
        position3.latitude = 60
        position3.longitude = 11.5
        position3.time = datetime.datetime(2020, 1, 1, 0, 0, 21)

        gate = Mock()
        self.calculator.calculate_enroute([position], gate, gate)
        self.calculator.calculate_enroute([position2], gate, gate)
        self.calculator.calculate_enroute([position3], gate, gate)
        self.update_score.assert_called_with(gate, 48, 'outside corridor (16 seconds)', 60.5, 11, 'anomaly',
                                             'outside_corridor', maximum_score=-1)

    def test_outside_20_seconds_until_finish(self):
        position = Mock()
        position.latitude = 60.5
        position.longitude = 11
        position.time = datetime.datetime(2020, 1, 1, 0, 0)
        position2 = Mock()
        position2.latitude = 60.5
        position2.longitude = 11
        position2.time = datetime.datetime(2020, 1, 1, 0, 0, 1)
        position3 = Mock()
        position3.latitude = 60
        position3.longitude = 11.5
        position3.time = datetime.datetime(2020, 1, 1, 0, 0, 21)

        gate = Mock()
        self.calculator.calculate_enroute([position], gate, gate)
        self.calculator.calculate_enroute([position2], gate, gate)
        self.calculator.passed_finishpoint([position3], gate)
        self.update_score.assert_called_with(gate, 48, 'outside corridor (16 seconds)', 60.5, 11, 'anomaly',
                                             'outside_corridor', maximum_score=-1)

    def test_outside_20_seconds_outside_route(self):
        position = Mock()
        position.latitude = 60.5
        position.longitude = 11
        position.time = datetime.datetime(2020, 1, 1, 0, 0)
        position2 = Mock()
        position2.latitude = 60.5
        position2.longitude = 11
        position2.time = datetime.datetime(2020, 1, 1, 0, 0, 1)
        position3 = Mock()
        position3.latitude = 60
        position3.longitude = 11.5
        position3.time = datetime.datetime(2020, 1, 1, 0, 0, 21)

        gate = Mock()
        self.calculator.calculate_outside_route([position], gate)
        self.calculator.calculate_outside_route([position2], gate)
        self.calculator.calculate_outside_route([position3], gate)
        self.update_score.assert_not_called()
