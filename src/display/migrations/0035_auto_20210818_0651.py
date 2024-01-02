# Generated by Django 3.2.6 on 2021-08-18 06:51

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('display', '0034_auto_20210817_0657'),
    ]

    operations = [
        migrations.AddField(
            model_name='navigationtask',
            name='editable_route',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='display.editableroute'),
        ),
        migrations.AlterField(
            model_name='navigationtask',
            name='scorecard',
            field=models.ForeignKey(help_text='Reference to an existing scorecard name. Currently existing scorecards: <function NavigationTask.<lambda> at 0x7f4b9db6d0d0>', on_delete=django.db.models.deletion.PROTECT, to='display.scorecard'),
        ),
    ]
