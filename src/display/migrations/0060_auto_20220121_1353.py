# Generated by Django 3.2.10 on 2022-01-21 13:53

from django.db import migrations, models
import django.db.models.deletion


def clone_scorecards(apps, schema_editor):
    db_alias = schema_editor.connection.alias
    GateScore = apps.get_model("display", "GateScore")
    GateScore.objects.using(db_alias).all().delete()

class Migration(migrations.Migration):

    dependencies = [
        ('display', '0059_auto_20220121_1310'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='scorecard',
            name='finish_point_gate_score',
        ),
        migrations.RemoveField(
            model_name='scorecard',
            name='landing_gate_score',
        ),
        migrations.RemoveField(
            model_name='scorecard',
            name='secret_gate_score',
        ),
        migrations.RemoveField(
            model_name='scorecard',
            name='starting_point_gate_score',
        ),
        migrations.RemoveField(
            model_name='scorecard',
            name='takeoff_gate_score',
        ),
        migrations.RemoveField(
            model_name='scorecard',
            name='turning_point_gate_score',
        ),
        migrations.AddField(
            model_name='gatescore',
            name='gate_type',
            field=models.CharField(choices=[('tp', 'Turning point'), ('sp', 'Starting point'), ('fp', 'Finish point'), ('secret', 'Secret point'), ('to', 'Takeoff gate'), ('ldg', 'Landing gate'), ('isp', 'Intermediary starting point'), ('ifp', 'Intermediary finish point')], default='tp', max_length=20),
            preserve_default=False,
        ),
        migrations.RunPython(clone_scorecards), 
        migrations.AddField(
            model_name='gatescore',
            name='scorecard',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='display.scorecard'),
            preserve_default=False,
        ),
        migrations.AlterUniqueTogether(
            name='gatescore',
            unique_together={('scorecard', 'gate_type')},
        ),
    ]
