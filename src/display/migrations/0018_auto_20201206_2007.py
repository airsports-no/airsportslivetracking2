# Generated by Django 3.1.4 on 2020-12-06 20:07

import display.my_pickled_object_field
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('display', '0017_auto_20201205_2014'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='contest',
            name='server_address',
        ),
        migrations.RemoveField(
            model_name='contest',
            name='server_token',
        ),
        migrations.RemoveField(
            model_name='gatescore',
            name='earliest_limit',
        ),
        migrations.RemoveField(
            model_name='gatescore',
            name='latest_limit',
        ),
        migrations.AddField(
            model_name='gatescore',
            name='bad_crossing_extended_gate_penalty',
            field=models.FloatField(default=200),
        ),
        migrations.AddField(
            model_name='gatescore',
            name='extended_gate_width',
            field=models.FloatField(default=0, help_text='For SP it is 2 (1 nm each side), for tp with procedure turn it is 6'),
        ),
        migrations.AddField(
            model_name='scorecard',
            name='backtracking_grace_time_seconds',
            field=models.FloatField(default=5),
        ),
        migrations.AddField(
            model_name='track',
            name='landing_gate',
            field=display.my_pickled_object_field.MyPickledObjectField(default=None, editable=False, null=True),
        ),
        migrations.AddField(
            model_name='track',
            name='takeoff_gate',
            field=display.my_pickled_object_field.MyPickledObjectField(default=None, editable=False, null=True),
        ),
    ]
