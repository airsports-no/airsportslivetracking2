import base64

import dateutil
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction, IntegrityError
from django_countries.serializer_fields import CountryField
from django_countries.serializers import CountryFieldMixin
from guardian.shortcuts import assign_perm
from phonenumber_field.serializerfields import PhoneNumberField
from rest_framework import serializers
from rest_framework.generics import get_object_or_404
from rest_framework.relations import SlugRelatedField
from rest_framework_guardian.serializers import ObjectPermissionsAssignmentMixin

from display.convert_flightcontest_gpx import create_route_from_gpx
from display.models import NavigationTask, Aeroplane, Team, Route, Contestant, ContestantTrack, Scorecard, Crew, \
    Contest, ContestSummary, TaskTest, Task, TaskSummary, TeamTestScore, Person, Club, ContestTeam
from display.waypoint import Waypoint


class ContestSerialiser(ObjectPermissionsAssignmentMixin, serializers.ModelSerializer):
    class Meta:
        model = Contest
        fields = "__all__"

    def get_permissions_map(self, created):
        user = self.context["request"].user
        return {
            "change_contest": [user],
            "delete_contest": [user],
            "view_contest": [user]
        }


class WaypointSerialiser(serializers.Serializer):
    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass

    name = serializers.CharField(max_length=200)
    latitude = serializers.FloatField(help_text="degrees")
    longitude = serializers.FloatField(help_text="degrees")
    elevation = serializers.FloatField(help_text="Metres above MSL")
    width = serializers.FloatField(help_text="Width of the gate in NM")
    gate_line = serializers.JSONField(
        help_text="Coordinates that describe the starting point and finish point of the gate line, e.g. [[lat1,lon2],[lat2,lon2]")
    time_check = serializers.BooleanField()
    gate_check = serializers.BooleanField()
    end_curved = serializers.BooleanField()
    type = serializers.CharField(max_length=50, help_text="The type of the gate (tp, sp, fp, to, ldg, secret)")
    distance_next = serializers.FloatField(help_text="Distance to the next gate (NM)")
    distance_previous = serializers.FloatField(help_text="Distance from the previous gate (NM)")
    bearing_next = serializers.FloatField(help_text="True track to the next gate (degrees)")
    bearing_from_previous = serializers.FloatField(help_text="True track from the previous gates to this")
    is_procedure_turn = serializers.BooleanField()


class RouteSerialiser(serializers.ModelSerializer):
    waypoints = WaypointSerialiser(many=True)
    landing_gate = WaypointSerialiser(required=False, help_text="Optional landing gate")
    takeoff_gate = WaypointSerialiser(required=False, help_text="Optional takeoff gate")

    class Meta:
        model = Route
        fields = "__all__"

    @staticmethod
    def _create_waypoint(waypoint_data) -> Waypoint:
        waypoint = Waypoint(waypoint_data["name"])
        waypoint.latitude = waypoint_data["latitude"]
        waypoint.longitude = waypoint_data["longitude"]
        waypoint.elevation = waypoint_data["elevation"]
        waypoint.gate_line = waypoint_data["gate_line"]
        waypoint.width = waypoint_data["width"]
        waypoint.time_check = waypoint_data["time_check"]
        waypoint.gate_check = waypoint_data["gate_check"]
        waypoint.end_curved = waypoint_data["end_curved"]
        waypoint.type = waypoint_data["type"]
        waypoint.distance_next = waypoint_data["distance_next"]
        waypoint.distance_previous = waypoint_data["distance_previous"]
        waypoint.bearing_next = waypoint_data["bearing_next"]
        waypoint.bearing_from_previous = waypoint_data["bearing_from_previous"]
        waypoint.is_procedure_turn = waypoint_data["is_procedure_turn"]

        # waypoint.inside_distance = waypoint_data["inside_distance"]
        # waypoint.outside_distance = waypoint_data["outside_distance"]
        return waypoint

    def create(self, validated_data):
        waypoints = []
        for waypoint_data in validated_data.pop("waypoints"):
            waypoints.append(self._create_waypoint(waypoint_data))
        route = Route.objects.create(waypoints=waypoints,
                                     landing_gate=self._create_waypoint(validated_data.pop("landing_gate")),
                                     takeoff_gate=self._create_waypoint(validated_data.pop("takeoff_gate")),
                                     **validated_data)
        return route

    def update(self, instance, validated_data):
        waypoints = []
        for waypoint_data in validated_data.pop("waypoints"):
            waypoints.append(self._create_waypoint(waypoint_data))
        instance.waypoints = waypoints
        instance.landing_gate = self._create_waypoint(validated_data.get("landing_gate"))
        instance.takeoff_gate = self._create_waypoint(validated_data.get("takeoff_gate"))
        return instance


class AeroplaneSerialiser(serializers.ModelSerializer):
    class Meta:
        model = Aeroplane
        fields = "__all__"


class PersonSerialiser(CountryFieldMixin, serializers.ModelSerializer):
    country_flag_url = serializers.CharField(max_length=200, required=False, read_only=True)
    country = CountryField(required=False)
    phone = PhoneNumberField(required=False)

    class Meta:
        model = Person
        fields = "__all__"


class ClubSerialiser(CountryFieldMixin, serializers.ModelSerializer):
    country_flag_url = serializers.CharField(max_length=200, required=False, read_only=True)
    country = CountryField(required=False)

    class Meta:
        model = Club
        fields = "__all__"


class CrewSerialiser(serializers.ModelSerializer):
    member1 = PersonSerialiser()
    member2 = PersonSerialiser(required=False)

    class Meta:
        model = Crew
        fields = "__all__"

    def create(self, validated_data):
        member1 = validated_data.pop("member1")
        member1_object = Person.get_or_create(member1["first_name"], member1["last_name"], member1.get("phone"),
                                              member1.get("email"))
        member2 = validated_data.pop("member2", None)
        member2_object = None
        if member2:
            member2_object = Person.get_or_create(member2["first_name"], member2["last_name"], member2.get("phone"),
                                                  member2.get("email"))
        crew, _ = Crew.objects.get_or_create(member1=member1_object, member2=member2_object)
        return crew

    def update(self, instance, validated_data):
        return self.create(validated_data)


class TeamNestedSerialiser(CountryFieldMixin, serializers.ModelSerializer):
    country_flag_url = serializers.CharField(max_length=200, required=False, read_only=True)
    aeroplane = AeroplaneSerialiser()
    country = CountryField(required=False)
    crew = CrewSerialiser()
    club = ClubSerialiser(required=False)

    class Meta:
        model = Team
        fields = "__all__"

    def create(self, validated_data):
        aeroplane, crew, club = self.nested_update(validated_data)
        team, _ = Team.objects.get_or_create(crew=crew, aeroplane=aeroplane, club=club, defaults=validated_data)
        return team

    def update(self, instance: Team, validated_data):
        instance.aeroplane, instance.crew, instance.club = self.nested_update(validated_data)
        instance.save()
        return instance

    @staticmethod
    def nested_update(validated_data):
        aeroplane_data = validated_data.pop("aeroplane")
        try:
            aeroplane_instance = Aeroplane.objects.get(registration=aeroplane_data.get("registration"))
        except ObjectDoesNotExist:
            aeroplane_instance = None
        aeroplane_serialiser = AeroplaneSerialiser(instance=aeroplane_instance, data=aeroplane_data)
        aeroplane_serialiser.is_valid(True)
        aeroplane = aeroplane_serialiser.save()
        crew_data = validated_data.pop("crew")
        try:
            crew_instance = Crew.objects.get(pk=crew_data.get("id"))
        except ObjectDoesNotExist:
            crew_instance = None
        crew_serialiser = CrewSerialiser(instance=crew_instance, data=crew_data)
        crew_serialiser.is_valid(True)
        crew = crew_serialiser.save()
        club = None
        club_data = validated_data.pop("club", None)
        if club_data:
            try:
                club_instance = Club.objects.get(pk=club_data.get("id"))
            except ObjectDoesNotExist:
                club_instance = None
            club_serialiser = ClubSerialiser(instance=club_instance, data=club_data)
            club_serialiser.is_valid(True)
            club = club_serialiser.save()
        return aeroplane, crew, club


class ContestTeamNestedSerialiser(serializers.ModelSerializer):
    team = TeamNestedSerialiser()

    class Meta:
        model = ContestTeam
        fields = "__all__"


class ScorecardSerialiser(serializers.ModelSerializer):
    class Meta:
        model = Scorecard
        fields = ("name",)


class PositionSerialiser(serializers.Serializer):
    """
    {
        "0": {
            "time": "2015-01-01T07:15:54Z",
            "altitude": 177.7005608388,
            "battery_level": 1,
            "contestant": "310",
            "course": 0,
            "device_id": "2017_101",
            "latitude": 48.10305,
            "longitude": 16.93245,
            "navigation_task": "31",
            "speed": 0
        }
    }
    """

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass

    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    altitude = serializers.FloatField()
    time = serializers.DateTimeField()


class GpxTrackSerialiser(serializers.Serializer):
    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass

    track_file = serializers.CharField(write_only=True, required=True,
                                       help_text="Base64 encoded gpx track file")

    def validate_track_file(self, value):
        if value:
            try:
                base64.decodebytes(bytes(value, 'utf-8'))
            except Exception as e:
                raise serializers.ValidationError("track_file must be in a valid base64 string format.")
        return value


class ContestantTrackWithTrackPointsSerialiser(serializers.ModelSerializer):
    """
    Used for output to the frontend
    """
    score_log = serializers.JSONField()
    score_per_gate = serializers.JSONField()
    track = PositionSerialiser(many=True, read_only=True)

    class Meta:
        model = ContestantTrack
        fields = "__all__"


class ContestantTrackSerialiser(serializers.ModelSerializer):
    """
    Used for output to the frontend
    """
    score_log = serializers.JSONField()
    score_per_gate = serializers.JSONField()

    class Meta:
        model = ContestantTrack
        fields = "__all__"


class ContestantSerialiser(serializers.ModelSerializer):
    class Meta:
        model = Contestant
        exclude = ("navigation_task", "predefined_gate_times")

    gate_times = serializers.JSONField(
        help_text="Dictionary where the keys are gate names (must match the gate names in the route file) and the values are $date-time strings (with time zone)")
    scorecard = SlugRelatedField(slug_field="name", queryset=Scorecard.objects.all(),
                                 help_text=lambda: "Reference to an existing scorecard name. Currently existing scorecards: {}".format(
                                     ", ".join(["'{}'".format(item) for item in Scorecard.objects.all()])))

    def create(self, validated_data):
        validated_data["navigation_task"] = self.context["navigation_task"]
        gate_times = validated_data.pop("gate_times", {})
        contestant = Contestant.objects.create(**validated_data)
        contestant.predefined_gate_times = {key: dateutil.parser.parse(value) for key, value in
                                            gate_times.items()}
        contestant.save()
        try:
            ContestTeam.objects.create(contest=contestant.navigation_task.contest, team=contestant.team,
                                       tracker_device_id=contestant.tracker_device_id,
                                       tracking_service=contestant.tracking_service, air_speed=contestant.air_speed)
        except IntegrityError:
            # Team has already, so no need to add is again
            pass
        return contestant

    def update(self, instance, validated_data):
        ContestTeam.objects.filter(contest=instance.navigation_task.contest, team=instance.team).delete()
        # validated_data.update({"navigation_task": self.context["navigation_task"]})
        gate_times = validated_data.pop("gate_times", {})
        Contestant.objects.filter(pk=instance.pk).update(**validated_data)
        instance.refresh_from_db()
        instance.predefined_gate_times = {key: dateutil.parser.parse(value) for key, value in
                                          gate_times.items()}
        instance.save()
        try:
            ContestTeam.objects.create(contest=instance.navigation_task.contest, team=instance.team,
                                       tracker_device_id=instance.tracker_device_id,
                                       tracking_service=instance.tracking_service, air_speed=instance.air_speed)
        except IntegrityError:
            # Team has already, so no need to add is again
            pass
        return instance


class ContestantNestedTeamSerialiser(ContestantSerialiser):
    """
    Contestants. When putting or patching, note that the entire team has to be specified for it to be changed.
    Otherwise changes will be ignored.
    """
    team = TeamNestedSerialiser()

    class Meta:
        model = Contestant
        exclude = ("navigation_task", "predefined_gate_times")

    def create(self, validated_data):
        team_data = validated_data.pop("team")
        team_serialiser = TeamNestedSerialiser(data=team_data)
        team_serialiser.is_valid(True)
        team = team_serialiser.save()
        validated_data["team"] = team
        return super().create(validated_data)

    def update(self, instance, validated_data):
        team_data = validated_data.pop("team", None)
        if team_data:
            try:
                team_instance = Team.objects.get(pk=team_data.get("id"))
            except ObjectDoesNotExist:
                team_instance = None
            team_serialiser = TeamNestedSerialiser(instance=team_instance, data=team_data)
            team_serialiser.is_valid(True)
            team = team_serialiser.save()
            validated_data.update({"team": team.pk})
        return super().update(instance, validated_data)


class ContestantNestedTeamSerialiserWithContestantTrack(ContestantNestedTeamSerialiser):
    contestanttrack = ContestantTrackSerialiser(read_only=True)


class NavigationTaskNestedTeamRouteSerialiser(serializers.ModelSerializer):
    contestant_set = ContestantNestedTeamSerialiserWithContestantTrack(many=True, read_only=True)
    route = RouteSerialiser()

    class Meta:
        model = NavigationTask
        exclude = ("contest",)

    def create(self, validated_data):
        user = self.context["request"].user
        contestant_set = validated_data.pop("contestant_set", [])
        validated_data["contest"] = self.context["contest"]
        route = validated_data.pop("route", None)
        route_serialiser = RouteSerialiser(data=route)
        route_serialiser.is_valid(raise_exception=True)
        route = route_serialiser.save()
        assign_perm("view_route", user, route)
        assign_perm("delete_route", user, route)
        assign_perm("change_route", user, route)
        navigation_task = NavigationTask.objects.create(**validated_data, route=route)
        for contestant_data in contestant_set:
            contestant_serialiser = ContestantNestedTeamSerialiser(data=contestant_data,
                                                                   context={"navigation_task": navigation_task})
            contestant_serialiser.is_valid(True)
            contestant_serialiser.save()
        return navigation_task


class ExternalNavigationTaskNestedTeamSerialiser(serializers.ModelSerializer):
    contestant_set = ContestantNestedTeamSerialiser(many=True)
    route_file = serializers.CharField(write_only=True, required=True,
                                       help_text="Base64 encoded gpx file")

    internal_serialiser = ContestantNestedTeamSerialiser

    class Meta:
        model = NavigationTask
        exclude = ("route", "contest")

    def validate_route_file(self, value):
        if value:
            try:
                base64.decodebytes(bytes(value, 'utf-8'))
            except Exception as e:
                raise serializers.ValidationError("route_file must be in a valid base64 string format.")
        return value

    def create(self, validated_data):
        with transaction.atomic():
            contestant_set = validated_data.pop("contestant_set", [])
            route_file = validated_data.pop("route_file", None)
            route = create_route_from_gpx(base64.decodebytes(route_file.encode("utf-8")))
            user = self.context["request"].user
            validated_data["contest"] = self.context["contest"]
            validated_data["route"] = route
            assign_perm("view_route", user, route)
            assign_perm("delete_route", user, route)
            assign_perm("change_route", user, route)
            print(self.context)
            navigation_task = NavigationTask.objects.create(**validated_data)
            for contestant_data in contestant_set:
                contestant_data["team"] = contestant_data["team"].pk

            contestant_serialiser = self.internal_serialiser(data=contestant_set, many=True,
                                                             context={"navigation_task": navigation_task})
            contestant_serialiser.is_valid(True)
        contestant_serialiser.save()
        return navigation_task


class ExternalNavigationTaskTeamIdSerialiser(ExternalNavigationTaskNestedTeamSerialiser):
    """
    Does not provide team data input, only team ID for each contestant.
    """
    contestant_set = ContestantSerialiser(many=True)
    route_file = serializers.CharField(write_only=True, required=True,
                                       help_text="Base64 encoded gpx file")

    internal_serialiser = ContestantSerialiser

    class Meta:
        model = NavigationTask
        exclude = ("route", "contest")


########## Results service ##########
class ContestSummarySerialiser(serializers.ModelSerializer):
    team = TeamNestedSerialiser()

    class Meta:
        model = ContestSummary
        fields = "__all__"


class TeamTestScoreSerialiser(serializers.ModelSerializer):
    class Meta:
        model = TeamTestScore
        fields = "__all__"


class TaskTestSerialiser(serializers.ModelSerializer):
    teamtestscore_set = TeamTestScoreSerialiser(many=True)

    class Meta:
        model = TaskTest
        fields = "__all__"


class TaskSummarySerialiser(serializers.ModelSerializer):
    class Meta:
        model = TaskSummary
        fields = "__all__"


class TaskSerialiser(serializers.ModelSerializer):
    tasktest_set = TaskTestSerialiser(many=True)
    tasksummary_set = TaskSummarySerialiser(many=True)

    class Meta:
        model = Task
        fields = "__all__"


# High level entry
class ContestResultsHighLevelSerialiser(serializers.ModelSerializer):
    contestsummary_set = ContestSummarySerialiser(many=True)

    class Meta:
        model = Contest
        fields = "__all__"


# Details entry
class ContestResultsDetailsSerialiser(serializers.ModelSerializer):
    contestsummary_set = ContestSummarySerialiser(many=True)
    task_set = TaskSerialiser(many=True)

    class Meta:
        model = Contest
        fields = "__all__"


# Team summary entry
class TeamResultsSummarySerialiser(serializers.ModelSerializer):
    contestsummary_set = ContestSummarySerialiser(many=True)

    class Meta:
        model = Team
        fields = "__all__"
