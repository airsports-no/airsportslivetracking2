# Generated by Django 4.1.7 on 2023-07-16 20:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('display', '0098_editableroute_number_of_waypoints_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='useruploadedmap',
            name='default_zoom_level',
            field=models.IntegerField(default=12, help_text='This zoom level is automatically selected when choosing the map in the flight order configuration or other map generation forms.'),
        ),
    ]
