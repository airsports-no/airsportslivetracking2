# Generated by Django 3.2.18 on 2023-03-17 13:29

import display.models
import display.my_pickled_object_field
import django.core.files.storage
import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('display', '0088_auto_20230304_1240'),
    ]

    operations = [
        migrations.AddField(
            model_name='navigationtask',
            name='_nominatim',
            field=display.my_pickled_object_field.MyPickledObjectField(default=dict, editable=False, help_text='Used to hold response from geolocation service'),
        ),
        migrations.AlterField(
            model_name='useruploadedmap',
            name='map_file',
            field=models.FileField(help_text='File must be of type MBTILES. This can be generated for instance using MapTile Desktop', storage=django.core.files.storage.FileSystemStorage(location='/maptiles/user_maps'), upload_to='', validators=[django.core.validators.FileExtensionValidator(allowed_extensions=['mbtiles']), display.models.validate_file_size]),
        ),
    ]
