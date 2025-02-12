# Generated by Django 3.2.1 on 2021-07-30 09:43

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('display', '0028_auto_20210730_0940'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contestteam',
            name='tracker_device_id',
            field=models.CharField(blank=True, help_text='ID of physical tracking device that will be brought into the plane. Leave empty if official Air Sports Live Tracking app is used. Note that only a single tracker is to be used per plane.', max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='navigationtask',
            name='scorecard',
            field=models.ForeignKey(help_text='Reference to an existing scorecard name. Currently existing scorecards: <function NavigationTask.<lambda> at 0x7fad5353b160>', on_delete=django.db.models.deletion.PROTECT, to='display.scorecard'),
        ),
    ]
