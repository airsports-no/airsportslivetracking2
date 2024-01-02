# Generated by Django 4.1.7 on 2023-04-04 09:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('display', '0091_reset_task_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contest',
            name='summary_score_sorting_direction',
            field=models.CharField(blank=True, choices=[('desc', 'Highest score is best'), ('asc', 'Lowest score is best')], default='asc', help_text='Whether the lowest (ascending) or highest (descending) score is the best result', max_length=50),
        ),
        migrations.AlterField(
            model_name='navigationtask',
            name='score_sorting_direction',
            field=models.CharField(blank=True, choices=[('desc', 'Highest score is best'), ('asc', 'Lowest score is best')], default='asc', help_text='Whether the lowest (ascending) or highest (descending) score is the best result', max_length=50),
        ),
        migrations.AlterField(
            model_name='task',
            name='summary_score_sorting_direction',
            field=models.CharField(choices=[('desc', 'Highest score is best'), ('asc', 'Lowest score is best')], default='asc', help_text='Whether the lowest (ascending) or highest (ascending) score is the best result', max_length=50),
        ),
        migrations.AlterField(
            model_name='tasktest',
            name='sorting',
            field=models.CharField(choices=[('desc', 'Highest score is best'), ('asc', 'Lowest score is best')], default='asc', help_text='Whether the lowest (ascending) or highest (ascending) score is the best result', max_length=50),
        ),
    ]
