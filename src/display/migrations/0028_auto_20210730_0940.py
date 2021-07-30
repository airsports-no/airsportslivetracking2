# Generated by Django 3.2.1 on 2021-07-30 09:40

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('display', '0027_auto_20210522_0927'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contestant',
            name='tracker_device_id',
            field=models.CharField(blank=True, help_text='ID of physical tracking device that will be brought into the plane. If using the Air Sports Live Tracking app this should be left blank.', max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='contestant',
            name='tracking_device',
            field=models.CharField(choices=[('device', 'Hardware GPS tracker'), ('pilot_app', "Pilot's Air Sports Live Tracking app"), ('copilot_app', "Copilot's Air Sports Live Tracking app"), ('pilot_app_or_copilot_a[[', "Pilot's or copilot's Air Sports Live Tracking app")], default='pilot_app_or_copilot_a[[', help_text='The device used for tracking the team', max_length=30),
        ),
        migrations.AlterField(
            model_name='contestteam',
            name='tracking_device',
            field=models.CharField(choices=[('device', 'Hardware GPS tracker'), ('pilot_app', "Pilot's Air Sports Live Tracking app"), ('copilot_app', "Copilot's Air Sports Live Tracking app"), ('pilot_app_or_copilot_a[[', "Pilot's or copilot's Air Sports Live Tracking app")], default='pilot_app_or_copilot_a[[', help_text='The device used for tracking the team', max_length=30),
        ),
        migrations.AlterField(
            model_name='navigationtask',
            name='scorecard',
            field=models.ForeignKey(help_text='Reference to an existing scorecard name. Currently existing scorecards: <function NavigationTask.<lambda> at 0x7f95d3f33160>', on_delete=django.db.models.deletion.PROTECT, to='display.scorecard'),
        ),
    ]
