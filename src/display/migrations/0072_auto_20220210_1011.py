# Generated by Django 3.2.10 on 2022-02-10 10:11

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('display', '0071_flightorderconfiguration_map_minute_mark_line_width'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='navigationtask',
            name='default_line_width',
        ),
        migrations.RemoveField(
            model_name='navigationtask',
            name='default_map',
        ),
    ]
