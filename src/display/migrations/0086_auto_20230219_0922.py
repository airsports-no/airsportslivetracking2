# Generated by Django 3.2.17 on 2023-02-19 09:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('display', '0085_auto_20230202_0728'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='scorecard',
            options={'ordering': ('-valid_from',)},
        ),
        migrations.AddField(
            model_name='contestant',
            name='has_been_tracked_by_simulator',
            field=models.BooleanField(default=False, help_text='Is true if any positions for the contestant has been received from the simulator tracking ID'),
        ),
    ]
