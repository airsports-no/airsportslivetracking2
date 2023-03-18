# Generated by Django 3.2.6 on 2021-08-15 16:59

import display.fields.my_pickled_object_field
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('display', '0032_auto_20210810_1940'),
    ]

    operations = [
        migrations.CreateModel(
            name='EditableRoute',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='User-friendly name', max_length=200)),
                ('route', display.fields.my_pickled_object_field.MyPickledObjectField(default=dict, editable=False)),
            ],
        ),
        migrations.AlterField(
            model_name='navigationtask',
            name='scorecard',
            field=models.ForeignKey(help_text='Reference to an existing scorecard name. Currently existing scorecards: <function NavigationTask.<lambda> at 0x7fafed1fc310>', on_delete=django.db.models.deletion.PROTECT, to='display.scorecard'),
        ),
    ]
