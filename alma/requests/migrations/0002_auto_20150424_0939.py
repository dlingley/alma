# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('requests', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='request',
            name='color',
            field=models.CharField(max_length=7, default='#ff8800'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='request',
            name='repeat_on',
            field=models.IntegerField(default=0),
        ),
    ]
