# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('items', '0001_initial'),
        ('users', '__first__'),
    ]

    operations = [
        migrations.CreateModel(
            name='Loan',
            fields=[
                ('loan_id', models.CharField(primary_key=True, max_length=255, serialize=False)),
                ('loaned_on', models.DateTimeField(auto_now_add=True)),
                ('returned_on', models.DateTimeField(default=None, null=True)),
                ('item', models.ForeignKey(to='items.Item')),
                ('user', models.ForeignKey(to='users.User')),
            ],
            options={
                'db_table': 'loan',
            },
        ),
    ]
