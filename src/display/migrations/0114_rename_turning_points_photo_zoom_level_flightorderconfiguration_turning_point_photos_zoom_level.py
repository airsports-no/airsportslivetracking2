# Generated by Django 5.0 on 2024-08-04 19:51

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('display', '0113_remove_flightorderconfiguration_photos_metres_across_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='flightorderconfiguration',
            old_name='turning_points_photo_zoom_level',
            new_name='turning_point_photos_zoom_level',
        ),
    ]
