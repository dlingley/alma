# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('requests', '0002_auto_20150424_0939'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='request',
            name='color',
        ),
        migrations.AlterField(
            model_name='requestinterval',
            name='state',
            field=models.IntegerField(choices=[(1, 'Reserved'), (2, 'Loaned'), (4, 'Returned')], default=1, help_text='The state of this request'),
        ),
    ]
