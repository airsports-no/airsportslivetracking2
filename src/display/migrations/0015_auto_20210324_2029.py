# Generated by Django 3.1.7 on 2021-03-24 20:29

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('display', '0014_auto_20210322_2033'),
    ]

    operations = [
        migrations.AlterField(
            model_name='navigationtask',
            name='scorecard',
            field=models.ForeignKey(help_text='Reference to an existing scorecard name. Currently existing scorecards: <function NavigationTask.<lambda> at 0x7f7d3595c0d0>', on_delete=django.db.models.deletion.PROTECT, to='display.scorecard'),
        ),
        migrations.AlterField(
            model_name='trackscoreoverride',
            name='prohibited_zone_penalty',
            field=models.FloatField(blank=True, default=None, help_text='Penalty for entering prohibited zone such as controlled airspace or other prohibited areas', null=True),
        ),
    ]
