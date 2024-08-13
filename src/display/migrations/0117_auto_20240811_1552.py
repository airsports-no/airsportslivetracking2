# Generated by Django 5.0 on 2024-08-11 15:52

import django.db.models.deletion
from django.db import migrations, models


def update_route(apps, schema_editor):
    for contestant in apps.get_model("display", "Contestant").objects.all():
        contestant.route = contestant.navigation_task.route
        contestant.save()


class Migration(migrations.Migration):

    dependencies = [
        ("display", "0116_remove_contestant_predefined_gate_times_and_more"),
    ]

    operations = [
        migrations.RunPython(update_route),
        migrations.AlterField(
            model_name="contestant",
            name="minutes_to_starting_point",
            field=models.FloatField(
                default=5,
                help_text="The number of minutes from the take-off time until the starting point. This will be the time of the takeoff gate if it exists.",
            ),
        ),
        migrations.AlterField(
            model_name="flightorderconfiguration",
            name="include_turning_point_images",
            field=models.BooleanField(
                default=False,
                help_text="Includes one or more pages with aerial photos of each turning point (turns in a anr corridor is not considered a turning point).",
            ),
        ),
        migrations.CreateModel(
            name="FreeWaypoint",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=200)),
                ("latitude", models.FloatField()),
                ("longitude", models.FloatField()),
                (
                    "waypoint_type",
                    models.IntegerField(choices=[(1, "Waypoint"), (2, "Circle Start"), (3, "Circle Center")]),
                ),
                ("route", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="display.route")),
            ],
        ),
    ]
