# Generated by Django 5.0 on 2024-08-04 19:53

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('display', '0114_rename_turning_points_photo_zoom_level_flightorderconfiguration_turning_point_photos_zoom_level'),
    ]

    operations = [
        migrations.AlterField(
            model_name='flightorderconfiguration',
            name='unknown_leg_photos_zoom_level',
            field=models.IntegerField(default=15, help_text='The tile zoom level used for generating unknown leg photos from google satellite imagery', validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(20)]),
        ),
    ]
