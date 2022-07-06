import datetime
import threading
from multiprocessing import Queue
from pprint import pprint
from unittest.mock import Mock, patch, call

import dateutil
import logging
from django.core.cache import cache
from django.test import TransactionTestCase
from django.test.utils import freeze_time

from display.calculators.anr_corridor_calculator import AnrCorridorCalculator
from display.calculators.calculator_factory import calculator_factory
from display.calculators.calculator_utilities import load_track_points_traccar_csv
from display.calculators.tests.utilities import load_traccar_track
from display.convert_flightcontest_gpx import create_anr_corridor_route_from_kml
from display.models import (
    Aeroplane,
    NavigationTask,
    Contest,
    Crew,
    Person,
    Team,
    Contestant,
    ContestantTrack,
)
from mock_utilities import TraccarMock
from redis_queue import RedisQueue

logger = logging.getLogger(__name__)


def calculator_runner(contestant, track):
    q = RedisQueue(contestant.pk)
    calculator = calculator_factory(contestant, live_processing=False)
    for i in track:
        i["id"] = 0
        i["deviceId"] = ""
        i["attributes"] = {}
        i["device_time"] = dateutil.parser.parse(i["time"])
        q.append(i)
    q.append(None)
    calculator.run()
    while not q.empty():
        q.pop()


@patch("display.calculators.gatekeeper.get_traccar_instance", return_value=TraccarMock)
@patch("display.models.get_traccar_instance", return_value=TraccarMock)
class TestANRPerLeg(TransactionTestCase):
    @patch(
        "display.calculators.gatekeeper.get_traccar_instance", return_value=TraccarMock
    )
    @patch("display.models.get_traccar_instance", return_value=TraccarMock)
    def setUp(self, p, p2):
        with open("display/calculators/tests/kjeller.kml", "r") as file:
            route = create_anr_corridor_route_from_kml("test", file, 0.5, False)
        navigation_task_start_time = datetime.datetime(
            2021, 1, 27, 6, 0, 0, tzinfo=datetime.timezone.utc
        )
        navigation_task_finish_time = datetime.datetime(
            2021, 1, 27, 16, 0, 0, tzinfo=datetime.timezone.utc
        )
        self.aeroplane = Aeroplane.objects.create(registration="LN-YDB")
        from display.default_scorecards import default_scorecard_fai_anr_2017

        self.navigation_task = NavigationTask.create(
            name="NM navigation_task",
            route=route,
            original_scorecard=default_scorecard_fai_anr_2017.get_default_scorecard(),
            contest=Contest.objects.create(
                name="contest",
                start_time=datetime.datetime.now(datetime.timezone.utc),
                finish_time=datetime.datetime.now(datetime.timezone.utc),
                time_zone="Europe/Oslo",
            ),
            start_time=navigation_task_start_time,
            finish_time=navigation_task_finish_time,
        )
        self.navigation_task.scorecard.corridor_maximum_penalty = 50
        self.navigation_task.scorecard.corridor_grace_time = 5
        self.navigation_task.scorecard.save()
        crew = Crew.objects.create(
            member1=Person.objects.create(first_name="Mister", last_name="Pilot")
        )
        self.team = Team.objects.create(crew=crew, aeroplane=self.aeroplane)
        # Required to make the time zone save correctly
        self.navigation_task.refresh_from_db()

    def test_anr_score_per_leg(self, p, p2):
        track = load_track_points_traccar_csv(
            load_traccar_track("display/calculators/tests/kjeller_anr_bad.csv")
        )
        start_time, speed = (
            datetime.datetime(2021, 3, 15, 19, 30, tzinfo=datetime.timezone.utc),
            70,
        )
        self.contestant = Contestant.objects.create(
            navigation_task=self.navigation_task,
            team=self.team,
            takeoff_time=start_time,
            finished_by_time=start_time + datetime.timedelta(hours=2),
            tracker_start_time=start_time - datetime.timedelta(minutes=30),
            tracker_device_id="Test contestant",
            contestant_number=1,
            minutes_to_starting_point=7,
            air_speed=speed,
            wind_direction=160,
            wind_speed=0,
        )
        calculator_runner(self.contestant, track)
        contestant_track = ContestantTrack.objects.get(contestant=self.contestant)
        strings = [item.string for item in self.contestant.scorelogentry_set.all()]
        pprint(strings)
        a = ['Takeoff: 0.0 points missing takeoff gate\nplanned: 20:30:00\nactual: --',
             'SP: 200.0 points passing gate (-367 s)\nplanned: 20:37:00\nactual: 20:30:53',
             'SP: 50.0 points outside corridor (40 s) (capped)',
             'SP: 0 points entering corridor',
             'Waypoint 1: 0 points passing gate (no time check) (-407 s)\nplanned: 20:39:00\nactual: 20:32:13',
             'Waypoint 1: 50.0 points outside corridor (115 s) (capped)',
             'Waypoint 1: 200.0 points backtracking',
             'Waypoint 1: 0 points entering corridor',
             'Waypoint 1: 0.0 points outside corridor (157 s) (capped)',
             'FP: 30.0 points outside corridor (10 s)',
             'FP: 200.0 points passing gate (-780 s)\nplanned: 20:48:10\nactual: 20:35:11',
             'Landing: 0.0 points missing landing gate\nplanned: 22:29:00\nactual: --']

        self.assertListEqual(a, strings)
        self.assertEqual(730, contestant_track.score)

    def test_anr_miss_multiple_finish(self, p, p2):
        track = load_track_points_traccar_csv(
            load_traccar_track("display/calculators/tests/anr_miss_multiple_finish.csv")
        )
        start_time, speed = datetime.datetime.now(datetime.timezone.utc), 70
        self.contestant = Contestant.objects.create(
            navigation_task=self.navigation_task,
            team=self.team,
            takeoff_time=start_time,
            finished_by_time=start_time + datetime.timedelta(seconds=30),
            tracker_start_time=start_time - datetime.timedelta(minutes=30),
            tracker_device_id="Test contestant",
            contestant_number=1,
            minutes_to_starting_point=7,
            air_speed=speed,
            wind_direction=160,
            wind_speed=0,
        )
        calculator_runner(self.contestant, track)
        contestant_track = ContestantTrack.objects.get(contestant=self.contestant)
        strings = [item.string for item in self.contestant.scorelogentry_set.all()]
        print(strings)
        fixed_strings = [item.split("\n")[0] for item in strings]
        fixed_strings[1] = fixed_strings[1][:10]
        fixed_strings[5] = fixed_strings[5][:20]
        pprint(fixed_strings)
        self.assertListEqual(
            [
                "Takeoff: 0.0 points missing takeoff gate",
                "SP: 200.0 ",
                "SP: 50.0 points outside corridor (21 s) (capped)",
                "Waypoint 1: 12.0 points outside corridor (4 s)",
                "Waypoint 1: 0 points entering corridor",
                "Waypoint 1: 38.0 poi",
                "Waypoint 1: 200.0 points backtracking",
                "Waypoint 2: 50.0 points outside corridor (0 s) (capped)",
                "Waypoint 3: 50.0 points outside corridor (0 s) (capped)",
                "FP: 200.0 points missing gate",
                "FP: 50.0 points outside corridor (0 s) (capped)",
                "Landing: 0.0 points missing landing gate",
            ],
            fixed_strings,
        )
        self.assertEqual(850, contestant_track.score)

    def test_manually_terminate_calculator(self, p, p2):
        cache.clear()
        track = load_track_points_traccar_csv(
            load_traccar_track("display/calculators/tests/anr_miss_multiple_finish.csv")
        )
        start_time, speed = datetime.datetime.now(datetime.timezone.utc), 70
        self.contestant = Contestant.objects.create(
            navigation_task=self.navigation_task,
            team=self.team,
            takeoff_time=start_time,
            finished_by_time=start_time + datetime.timedelta(minutes=30),
            tracker_start_time=start_time - datetime.timedelta(minutes=30),
            tracker_device_id="Test contestant",
            contestant_number=1,
            minutes_to_starting_point=7,
            air_speed=speed,
            wind_direction=160,
            wind_speed=0,
        )
        q = RedisQueue(self.contestant.pk)
        calculator = calculator_factory(self.contestant, live_processing=True)
        for i in track:
            i["id"] = 0
            i["deviceId"] = ""
            i["attributes"] = {}
            i["device_time"] = dateutil.parser.parse(i["time"])
            q.append(i)
        threading.Timer(
            1, lambda: self.contestant.request_calculator_termination()
        ).start()
        calculator.run()
        contestant_track = ContestantTrack.objects.get(contestant=self.contestant)
        strings = [item.string for item in self.contestant.scorelogentry_set.all()]

        print(strings)
        self.assertTrue("SP: 0 points manually terminated" in strings)
        # self.assertEqual(492, contestant_track.score)

    def test_anr_miss_start_and_finish(self, p, p2):
        track = load_track_points_traccar_csv(
            load_traccar_track(
                "display/calculators/tests/anr_miss_start_and_finish.csv"
            )
        )
        start_time, speed = (
            datetime.datetime(2021, 3, 16, 14, 5, tzinfo=datetime.timezone.utc),
            70,
        )
        self.contestant = Contestant.objects.create(
            navigation_task=self.navigation_task,
            team=self.team,
            takeoff_time=start_time,
            finished_by_time=start_time + datetime.timedelta(seconds=30),
            tracker_start_time=start_time - datetime.timedelta(minutes=30),
            tracker_device_id="Test contestant",
            contestant_number=1,
            minutes_to_starting_point=7,
            adaptive_start=True,
            air_speed=speed,
            wind_direction=160,
            wind_speed=0,
        )
        calculator_runner(self.contestant, track)
        contestant_track = ContestantTrack.objects.get(contestant=self.contestant)
        strings = [item.string for item in self.contestant.scorelogentry_set.all()]
        print(strings)
        expected = [
            "SP: 9.0 points passing gate (+4 s)\nplanned: 14:17:00\nactual: 14:17:04",
            "Waypoint 1: 0 points passing gate (no time check) (-57 s)\nplanned: 14:19:00\nactual: 14:18:03",
            "Waypoint 2: 0 points passing gate (no time check) (-168 s)\nplanned: 14:22:34\nactual: 14:19:46",
            "Waypoint 3: 0 points passing gate (no time check) (-221 s)\nplanned: 14:24:32\nactual: 14:20:51",
            "FP: 200.0 points passing gate (-320 s)\nplanned: 14:28:10\nactual: 14:22:51",
            "Landing: 0.0 points missing landing gate\nplanned: 15:04:30\nactual: --",
        ]
        self.assertListEqual(expected, strings)
        self.assertEqual(209, contestant_track.score)


@patch("display.models.get_traccar_instance", return_value=TraccarMock)
@patch("display.calculators.gatekeeper.get_traccar_instance", return_value=TraccarMock)
class TestANR(TransactionTestCase):
    @patch(
        "display.calculators.gatekeeper.get_traccar_instance", return_value=TraccarMock
    )
    @patch("display.models.get_traccar_instance", return_value=TraccarMock)
    def setUp(self, p, p2):
        with open("display/calculators/tests/eidsvoll.kml", "r") as file:
            route = create_anr_corridor_route_from_kml("test", file, 0.5, False)
        navigation_task_start_time = datetime.datetime(
            2021, 1, 27, 6, 0, 0, tzinfo=datetime.timezone.utc
        )
        navigation_task_finish_time = datetime.datetime(
            2021, 1, 27, 16, 0, 0, tzinfo=datetime.timezone.utc
        )
        self.aeroplane = Aeroplane.objects.create(registration="LN-YDB")
        from display.default_scorecards import default_scorecard_fai_anr_2017

        self.navigation_task = NavigationTask.create(
            name="NM navigation_task",
            route=route,
            original_scorecard=default_scorecard_fai_anr_2017.get_default_scorecard(),
            contest=Contest.objects.create(
                name="contest",
                start_time=datetime.datetime.now(datetime.timezone.utc),
                finish_time=datetime.datetime.now(datetime.timezone.utc),
                time_zone="Europe/Oslo",
            ),
            start_time=navigation_task_start_time,
            finish_time=navigation_task_finish_time,
        )
        self.navigation_task.scorecard.corridor_grace_time = 5
        self.navigation_task.scorecard.save()
        crew = Crew.objects.create(
            member1=Person.objects.create(first_name="Mister", last_name="Pilot")
        )
        self.team = Team.objects.create(crew=crew, aeroplane=self.aeroplane)
        # Required to make the time zone save correctly
        self.navigation_task.refresh_from_db()

    def test_track(self, p, p2):
        track = load_track_points_traccar_csv(
            load_traccar_track("display/calculators/tests/kolaf_eidsvoll_traccar.csv")
        )
        start_time, speed = (
            datetime.datetime(2021, 1, 27, 6, 45, tzinfo=datetime.timezone.utc),
            40,
        )
        self.contestant = Contestant.objects.create(
            navigation_task=self.navigation_task,
            team=self.team,
            takeoff_time=start_time,
            finished_by_time=start_time + datetime.timedelta(hours=2),
            tracker_start_time=start_time - datetime.timedelta(minutes=30),
            tracker_device_id="Test contestant",
            contestant_number=1,
            minutes_to_starting_point=7,
            air_speed=speed,
            wind_direction=160,
            wind_speed=0,
        )
        calculator_runner(self.contestant, track)
        contestant_track = ContestantTrack.objects.get(contestant=self.contestant)
        self.assertEqual(476, contestant_track.score)  # 971,  # 593,  # 2368,
        strings = [item.string for item in self.contestant.scorelogentry_set.all()]
        self.assertTrue(
            "SP: 96.0 points passing gate (+33 s)\nplanned: 07:52:00\nactual: 07:52:33"
            in strings
        )

    def test_track_adaptive_start(self, p, p2):
        track = load_track_points_traccar_csv(
            load_traccar_track("display/calculators/tests/kolaf_eidsvoll_traccar.csv")
        )
        start_time, speed = (
            datetime.datetime(2021, 1, 27, 6, 45, tzinfo=datetime.timezone.utc),
            40,
        )
        self.contestant = Contestant.objects.create(
            navigation_task=self.navigation_task,
            team=self.team,
            adaptive_start=True,
            takeoff_time=start_time,
            finished_by_time=start_time + datetime.timedelta(hours=2),
            tracker_start_time=start_time - datetime.timedelta(minutes=30),
            tracker_device_id="Test contestant",
            contestant_number=1,
            minutes_to_starting_point=7,
            air_speed=speed,
            wind_direction=160,
            wind_speed=0,
        )
        calculator_runner(self.contestant, track)

        contestant_track = ContestantTrack.objects.get(contestant=self.contestant)
        self.assertEqual(458, contestant_track.score)  # 953,  # 575,  # 2350,
        strings = [item.string for item in self.contestant.scorelogentry_set.all()]
        print(strings)
        self.assertTrue(
            "SP: 78.0 points passing gate (-27 s)\nplanned: 07:53:00\nactual: 07:52:33"
            in strings
        )


class TestAnrCorridorCalculator(TransactionTestCase):
    @patch("display.models.get_traccar_instance", return_value=TraccarMock)
    def setUp(self, p):
        with patch(
                "display.convert_flightcontest_gpx.load_features_from_kml",
                return_value={"route": [(60, 11), (60, 12), (61, 12), (61, 11)]},
        ):
            self.route = create_anr_corridor_route_from_kml("test", Mock(), 0.5, False)
        from display.default_scorecards import default_scorecard_fai_anr_2017

        navigation_task_start_time = datetime.datetime(
            2021, 1, 27, 6, 0, 0, tzinfo=datetime.timezone.utc
        )
        navigation_task_finish_time = datetime.datetime(
            2021, 1, 27, 16, 0, 0, tzinfo=datetime.timezone.utc
        )

        self.navigation_task = NavigationTask.create(
            name="NM navigation_task",
            route=self.route,
            original_scorecard=default_scorecard_fai_anr_2017.get_default_scorecard(),
            contest=Contest.objects.create(
                name="123467",
                start_time=datetime.datetime.now(datetime.timezone.utc),
                finish_time=datetime.datetime.now(datetime.timezone.utc),
                time_zone="Europe/Oslo",
            ),
            start_time=navigation_task_start_time,
            finish_time=navigation_task_finish_time,
        )
        self.navigation_task.scorecard.corridor_grace_time = 5
        self.navigation_task.scorecard.save()
        start_time, speed = (
            datetime.datetime(2021, 1, 27, 6, 45, tzinfo=datetime.timezone.utc),
            40,
        )
        self.aeroplane = Aeroplane.objects.create(registration="LN-YDB")
        crew = Crew.objects.create(
            member1=Person.objects.create(first_name="Mister", last_name="Pilot")
        )
        self.team = Team.objects.create(crew=crew, aeroplane=self.aeroplane)

        self.contestant = Contestant.objects.create(
            navigation_task=self.navigation_task,
            team=self.team,
            takeoff_time=start_time,
            finished_by_time=start_time + datetime.timedelta(hours=2),
            tracker_start_time=start_time - datetime.timedelta(minutes=30),
            tracker_device_id="Test contestant",
            contestant_number=1,
            minutes_to_starting_point=7,
            air_speed=speed,
            wind_direction=160,
            wind_speed=0,
        )
        self.update_score = Mock()
        self.calculator = AnrCorridorCalculator(
            self.contestant,
            self.navigation_task.scorecard,
            self.route.waypoints,
            self.route,
            self.update_score,
        )

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
        self.calculator.calculate_enroute([position], gate, gate, None)
        self.calculator.calculate_enroute([position2], gate, gate, None)
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
        self.calculator.calculate_enroute([position], gate, gate, None)
        self.calculator.calculate_enroute([position2], gate, gate, None)
        er = self.calculator.existing_reference
        self.calculator.calculate_enroute([position3], gate, gate, None)
        self.update_score.assert_has_calls(
            [
                call(
                    gate,
                    0,
                    "outside corridor (0 s)",
                    60.5,
                    11,
                    "anomaly",
                    f"outside_corridor_{gate.name}",
                    maximum_score=-1,
                    existing_reference=None,
                ),
                call(
                    gate,
                    0,
                    "outside corridor (2 s)",
                    60.5,
                    11,
                    "anomaly",
                    f"outside_corridor_{gate.name}",
                    maximum_score=-1,
                    existing_reference=er,
                ),
                call(
                    gate,
                    0,
                    "entering corridor",
                    60,
                    11.5,
                    "information",
                    "entering_corridor",
                ),
            ]
        )

    def test_outside_20_seconds_enroute(self):
        position = Mock()
        position.latitude = 60.5
        position.longitude = 11
        position.time = datetime.datetime(2020, 1, 1, 0, 0)
        position2 = Mock()
        position2.latitude = 60.5
        position2.longitude = 11
        position2.time = datetime.datetime(2020, 1, 1, 0, 0, 1)
        position2 = Mock()
        position2.latitude = 60.5
        position2.longitude = 11
        position2.time = datetime.datetime(2020, 1, 1, 0, 0, 20)
        position3 = Mock()
        position3.latitude = 60
        position3.longitude = 11.5
        position3.time = datetime.datetime(2020, 1, 1, 0, 0, 21)

        gate = Mock()
        self.calculator.calculate_enroute([position], gate, gate, None)
        self.calculator.calculate_enroute([position2], gate, gate, None)
        er = self.calculator.existing_reference
        self.calculator.calculate_enroute([position3], gate, gate, None)
        self.update_score.assert_has_calls(
            [
                call(
                    gate,
                    45.0,
                    "outside corridor (20 s)",
                    60.5,
                    11,
                    "anomaly",
                    f"outside_corridor_{gate.name}",
                    maximum_score=-1,
                    existing_reference=er,
                )
            ]
        )

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
        self.calculator.calculate_enroute([position], gate, gate, None)
        self.calculator.calculate_enroute([position2], gate, gate, None)
        er = self.calculator.existing_reference
        self.calculator.passed_finishpoint([position3], gate)

        self.update_score.assert_called_with(
            gate,
            48.0,
            "outside corridor (21 s)",
            60.5,
            11,
            "anomaly",
            f"outside_corridor_{gate.name}",
            maximum_score=-1,
            existing_reference=er,
        )

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


@patch("display.models.get_traccar_instance", return_value=TraccarMock)
@patch("display.calculators.gatekeeper.get_traccar_instance", return_value=TraccarMock)
class TestANRPolygon(TransactionTestCase):
    @patch(
        "display.calculators.gatekeeper.get_traccar_instance", return_value=TraccarMock
    )
    @patch("display.models.get_traccar_instance", return_value=TraccarMock)
    def setUp(self, p, p2):
        with open("display/calculators/tests/kjeller.kml", "r") as file:
            route = create_anr_corridor_route_from_kml("test", file, 0.5, False)
        navigation_task_start_time = datetime.datetime(
            2021, 1, 27, 6, 0, 0, tzinfo=datetime.timezone.utc
        )
        navigation_task_finish_time = datetime.datetime(
            2021, 1, 27, 16, 0, 0, tzinfo=datetime.timezone.utc
        )
        self.aeroplane = Aeroplane.objects.create(registration="LN-YDB")
        from display.default_scorecards import default_scorecard_fai_anr_2017

        self.navigation_task = NavigationTask.create(
            name="NM navigation_task",
            route=route,
            original_scorecard=default_scorecard_fai_anr_2017.get_default_scorecard(),
            contest=Contest.objects.create(
                name="contest",
                start_time=datetime.datetime.now(datetime.timezone.utc),
                finish_time=datetime.datetime.now(datetime.timezone.utc),
                time_zone="Europe/Oslo",
            ),
            start_time=navigation_task_start_time,
            finish_time=navigation_task_finish_time,
        )
        self.navigation_task.scorecard.corridor_grace_time = 5
        self.navigation_task.scorecard.save()
        crew = Crew.objects.create(
            member1=Person.objects.create(first_name="Mister", last_name="Pilot")
        )
        self.team = Team.objects.create(crew=crew, aeroplane=self.aeroplane)
        # Required to make the time zone save correctly
        self.navigation_task.refresh_from_db()

    def test_track(self, p, p2):
        track = load_track_points_traccar_csv(
            load_traccar_track("display/calculators/tests/kolaf_eidsvoll_traccar.csv")
        )
        start_time, speed = (
            datetime.datetime(2021, 1, 27, 6, 45, tzinfo=datetime.timezone.utc),
            40,
        )
        self.contestant = Contestant.objects.create(
            navigation_task=self.navigation_task,
            team=self.team,
            takeoff_time=start_time,
            finished_by_time=start_time + datetime.timedelta(hours=2),
            tracker_start_time=start_time - datetime.timedelta(minutes=30),
            tracker_device_id="Test contestant",
            contestant_number=1,
            minutes_to_starting_point=7,
            air_speed=speed,
            wind_direction=160,
            wind_speed=0,
        )
        calculator_runner(self.contestant, track)


@patch("display.models.get_traccar_instance", return_value=TraccarMock)
@patch("display.calculators.gatekeeper.get_traccar_instance", return_value=TraccarMock)
class TestANRBergenBacktracking(TransactionTestCase):
    @patch(
        "display.calculators.gatekeeper.get_traccar_instance", return_value=TraccarMock
    )
    @patch("display.models.get_traccar_instance", return_value=TraccarMock)
    def setUp(self, p, p2):
        with open("display/calculators/tests/Bergen_Open_Test.kml", "r") as file:
            route = create_anr_corridor_route_from_kml("test", file, 0.5, False)
        navigation_task_start_time = datetime.datetime(
            2021, 3, 24, 6, 0, 0, tzinfo=datetime.timezone.utc
        )
        navigation_task_finish_time = datetime.datetime(
            2021, 3, 24, 16, 0, 0, tzinfo=datetime.timezone.utc
        )
        self.aeroplane = Aeroplane.objects.create(registration="LN-YDB")
        from display.default_scorecards import default_scorecard_fai_anr_2017

        self.navigation_task = NavigationTask.create(
            name="NM navigation_task",
            route=route,
            original_scorecard=default_scorecard_fai_anr_2017.get_default_scorecard(),
            contest=Contest.objects.create(
                name="contest",
                start_time=datetime.datetime.now(datetime.timezone.utc),
                finish_time=datetime.datetime.now(datetime.timezone.utc),
                time_zone="Europe/Oslo",
            ),
            start_time=navigation_task_start_time,
            finish_time=navigation_task_finish_time,
        )
        self.navigation_task.scorecard.corridor_grace_time = 5
        self.navigation_task.scorecard.save()
        crew = Crew.objects.create(
            member1=Person.objects.create(first_name="Mister", last_name="Pilot")
        )
        self.team = Team.objects.create(crew=crew, aeroplane=self.aeroplane)
        # Required to make the time zone save correctly
        self.navigation_task.refresh_from_db()

    def test_track(self, p, p2):
        track = load_track_points_traccar_csv(
            load_traccar_track("display/calculators/tests/kurtbergen.csv")
        )
        start_time, speed = (
            datetime.datetime(2021, 3, 24, 13, 17, tzinfo=datetime.timezone.utc),
            70,
        )
        self.contestant = Contestant.objects.create(
            navigation_task=self.navigation_task,
            team=self.team,
            takeoff_time=start_time,
            finished_by_time=start_time + datetime.timedelta(hours=2),
            tracker_start_time=start_time - datetime.timedelta(minutes=30),
            tracker_device_id="Test contestant",
            contestant_number=1,
            minutes_to_starting_point=7,
            adaptive_start=True,
            air_speed=speed,
            wind_direction=220,
            wind_speed=18,
        )
        calculator_runner(self.contestant, track)
        # Incorrectly gets 200 points for prohibited zone at departure and arrival, actual score is 51.
        self.assertEqual(406, self.contestant.contestanttrack.score)


@patch("display.calculators.gatekeeper.get_traccar_instance", return_value=TraccarMock)
@patch("display.models.get_traccar_instance", return_value=TraccarMock)
class TestANRBergenBacktrackingTommy(TransactionTestCase):
    @patch("display.models.get_traccar_instance", return_value=TraccarMock)
    def setUp(self, p):
        with open("display/calculators/tests/tommy_test.kml", "r") as file:
            route = create_anr_corridor_route_from_kml("test", file, 0.5, False)
        navigation_task_start_time = datetime.datetime(
            2021, 3, 31, 14, 0, 0, tzinfo=datetime.timezone.utc
        )
        navigation_task_finish_time = datetime.datetime(
            2021, 3, 31, 16, 0, 0, tzinfo=datetime.timezone.utc
        )
        self.aeroplane = Aeroplane.objects.create(registration="LN-YDB")
        from display.default_scorecards import default_scorecard_fai_anr_2017

        self.navigation_task = NavigationTask.create(
            name="NM navigation_task",
            route=route,
            original_scorecard=default_scorecard_fai_anr_2017.get_default_scorecard(),
            contest=Contest.objects.create(
                name="contest",
                start_time=datetime.datetime.now(datetime.timezone.utc),
                finish_time=datetime.datetime.now(datetime.timezone.utc),
                time_zone="Europe/Oslo",
            ),
            start_time=navigation_task_start_time,
            finish_time=navigation_task_finish_time,
        )
        self.navigation_task.scorecard.corridor_grace_time = 5
        self.navigation_task.scorecard.save()
        crew = Crew.objects.create(
            member1=Person.objects.create(first_name="Mister", last_name="Pilot")
        )
        self.team = Team.objects.create(crew=crew, aeroplane=self.aeroplane)
        # Required to make the time zone save correctly
        self.navigation_task.refresh_from_db()

    def test_track(self, p, p2):
        track = load_track_points_traccar_csv(
            load_traccar_track(
                "display/calculators/tests/tommy_missing_circling_penalty.csv"
            )
        )
        start_time, speed = (
            datetime.datetime(2021, 3, 31, 12, 35, tzinfo=datetime.timezone.utc),
            70,
        )
        self.contestant = Contestant.objects.create(
            navigation_task=self.navigation_task,
            team=self.team,
            takeoff_time=start_time,
            finished_by_time=start_time + datetime.timedelta(hours=2),
            tracker_start_time=start_time - datetime.timedelta(minutes=30),
            tracker_device_id="Test contestant",
            contestant_number=1,
            minutes_to_starting_point=7,
            adaptive_start=True,
            air_speed=speed,
            wind_direction=340,
            wind_speed=15,
        )
        calculator_runner(self.contestant, track)
        # Gets 200 unnecessary points for being inside prohibited zone at departure. Also 200 points for missing final gate. Actual score is 368
        strings = [item.string for item in self.contestant.scorelogentry_set.all()]
        for s in strings:
            print(s)
        self.assertEqual(3348, self.contestant.contestanttrack.score)
        contestant_track = ContestantTrack.objects.get(contestant=self.contestant)
        self.assertTrue("SP: 200.0 points circling start" in strings)
