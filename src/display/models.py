import dateutil.parser
import html2text as html2text
import rest_framework.exceptions as drf_exceptions
import datetime
import logging
import random
import uuid
from random import choice
from string import ascii_uppercase, digits, ascii_lowercase
from typing import List, Optional, Tuple, Dict
from unittest.mock import Mock

import eval7 as eval7
from django import core
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User, Group
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.mail import send_mail
from django.core.validators import MaxValueValidator, MinValueValidator

from django.db import models, IntegrityError
from django.db.models import Q
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django_use_email_as_username.models import BaseUser, BaseUserManager
from guardian.mixins import GuardianUserMixin
from guardian.shortcuts import get_objects_for_user, assign_perm, get_users_with_perms
from multiselectfield import MultiSelectField
from six import text_type
from timezone_field import TimeZoneField

# Create your models here.
from django.db.models.signals import post_save, pre_save, post_delete, pre_delete, m2m_changed
from django.dispatch import receiver
from django_countries.fields import CountryField
from phonenumber_field.modelfields import PhoneNumberField
from solo.models import SingletonModel

from display.calculate_gate_times import calculate_and_get_relative_gate_times
from display.calculators.positions_and_gates import Position
from display.coordinate_utilities import bearing_difference
from display.map_plotter_shared_utilities import MAP_CHOICES
from display.my_pickled_object_field import MyPickledObjectField
from display.poker_cards import PLAYING_CARDS
from display.track_merger import merge_tracks
from display.utilities import get_country_code_from_location
from display.waypoint import Waypoint
from display.wind_utilities import calculate_ground_speed_combined
from display.traccar_factory import get_traccar_instance
from live_tracking_map.settings import SERVER_ROOT

from phonenumbers.phonenumber import PhoneNumber

from traccar_facade import Traccar

TRACCAR = "traccar"
TRACKING_SERVICES = ((TRACCAR, "Traccar"),)
TRACKING_DEVICE = "device"
TRACKING_PILOT = "pilot_app"
TRACKING_COPILOT = "copilot_app"
TRACKING_PILOT_AND_COPILOT = "pilot_app_or_copilot_a[["
TRACKING_DEVICES = (
    (TRACKING_DEVICE, "Hardware GPS tracker"),
    (TRACKING_PILOT, "Pilot's Air Sports Live Tracking app"),
    (TRACKING_COPILOT, "Copilot's Air Sports Live Tracking app"),
    (TRACKING_PILOT_AND_COPILOT, "Pilot's or copilot's Air Sports Live Tracking app"),
)

TURNPOINT = "tp"
STARTINGPOINT = "sp"
FINISHPOINT = "fp"
SECRETPOINT = "secret"
TAKEOFF_GATE = "to"
LANDING_GATE = "ldg"
INTERMEDIARY_STARTINGPOINT = "isp"
INTERMEDIARY_FINISHPOINT = "ifp"
GATES_TYPES = (
    (TURNPOINT, "Turning point"),
    (STARTINGPOINT, "Starting point"),
    (FINISHPOINT, "Finish point"),
    (SECRETPOINT, "Secret point"),
    (TAKEOFF_GATE, "Takeoff gate"),
    (LANDING_GATE, "Landing gate"),
    (INTERMEDIARY_STARTINGPOINT, "Intermediary starting point"),
    (INTERMEDIARY_FINISHPOINT, "Intermediary finish point"),
)

TRACKING_DEVICE_TIMEOUT = 10

logger = logging.getLogger(__name__)


def user_directory_path(instance, filename):
    return "aeroplane_{0}/{1}".format(instance.registration, filename)


class TraccarCredentials(SingletonModel):
    server_name = models.CharField(max_length=100, default="A name")
    protocol = models.CharField(max_length=10, default="http")
    address = models.CharField(max_length=100, default="traccar:8082")
    token = models.CharField(max_length=100, default="REPLACE_ME")

    def __str__(self):
        return "Traccar credentials: {}".format(self.address)

    class Meta:
        verbose_name = "Traccar credentials"


class MyUser(BaseUser, GuardianUserMixin):
    username = models.CharField(max_length=50, default="not_applicable")
    objects = BaseUserManager()

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

    def send_welcome_email(self, person: "Person"):
        html = render_to_string("display/welcome_email.html",
                                {"person": person})
        converter = html2text.HTML2Text()
        plaintext = converter.handle(html)
        try:
            send_mail(
                f"Welcome to Air Sports Live Tracking",
                plaintext,
                None,  # Should default to system from email
                recipient_list=[self.email, "support@airsports.no"],
                html_message=html
            )
        except:
            logger.error(f"Failed sending email to {self}")

    def send_contest_creator_email(self, person: "Person"):
        html = render_to_string("display/contestmanagement_email.html",
                                {"person": person})
        converter = html2text.HTML2Text()
        plaintext = converter.handle(html)
        logger.debug(f'Sending welcome email to {person}')
        try:
            send_mail(
                f"You have been granted contest creation privileges at Air Sports Live Tracking",
                plaintext,
                None,  # Should default to system from email
                recipient_list=[self.email, "support@airsports.no"],
                html_message=html
            )
        except:
            logger.error(f"Failed sending email to {self}")


class Aeroplane(models.Model):
    registration = models.CharField(max_length=20)
    colour = models.CharField(max_length=40, blank=True)
    type = models.CharField(max_length=50, blank=True)
    picture = models.ImageField(null=True, blank=True)

    def __str__(self):
        return self.registration


class Route(models.Model):
    name = models.CharField(max_length=200)
    use_procedure_turns = models.BooleanField(default=True, blank=True)
    rounded_corners = models.BooleanField(default=False, blank=True)
    corridor_width = models.FloatField(default=0.5, blank=True)
    waypoints = MyPickledObjectField(default=list)
    takeoff_gate = MyPickledObjectField(default=None, null=True)
    landing_gate = MyPickledObjectField(default=None, null=True)

    def get_location(self) -> Tuple[float, float]:
        if self.waypoints and len(self.waypoints) > 0:
            return self.waypoints[0].latitude, self.waypoints[0].longitude
        if self.takeoff_gate:
            return self.takeoff_gate.latitude, self.takeoff_gate.longitude
        if self.landing_gate:
            return self.landing_gate.latitude, self.landing_gate.longitude
        return 0, 0

    def clean(self):
        return
        # for index in range(len(self.waypoints) - 1):
        #     waypoint = self.waypoints[index]  # type: Waypoint
        #     if waypoint.distance_next < 1852 and self.rounded_corners:
        #         raise ValidationError(
        #             f"Distance from {waypoint.name} to {self.waypoints[index + 1].name} should be greater than 1 NM when using rounded corners. Perhaps there is an error in your route file."
        #         )
        #     if (
        #             waypoint.distance_next < 1852 / 2
        #             and self.waypoints[index + 1].type != "secret"
        #             and waypoint.type != "secret"
        #     ):
        #         raise ValidationError(
        #             f"Distance from {waypoint.name} to {self.waypoints[index + 1].name} should be greater than 0.5 NM"
        #         )
        #     if waypoint.distance_next < 20:
        #         raise ValidationError(
        #             f"Distance from {waypoint.name} to {self.waypoints[index + 1].name} ({waypoint.distance_next}m) should be greater than 200m if not this or the next gate are secret"
        #         )

    def validate_gate_polygons(self):
        waypoint_names = [gate.name for gate in self.waypoints if gate.type != "secret"]
        if self.prohibited_set.filter(type="gate"):
            if len(waypoint_names) != len(set(waypoint_names)):
                self.delete()
                raise ValidationError("You cannot have multiple waypoints with the same name if you use gate polygons")
        for gate_polygon in self.prohibited_set.filter(type="gate"):
            if gate_polygon.name not in waypoint_names:
                self.delete()
                raise ValidationError(f"Gate polygon '{gate_polygon.name}' is not matched by any turning point names.")

    def __str__(self):
        return self.name


class Prohibited(models.Model):
    name = models.CharField(max_length=200)
    route = models.ForeignKey(Route, on_delete=models.CASCADE)
    path = MyPickledObjectField(default=list)
    type = models.CharField(max_length=100, blank=True, default="")
    tooltip_position = models.JSONField(null=True, blank=True)


def get_next_turning_point(waypoints: List, gate_name: str) -> Waypoint:
    found_current = False
    for gate in waypoints:
        if found_current:
            return gate
        if gate.name == gate_name:
            found_current = True


def is_procedure_turn(bearing1, bearing2) -> bool:
    """
    Return True if the turn is more than 90 degrees

    :param bearing1: degrees
    :param bearing2: degrees
    :return:
    """
    return abs(bearing_difference(bearing1, bearing2)) > 90


class CharNullField(models.CharField):
    description = "CharField that stores NULL"

    def get_db_prep_value(self, value, connection=None, prepared=False):
        value = super(CharNullField, self).get_db_prep_value(value, connection, prepared)
        if value == "":
            return None
        else:
            return value


class Person(models.Model):
    first_name = models.CharField(max_length=200)
    last_name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = PhoneNumberField(blank=True, null=True)
    creation_time = models.DateTimeField(
        auto_now_add=True,
        help_text="Used to figure out when a not validated personal and user should be deleted",
    )
    validated = models.BooleanField(
        default=True,
        help_text="Usually true, but set to false for persons created automatically during "
                  "app API login. This is used to signify that the user profile must be "
                  "updated. If this remains false for more than a few days, the person "
                  "object and corresponding user will be deleted from the system.  This "
                  "must therefore be set to True when submitting an updated profile from "
                  "the app.",
    )
    app_tracking_id = models.CharField(
        max_length=28,
        editable=False,
        help_text="An automatically generated tracking ID which is distributed to the tracking app",
    )
    simulator_tracking_id = models.CharField(
        max_length=28,
        editable=False,
        help_text="An automatically generated tracking ID which is distributed to the simulator integration. Persons or contestants identified by this field should not be displayed on the global map.",
    )
    app_aircraft_registration = models.CharField(
        max_length=100,
        default="",
        blank=True,
        help_text="The display name of person positions on the global tracking map (should be an aircraft registration",
    )
    picture = models.ImageField(null=True, blank=True)
    biography = models.TextField(blank=True)
    country = CountryField(blank=True)
    is_public = models.BooleanField(
        default=False,
        help_text="If true, the person's name will be displayed together with the callsign on the global map",
    )
    last_seen = models.DateTimeField(null=True, blank=True)

    @property
    def is_tracking_active(self):
        return (
                self.last_seen and (
                datetime.datetime.now(datetime.timezone.utc) - self.last_seen).total_seconds() < 10 * 60
        )

    @property
    def phone_country_prefix(self):
        phone = self.phone  # type: PhoneNumber
        return phone.country_code if phone else ""

    @property
    def phone_national_number(self):
        phone = self.phone  # type: PhoneNumber
        return phone.national_number if phone else ""

    @property
    def country_flag_url(self):
        if self.country:
            return self.country.flag
        return None

    @property
    def has_user(self):
        return MyUser.objects.filter(email=self.email).exists()

    def __str__(self):
        return "{} {}".format(self.first_name, self.last_name)

    @classmethod
    def get_or_create(
            cls,
            first_name: Optional[str],
            last_name: Optional[str],
            phone: Optional[str],
            email: Optional[str],
    ) -> Optional["Person"]:
        possible_person = None
        if phone is not None and len(phone) > 0:
            possible_person = Person.objects.filter(phone=phone)
        if (not possible_person or possible_person.count() == 0) and email is not None and len(email) > 0:
            possible_person = Person.objects.filter(email__iexact=email)
        elif not possible_person or possible_person.count() == 0:
            if first_name is not None and len(first_name) > 0 and last_name is not None and len(last_name) > 0:
                possible_person = Person.objects.filter(
                    first_name__iexact=first_name, last_name__iexact=last_name
                ).first()
        if possible_person is None or possible_person.count() == 0:
            return Person.objects.create(phone=phone, email=email, first_name=first_name, last_name=last_name)
        return possible_person.first()

    def validate(self):
        if Person.objects.filter(email=self.email).exclude(pk=self.pk).exists():
            raise ValidationError("A person with this email already exists")


class Crew(models.Model):
    member1 = models.ForeignKey(Person, on_delete=models.PROTECT, related_name="crewmember_one")
    member2 = models.ForeignKey(
        Person,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="crewmember_two",
    )

    @property
    def table_display(self):
        if self.member2:
            return "{}<br/>{}".format(self.member1, self.member2)
        return "{}".format(self.member1)

    def validate(self):
        if Crew.objects.filter(member1=self.member1, member2=self.member2).exclude(pk=self.pk).exists():
            raise ValidationError("A crew with this email already exists")

    def __str__(self):
        if self.member2:
            return "{} and {}".format(self.member1, self.member2)
        return "{}".format(self.member1)


class Club(models.Model):
    name = models.CharField(max_length=200)
    country = CountryField(blank=True)
    logo = models.ImageField(null=True, blank=True)

    # class Meta:
    #     unique_together = ("name", "country")

    def validate(self):
        if Club.objects.filter(name=self.name).exclude(pk=self.pk).exists():
            raise ValidationError("A club with this email already exists")

    def __str__(self):
        return self.name

    @property
    def country_flag_url(self):
        if self.country:
            return self.country.flag
        return None


class Team(models.Model):
    aeroplane = models.ForeignKey(Aeroplane, on_delete=models.PROTECT)
    crew = models.ForeignKey(Crew, on_delete=models.PROTECT)
    logo = models.ImageField(null=True, blank=True)
    country = CountryField(blank=True)
    club = models.ForeignKey(Club, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return "{} in {}".format(self.crew, self.aeroplane)

    @property
    def table_display(self):
        return f"{self.crew.table_display}<br/>{self.aeroplane}"

    @property
    def country_flag_url(self):
        if self.country:
            return self.country.flag
        return None

    @classmethod
    def get_or_create_from_signup(
            cls, user: MyUser, copilot: Person, aircraft_registration: str, club_name: str
    ) -> "Team":
        my_person = Person.objects.get(email=user.email)
        crew, _ = Crew.objects.get_or_create(member1=my_person, member2=copilot)
        aircraft, _ = Aeroplane.objects.get_or_create(registration=aircraft_registration)
        club, _ = Club.objects.get_or_create(name=club_name)
        team, _ = Team.objects.get_or_create(crew=crew, aeroplane=aircraft, club=club)
        return team


class ContestTeam(models.Model):
    contest = models.ForeignKey("Contest", on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    air_speed = models.FloatField(default=70, help_text="The planned airspeed for the contestant")
    tracking_service = models.CharField(
        default=TRACCAR,
        choices=TRACKING_SERVICES,
        max_length=30,
        help_text="Supported tracking services: {}".format(TRACKING_SERVICES),
    )
    tracking_device = models.CharField(
        default=TRACKING_PILOT_AND_COPILOT,
        choices=TRACKING_DEVICES,
        max_length=30,
        help_text="The device used for tracking the team",
    )
    tracker_device_id = models.CharField(
        max_length=100,
        help_text="ID of physical tracking device that will be brought into the plane. Leave empty if official Air Sports Live Tracking app is used. Note that only a single tracker is to be used per plane.",
        blank=True,
        null=True,
    )

    class Meta:
        unique_together = ("contest", "team")

    def clean(self):
        if self.tracking_device == TRACKING_DEVICE and (
                self.tracker_device_id is None or len(self.tracker_device_id) == 0
        ):
            raise ValidationError(
                f"Tracking device is set to {self.get_tracking_device_display()}, but no tracker device ID is supplied"
            )
        try:
            if self.tracking_device == TRACKING_COPILOT and self.team.crew.member2 is None:
                raise ValidationError(
                    f"Tracking device is set to {self.get_tracking_device_display()}, but there is no copilot"
                )
        except ObjectDoesNotExist:
            pass

    def __str__(self):
        return str(self.team)

    def get_tracker_id(self) -> str:
        if self.tracking_device == TRACKING_DEVICE:
            return self.tracker_device_id
        if self.tracking_device in (TRACKING_PILOT, TRACKING_PILOT_AND_COPILOT):
            return self.team.crew.member1.app_tracking_id
        if self.tracking_device == TRACKING_COPILOT:
            return self.team.crew.member2.app_tracking_id
        logger.error(
            f"ContestTeam {self.team} for contest {self.contest} does not have a tracker ID for tracking device {self.tracking_device}"
        )
        return ""


class Contest(models.Model):
    DESCENDING = "desc"
    ASCENDING = "asc"
    SORTING_DIRECTION = ((DESCENDING, "Descending"), (ASCENDING, "Ascending"))
    summary_score_sorting_direction = models.CharField(
        default=ASCENDING,
        choices=SORTING_DIRECTION,
        help_text="Whether the lowest (ascending) or highest (descending) score is the best result",
        max_length=50,
        blank=True,
    )
    autosum_scores = models.BooleanField(
        default=True,
        help_text="If true, contest summary points for a team will be updated with the new sum when any task is updated",
    )
    name = models.CharField(max_length=100, unique=True)
    time_zone = TimeZoneField()
    latitude = models.FloatField(
        default=0,
        help_text="Approximate location of contest, used for global map display",
        blank=True,
    )
    longitude = models.FloatField(
        default=0,
        help_text="Approximate location of contest, used for global map display",
        blank=True,
    )
    start_time = models.DateTimeField(
        help_text="The start time of the contest. Used for sorting. All navigation tasks should ideally be within this time interval."
    )
    finish_time = models.DateTimeField(
        help_text="The finish time of the contest. Used for sorting. All navigation tasks should ideally be within this time interval."
    )
    contest_teams = models.ManyToManyField(Team, blank=True, through=ContestTeam)
    is_public = models.BooleanField(
        default=False,
        help_text="A public contest is visible to people who are not logged and does not require special privileges",
    )
    is_featured = models.BooleanField(
        default=False,
        help_text="A featured contest is visible to all (if it is public). If it is not featured, a direct link is required to access it.",
    )
    contest_website = models.CharField(help_text="URL to contest website", blank=True, default="", max_length=300)
    header_image = models.ImageField(
        null=True,
        blank=True,
        help_text="Nice image that is shown on top of the event information on the map.",
    )
    logo = models.ImageField(
        null=True,
        blank=True,
        help_text="Quadratic logo that is shown next to the event in the event list",
    )
    country = CountryField(blank=True, null=True, help_text="Optional, if omitted country will be inferred from latitude and longitude if they are provided.")

    @property
    def country_flag_url(self):
        print(f"Country: {self.country}")
        if self.country:
            return self.country.flag
        return None

    @property
    def share_string(self):
        if self.is_public and self.is_featured:
            return "Public"
        elif self.is_public and not self.is_featured:
            return "Unlisted"
        else:
            return "Private"

    def __str__(self):
        return self.name

    class Meta:
        ordering = ("-start_time", "-finish_time")

    def initialise(self, user: MyUser):
        self.start_time = self.time_zone.localize(self.start_time.replace(tzinfo=None))
        self.finish_time = self.time_zone.localize(self.finish_time.replace(tzinfo=None))
        if self.latitude != 0 and self.longitude != 0 and (not self.country or self.country==""):
            self.country = get_country_code_from_location(self.latitude, self.longitude)
        self.save()
        assign_perm("delete_contest", user, self)
        assign_perm("view_contest", user, self)
        assign_perm("add_contest", user, self)
        assign_perm("change_contest", user, self)

    def replace_team(self, old_team: Optional[Team], new_team: Team, tracking_data: Dict) -> ContestTeam:
        """
        Whenever a ContestTeam is modified, we need to update all navigation tasks, contest summaries, tasks summaries,
        and team test scores.
        """
        ContestTeam.objects.filter(contest=self, team=old_team).delete()
        ContestTeam.objects.filter(contest=self, team=new_team).delete()
        ct = ContestTeam.objects.create(contest=self, team=new_team, **tracking_data)
        Contestant.objects.filter(navigation_task__contest=self, team=old_team).update(team=new_team)
        ContestSummary.objects.filter(contest=self, team=old_team).update(team=new_team)
        TaskSummary.objects.filter(task__contest=self, team=old_team).update(team=new_team)
        TeamTestScore.objects.filter(task_test__task__contest=self, team=old_team).update(team=new_team)
        return ct

    def update_position_if_not_set(self, latitude, longitude):
        if self.latitude == 0 and self.longitude == 0:
            self.latitude = latitude
            self.longitude = longitude
            if not self.country:
                self.country = get_country_code_from_location(self.latitude, self.longitude)
            self.save()

    def make_public(self):
        self.is_public = True
        self.is_featured = True
        self.save()

    def make_private(self):
        self.is_public = False
        self.is_featured = False
        self.navigationtask_set.all().update(is_featured=False, is_public=False)
        self.save()

    def make_unlisted(self):
        self.is_public = True
        self.is_featured = False
        self.navigationtask_set.all().update(is_featured=False)
        self.save()

    @classmethod
    def visible_contests_for_user(cls, user: MyUser):
        return get_objects_for_user(
            user, "display.view_contest", klass=Contest, accept_global_perms=False
        ) | Contest.objects.filter(is_public=True)

    @property
    def contest_team_count(self):
        return self.contest_teams.all().count()

    @property
    def editors(self) -> List:
        users = get_users_with_perms(self, attach_perms=True)
        return [user for user, permissions in users.items() if "change_contest" in permissions]


class NavigationTask(models.Model):
    PRECISION = "precision"
    ANR_CORRIDOR = "anr_corridor"
    AIRSPORTS = "airsports"
    POKER = "poker"
    LANDING = "landing"
    NAVIGATION_TASK_TYPES = (
        (PRECISION, "Precision"),
        (ANR_CORRIDOR, "ANR Corridor"),
        (AIRSPORTS, "Airsports"),
        (POKER, "Poker run"),
        (LANDING, "Landing"),
    )
    DESCENDING = "desc"
    ASCENDING = "asc"
    SORTING_DIRECTION = ((DESCENDING, "Descending"), (ASCENDING, "Ascending"))
    name = models.CharField(max_length=200)
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE)
    route = models.OneToOneField(Route, on_delete=models.PROTECT)
    scorecard = models.ForeignKey(
        "Scorecard",
        on_delete=models.PROTECT,
        help_text="Reference to an existing scorecard name. Currently existing scorecards: {}".format(
            lambda: ", ".join([str(item) for item in Scorecard.objects.all()])
        ),
    )
    track_score_override = models.ForeignKey("TrackScoreOverride", on_delete=models.SET_NULL, null=True, blank=True)
    gate_score_override = models.ManyToManyField("GateScoreOverride", blank=True)
    editable_route = models.ForeignKey("EditableRoute", on_delete=models.SET_NULL, null=True, blank=True)
    score_sorting_direction = models.CharField(
        default=ASCENDING,
        choices=SORTING_DIRECTION,
        help_text="Whether the lowest (ascending) or highest (descending) score is the best result",
        max_length=50,
        blank=True,
    )
    start_time = models.DateTimeField(
        help_text="The start time of the navigation test. Not really important, but nice to have"
    )
    finish_time = models.DateTimeField(
        help_text="The finish time of the navigation test. Not really important, but nice to have"
    )
    is_public = models.BooleanField(
        default=False,
        help_text="The navigation test is only viewable by unauthenticated users or users without object permissions if this is True",
    )
    is_featured = models.BooleanField(
        default=False,
        help_text="A featured navigation is visible to all (if public). Otherwise a direct link is required to access it",
    )

    wind_speed = models.FloatField(
        default=0,
        help_text="The navigation test wind speed. This is used to calculate gate times if these are not predefined.",
        validators=[MaxValueValidator(40), MinValueValidator(0)],
    )
    wind_direction = models.FloatField(
        default=0,
        help_text="The navigation test wind direction. This is used to calculate gate times if these are not predefined.",
        validators=[MaxValueValidator(360), MinValueValidator(0)],
    )
    minutes_to_starting_point = models.FloatField(
        default=5,
        help_text="The number of minutes from the take-off time until the starting point",
    )
    minutes_to_landing = models.FloatField(
        default=30,
        help_text="The number of minutes from the finish point to the contestant should have landed",
    )
    display_background_map = models.BooleanField(
        default=True,
        help_text="If checked the online tracking map shows the mapping background. Otherwise the map will be blank.",
    )
    display_secrets = models.BooleanField(
        default=True,
        help_text="If checked secret gates will be displayed on the map. Otherwise the map will only include gates that"
                  " are not secret, and also not display annotations related to the secret gates.",
    )
    allow_self_management = models.BooleanField(
        default=False,
        help_text="If checked, authenticated users will be allowed to set up themselves as a contestant after having registered for the contest.",
    )
    default_map = models.CharField(choices=MAP_CHOICES, default="cyclosm", max_length=200)
    default_line_width = models.FloatField(default=1)
    calculation_delay_minutes = models.FloatField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Number of minutes processions and scores should be delayed before they are made available on the tracking map.",
    )

    @classmethod
    def get_visible_navigation_tasks(cls, user: User):
        contests = get_objects_for_user(user, "display.view_contest", klass=Contest, accept_global_perms=False)
        return NavigationTask.objects.filter(
            Q(contest__in=contests) | Q(is_public=True, contest__is_public=True, is_featured=True)
        )

    @property
    def is_poker_run(self) -> bool:
        return self.POKER in self.scorecard.task_type

    @property
    def tracking_link(self) -> str:
        return reverse("frontend_view_map", kwargs={"pk": self.pk})

    @property
    def everything_public(self):
        return self.is_public and self.contest.is_public and self.is_featured

    @property
    def actual_rules(self):
        mock_contestant = Mock(Contestant)
        mock_contestant.navigation_task = self
        mock_contestant.get_track_score_override.return_value = self.track_score_override

        def gate_score_override(gate_type):
            for item in self.gate_score_override.all():
                if gate_type in item.for_gate_types:
                    return item

        mock_contestant.get_gate_score_override = gate_score_override
        return self.scorecard.scores_display(mock_contestant)

    @property
    def share_string(self):
        if self.is_public and self.is_featured:
            return "Public"
        elif self.is_public and not self.is_featured:
            return "Unlisted"
        else:
            return "Private"

    @property
    def display_contestant_rank_summary(self):
        return TaskTest.objects.filter(task__contest=self.contest).count() > 1

    class Meta:
        ordering = ("start_time", "finish_time")

    def __str__(self):
        return "{}: {}".format(self.name, self.start_time.isoformat())

    def refresh_editable_route(self):
        if self.contestant_set.all().count() > 0:
            raise ValidationError("Cannot refresh the route as long as they are contestants")
        if self.editable_route is None:
            raise ValidationError("There is no route to refresh")
        route = None
        if self.scorecard.calculator in (Scorecard.PRECISION, Scorecard.POKER):
            route = self.editable_route.create_precision_route(self.route.use_procedure_turns)
        elif self.scorecard.calculator == Scorecard.ANR_CORRIDOR:
            route = self.editable_route.create_anr_route(self.route.rounded_corners, self.route.corridor_width)
        elif self.scorecard.calculator == Scorecard.AIRSPORTS:
            route = self.editable_route.create_airsports_route(self.route.rounded_corners)
        if route:
            old_route = self.route
            self.route = route
            self.save()
            old_route.delete()

    def make_public(self):
        self.is_public = True
        self.is_featured = True
        self.contest.is_public = True
        self.contest.is_featured = True
        self.save()
        self.contest.save()

    def make_unlisted(self):
        self.is_public = True
        self.is_featured = False
        self.contest.is_public = True
        self.save()
        self.contest.save()

    def make_private(self):
        self.is_public = False
        self.is_featured = False
        self.save()

    def create_results_service_test(self):
        task, _ = Task.objects.get_or_create(
            contest=self.contest,
            name=f"Navigation task {self.name}",
            defaults={
                "summary_score_sorting_direction": Task.ASCENDING,
                "heading": self.name,
            },
        )
        TaskTest.objects.filter(task=task, name="Navigation").delete()
        test = TaskTest.objects.create(
            task=task,
            name="Navigation",
            heading="Navigation",
            sorting=TaskTest.ASCENDING,
            index=0,
            navigation_task=self,
        )
        return test

    def export_to_results_service(self):
        self.create_results_service_test()
        test = self.tasktest
        task = test.task
        for contestant in self.contestant_set.all().order_by("contestanttrack__score"):
            try:
                TeamTestScore.objects.create(
                    team=contestant.team,
                    task_test=test,
                    points=contestant.contestanttrack.score,
                )
                # try:
                #     existing_task_summary = TaskSummary.objects.get(team=contestant.team, task=task)
                #     existing_task_summary.points += contestant.contestanttrack.score
                #     existing_task_summary.save()
                # except ObjectDoesNotExist:
                #     TaskSummary.objects.create(team=contestant.team, task=task, points=contestant.contestanttrack.score)
                #
                # try:
                #     existing_contest_summary = ContestSummary.objects.get(team=contestant.team, contest=self.contest)
                #     existing_contest_summary.points += contestant.contestanttrack.score
                #     existing_contest_summary.save()
                # except ObjectDoesNotExist:
                #     ContestSummary.objects.create(team=contestant.team, contest=self.contest,
                #                                   points=contestant.contestanttrack.score)
            except IntegrityError:
                # Caused if there are multiple contestants for the same team. We ignore all but the first one so we only include the lowest score
                pass


class Scorecard(models.Model):
    PRECISION = "precision"
    ANR_CORRIDOR = "anr_corridor"
    AIRSPORTS = "airsports"
    POKER = "poker"
    LANDING = "landing"
    CALCULATORS = (
        (PRECISION, "Precision"),
        (ANR_CORRIDOR, "ANR Corridor"),
        (POKER, "Poker run"),
        (LANDING, "Landing"),
        (AIRSPORTS, "Airsports"),
    )

    name = models.CharField(max_length=100, default="default", unique=True)
    calculator = models.CharField(
        choices=CALCULATORS,
        default=PRECISION,
        max_length=20,
        help_text="Supported calculator types",
    )
    task_type = MultiSelectField(choices=NavigationTask.NAVIGATION_TASK_TYPES, default=list)
    use_procedure_turns = models.BooleanField(default=True, blank=True)
    backtracking_penalty = models.FloatField(default=200, help_text="The number of points given for backtracking")
    backtracking_bearing_difference = models.FloatField(
        default=90,
        help_text="The bearing difference from the leg direction to initiate backtracking",
    )
    backtracking_grace_time_seconds = models.FloatField(
        default=5,
        help_text="The number of seconds the contestant is allowed to backtrack before backtracking penalty is applied",
    )
    backtracking_maximum_penalty = models.FloatField(
        default=-1, help_text="Negative numbers means the maximum is ignored"
    )
    below_minimum_altitude_penalty = models.FloatField(
        default=500,
        help_text="Penalty for flying below the minimum altitude (not applied automatically)",
    )
    below_minimum_altitude_maximum_penalty = models.FloatField(
        default=500,
        help_text="The maximum penalty that can be accumulated for flying below minimum altitude (not applied automatically)",
    )

    takeoff_gate_score = models.ForeignKey(
        "GateScore",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="takeoff",
    )
    landing_gate_score = models.ForeignKey(
        "GateScore",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="landing",
    )
    turning_point_gate_score = models.ForeignKey(
        "GateScore",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="turning_point",
    )
    starting_point_gate_score = models.ForeignKey(
        "GateScore",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="starting",
    )
    finish_point_gate_score = models.ForeignKey(
        "GateScore",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="finish",
    )
    secret_gate_score = models.ForeignKey(
        "GateScore",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="secret",
    )

    prohibited_zone_penalty = models.FloatField(
        default=200,
        help_text="Penalty for entering prohibited zone such as controlled airspace or other prohibited areas",
    )

    penalty_zone_grace_time = models.FloatField(
        default=3,
        help_text="The number of seconds the contestant can be within the penalty zone before getting penalty",
    )
    penalty_zone_penalty_per_second = models.FloatField(
        default=3, help_text="The number of points per second beyond the grace time while inside the penalty zone"
    )
    penalty_zone_maximum = models.FloatField(default=100, help_text="Maximum penalty within a single zone")

    ##### ANR Corridor
    corridor_grace_time = models.IntegerField(default=5, help_text="The corridor grace time for ANR tasks")
    corridor_outside_penalty = models.FloatField(
        default=3, help_text="The penalty awarded for leaving the ANR corridor"
    )
    corridor_maximum_penalty = models.FloatField(default=-1, help_text="The maximum penalty for leaving the corridor")

    def __str__(self):
        return self.name

    def __get_label(self, field):
        return text_type(self._meta.get_field(field).verbose_name)

    def __get_help_text(self, field):
        return text_type(self._meta.get_field(field).help_text)

    def __format_value(self, field, contestant) -> Dict:
        return {
            "name": self.__get_label(field),
            "value": getattr(self, f"get_{field}")(contestant)
            if hasattr(self, f"get_{field}")
            else getattr(self, f"{field}"),
            "help_text": self.__get_help_text(field),
        }

    @staticmethod
    def __format_title(title):
        text = title.split("_")
        return text[0].capitalize() + " " + " ".join(text[1:])

    def __format_value_gate(self, field, contestant, gate_type) -> Dict:
        return {
            "name": self.__format_title(field),
            "value": getattr(self, f"get_{field}_for_gate_type")(gate_type, contestant),
            "help_text": getattr(self, f"get_{field}_for_gate_type").__doc__,
        }

    def scores_display(self, contestant: "Contestant") -> List[Dict]:
        if self.PRECISION in self.task_type:
            return self.__scores_display_precision(contestant)
        elif self.ANR_CORRIDOR in self.task_type:
            return self.__scores_display_anr(contestant)
        elif self.AIRSPORTS in self.task_type:
            return self.__scores_display_airsports(contestant)
        return []

    def scores_for_gate(self, contestant: "Contestant", gate: str) -> List[Dict]:
        return [
            self.__format_value_gate("penalty_per_second", contestant, gate),
            self.__format_value_gate("graceperiod_before", contestant, gate),
            self.__format_value_gate("graceperiod_after", contestant, gate),
            self.__format_value_gate("maximum_timing_penalty", contestant, gate),
            self.__format_value_gate("missed_penalty", contestant, gate),
            self.__format_value_gate("procedure_turn_penalty", contestant, gate),
            self.__format_value_gate("bad_crossing_extended_gate_penalty", contestant, gate),
            self.__format_value_gate("extended_gate_width", contestant, gate),
            self.__format_value_gate("backtracking_after_steep_gate_grace_period_seconds", contestant, gate),
            self.__format_value_gate("backtracking_after_gate_grace_period_nm", contestant, gate),
        ]

    def __scores_display_precision(self, contestant: "Contestant") -> List[Dict]:
        scores = {
            "track": [
                self.__format_value("backtracking_penalty", contestant),
                self.__format_value("backtracking_bearing_difference", contestant),
                self.__format_value("backtracking_grace_time_seconds", contestant),
                self.__format_value("backtracking_maximum_penalty", contestant),
                self.__format_value("below_minimum_altitude_penalty", contestant),
                self.__format_value("below_minimum_altitude_maximum_penalty", contestant),
                self.__format_value("prohibited_zone_penalty", contestant),
            ],
            "gates": [{"gate": item[1], "rules": self.scores_for_gate(contestant, item[0])} for item in GATES_TYPES],
        }
        return scores

    def __scores_display_anr(self, contestant: "Contestant") -> List[Dict]:
        scores = {
            "track": [
                self.__format_value("backtracking_penalty", contestant),
                self.__format_value("backtracking_bearing_difference", contestant),
                self.__format_value("backtracking_grace_time_seconds", contestant),
                self.__format_value("backtracking_maximum_penalty", contestant),
                self.__format_value("below_minimum_altitude_penalty", contestant),
                self.__format_value("below_minimum_altitude_maximum_penalty", contestant),
                self.__format_value("prohibited_zone_penalty", contestant),
                self.__format_value("corridor_grace_time", contestant),
                self.__format_value("corridor_outside_penalty", contestant),
                self.__format_value("corridor_maximum_penalty", contestant),
                self.__format_value("penalty_zone_grace_time", contestant),
                self.__format_value("penalty_zone_penalty_per_second", contestant),
                self.__format_value("penalty_zone_maximum", contestant),
                {
                    "name": "corridor width",
                    "value": contestant.navigation_task.route.corridor_width,
                    "help_text": "The width of the corridor in nautical miles",
                },
            ],
            "gates": [
                {"gate": item[1], "rules": self.scores_for_gate(contestant, item[0])}
                for item in GATES_TYPES
                if item[0] in (STARTINGPOINT, FINISHPOINT)
            ],
        }
        return scores

    def __scores_display_airsports(self, contestant: "Contestant") -> List[Dict]:
        scores = {
            "track": [
                self.__format_value("backtracking_penalty", contestant),
                self.__format_value("backtracking_bearing_difference", contestant),
                self.__format_value("backtracking_grace_time_seconds", contestant),
                self.__format_value("backtracking_maximum_penalty", contestant),
                self.__format_value("below_minimum_altitude_penalty", contestant),
                self.__format_value("below_minimum_altitude_maximum_penalty", contestant),
                self.__format_value("prohibited_zone_penalty", contestant),
                self.__format_value("corridor_grace_time", contestant),
                self.__format_value("corridor_outside_penalty", contestant),
                self.__format_value("corridor_maximum_penalty", contestant),
                self.__format_value("penalty_zone_grace_time", contestant),
                self.__format_value("penalty_zone_penalty_per_second", contestant),
                self.__format_value("penalty_zone_maximum", contestant),
                {
                    "name": "corridor width",
                    "value": contestant.navigation_task.route.corridor_width,
                    "help_text": "The width of the corridor in nautical miles",
                },
            ],
            "gates": [
                {"gate": item[1], "rules": self.scores_for_gate(contestant, item[0])}
                for item in GATES_TYPES
            ],
        }
        return scores

    def get_gate_scorecard(self, gate_type: str) -> "GateScore":
        if gate_type == "tp":
            gate_score = self.turning_point_gate_score
        elif gate_type in ("sp", "isp"):
            gate_score = self.starting_point_gate_score
        elif gate_type in ("fp", "ifp"):
            gate_score = self.finish_point_gate_score
        elif gate_type == "secret":
            gate_score = self.secret_gate_score
        elif gate_type in ("to", "ito"):
            gate_score = self.takeoff_gate_score
        elif gate_type in ("ldg", "ildg"):
            gate_score = self.landing_gate_score
        else:
            raise ValueError("Unknown gate type '{}'".format(gate_type))
        if gate_score is None:
            raise ValueError("Undefined gate score for '{}'".format(gate_type))
        return gate_score

    def get_gate_score_override(self, gate_type: str, contestant: "Contestant"):
        return contestant.get_gate_score_override(gate_type)

    def calculate_penalty_zone_score(self, contestant: "Contestant", enter: datetime.datetime, exit: datetime.datetime):
        difference = round((exit - enter).total_seconds()) - self.get_penalty_zone_grace_time(contestant)
        if difference < 0:
            return 0
        return min(
            self.get_penalty_zone_maximum(contestant), difference * self.get_penalty_zone_penalty_per_second(contestant)
        )

    def get_penalty_zone_grace_time(self, contestant: "Contestant"):
        if contestant:
            override = contestant.get_track_score_override()
            if override:
                if override.penalty_zone_grace_time is not None:
                    return override.penalty_zone_grace_time
        return self.penalty_zone_grace_time

    def get_penalty_zone_penalty_per_second(self, contestant: "Contestant"):
        if contestant:
            override = contestant.get_track_score_override()
            if override:
                if override.penalty_zone_penalty_per_second is not None:
                    return override.penalty_zone_penalty_per_second
        return self.penalty_zone_penalty_per_second

    def get_penalty_zone_maximum(self, contestant: "Contestant"):
        if contestant:
            override = contestant.get_track_score_override()
            if override:
                if override.penalty_zone_maximum is not None:
                    return override.penalty_zone_maximum
        return self.penalty_zone_maximum

    def get_backtracking_penalty(self, contestant: "Contestant"):
        if contestant:
            override = contestant.get_track_score_override()
            if override:
                if override.bad_course_penalty is not None:
                    return override.bad_course_penalty
        return self.backtracking_penalty

    def get_maximum_backtracking_penalty(self, contestant: "Contestant"):
        if contestant:
            override = contestant.get_track_score_override()
            if override:
                if override.bad_course_maximum_penalty is not None:
                    return override.bad_course_maximum_penalty
        return self.backtracking_maximum_penalty

    def get_backtracking_grace_time_seconds(self, contestant: "Contestant"):
        if contestant:
            override = contestant.get_track_score_override()
            if override:
                if override.bad_course_grace_time is not None:
                    return override.bad_course_grace_time
        return self.backtracking_grace_time_seconds

    def get_prohibited_zone_penalty(self, contestant: "Contestant"):
        if contestant:
            override = contestant.get_track_score_override()
            if override:
                if override.prohibited_zone_penalty is not None:
                    return override.prohibited_zone_penalty
        return self.prohibited_zone_penalty

    def get_gate_timing_score_for_gate_type(
            self,
            gate_type: str,
            contestant: "Contestant",
            planned_time: datetime.datetime,
            actual_time: Optional[datetime.datetime],
    ) -> float:
        gate_score = self.get_gate_scorecard(gate_type)
        return gate_score.calculate_score(
            planned_time,
            actual_time,
            self.get_gate_score_override(gate_type, contestant),
        )

    def get_missed_penalty_for_gate_type(self, gate_type: str, contestant: "Contestant") -> float:
        """
        The number of points given for each second from the target time
        """
        gate_score = self.get_gate_scorecard(gate_type)
        return gate_score.get_missed_penalty(self.get_gate_score_override(gate_type, contestant))

    def get_penalty_per_second_for_gate_type(self, gate_type: str, contestant: "Contestant") -> float:
        """
        The number of points given for each second from the target time
        """
        gate_score = self.get_gate_scorecard(gate_type)
        return gate_score.get_penalty_per_second(self.get_gate_score_override(gate_type, contestant))

    def get_maximum_timing_penalty_for_gate_type(self, gate_type: str, contestant: "Contestant") -> float:
        """
        The maximum penalty that can be awarded for being off time
        """
        gate_score = self.get_gate_scorecard(gate_type)
        return gate_score.get_maximum_penalty(self.get_gate_score_override(gate_type, contestant))

    def get_graceperiod_before_for_gate_type(self, gate_type: str, contestant: "Contestant") -> float:
        """
        The number of seconds the gate can be passed early without giving penalty
        """
        gate_score = self.get_gate_scorecard(gate_type)
        return gate_score.get_graceperiod_before(self.get_gate_score_override(gate_type, contestant))

    def get_graceperiod_after_for_gate_type(self, gate_type: str, contestant: "Contestant") -> float:
        """
        The number of seconds the gate can be passed late without giving penalty
        """
        gate_score = self.get_gate_scorecard(gate_type)
        return gate_score.get_graceperiod_after(self.get_gate_score_override(gate_type, contestant))

    def get_procedure_turn_penalty_for_gate_type(self, gate_type: str, contestant: "Contestant") -> float:
        """
        The penalty for missing a procedure turn
        """
        gate_score = self.get_gate_scorecard(gate_type)
        return gate_score.get_missed_procedure_turn_penalty(self.get_gate_score_override(gate_type, contestant))

    def get_bad_crossing_extended_gate_penalty_for_gate_type(self, gate_type: str, contestant: "Contestant") -> float:
        """
        The penalty for crossing the extended starting line backwards
        """
        gate_score = self.get_gate_scorecard(gate_type)
        return gate_score.get_bad_crossing_extended_gate_penalty(self.get_gate_score_override(gate_type, contestant))

    def get_extended_gate_width_for_gate_type(self, gate_type: str, contestant: "Contestant") -> float:
        """
        The width of the extended gate line
        """
        gate_score = self.get_gate_scorecard(gate_type)
        return gate_score.extended_gate_width

    def get_backtracking_after_steep_gate_grace_period_seconds_for_gate_type(
            self, gate_type: str, contestant: "Contestant"
    ) -> float:
        """
        The number of seconds after passing a gate with a steep turn (more than 90 degrees) where backtracking is not calculated
        """
        gate_score = self.get_gate_scorecard(gate_type)
        return gate_score.backtracking_after_steep_gate_grace_period_seconds

    def get_backtracking_after_gate_grace_period_nm_for_gate_type(
            self, gate_type: str, contestant: "Contestant"
    ) -> float:
        """
        The number of NM around a gate where backtracking is not calculated
        """
        gate_score = self.get_gate_scorecard(gate_type)
        return gate_score.backtracking_after_gate_grace_period_nm

    ### ANR Corridor
    def get_corridor_width(self, contestant: "Contestant"):
        """
        contestant is not optional

        :param contestant: not optional
        :return:
        """
        if contestant:
            override = contestant.get_track_score_override()
            if override:
                if override.corridor_width is not None:
                    return override.corridor_width
            return contestant.navigation_task.route.corridor_width

    def get_corridor_grace_time(self, contestant: "Contestant"):
        if contestant:
            override = contestant.get_track_score_override()
            if override:
                if override.corridor_grace_time is not None:
                    return override.corridor_grace_time
        return self.corridor_grace_time

    def get_corridor_outside_penalty(self, contestant: "Contestant"):
        if contestant:
            override = contestant.get_track_score_override()
            if override:
                if override.corridor_outside_penalty is not None:
                    return override.corridor_outside_penalty
        return self.corridor_outside_penalty

    def get_corridor_maximum_penalty(self, contestant: "Contestant"):
        if contestant:
            override = contestant.get_track_score_override()
            if override:
                if override.corridor_maximum_penalty is not None:
                    return override.corridor_maximum_penalty
        return self.corridor_maximum_penalty


class GateScore(models.Model):
    name = models.CharField(max_length=100, default="")
    extended_gate_width = models.FloatField(
        default=0,
        help_text="For SP it is 2 (1 nm each side), for tp with procedure turn it is 6",
    )
    bad_crossing_extended_gate_penalty = models.FloatField(default=200)
    graceperiod_before = models.FloatField(default=3)
    graceperiod_after = models.FloatField(default=3)
    maximum_penalty = models.FloatField(default=100)
    penalty_per_second = models.FloatField(default=2)
    missed_penalty = models.FloatField(default=100)
    bad_course_crossing_penalty = models.FloatField(default=0)
    missed_procedure_turn_penalty = models.FloatField(default=200)
    backtracking_after_steep_gate_grace_period_seconds = models.FloatField(default=0)
    backtracking_after_gate_grace_period_nm = models.FloatField(default=0.5)

    def get_missed_penalty(self, score_override: Optional["GateScoreOverride"]):
        if score_override and score_override.checkpoint_not_found is not None:
            return score_override.checkpoint_not_found
        return self.missed_penalty

    def get_graceperiod_before(self, score_override: Optional["GateScoreOverride"]):
        if score_override and score_override.checkpoint_grace_period_before is not None:
            return score_override.checkpoint_grace_period_before
        return self.graceperiod_before

    def get_graceperiod_after(self, score_override: Optional["GateScoreOverride"]):
        if score_override and score_override.checkpoint_grace_period_after is not None:
            return score_override.checkpoint_grace_period_after
        return self.graceperiod_after

    def get_maximum_penalty(self, score_override: Optional["GateScoreOverride"]):
        if score_override and score_override.checkpoint_maximum_penalty is not None:
            return score_override.checkpoint_maximum_penalty
        return self.maximum_penalty

    def get_bad_course_crossing_penalty(self, score_override: Optional["GateScoreOverride"]):
        if score_override and score_override.bad_course_penalty is not None:
            return score_override.bad_course_penalty
        return self.bad_course_crossing_penalty

    def get_bad_crossing_extended_gate_penalty(self, score_override: Optional["GateScoreOverride"]):
        if score_override and score_override.bad_crossing_extended_gate_penalty is not None:
            return score_override.bad_crossing_extended_gate_penalty
        return self.bad_crossing_extended_gate_penalty

    def get_missed_procedure_turn_penalty(self, score_override: Optional["GateScoreOverride"]):
        if score_override and score_override.missing_procedure_turn_penalty is not None:
            return score_override.missing_procedure_turn_penalty
        return self.missed_procedure_turn_penalty

    def get_penalty_per_second(self, score_override: Optional["GateScoreOverride"]):
        if score_override and score_override.checkpoint_penalty_per_second is not None:
            return score_override.checkpoint_penalty_per_second
        return self.penalty_per_second

    def get_backtracking_after_steep_gate_grace_period_seconds(self, score_override: Optional["GateScoreOverride"]):
        return self.backtracking_after_steep_gate_grace_period_seconds

    def get_backtracking_after_gate_grace_period_nm(self, score_override: Optional["GateScoreOverride"]):
        return self.backtracking_after_gate_grace_period_nm

    def calculate_score(
            self,
            planned_time: datetime.datetime,
            actual_time: Optional[datetime.datetime],
            score_override: Optional["GateScoreOverride"],
    ) -> float:
        """

        :param planned_time:
        :param actual_time: If None the gate is missed
        :return:
        """
        if actual_time is None:
            return self.get_missed_penalty(score_override)
        time_difference = (actual_time - planned_time).total_seconds()
        if -self.get_graceperiod_before(score_override) < time_difference < self.get_graceperiod_after(score_override):
            return 0
        else:
            if time_difference > 0:
                grace_limit = self.get_graceperiod_after(score_override)
            else:
                grace_limit = self.get_graceperiod_before(score_override)
            score = (round(abs(time_difference) - grace_limit)) * self.get_penalty_per_second(score_override)
            if self.get_maximum_penalty(score_override) >= 0:
                return min(self.get_maximum_penalty(score_override), score)
            return score


class TrackScoreOverride(models.Model):
    bad_course_grace_time = models.FloatField(
        default=None,
        blank=True,
        null=True,
        help_text="The number of seconds a bad course can be tolerated before generating a penalty",
    )
    bad_course_penalty = models.FloatField(
        default=None,
        blank=True,
        null=True,
        help_text="A amount of points awarded for a bad course",
    )
    bad_course_maximum_penalty = models.FloatField(
        default=None,
        blank=True,
        null=True,
        help_text="A amount of points awarded for a bad course",
    )
    prohibited_zone_penalty = models.FloatField(
        default=None,
        blank=True,
        null=True,
        help_text="Penalty for entering prohibited zone such as controlled airspace or other prohibited areas",
    )
    penalty_zone_grace_time = models.FloatField(
        default=3,
        help_text="The number of seconds the contestant can be within the penalty zone before getting penalty",
    )
    penalty_zone_penalty_per_second = models.FloatField(
        default=3, help_text="The number of points per second beyond the grace time while inside the penalty zone"
    )
    penalty_zone_maximum = models.FloatField(default=100, help_text="Maximum penalty within a single zone")

    ### ANR Corridor
    corridor_width = models.FloatField(default=None, blank=True, null=True, help_text="The width of the ANR corridor")
    corridor_grace_time = models.FloatField(
        default=None,
        blank=True,
        null=True,
        help_text="The grace time of the ANR corridor",
    )
    corridor_outside_penalty = models.FloatField(
        default=None,
        blank=True,
        null=True,
        help_text="The penalty awarded for leaving the ANR corridor",
    )
    corridor_maximum_penalty = models.FloatField(
        default=None,
        blank=True,
        null=True,
        help_text="The maximum penalty for leaving the corridor",
    )

    def __str__(self):
        return "Track score override for {}".format(self.navigationtask_set.first())


class GateScoreOverride(models.Model):
    for_gate_types = MyPickledObjectField(
        default=list,
        help_text="List of gates types (eg. tp, secret, sp) that should be overridden (all lower case)",
    )
    checkpoint_grace_period_before = models.FloatField(
        default=None,
        blank=True,
        null=True,
        help_text="The time before a checkpoint that no penalties are awarded",
    )
    checkpoint_grace_period_after = models.FloatField(
        default=None,
        blank=True,
        null=True,
        help_text="The time after a checkpoint that no penalties are awarded",
    )
    checkpoint_penalty_per_second = models.FloatField(
        default=None,
        blank=True,
        null=True,
        help_text="The number of points awarded per second outside of the grace period",
    )
    checkpoint_maximum_penalty = models.FloatField(
        default=None,
        blank=True,
        null=True,
        help_text="The maximum number of penalty points awarded for checkpoint timing",
    )
    checkpoint_not_found = models.FloatField(
        default=None,
        blank=True,
        null=True,
        help_text="The penalty for missing a checkpoint",
    )
    missing_procedure_turn_penalty = models.FloatField(
        default=None,
        blank=True,
        null=True,
        help_text="The penalty for missing a procedure turn",
    )
    bad_course_penalty = models.FloatField(
        default=None,
        blank=True,
        null=True,
        help_text="A amount of points awarded for crossing the gate in the wrong direction (e.g. for landing or takeoff)",
    )
    bad_crossing_extended_gate_penalty = models.FloatField(
        default=None,
        blank=True,
        null=True,
        help_text="The penalty awarded when crossing the extended gate in the wrong direction (typically used for start gate)",
    )

    def __str__(self):
        return "Gate score override for {}".format(self.navigationtask_set.first())


class Contestant(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    navigation_task = models.ForeignKey(NavigationTask, on_delete=models.CASCADE)
    adaptive_start = models.BooleanField(
        default=False,
        help_text="If true, takeoff time and minutes to starting point is ignored. Start time is set to the closest minute to the time crossing the starting line. This is typically used for a case where it is difficult to control the start time because of external factors such as ATC.",
    )
    takeoff_time = models.DateTimeField(
        help_text="The time the take of gate (if it exists) should be crossed. Otherwise it is the time power should be applied"
    )
    minutes_to_starting_point = models.FloatField(
        default=5,
        help_text="The number of minutes from the take-off time until the starting point",
    )
    finished_by_time = models.DateTimeField(
        help_text="The time it is expected that the navigation task has finished and landed (used among other things for knowing when the tracker is busy). Is also used for the gate time for the landing gate"
    )
    air_speed = models.FloatField(default=70, help_text="The planned airspeed for the contestant")
    contestant_number = models.PositiveIntegerField(
        help_text="A unique number for the contestant in this navigation task"
    )
    tracking_service = models.CharField(
        default=TRACCAR,
        choices=TRACKING_SERVICES,
        max_length=30,
        help_text="Supported tracking services: {}".format(TRACKING_SERVICES),
    )
    tracking_device = models.CharField(
        default=TRACKING_PILOT_AND_COPILOT,
        choices=TRACKING_DEVICES,
        max_length=30,
        help_text="The device used for tracking the team",
    )
    tracker_device_id = models.CharField(
        max_length=100,
        help_text="ID of physical tracking device that will be brought into the plane. If using the Air Sports Live Tracking app this should be left blank.",
        blank=True,
        null=True,
    )
    tracker_start_time = models.DateTimeField(
        help_text="When the tracker is handed to the contestant, can have no changes to the route (e.g. wind and timing) after this."
    )
    competition_class_longform = models.CharField(
        max_length=100,
        help_text="The class of the contestant, e.g. beginner, professional, et cetera",
        blank=True,
        null=True,
    )
    competition_class_shortform = models.CharField(
        max_length=100,
        help_text="The abbreviated class of the contestant, e.g. beginner, professional, et cetera",
        blank=True,
        null=True,
    )
    track_score_override = models.ForeignKey(TrackScoreOverride, on_delete=models.SET_NULL, null=True, blank=True)
    calculator_started = models.BooleanField(
        default=False,
        help_text="Set to true when the calculator has started. After this point it is not permitted to change the contestant",
    )
    gate_score_override = models.ManyToManyField(GateScoreOverride, blank=True)
    predefined_gate_times = MyPickledObjectField(
        default=None,
        null=True,
        blank=True,
        help_text="Dictionary of gates and their starting times (with time zone)",
    )
    wind_speed = models.FloatField(
        default=0,
        help_text="The navigation test wind speed. This is used to calculate gate times if these are not predefined.",
        validators=[MaxValueValidator(40), MinValueValidator(0)],
    )
    wind_direction = models.FloatField(
        default=0,
        help_text="The navigation test wind direction. This is used to calculate gate times if these are not predefined.",
        validators=[MaxValueValidator(360), MinValueValidator(0)],
    )
    annotation_index = models.IntegerField(default=0, help_text="Internal housekeeping for annotation transmission")

    class Meta:
        unique_together = ("navigation_task", "contestant_number")
        ordering = ("takeoff_time",)

    @property
    def starting_point_time_local(self) -> datetime.datetime:
        starting_point_time = self.takeoff_time + datetime.timedelta(
            minutes=self.navigation_task.minutes_to_starting_point
        )
        return starting_point_time.astimezone(self.navigation_task.contest.time_zone)

    @property
    def tracker_start_time_local(self) -> datetime.datetime:
        return self.tracker_start_time.astimezone(self.navigation_task.contest.time_zone)

    @property
    def finished_by_time_local(self) -> datetime.datetime:
        return self.finished_by_time.astimezone(self.navigation_task.contest.time_zone)

    @property
    def starting_gate_time(self) -> Optional[datetime.datetime]:
        return self.gate_times.get(self.navigation_task.route.waypoints[0].name)

    def get_final_gate_time(self) -> Optional[datetime.datetime]:
        final_gate = self.navigation_task.route.landing_gate or self.navigation_task.route.waypoints[-1]
        return self.gate_times.get(final_gate.name)

    def calculate_finish_time(self) -> datetime.datetime:
        print(self.gate_times)
        print(self.navigation_task.route.landing_gate)
        if self.navigation_task.route.landing_gate:
            return self.gate_times[self.navigation_task.route.landing_gate.name]
        return self.gate_times[self.navigation_task.route.waypoints[-1].name] + datetime.timedelta(
            minutes=self.navigation_task.minutes_to_landing
        )

    @property
    def termination_request_key(self):
        return f"termination_request_{self.pk}"

    def request_calculator_termination(self):
        logger.info(f"Signalling manual termination for contestant {self}")
        cache.set(self.termination_request_key, True, timeout=600)

    def save(self, **kwargs):
        self.tracker_device_id = self.tracker_device_id.strip() if self.tracker_device_id else ""
        if self.tracking_service == TRACCAR:
            traccar = get_traccar_instance()
            traccar.get_or_create_device(self.tracker_device_id, self.tracker_device_id)
        super().save(**kwargs)

    def _prohibited_zone_text(self):
        scorecard = self.navigation_task.scorecard
        return f"""Entering a prohibited area gives a penalty of {"{:.04}".format(scorecard.get_prohibited_zone_penalty(self))} points."""

    def _penalty_zone_text(self):
        scorecard = self.navigation_task.scorecard
        return f"""Entering a penalty area gives a penalty of {"{:.04}".format(scorecard.get_penalty_zone_penalty_per_second(self))} 
points per second after the first {"{:.04}".format(scorecard.get_penalty_zone_grace_time(self))} seconds."""

    def _precision_rule_description(self):
        scorecard = self.navigation_task.scorecard
        gate_sizes = [item.width for item in self.navigation_task.route.waypoints]
        return f"""For this task the turning point gate width is between {min(gate_sizes)} and {max(gate_sizes)} nm.
 The penalty for 
crossing the gate at the wrong time is {self.navigation_task.scorecard.get_penalty_per_second_for_gate_type("tp", self)} 
per second beyond the first {self.navigation_task.scorecard.get_graceperiod_after_for_gate_type("tp", self)} seconds.
Crossing the extended starting line before start ({self.navigation_task.scorecard.get_extended_gate_width_for_gate_type("sp", self)} nm) 
gives a penalty of {self.navigation_task.scorecard.get_bad_crossing_extended_gate_penalty_for_gate_type("sp", self)}.

Flying off track by more than {"{:.0f}".format(scorecard.backtracking_bearing_difference)} degrees for more than 
{scorecard.get_backtracking_grace_time_seconds(self)} seconds
gives a penalty of {scorecard.get_backtracking_penalty(self)} points.

{self._prohibited_zone_text()} {self._penalty_zone_text()}
{"The route has a takeoff gate." if self.navigation_task.route.takeoff_gate else ""} {"The route has a landing gate" if self.navigation_task.route.landing_gate else ""}
"""

    def _anr_rule_description(self):
        scorecard = self.navigation_task.scorecard
        text = f"""For this task the corridor width is {"{:.1f}".format(self.navigation_task.scorecard.get_corridor_width(self))} nm. 
Flying outside of the corridor more than {scorecard.get_corridor_grace_time(self)} seconds gives a penalty of 
{"{:.0f}".format(scorecard.get_corridor_outside_penalty(self))} point(s) per second."""
        if scorecard.get_corridor_maximum_penalty(self) != -1:
            text += f"""There is a maximum penalty of {"{:.0f}".format(scorecard.get_corridor_maximum_penalty(self))} points for being outside the corridor per leg."""
        text += f"""
{self._prohibited_zone_text()} {self._penalty_zone_text()} {"The route has a takeoff gate." if self.navigation_task.route.takeoff_gate else ""} {"The route has a landing gate" if self.navigation_task.route.landing_gate else ""}
"""
        return text

    def _air_sports_rule_description(self):
        scorecard = self.navigation_task.scorecard
        gate_sizes = [item.width for item in self.navigation_task.route.waypoints]
        minimum_size = min(gate_sizes)
        maximum_size = max(gate_sizes)
        if maximum_size == minimum_size:
            corridor_width_text = f"For this task the corridor with is {minimum_size} NM."
        else:
            corridor_width_text = (
                f"For this task the corridor width is between {minimum_size} NM and {maximum_size} NM."
            )
        text = f"""
{corridor_width_text} Flying outside of the corridor for more than {scorecard.get_corridor_grace_time(self)} seconds gives a penalty of 
{"{:.0f}".format(scorecard.get_corridor_outside_penalty(self))} point(s) per second. """
        if scorecard.get_corridor_maximum_penalty(self) != -1:
            text += f"""There is a maximum penalty of {"{:.0f}".format(scorecard.get_corridor_maximum_penalty(self))} points for being outside the corridor per leg."""

        text += f"""
There are timed gates on the track. The penalty for crossing the gate at the wrong time is {self.navigation_task.scorecard.get_penalty_per_second_for_gate_type("tp", self)} point(s) per second beyond the first {self.navigation_task.scorecard.get_graceperiod_after_for_gate_type("tp", self)} seconds. 
Flying off track by more than {"{:.0f}".format(scorecard.backtracking_bearing_difference)} degrees for more than {scorecard.get_backtracking_grace_time_seconds(self)} seconds gives a penalty of {scorecard.get_backtracking_penalty(self)} points. 
{self._prohibited_zone_text()} {self._penalty_zone_text()}
{"The route has a takeoff gate." if self.navigation_task.route.takeoff_gate else ""} {"The route has a landing gate" if self.navigation_task.route.landing_gate else ""}

"""
        return text

    def get_formatted_rules_description(self):
        if self.navigation_task.scorecard.calculator == Scorecard.PRECISION:
            return self._precision_rule_description()
        if self.navigation_task.scorecard.calculator == Scorecard.ANR_CORRIDOR:
            return self._anr_rule_description()
        if self.navigation_task.scorecard.calculator == Scorecard.AIRSPORTS:
            return self._air_sports_rule_description()

    def __str__(self):
        return "{} - {}".format(self.contestant_number, self.team)
        # return "{}: {} in {} ({}, {})".format(self.contestant_number, self.team, self.navigation_task.name, self.takeoff_time,
        #                                       self.finished_by_time)

    def calculate_progress(self, latest_time: datetime, ignore_finished: bool = False) -> float:
        if NavigationTask.POKER in self.navigation_task.scorecard.task_type:
            return 100 * self.playingcard_set.all().count() / 5
        if NavigationTask.LANDING in self.navigation_task.scorecard.task_type:
            # A progress of zero will also leave estimated score blank
            return 0
        route_progress = 100
        if len(self.navigation_task.route.waypoints) > 0 and (
                not self.contestanttrack.calculator_finished or ignore_finished
        ):
            first_gate = self.navigation_task.route.waypoints[0]
            last_gate = self.navigation_task.route.waypoints[-1]

            first_gate_time = self.gate_times[first_gate.name]
            last_gate_time = self.gate_times[last_gate.name]
            route_duration = (last_gate_time - first_gate_time).total_seconds()
            route_duration_progress = (latest_time - first_gate_time).total_seconds()
            route_progress = 100 * route_duration_progress / route_duration
        return route_progress

    def get_groundspeed(self, bearing) -> float:
        return calculate_ground_speed_combined(bearing, self.air_speed, self.wind_speed, self.wind_direction)

    def clean(self):
        if self.tracking_device == TRACKING_DEVICE and (
                self.tracker_device_id is None or len(self.tracker_device_id) == 0
        ):
            raise ValidationError(
                f"Tracking device is set to {self.get_tracking_device_display()}, but no tracker device ID is supplied"
            )
        if self.tracking_device == TRACKING_COPILOT and self.team.crew.member2 is None:
            raise ValidationError(
                f"Tracking device is set to {self.get_tracking_device_display()}, but there is no copilot"
            )
        # Validate single-use tracker
        overlapping_trackers = Contestant.objects.filter(
            tracking_service=self.tracking_service,
            tracker_device_id__in=self.get_tracker_ids(),
            tracker_start_time__lte=self.finished_by_time,
            finished_by_time__gte=self.tracker_start_time,
        ).exclude(pk=self.pk)
        if overlapping_trackers.exists():
            intervals = []
            for contestant in overlapping_trackers:
                smallest_end = min(contestant.finished_by_time, self.finished_by_time)
                largest_start = max(contestant.tracker_start_time, self.tracker_start_time)
                intervals.append(
                    (
                        contestant.navigation_task,
                        largest_start.isoformat(),
                        smallest_end.isoformat(),
                    )
                )
            raise ValidationError(
                "The tracker '{}' is in use by other contestants for the intervals: {}".format(
                    self.tracker_device_id, intervals
                )
            )
        # Validate that persons are not part of other contestants for the same interval
        overlapping1 = Contestant.objects.filter(
            Q(team__crew__member1=self.team.crew.member1) | Q(team__crew__member2=self.team.crew.member1),
            tracker_start_time__lte=self.finished_by_time,
            finished_by_time__gte=self.tracker_start_time,
        ).exclude(pk=self.pk)
        if overlapping1.exists():
            intervals = []
            for contestant in overlapping1:
                smallest_end = min(contestant.finished_by_time, self.finished_by_time)
                largest_start = max(contestant.tracker_start_time, self.tracker_start_time)
                intervals.append(
                    (
                        contestant.navigation_task,
                        largest_start.isoformat(),
                        smallest_end.isoformat(),
                    )
                )
            raise ValidationError(
                f"The pilot '{self.team.crew.member1}' is competing as a different contestant for the intervals: {intervals}"
            )

        if self.team.crew.member2 is not None:
            overlapping2 = Contestant.objects.filter(
                Q(team__crew__member1=self.team.crew.member2) | Q(team__crew__member2=self.team.crew.member2),
                tracker_start_time__lte=self.finished_by_time,
                finished_by_time__gte=self.tracker_start_time,
            ).exclude(pk=self.pk)
            if overlapping2.exists():
                intervals = []
                for contestant in overlapping2:
                    smallest_end = min(contestant.finished_by_time, self.finished_by_time)
                    largest_start = max(contestant.tracker_start_time, self.tracker_start_time)
                    intervals.append(
                        (
                            contestant.navigation_task,
                            largest_start.isoformat(),
                            smallest_end.isoformat(),
                        )
                    )
                raise ValidationError(
                    f"The copilot '{self.team.crew.member2}' is competing as a different contestant for the intervals: {intervals}"
                )

        # Validate takeoff time after tracker start
        if self.tracker_start_time > self.takeoff_time:
            raise ValidationError(
                "Tracker start time '{}' is after takeoff time '{}' for contestant number {}".format(
                    self.tracker_start_time, self.takeoff_time, self.contestant_number
                )
            )
        if self.takeoff_time > self.finished_by_time:
            raise ValidationError(
                "Takeoff time '{}' is after finished by time '{}' for contestant number {}".format(
                    self.takeoff_time, self.finished_by_time, self.contestant_number
                )
            )
        # Validate no timing changes after calculator start
        if self.pk is not None:
            original = Contestant.objects.get(pk=self.pk)
            if original.calculator_started:
                if original.takeoff_time.replace(microsecond=0) != self.takeoff_time.replace(microsecond=0):
                    raise ValidationError(
                        f"Calculator has started for {self}, it is not possible to change takeoff time from {original.takeoff_time} to {self.takeoff_time}"
                    )
                if original.tracker_start_time.replace(microsecond=0) != self.tracker_start_time.replace(microsecond=0):
                    raise ValidationError(
                        f"Calculator has started for {self}, it is not possible to change tracker start time"
                    )
                if original.wind_speed != self.wind_speed:
                    raise ValidationError(f"Calculator has started for {self}, it is not possible to change wind speed")
                if original.wind_direction != self.wind_direction:
                    raise ValidationError(
                        f"Calculator has started for {self}, it is not possible to change wind direction"
                    )
                if original.adaptive_start != self.adaptive_start:
                    raise ValidationError(
                        f"Calculator has started for {self}, it is not possible to change adaptive start"
                    )
                if original.minutes_to_starting_point != self.minutes_to_starting_point:
                    raise ValidationError(
                        f"Calculator has started for {self}, it is not possible to change minutes to starting point"
                    )

    def calculate_and_get_gate_times(self, start_point_override: Optional[datetime.datetime] = None) -> Dict:
        gates = self.navigation_task.route.waypoints  # type: List[Waypoint]
        if len(gates) == 0:
            return {}
        crossing_times = {}
        relative_crossing_times = calculate_and_get_relative_gate_times(
            self.navigation_task.route,
            self.air_speed,
            self.wind_speed,
            self.wind_direction,
        )

        if start_point_override is not None:
            crossing_time = start_point_override
        else:
            crossing_time = self.takeoff_time + datetime.timedelta(minutes=self.minutes_to_starting_point)
        for gate, relative in relative_crossing_times:
            crossing_times[gate] = crossing_time + relative
        if (
                self.navigation_task.route.takeoff_gate is not None
                and self.navigation_task.route.takeoff_gate.name not in crossing_times
        ):
            crossing_times[self.navigation_task.route.takeoff_gate.name] = self.takeoff_time
        if (
                self.navigation_task.route.landing_gate is not None
                and self.navigation_task.route.landing_gate.name not in crossing_times
        ):
            crossing_times[self.navigation_task.route.landing_gate.name] = self.finished_by_time + datetime.timedelta(
                minutes=1
            )
        return crossing_times

    @property
    def gate_times(self) -> Dict:
        if self.predefined_gate_times is not None and len(self.predefined_gate_times) > 0:
            if (
                    self.navigation_task.route.takeoff_gate is not None
                    and self.navigation_task.route.takeoff_gate.name not in self.predefined_gate_times
            ):
                self.predefined_gate_times[self.navigation_task.route.takeoff_gate.name] = self.takeoff_time
            if (
                    self.navigation_task.route.landing_gate is not None
                    and self.navigation_task.route.landing_gate.name not in self.predefined_gate_times
            ):
                self.predefined_gate_times[
                    self.navigation_task.route.landing_gate.name
                ] = self.finished_by_time + datetime.timedelta(minutes=1)
            return self.predefined_gate_times
        zero_time = None
        if self.adaptive_start:
            zero_time = self.takeoff_time.astimezone(self.navigation_task.contest.time_zone).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        return self.calculate_and_get_gate_times(zero_time)

    @gate_times.setter
    def gate_times(self, value):
        self.predefined_gate_times = value

    def get_gate_time_offset(self, gate_name):
        planned = self.gate_times.get(gate_name)
        if planned is None:
            if gate_name == self.navigation_task.route.takeoff_gate.name:
                planned = self.takeoff_time
            elif gate_name == self.navigation_task.route.landing_gate.name:
                planned = self.finished_by_time
        actual = self.actualgatetime_set.filter(gate=gate_name).first()
        if planned and actual:
            return (actual.time - planned).total_seconds()
        return None

    def get_track_score_override(self) -> Optional[TrackScoreOverride]:
        if self.track_score_override is not None:
            return self.track_score_override
        return self.navigation_task.track_score_override

    def get_gate_score_override(self, gate_type: str) -> Optional[GateScoreOverride]:
        for item in self.gate_score_override.all():
            if gate_type in item.for_gate_types:
                return item
        for item in self.navigation_task.gate_score_override.all():
            if gate_type in item.for_gate_types:
                return item
        return None

    def get_tracker_ids(self) -> List[str]:
        if self.tracking_device == TRACKING_DEVICE:
            return [self.tracker_device_id]
        if self.tracking_device in (TRACKING_PILOT, TRACKING_PILOT_AND_COPILOT):
            trackers = [self.team.crew.member1.app_tracking_id]
            if self.team.crew.member2 is not None:
                trackers.append(self.team.crew.member2.app_tracking_id)
            return trackers
        if self.tracking_device == TRACKING_COPILOT:
            return [self.team.crew.member2.app_tracking_id]
        logger.error(
            f"Contestant {self.team} for navigation task {self.navigation_task} does not have a tracker ID for tracking device {self.tracking_device}"
        )
        return [""]

    def get_simulator_tracker_ids(self) -> List[str]:
        if self.tracking_device in (TRACKING_PILOT, TRACKING_PILOT_AND_COPILOT):
            trackers = [self.team.crew.member1.simulator_tracking_id]
            if self.team.crew.member2 is not None:
                trackers.append(self.team.crew.member2.simulator_tracking_id)
            return trackers
        if self.tracking_device == TRACKING_COPILOT:
            return [self.team.crew.member2.simulator_tracking_id]
        logger.error(
            f"Contestant {self.team} for navigation task {self.navigation_task} does not have a simulator tracker ID for tracking device {self.tracking_device}"
        )
        return [""]

    @property
    def tracker_id_display(self) -> List[Dict]:
        devices = []
        if self.tracking_device == TRACKING_DEVICE:
            devices.append({"tracker": self.tracker_device_id, "has_user": True})
        if self.tracking_device in (TRACKING_PILOT, TRACKING_PILOT_AND_COPILOT) and self.team.crew.member1 is not None:
            devices.append(
                {
                    "tracker": self.team.crew.member1.email,
                    "has_user": get_user_model().objects.filter(email=self.team.crew.member1.email).exists(),
                    "is_active": self.team.crew.member1.is_tracking_active,
                }
            )
        if (
                self.tracking_device in (TRACKING_COPILOT, TRACKING_PILOT_AND_COPILOT)
                and self.team.crew.member2 is not None
        ):
            devices.append(
                {
                    "tracker": self.team.crew.member2.email,
                    "has_user": get_user_model().objects.filter(email=self.team.crew.member2.email).exists(),
                    "is_active": self.team.crew.member2.is_tracking_active,
                }
            )
        return devices

    @staticmethod
    def generate_position_block_for_contestant(position_data: Dict, device_time: datetime.datetime) -> Dict:
        return {
            "time": device_time,
            "position_id": position_data["id"],
            "device_id": position_data["deviceId"],
            "latitude": float(position_data["latitude"]),
            "longitude": float(position_data["longitude"]),
            "altitude": float(position_data["altitude"]),
            "battery_level": float(position_data["attributes"].get("batteryLevel", -1.0)),
            "speed": float(position_data["speed"]),
            "course": float(position_data["course"]),
        }

    @classmethod
    def get_contestant_for_device_at_time(
            cls, device: str, stamp: datetime.datetime
    ) -> Tuple[Optional["Contestant"], bool]:
        """
        Retrieves the contestant that owns the tracking device for the time stamp. Returns an extra flag "is_simulator"
        which is true if the contestant is running the simulator tracking ID.
        """
        contestant, is_simulator = cls._try_to_get_tracker_tracking(device, stamp)
        if contestant is None:
            contestant, is_simulator = cls._try_to_get_pilot_tracking(device, stamp)
            if contestant is None:
                contestant, is_simulator = cls._try_to_get_copilot_tracking(device, stamp)
        if contestant:
            currently_tracked = contestant.is_currently_tracked_by_device(device)
            # Only allow contestants with validated team members compete
            if currently_tracked:
                if contestant.team.crew.member1 is None or contestant.team.crew.member1.validated:
                    if contestant.team.crew.member2 is None or contestant.team.crew.member2.validated:
                        return contestant, is_simulator
        return None, is_simulator

    @classmethod
    def _try_to_get_tracker_tracking(cls, device: str, stamp: datetime.datetime) -> Tuple[Optional["Contestant"], bool]:
        try:
            # Device belongs to contestant from 30 minutes before takeoff
            return (
                cls.objects.get(
                    tracker_device_id=device,
                    tracker_start_time__lte=stamp,
                    tracking_device=TRACKING_DEVICE,
                    finished_by_time__gte=stamp,
                    contestanttrack__calculator_finished=False,
                ),
                False,
            )
        except ObjectDoesNotExist:
            return None, False

    @classmethod
    def _try_to_get_pilot_tracking(cls, device: str, stamp: datetime.datetime) -> Tuple[Optional["Contestant"], bool]:
        try:
            contestant = cls.objects.get(
                Q(team__crew__member1__app_tracking_id=device) | Q(team__crew__member1__simulator_tracking_id=device),
                tracker_start_time__lte=stamp,
                finished_by_time__gte=stamp,
                contestanttrack__calculator_finished=False,
                tracking_device__in=(TRACKING_PILOT, TRACKING_PILOT_AND_COPILOT),
            )
            contestant.team.crew.member1.last_seen = stamp
            contestant.team.crew.member1.save(update_fields=["last_seen"])
            return (
                contestant,
                contestant.team.crew.member1.simulator_tracking_id == device,
            )
        except ObjectDoesNotExist:
            return None, False

    @classmethod
    def _try_to_get_copilot_tracking(cls, device: str, stamp: datetime.datetime) -> Tuple[Optional["Contestant"], bool]:
        try:
            contestant = cls.objects.get(
                Q(team__crew__member2__app_tracking_id=device) | Q(team__crew__member2__simulator_tracking_id=device),
                tracker_start_time__lte=stamp,
                finished_by_time__gte=stamp,
                contestanttrack__calculator_finished=False,
                tracking_device__in=(TRACKING_COPILOT, TRACKING_PILOT_AND_COPILOT),
            )
            contestant.team.crew.member2.last_seen = stamp
            contestant.team.crew.member2.save(update_fields=["last_seen"])
            return (
                contestant,
                contestant.team.crew.member2.simulator_tracking_id == device,
            )
        except ObjectDoesNotExist:
            return None, False

    def is_currently_tracked_by_device(self, device_id: str) -> bool:
        """
        Returns true unless tracking_device is TRACKING_PILOT_AND_COPILOT. In this case the function returns true if we
        responded to this device_id the last time, or the was no loss time. Otherwise it will return false.
        """
        if self.tracking_device == TRACKING_PILOT_AND_COPILOT:
            key = f"latest_tracking_device_{self.pk}"
            previously_used_device_id = cache.get(key)
            if previously_used_device_id == device_id or previously_used_device_id is None:
                cache.set(key, device_id, TRACKING_DEVICE_TIMEOUT)
                return True
            return False
        return True

    def get_traccar_track(self) -> List[Dict]:
        traccar = Traccar.create_from_configuration(TraccarCredentials.get_solo())
        device_ids = traccar.get_device_ids_for_contestant(self)

        tracks = []
        for device_id in device_ids:
            track = traccar.get_positions_for_device_id(device_id, self.tracker_start_time, self.finished_by_time)
            for item in track:
                item["device_time"] = dateutil.parser.parse(item["deviceTime"])
            tracks.append(track)
        logger.debug(f"Returned {len(tracks)} with lengths {', '.join([str(len(item)) for item in tracks])}")
        return merge_tracks(tracks)

    def get_track(self) -> List["Position"]:
        try:
            track = self.contestantuploadedtrack.track
            logger.debug(f"{self}: Fetching data from uploaded track")
        except:
            p = ContestantReceivedPosition.objects.filter(contestant=self)
            if p.count() > 0:
                return ContestantReceivedPosition.convert_to_traccar(p)
            logger.debug(f"{self}: There is no uploaded track, fetching data from traccar")
            track = self.get_traccar_track()
        return [Position(**self.generate_position_block_for_contestant(item, item["device_time"])) for item in track]

    def get_latest_position(self) -> Optional[Position]:
        try:
            return self.get_track()[-1]
        except IndexError:
            return None

    def record_actual_gate_time(self, gate_name: str, passing_time: datetime.datetime):
        try:
            ActualGateTime.objects.create(gate=gate_name, time=passing_time, contestant=self)
        except IntegrityError:
            logger.exception(f"Contestant has already passed gate {gate_name}")

    def record_score_by_gate(self, gate_name: str, score: float):
        gate_score, _ = GateCumulativeScore.objects.get_or_create(gate=gate_name, contestant=self)
        gate_score.points += score
        gate_score.save()

    def reset_track_and_score(self):
        self.scorelogentry_set.all().delete()
        self.trackannotation_set.all().delete()
        self.gatecumulativescore_set.all().delete()
        self.actualgatetime_set.all().delete()
        self.contestanttrack.delete()
        contestant_track = ContestantTrack.objects.create(contestant=self)
        contestant_track.update_score(0)


class ContestantUploadedTrack(models.Model):
    contestant = models.OneToOneField(Contestant, on_delete=models.CASCADE)
    track = MyPickledObjectField(default=list, help_text="List of traccar position reports (Dict)")


class ContestantReceivedPosition(models.Model):
    contestant = models.ForeignKey(Contestant, on_delete=models.CASCADE)
    time = models.DateTimeField()
    latitude = models.FloatField()
    longitude = models.FloatField()
    course = models.FloatField()
    interpolated = models.BooleanField(default=False)

    class Meta:
        ordering = ("time",)

    @staticmethod
    def convert_to_traccar(positions: List["ContestantReceivedPosition"]) -> List[Position]:
        try:
            contestant = positions[0].contestant
        except IndexError:
            return []
        return [
            Position(
                **contestant.generate_position_block_for_contestant(
                    {
                        "deviceId": contestant.tracker_device_id,
                        "id": index,
                        "latitude": float(point.latitude),
                        "longitude": float(point.longitude),
                        "altitude": 0,
                        "attributes": {"batteryLevel": 1.0},
                        "speed": 0.0,
                        "course": point.course,
                        "device_time": point.time,
                    },
                    point.time,
                ), interpolated=point.interpolated
            )
            for index, point in enumerate(positions)
        ]


ANOMALY = "anomaly"
INFORMATION = "information"
DEBUG = "debug"
ANNOTATION_TYPES = [(ANOMALY, "Anomaly"), (INFORMATION, "Information"), (DEBUG, "Debug")]


class ScoreLogEntry(models.Model):
    time = models.DateTimeField()
    contestant = models.ForeignKey(Contestant, on_delete=models.CASCADE)
    gate = models.CharField(max_length=30, default="")
    message = models.TextField(default="")
    string = models.TextField(default="")
    points = models.FloatField()
    planned = models.DateTimeField(blank=True, null=True)
    actual = models.DateTimeField(blank=True, null=True)
    offset_string = models.CharField(max_length=200, default="")
    times_string = models.CharField(max_length=200, default="")
    type = models.CharField(max_length=30, choices=ANNOTATION_TYPES, default=INFORMATION)

    class Meta:
        ordering = ("time", "pk")

    @classmethod
    def push(cls, entry):
        from websocket_channels import WebsocketFacade

        ws = WebsocketFacade()
        ws.transmit_score_log_entry(entry.contestant)
        return entry

    @classmethod
    def update(cls, pk: int, **kwargs):
        cls.objects.filter(pk=pk).update(**kwargs)

    @classmethod
    def create_and_push(cls, **kwargs) -> "ScoreLogEntry":
        entry = cls.objects.create(**kwargs)
        cls.push(entry)
        return entry


class TrackAnnotation(models.Model):
    time = models.DateTimeField()
    contestant = models.ForeignKey(Contestant, on_delete=models.CASCADE)
    score_log_entry = models.ForeignKey(ScoreLogEntry, on_delete=models.CASCADE)
    latitude = models.FloatField()
    longitude = models.FloatField()
    message = models.TextField()
    gate = models.CharField(max_length=30, blank=True, default="")
    gate_type = models.CharField(max_length=30, blank=True, default=TURNPOINT, choices=GATES_TYPES)
    type = models.CharField(max_length=30, choices=ANNOTATION_TYPES)

    class Meta:
        ordering = ("time",)

    @classmethod
    def update(cls, pk, **kwargs):
        cls.objects.filter(pk=pk).update(**kwargs)

    @classmethod
    def push(cls, annotation):
        from websocket_channels import WebsocketFacade

        ws = WebsocketFacade()
        ws.transmit_annotations(annotation.contestant)

    @classmethod
    def create_and_push(cls, **kwargs) -> "TrackAnnotation":
        annotation = cls.objects.create(**kwargs)
        cls.push(annotation)
        return annotation


class GateCumulativeScore(models.Model):
    contestant = models.ForeignKey(Contestant, on_delete=models.CASCADE)
    gate = models.CharField(max_length=30)
    points = models.FloatField(default=0)

    class Meta:
        unique_together = ("contestant", "gate")


class ActualGateTime(models.Model):
    contestant = models.ForeignKey(Contestant, on_delete=models.CASCADE)
    gate = models.CharField(max_length=30)
    time = models.DateTimeField()

    class Meta:
        unique_together = ("contestant", "gate")


class ContestantTrack(models.Model):
    contestant = models.OneToOneField(Contestant, on_delete=models.CASCADE)
    score = models.FloatField(default=0)
    current_state = models.CharField(max_length=200, default="Waiting...")
    current_leg = models.CharField(max_length=100, default="")
    last_gate = models.CharField(max_length=100, default="")
    last_gate_time_offset = models.FloatField(default=0)
    passed_starting_gate = models.BooleanField(default=False)
    passed_finish_gate = models.BooleanField(default=False)
    calculator_finished = models.BooleanField(default=False)
    calculator_started = models.BooleanField(default=False)

    @property
    def contest_summary(self):
        try:
            return ContestSummary.objects.get(
                team=self.contestant.team,
                contest=self.contestant.navigation_task.contest,
            ).points
        except ObjectDoesNotExist:
            return None

    def update_last_gate(self, gate_name, time_difference):
        self.refresh_from_db()
        self.last_gate = gate_name
        self.last_gate_time_offset = time_difference
        self.save()
        self.__push_change()

    def update_score(self, score):
        ContestantTrack.objects.filter(pk=self.pk).update(score=score)
        # Update task test score if it exists
        if hasattr(self.contestant.navigation_task, "task_test"):
            entry, _ = TeamTestScore.objects.update_or_create(
                team=self.contestant.team,
                task_test=self.contestant.navigation_task.task_test,
                defaults={"points": score},
            )
        self.__push_change()

    def updates_current_state(self, state: str):
        self.refresh_from_db()
        if self.current_state != state:
            self.current_state = state
            self.save()
            self.__push_change()

    def update_current_leg(self, current_leg: str):
        self.refresh_from_db()
        if self.current_leg != current_leg:
            self.current_leg = current_leg
            self.save()
            self.__push_change()

    def set_calculator_finished(self):
        self.calculator_finished = True
        self.save(update_fields=["calculator_finished"])
        self.__push_change()

    def set_calculator_started(self):
        self.calculator_started = True
        self.save(update_fields=["calculator_started"])
        self.__push_change()

    def set_passed_starting_gate(self):
        self.refresh_from_db()
        self.passed_starting_gate = True
        self.save()
        self.__push_change()

    def set_passed_finish_gate(self):
        self.refresh_from_db()
        self.passed_finish_gate = True
        self.save()
        self.__push_change()

    def __push_change(self):
        from websocket_channels import WebsocketFacade

        ws = WebsocketFacade()
        ws.transmit_basic_information(self.contestant)


########### POKER
class PlayingCard(models.Model):
    contestant = models.ForeignKey(Contestant, on_delete=models.CASCADE)
    card = models.CharField(max_length=2, choices=PLAYING_CARDS)
    waypoint_name = models.CharField(max_length=50, blank=True, null=True)
    waypoint_index = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.card} for {self.contestant} at {self.waypoint_name} (waypoint {self.waypoint_index})"

    @classmethod
    def get_random_unique_card(cls, contestant: Contestant) -> str:
        cards = [item[0] for item in PLAYING_CARDS]
        existing_cards = contestant.playingcard_set.all().values_list("card", flat=True)
        available_cards = set(cards) - set(existing_cards)
        if len(available_cards) == 0:
            raise ValueError(
                f"There are no available cards to choose for the contestant, he/she already has {len(existing_cards)}."
            )
        random_card = random.choice(list(available_cards))
        while contestant.playingcard_set.filter(card=random_card).exists():
            random_card = random.choice([item[0] for item in PLAYING_CARDS])
        return random_card

    @classmethod
    def evaluate_hand(cls, contestant: Contestant) -> Tuple[int, str]:
        hand = [eval7.Card(s.card) for s in cls.objects.filter(contestant=contestant)]
        score = eval7.evaluate(hand)
        return score, eval7.handtype(score)

    @classmethod
    def maximum_score(cls) -> int:
        return 135004160

    @classmethod
    def get_relative_score(cls, contestant: Contestant) -> Tuple[float, str]:
        score, hand_type = cls.evaluate_hand(contestant)
        return 10000 * score / cls.maximum_score(), hand_type

    @classmethod
    def remove_contestant_card(cls, contestant: Contestant, card_pk: int):
        card = contestant.playingcard_set.filter(pk=card_pk).first()
        if card is not None:
            card.delete()
            relative_score, hand_description = cls.get_relative_score(contestant)
            waypoint = contestant.navigation_task.route.waypoints[-1].name
            message = "Removed card {}, current hand is {}".format(card.get_card_display(), hand_description)
            ScoreLogEntry.create_and_push(
                contestant=contestant,
                time=datetime.datetime.now(datetime.timezone.utc),
                gate=waypoint,
                message=message,
                points=relative_score,
                string="{}: {}".format(waypoint, message),
            )

            contestant.contestanttrack.update_score(relative_score)
            from websocket_channels import WebsocketFacade

            ws = WebsocketFacade()
            ws.transmit_playing_cards(contestant)

    @classmethod
    def add_contestant_card(cls, contestant: Contestant, card: str, waypoint: str, waypoint_index: int):
        poker_card = cls.objects.create(
            contestant=contestant,
            card=card,
            waypoint_name=waypoint,
            waypoint_index=waypoint_index,
        )
        relative_score, hand_description = cls.get_relative_score(contestant)
        message = "Received card {}, current hand is {}".format(poker_card.get_card_display(), hand_description)
        entry = ScoreLogEntry.create_and_push(
            contestant=contestant,
            time=datetime.datetime.now(datetime.timezone.utc),
            gate=waypoint,
            message=message,
            points=relative_score,
            type=ANOMALY,
            string="{}: {}".format(waypoint, message),
        )

        contestant.contestanttrack.update_score(relative_score)
        pos = contestant.get_latest_position()
        longitude = 0
        latitude = 0
        if pos:
            latitude = pos.latitude
            longitude = pos.longitude
        TrackAnnotation.create_and_push(
            contestant=contestant,
            latitude=latitude,
            longitude=longitude,
            message=entry.string,
            type=ANOMALY,
            time=datetime.datetime.now(datetime.timezone.utc),
            score_log_entry=entry,
        )
        contestant.contestanttrack.update_score(relative_score)
        from websocket_channels import WebsocketFacade

        ws = WebsocketFacade()
        ws.transmit_playing_cards(contestant)


########## Scoring portal models ##########
class Task(models.Model):
    """
    Models a generic task for which we want to store scores
    """

    DESCENDING = "desc"
    ASCENDING = "asc"
    SORTING_DIRECTION = ((DESCENDING, "Descending"), (ASCENDING, "Ascending"))
    summary_score_sorting_direction = models.CharField(
        default=ASCENDING,
        choices=SORTING_DIRECTION,
        help_text="Whether the lowest (ascending) or highest (ascending) score is the best result",
        max_length=50,
    )
    name = models.CharField(max_length=100)
    heading = models.CharField(max_length=100)
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE)
    index = models.IntegerField(
        help_text="The index of the task when displayed as columns in a table. Indexes are sorted in ascending order to determine column order",
        default=0,
    )
    autosum_scores = models.BooleanField(
        default=True,
        help_text="If true, the server sum all tests into TaskSummary when any test is updated",
    )

    class Meta:
        unique_together = ("name", "contest")
        ordering = ("index",)


class TaskTest(models.Model):
    """
    Models and individual test (e.g. landing one, landing two, or landing three that is part of a task. It includes
    the configuration for how the score is displayed for the test.
    """

    DESCENDING = "desc"
    ASCENDING = "asc"
    SORTING_DIRECTION = ((DESCENDING, "Descending"), (ASCENDING, "Ascending"))
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    navigation_task = models.OneToOneField(NavigationTask, on_delete=models.CASCADE, blank=True, null=True)
    name = models.CharField(max_length=100)
    heading = models.CharField(max_length=100)
    sorting = models.CharField(
        default=ASCENDING,
        choices=SORTING_DIRECTION,
        help_text="Whether the lowest (ascending) or highest (ascending) score is the best result",
        max_length=50,
    )
    index = models.IntegerField(
        help_text="The index of the task when displayed as columns in a table. Indexes are sorted in ascending order to determine column order",
        default=0,
    )

    class Meta:
        unique_together = ("name", "task")
        ordering = ("index",)


class TaskSummary(models.Model):
    """
    Summary score for all tests inside a task for a team
    """

    team = models.ForeignKey(Team, on_delete=models.PROTECT)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    points = models.FloatField()

    class Meta:
        unique_together = ("team", "task")

    def update_sum(self):
        if self.task.autosum_scores:
            tests = TeamTestScore.objects.filter(team=self.team, task_test__task=self.task)
            if tests.exists():
                total = sum([test.points for test in tests])
                self.points = total
            else:
                self.points = 0
            self.save()


class ContestSummary(models.Model):
    """
    Summary score for the entire contest for a team
    """

    team = models.ForeignKey(Team, on_delete=models.PROTECT)
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE)
    points = models.FloatField()

    class Meta:
        unique_together = ("team", "contest")

    def update_sum(self):
        if self.contest.autosum_scores:
            tasks = TaskSummary.objects.filter(team=self.team, task__contest=self.contest)
            if tasks.exists():
                total = sum([task.points for task in tasks])
                self.points = total
            else:
                self.points = 0
            self.save()


class TeamTestScore(models.Model):
    """
    Represents the score a team received for a test
    """

    team = models.ForeignKey(Team, on_delete=models.PROTECT)
    task_test = models.ForeignKey(TaskTest, on_delete=models.CASCADE)
    points = models.FloatField()

    class Meta:
        unique_together = ("team", "task_test")


class EmailMapLink(models.Model):
    """
    Holds all self registrations in order to deliver a generated map based on a link sent by email
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contestant = models.ForeignKey(Contestant, on_delete=models.CASCADE)
    orders = models.BinaryField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at",)

    HTML_SIGNATURE = """
<h3><strong>Best Regards,</strong><br /><span style="color: #000080;">
<strong>Team&nbsp;Air Sports Live Tracking</strong>
<strong>&nbsp;</strong>
</span></h3>
<p>Flight Tracking and competition flying made easy!&nbsp;<br /> <br /> 
<em>Air Sports Live Tracking gives you live tracking and live scoring of competitions in Precision Flying and Air 
Navigation Racing. GA pilot? We also provide an open GA flight tracking service. Using your mobile as a tracker you 
can follow it live on&nbsp;</em><em><a href="http://www.airsports.no/" data-saferedirecturl="https://www.google.com/url?q=http://www.airsports.no/&amp;source=gmail&amp;ust=1630044200327000&amp;usg=AFQjCNGxwqYMGGRw9YV110LVORQjwrEKSg">www.airsports.no</a></em><em>.</em></p>

<p><em>Download APP:&nbsp;&nbsp;</em><em><a href="https://apps.apple.com/no/app/air-sports-live-tracking/id1559193686?l=nb" data-saferedirecturl="https://www.google.com/url?q=https://apps.apple.com/no/app/air-sports-live-tracking/id1559193686?l%3Dnb&amp;source=gmail&amp;ust=1630044200327000&amp;usg=AFQjCNEaGuuRKna3cTbq1d9pFS5W0XjhHg">Apple Store</a></em><em>&nbsp;|&nbsp;</em><em><a href="https://play.google.com/store/apps/details?id=no.airsports.android.livetracking" data-saferedirecturl="https://www.google.com/url?q=https://play.google.com/store/apps/details?id%3Dno.airsports.android.livetracking&amp;source=gmail&amp;ust=1630044200327000&amp;usg=AFQjCNGm5zuqA1ARkWWhBHJFCMoEHOEITQ">Google Play</a></em><br /> <br /> Follow us:&nbsp;<a href="https://www.instagram.com/AirSportsLive" data-saferedirecturl="https://www.google.com/url?q=https://www.instagram.com/AirSportsLive&amp;source=gmail&amp;ust=1630044200327000&amp;usg=AFQjCNHQAv3QL2PQFDIv8jmTQj6QVXNDng">Instagram</a>&nbsp;|&nbsp;&nbsp;<a href="https://twitter.com/AirSportsLive" data-saferedirecturl="https://www.google.com/url?q=https://twitter.com/AirSportsLive&amp;source=gmail&amp;ust=1630044200327000&amp;usg=AFQjCNFgfCQfnysD__aABYrpmxbmDh36EQ">Twitter</a>&nbsp; |&nbsp;&nbsp;<a href="https://www.facebook.com/AirSportsLive" data-saferedirecturl="https://www.google.com/url?q=https://www.facebook.com/AirSportsLive&amp;source=gmail&amp;ust=1630044200327000&amp;usg=AFQjCNHYjyR8NJqLEAtt7acO6jaJCF7Suw">Facebook</a>&nbsp; |&nbsp;&nbsp;<a href="https://www.youtube.com/channel/UCgKCfAzU9wl42wnb1Tj_SCA" data-saferedirecturl="https://www.google.com/url?q=https://www.youtube.com/channel/UCgKCfAzU9wl42wnb1Tj_SCA&amp;source=gmail&amp;ust=1630044200327000&amp;usg=AFQjCNHx8Xk2Xlrp6S9RRedRguMFi2Gi7w">YouTube</a><br /> <br /> <span style="color: #ff0000;"><strong>Partners:&nbsp;</strong></span><br /> <strong>Norges Luftsportforbund /&nbsp;<em>Norwegian Air Sports Federation&nbsp;</em></strong><strong><a href="https://nlf.no/" data-saferedirecturl="https://www.google.com/url?q=https://nlf.no/&amp;source=gmail&amp;ust=1630044200327000&amp;usg=AFQjCNH_cLc2E8CUYMNJH9lDgRKxaAQksw">&gt;&gt;</a></strong><br /> <strong>IG - TRADE WITH IG&nbsp;</strong><strong><a href="https://www.ig.com/no/demokonto/?CHID=15&amp;QPID=35652" data-saferedirecturl="https://www.google.com/url?q=https://www.ig.com/no/demokonto/?CHID%3D15%26QPID%3D35652&amp;source=gmail&amp;ust=1630044200328000&amp;usg=AFQjCNET2W7jI_hyJLIFfL986LWWgdaA7g">&gt;&gt;</a></strong></p>

<p><br /> <em>Air Sports Live Tracking is based on voluntary work and is a non-profit organization.&nbsp;We depend on 
partners who support our work.&nbsp;If you want to become our partners, please get in touch, we are very grateful for 
your support.&nbsp;Thanks!</em></p>

<p><em><img src="https://airsports.no/static/img/AirSportsLiveTracking.png" alt="Air Sports Live Tracking" width="350" height="52" /></em></p>
<p><span style="color: #999999;">____________________________________________________________</span></p>
<p><span style="color: #999999;"><em>NOTICE: This e-mail transmission, and any documents, files or previous e-mail 
messages attached to it, may contain confidential or privileged information. If you are not the intended recipient, or 
a person responsible for delivering it to the intended recipient, you are hereby notified that any disclosure, copying, 
distribution or use of any of the information contained in or attached to this message is STRICTLY PROHIBITED. If you 
have received this transmission in error, please immediately notify the sender and delete the e-mail and attached 
documents. Thank you.</em></span></p>
<p><span style="color: #999999;">____________________________________________________________</span></p>"""

    PLAINTEXT_SIGNATURE = """Best Regards,
Team Air Sports Live Tracking 
Flight Tracking and competition flying made easy! 

Air Sports Live Tracking gives you live tracking and live scoring of competitions in Precision Flying and Air Navigation 
Racing. GA pilot? We also provide an open GA flight tracking service. Using your mobile as a tracker you can follow it 
live on www.airsports.no.

Download the APP from:
Apple Store (https://apps.apple.com/no/app/air-sports-live-tracking/id1559193686?l=nb)
Google Play (https://play.google.com/store/apps/details?id=no.airsports.android.livetracking)

Follow us: 
Instagram (https://www.instagram.com/AirSportsLive)
Twitter (https://twitter.com/AirSportsLive)
Facebook (https://www.facebook.com/AirSportsLive)
YouTube (https://www.youtube.com/channel/UCgKCfAzU9wl42wnb1Tj_SCA)

Partners: 
Norges Luftsportforbund / Norwegian Air Sports Federation (https://nlf.no/)
IG - TRADE WITH IG (https://www.ig.com/no/demokonto/?CHID=15&QPID=35652)

Air Sports Live Tracking is based on voluntary work and is a non-profit organization. We depend on partners who support 
our work. If you want to become our partners, please get in touch, we need your  support. Thanks!
____________________________________________________________
 NOTICE: This e-mail transmission, and any documents, files or previous e-mail messages attached to it, may contain 
 confidential or privileged information. If you are not the intended recipient, or a person responsible for delivering 
 it to the intended recipient, you are hereby notified that any disclosure, copying, distribution or use of any of the 
 information contained in or attached to this message is STRICTLY PROHIBITED. If you have received this transmission in 
 error, please immediately notify the sender and delete the e-mail and attached documents. Thank you.
____________________________________________________________    
"""

    def __str__(self):
        return str(self.contestant) + " " + str(self.contestant.navigation_task)

    def send_email(self, email_address: str, first_name: str):
        logger.info(f"Sending email to {email_address}")
        url = "https://airsports.no" + reverse("email_map_link", kwargs={"key": self.id})

        starting_point_time_string = self.contestant.starting_point_time_local.strftime("%Y-%m-%d %H:%M:%S")
        tracking_start_time_string = self.contestant.tracker_start_time_local.strftime("%Y-%m-%d %H:%M:%S")
        send_mail(
            f"Flight orders for task {self.contestant.navigation_task.name}",
            f"Hi {first_name},\n\nHere is the <a href='{url}'>link to download the flight orders</a> for your navigation task "
            + f"'{self.contestant.navigation_task.name}' with {'estimated' if self.contestant.adaptive_start else 'exact'} starting point time {starting_point_time_string} "
              f"{f'and adaptive start (with earliest takeoff time {tracking_start_time_string})' if self.contestant.adaptive_start else ''}.\n\n{url}\n{self.PLAINTEXT_SIGNATURE}",
            None,  # Should default to system from email
            recipient_list=[email_address],
            html_message=f"Hi {first_name},<p>Here is the link to download the flight orders for  "
                         f"your navigation task "
                         f"'{self.contestant.navigation_task.name}' with {'estimated' if self.contestant.adaptive_start else 'exact'} starting point time {starting_point_time_string} "
                         f"{f'and adaptive start (with earliest takeoff time {tracking_start_time_string})' if self.contestant.adaptive_start else ''}.<p>"
                         f"<a href='{url}'>Flight orders link</a><p>{self.HTML_SIGNATURE}",
        )


class EditableRoute(models.Model):
    route_type = models.CharField(
        choices=NavigationTask.NAVIGATION_TASK_TYPES, default=NavigationTask.PRECISION, max_length=200
    )
    name = models.CharField(max_length=200, help_text="User-friendly name")
    route = MyPickledObjectField(default=dict)

    def __str__(self):
        return self.name

    def _get_features_type(self, feature_type: str) -> List[Dict]:
        return [item for item in self.route if item["feature_type"] == feature_type]

    def _get_feature_type(self, feature_type: str) -> Optional[Dict]:
        try:
            return self._get_features_type(feature_type)[0]
        except IndexError:
            return None

    @staticmethod
    def _get_feature_coordinates(feature: Dict, flip: bool = True) -> List[Tuple[float, float]]:
        """
        Switch lon, lat to lat, lon.
        :param feature:
        :return:
        """
        try:
            coordinates = feature["geojson"]["geometry"]["coordinates"]
            if feature["geojson"]["geometry"]["type"] == "Polygon":
                coordinates = coordinates[0]
            if flip:
                return [tuple(reversed(item)) for item in coordinates]
        except KeyError as e:
            raise ValidationError(f"Malformed internal route: {e}")
        return coordinates

    def create_landing_route(self):
        route = Route.objects.create(name="", waypoints=[], use_procedure_turns=False)
        self.extract_additional_features(route)
        if route.landing_gate is None:
            raise ValidationError("Route must have a landing gate")
        route.waypoints = [route.landing_gate]
        route.save()
        return route

    def create_precision_route(self, use_procedure_turns: bool) -> Route:
        from display.convert_flightcontest_gpx import build_waypoint
        from display.convert_flightcontest_gpx import create_precision_route_from_waypoint_list

        track = self._get_feature_type("track")
        waypoint_list = []
        coordinates = self._get_feature_coordinates(track)
        track_points = track["track_points"]
        for index, (latitude, longitude) in enumerate(coordinates):
            item = track_points[index]
            waypoint_list.append(
                build_waypoint(
                    item["name"],
                    latitude,
                    longitude,
                    item["gateType"],
                    item["gateWidth"],
                    item["timeCheck"],
                    item["timeCheck"],  # We do not include gate check in GUI
                )
            )
        route = create_precision_route_from_waypoint_list(track["name"], waypoint_list, use_procedure_turns)
        self.extract_additional_features(route)
        return route

    def create_anr_route(self, rounded_corners: bool, corridor_width: float) -> Route:
        from display.convert_flightcontest_gpx import build_waypoint
        from display.convert_flightcontest_gpx import create_anr_corridor_route_from_waypoint_list

        track = self._get_feature_type("track")
        waypoint_list = []
        coordinates = self._get_feature_coordinates(track)
        track_points = track["track_points"]
        for index, (latitude, longitude) in enumerate(coordinates):
            item = track_points[index]
            waypoint_list.append(
                build_waypoint(item["name"], latitude, longitude, "secret", corridor_width, False, False)
            )
        waypoint_list[0].type = "sp"
        waypoint_list[0].gate_check = True
        waypoint_list[0].time_check = True

        waypoint_list[-1].type = "fp"
        waypoint_list[-1].gate_check = True
        waypoint_list[-1].time_check = True
        logger.debug(f"Created waypoints {waypoint_list}")
        route = create_anr_corridor_route_from_waypoint_list(track["name"], waypoint_list, rounded_corners)
        route.corridor_width = corridor_width
        route.save()
        self.extract_additional_features(route)
        return route

    def create_airsports_route(self, rounded_corners: bool) -> Route:
        from display.convert_flightcontest_gpx import build_waypoint
        from display.convert_flightcontest_gpx import create_anr_corridor_route_from_waypoint_list

        track = self._get_feature_type("track")
        waypoint_list = []
        coordinates = self._get_feature_coordinates(track)
        track_points = track["track_points"]
        for index, (latitude, longitude) in enumerate(coordinates):
            item = track_points[index]
            waypoint_list.append(
                build_waypoint(
                    item["name"],
                    latitude,
                    longitude,
                    item["gateType"],
                    item["gateWidth"],
                    item["timeCheck"],
                    item["timeCheck"],
                )
            )
        route = create_anr_corridor_route_from_waypoint_list(track["name"], waypoint_list, rounded_corners)
        self.extract_additional_features(route)
        return route

    def extract_additional_features(self, route: Route):
        from display.convert_flightcontest_gpx import create_gate_from_line

        takeoff_gate = self._get_feature_type("to")
        if takeoff_gate is not None:
            takeoff_gate_line = self._get_feature_coordinates(takeoff_gate)
            if len(takeoff_gate_line) != 2:
                raise ValidationError("Take-off gate should have exactly 2 points")
            route.takeoff_gate = create_gate_from_line(takeoff_gate_line, "Takeoff", "to")
            route.takeoff_gate.gate_line = takeoff_gate_line
        landing_gate = self._get_feature_type("ldg")
        if landing_gate is not None:
            landing_gate_line = self._get_feature_coordinates(landing_gate)
            if len(landing_gate_line) != 2:
                raise ValidationError("Landing gate should have exactly 2 points")
            route.landing_gate = create_gate_from_line(landing_gate_line, "Landing", "ldg")
            route.landing_gate.gate_line = landing_gate_line
        route.save()
        # Create prohibited zones
        for zone_type in ("info", "penalty", "prohibited", "gate"):
            for feature in self._get_features_type(zone_type):
                logger.debug(feature)
                Prohibited.objects.create(
                    name=feature["name"],
                    route=route,
                    path=self._get_feature_coordinates(feature, flip=True),
                    type=zone_type,
                    tooltip_position=feature.get("tooltip_position", [])
                )


# @receiver(post_save, sender=Task)
# def populate_task_summaries(sender, instance: Task, **kwargs):
#     teams = Team.objects.filter(contestteam__contest=instance.contest)
#     for team in teams:
#         TaskSummary.objects.create(team=team, task=instance, points=0)
#
#
@receiver(post_save, sender=TeamTestScore)
@receiver(post_delete, sender=TeamTestScore)
def auto_summarise_tests(sender, instance: TeamTestScore, **kwargs):
    if instance.task_test.task.autosum_scores:
        task_summary, _ = TaskSummary.objects.get_or_create(
            task=instance.task_test.task,
            team=instance.team,
            defaults={"points": instance.points},
        )
        task_summary.update_sum()


@receiver(post_save, sender=TaskSummary)
@receiver(post_delete, sender=TaskSummary)
def auto_summarise_tasks(sender, instance: TaskSummary, **kwargs):
    if instance.task.contest.autosum_scores:
        contest_summary, _ = ContestSummary.objects.get_or_create(
            contest=instance.task.contest,
            team=instance.team,
            defaults={"points": instance.points},
        )
        contest_summary.update_sum()
        # Update contestants
        from websocket_channels import WebsocketFacade

        ws = WebsocketFacade()
        for c in instance.team.contestant_set.filter(navigation_task__contest=instance.task.contest):
            ws.transmit_basic_information(c)


@receiver(post_delete, sender=Task)
def update_contest_summary_on_task_delete(sender, instance: Task, **kwargs):
    for contest_summary in ContestSummary.objects.filter(contest=instance.contest):
        contest_summary.update_sum()


@receiver(post_delete, sender=TaskTest)
def update_task_summary_on_task_test_delete(sender, instance: TaskTest, **kwargs):
    for task_summary in TaskSummary.objects.filter(task=instance.task):
        task_summary.update_sum()


@receiver(post_save, sender=ContestTeam)
@receiver(post_delete, sender=ContestTeam)
def post_contest_team_change(sender, instance: ContestTeam, **kwargs):
    from websocket_channels import WebsocketFacade

    ws = WebsocketFacade()
    ws.transmit_teams(instance.contest)


@receiver(post_save, sender=TeamTestScore)
@receiver(post_delete, sender=TeamTestScore)
def post_team_test_score_change(sender, instance: TeamTestScore, **kwargs):
    from websocket_channels import WebsocketFacade

    ws = WebsocketFacade()
    ws.transmit_contest_results(None, instance.task_test.task.contest)


@receiver(post_save, sender=TaskSummary)
@receiver(post_delete, sender=TaskSummary)
def post_task_summary_change(sender, instance: TaskSummary, **kwargs):
    from websocket_channels import WebsocketFacade

    ws = WebsocketFacade()
    ws.transmit_contest_results(None, instance.task.contest)


@receiver(post_save, sender=ContestSummary)
@receiver(post_delete, sender=ContestSummary)
def push_contest_summary_change(sender, instance: ContestSummary, **kwargs):
    from websocket_channels import WebsocketFacade

    ws = WebsocketFacade()
    ws.transmit_contest_results(None, instance.contest)


@receiver(post_save, sender=Task)
@receiver(post_delete, sender=Task)
def push_task_change(sender, instance: Task, **kwargs):
    from websocket_channels import WebsocketFacade

    ws = WebsocketFacade()
    ws.transmit_tasks(instance.contest)


@receiver(post_save, sender=Task)
def update_task_index(sender, instance: Task, created, **kwargs):
    if created:
        if instance.contest.task_set.all().count() > 0:
            highest_index = max([item.index for item in instance.contest.task_set.all()])
            instance.index = highest_index + 1
            instance.save()


@receiver(post_save, sender=TaskTest)
def update_task_test_index(sender, instance: TaskTest, created, **kwargs):
    if created:
        if instance.task.tasktest_set.all().count() > 0:
            highest_index = max([item.index for item in instance.task.tasktest_set.all()])
            instance.index = highest_index + 1
            instance.save()


@receiver(post_save, sender=TaskTest)
@receiver(post_delete, sender=TaskTest)
def push_test_change(sender, instance: TaskTest, **kwargs):
    from websocket_channels import WebsocketFacade

    ws = WebsocketFacade()
    ws.transmit_tests(instance.task.contest)


#
#
# @receiver(post_save, sender=ContestTeam)
# def populate_team_results(sender, instance: ContestTeam, **kwargs):
#     for task in Task.objects.filter(contest=instance.contest):
#         TaskSummary.objects.create(team=instance.team, task=task, points=0)
#     for task_test in TaskTest.objects.filter(
#             task__contest=instance.contest):
#         TeamTestScore.objects.create(team=instance.team, task=task_test)
#     ContestSummary.objects.create(team=instance.team, contest=instance.contest, points=0)


@receiver(post_save, sender=Contestant)
def create_contestant_track_if_not_exists(sender, instance: Contestant, **kwargs):
    ContestantTrack.objects.get_or_create(contestant=instance)


@receiver(pre_save, sender=Contestant)
def validate_contestant(sender, instance: Contestant, **kwargs):
    instance.clean()


@receiver(pre_save, sender=ContestTeam)
def validate_contest_team(sender, instance: ContestTeam, **kwargs):
    instance.clean()


@receiver(pre_save, sender=Crew)
def validate_crew(sender, instance: Crew, **kwargs):
    instance.validate()


@receiver(pre_save, sender=Club)
def validate_club(sender, instance: Club, **kwargs):
    instance.validate()


@receiver(pre_save, sender=Route)
def validate_route(sender, instance: Route, **kwargs):
    instance.clean()


@receiver(post_delete, sender=NavigationTask)
def remove_route_from_deleted_navigation_task(sender, instance: NavigationTask, **kwargs):
    instance.route.delete()


# @receiver(post_delete, sender=ContestantTrack)
# def remove_route_from_deleted_navigation_task(sender, instance: ContestantTrack, **kwargs):
#     if instance.contestant:
#         instance.contestant.reset_track_and_score()


@receiver(post_save, sender=NavigationTask)
def create_results_service_test(sender, instance: NavigationTask, created, **kwargs):
    if created:
        instance.create_results_service_test()


@receiver(post_delete, sender=NavigationTask)
def clear_navigation_task_results_service_test(sender, instance: NavigationTask, **kwargs):
    if hasattr(instance, "tasktest"):
        task = instance.tasktest.task
        for test in instance.tasktest.teamtestscore_set.all():
            # Must be explicitly called for the signal to recalculate summary to be called.
            test.delete()
        instance.tasktest.delete()
        if task.tasktest_set.all().count() == 0:
            for task_summary in task.tasksummary_set.all():
                # Must be explicitly called for the signal to recalculate summary to be called.
                task_summary.delete()
            task.delete()


@receiver(post_save, sender=Contestant)
def create_tracker_in_traccar(sender, instance: Contestant, **kwargs):
    if (
            instance.tracking_service == TRACCAR
            and instance.tracker_device_id
            and len(instance.tracker_device_id) > 0
            and instance.tracking_device == TRACKING_DEVICE
    ):
        traccar = get_traccar_instance()
        traccar.get_or_create_device(instance.tracker_device_id, instance.tracker_device_id)


def generate_random_string(length) -> str:
    return "".join(choice(ascii_uppercase + ascii_lowercase + digits) for i in range(length))


@receiver(pre_save, sender=Person)
def register_personal_tracker(sender, instance: Person, **kwargs):
    instance.validate()
    if instance.pk is None:
        try:
            original = Person.objects.get(pk=instance.pk)
            original_tracking_id = original.app_tracking_id
            simulator_original_tracking_id = original.simulator_tracking_id
        except ObjectDoesNotExist:
            original_tracking_id = None
            simulator_original_tracking_id = None
        traccar = get_traccar_instance()
        app_random_string = "SHOULD_NOT_BE_HERE"
        simulator_random_string = "SHOULD_NOT_BE_HERE"
        existing = True
        while existing:
            app_random_string = generate_random_string(28)
            simulator_random_string = generate_random_string(28)
            logger.debug(f"Generated random string {app_random_string} for person {instance}")
            existing = Person.objects.filter(
                Q(app_tracking_id=app_random_string) | Q(simulator_tracking_id=simulator_random_string)
            ).exists()
        instance.app_tracking_id = app_random_string
        instance.simulator_tracking_id = simulator_random_string
        logger.debug(f"Assigned random string {instance.app_tracking_id} to person {instance}")
        device, created = traccar.get_or_create_device(str(instance), instance.app_tracking_id)
        logger.debug(f"Traccar device {device} was created: {created}")
        if created and original_tracking_id is not None and original_tracking_id != instance.app_tracking_id:
            original_device = traccar.get_device(original_tracking_id)
            if original_device is not None:
                logger.debug(f"Clearing original device {original_device}")
                traccar.delete_device(original_device["id"])
        device, created = traccar.get_or_create_device(str(instance) + " simulator", instance.simulator_tracking_id)
        logger.debug(f"Traccar device {device} was created: {created}")
        if (
                created
                and simulator_original_tracking_id is not None
                and simulator_original_tracking_id != instance.simulator_tracking_id
        ):
            original_device = traccar.get_device(simulator_original_tracking_id)
            if original_device is not None:
                logger.debug(f"Clearing original device {original_device}")
                traccar.delete_device(original_device["id"])
    else:
        original = Person.objects.get(pk=instance.pk)
        # Update traccar device names
        if str(original) != str(instance):
            traccar = get_traccar_instance()
            traccar.update_device_name(str(instance), instance.app_tracking_id)
            traccar.update_device_name(str(instance) + " simulator", instance.simulator_tracking_id)
    # Send welcome email if the person is validated, but previously was not
    previous_person = Person.objects.filter(pk=instance.pk).first()
    if previous_person and not previous_person.validated and instance.validated:
        user = MyUser.objects.filter(email=instance.email).first()
        if user:
            user.send_welcome_email(instance)


@receiver(pre_delete, sender=Person)
def delete_personal_tracker(sender, instance: Person, **kwargs):
    if instance.app_tracking_id is not None:
        traccar = get_traccar_instance()
        original_device = traccar.get_device(instance.app_tracking_id)
        if original_device is not None:
            traccar.delete_device(original_device["id"])
    if instance.simulator_tracking_id is not None:
        traccar = get_traccar_instance()
        original_device = traccar.get_device(instance.simulator_tracking_id)
        if original_device is not None:
            traccar.delete_device(original_device["id"])


@receiver(post_save, sender=MyUser)
def create_random_password_for_user(sender, instance: MyUser, created: bool, **kwargs):
    if created:
        person = Person.objects.filter(email=instance.email).first()
        if person and person.validated:
            # This is a new user object for an already existing valid person. Send the welcome email.
            instance.send_welcome_email(person)
    if not instance.has_usable_password():
        instance.set_password(MyUser.objects.make_random_password(length=20))
        instance.save()


@receiver(signal=m2m_changed, sender=User.groups.through)
def adjust_group_notifications(instance, action, reverse, model, pk_set, using, *args, **kwargs):
    if model == Group and not reverse:
        logger.info("User %s deleted their relation to groups «%s»", instance.username, pk_set)
        if action == 'post_remove':
            pass
        elif action == 'post_add':
            logger.info("User %s created a relation to groups «%s»", instance.username,
                        ", ".join([str(i) for i in pk_set]))
            group = Group.objects.filter(pk__in=pk_set, name="ContestCreator").first()
            if group:
                person = Person.objects.filter(email=instance.email).first()
                if person:
                    instance.send_contest_creator_email(person)
    else:
        logger.info("Group %s is modifying its relation to users «%s»", instance, pk_set)
