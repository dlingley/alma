# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Item',
            fields=[
                ('item_id', models.CharField(primary_key=True, serialize=False, max_length=255)),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField()),
                ('barcode', models.CharField(max_length=255, unique=True)),
                ('mms_id', models.CharField(max_length=255)),
                ('category', models.CharField(max_length=255)),
            ],
            options={
                'db_table': 'item',
            },
            bases=(models.Model,),
        ),
    ]
