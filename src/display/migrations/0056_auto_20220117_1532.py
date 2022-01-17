# Generated by Django 3.2.10 on 2022-01-17 15:32

from django.db import migrations, models
import django.db.models.deletion
import multiselectfield.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('display', '0055_auto_20211206_2115'),
    ]

    operations = [
        migrations.AddField(
            model_name='scorecard',
            name='prohibited_zone_grace_time',
            field=models.FloatField(default=3, help_text='The number of seconds the contestant can be within the prohibited zone before getting penalty'),
        ),
        migrations.AddField(
            model_name='trackscoreoverride',
            name='prohibited_zone_grace_time',
            field=models.FloatField(blank=True, default=None, help_text='The number of seconds the contestant can be within the prohibited zone before getting penalty', null=True),
        ),
        migrations.AlterField(
            model_name='editableroute',
            name='route_type',
            field=models.CharField(choices=[('precision', 'Precision'), ('anr_corridor', 'ANR Corridor'), ('airsports', 'Air Sports Race'), ('poker', 'Poker run'), ('landing', 'Landing')], default='precision', max_length=200),
        ),
        migrations.AlterField(
            model_name='navigationtask',
            name='scorecard',
            field=models.ForeignKey(help_text='Reference to an existing scorecard name. Currently existing scorecards: <function NavigationTask.<lambda> at 0x7f637d888700>', on_delete=django.db.models.deletion.PROTECT, to='display.scorecard'),
        ),
        migrations.AlterField(
            model_name='scorecard',
            name='task_type',
            field=multiselectfield.db.fields.MultiSelectField(choices=[('precision', 'Precision'), ('anr_corridor', 'ANR Corridor'), ('airsports', 'Air Sports Race'), ('poker', 'Poker run'), ('landing', 'Landing')], default=list, max_length=46),
        ),
    ]
