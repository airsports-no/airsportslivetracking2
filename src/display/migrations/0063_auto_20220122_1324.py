# Generated by Django 3.2.10 on 2022-01-22 13:24

from django.db import migrations

from display.utilities.clone_object import simple_clone


def copy(scorecard, name_postfix: str) -> "Scorecard":
    obj = simple_clone(scorecard, {"name": f"{scorecard.name}_{name_postfix}", "original": False})
    for gate in scorecard.gatescore_set.all():
        simple_clone(gate, {"scorecard": obj})
    return obj


def reapply_originals_scorecards(apps, schema_editor):
    db_alias = schema_editor.connection.alias
    # create_scorecards()
    NavigationTask = apps.get_model("display", "NavigationTask")
    for task in NavigationTask.objects.using(db_alias).all():
        task.scorecard = copy(task.original_scorecard, task.pk)
        task.save(update_fields=("scorecard",))


class Migration(migrations.Migration):
    dependencies = [
        ('display', '0062_auto_20220121_1536'),
    ]

    operations = [
        migrations.RunPython(reapply_originals_scorecards)
    ]
