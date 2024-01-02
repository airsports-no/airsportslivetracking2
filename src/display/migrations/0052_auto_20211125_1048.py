# Generated by Django 3.2.9 on 2021-11-25 10:48

from django.db import migrations, models
import django.db.models.deletion
import django_countries.fields


class Migration(migrations.Migration):

    dependencies = [
        ('display', '0051_auto_20211122_0834'),
    ]

    operations = [
        migrations.AddField(
            model_name='contest',
            name='country',
            field=django_countries.fields.CountryField(blank=True, max_length=2, null=True),
        ),
        migrations.AlterField(
            model_name='navigationtask',
            name='default_map',
            field=models.CharField(choices=[('/maptiles/Finland', 'Finland'), ('/maptiles/Switzerland', 'Switzerland'), ('osm', 'OSM'), ('fc', 'Flight Contest'), ('mto', 'MapTiler Outdoor'), ('cyclosm', 'CycleOSM')], default='cyclosm', max_length=200),
        ),
        migrations.AlterField(
            model_name='navigationtask',
            name='scorecard',
            field=models.ForeignKey(help_text='Reference to an existing scorecard name. Currently existing scorecards: <function NavigationTask.<lambda> at 0x7f1d1d473280>', on_delete=django.db.models.deletion.PROTECT, to='display.scorecard'),
        ),
    ]
