# Generated by Django 5.0 on 2024-08-14 20:10

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("display", "0117_auto_20240811_1552"),
    ]

    operations = [
        migrations.AddField(
            model_name="gatescore",
            name="hit_bonus",
            field=models.FloatField(default=0),
        ),
        migrations.AlterField(
            model_name="contestant",
            name="route",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="display.route"),
        ),
        migrations.AlterField(
            model_name="editableroute",
            name="route_type",
            field=models.CharField(
                choices=[
                    ("precision", "FAI Precision"),
                    ("cima_precision", "CIMA Precision"),
                    ("anr_corridor", "ANR Corridor"),
                    ("airsports", "Air Sports Race"),
                    ("airsportchallenge", "AirSport Challenge"),
                    ("poker", "Poker run"),
                    ("landing", "Landing"),
                ],
                default="precision",
                help_text="Not used",
                max_length=200,
            ),
        ),
        migrations.AlterField(
            model_name="scorecard",
            name="calculator",
            field=models.CharField(
                choices=[
                    ("precision", "FAI Precision"),
                    ("cima_precision", "CIMA Precision"),
                    ("anr_corridor", "ANR Corridor"),
                    ("airsports", "Air Sports Race"),
                    ("airsportchallenge", "AirSport Challenge"),
                    ("poker", "Poker run"),
                    ("landing", "Landing"),
                ],
                default="precision",
                help_text="Supported calculator types",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="scorecard",
            name="initial_score",
            field=models.FloatField(
                blank=True,
                help_text="Initial score awarded to the contestant it start. If set this will be used for the initial score for each contestant. If it is unset, the initial score will be calculated based on the chosen scorecard. This is typically 0 for most scorecards, and greater than 0 for CIMA scorecards.",
                null=True,
            ),
        ),
    ]
