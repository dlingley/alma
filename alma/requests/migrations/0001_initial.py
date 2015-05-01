# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('items', '0001_initial'),
        ('users', '__first__'),
    ]

    operations = [
        migrations.CreateModel(
            name='Request',
            fields=[
                ('request_id', models.AutoField(primary_key=True, serialize=False)),
                ('repeat_on', models.IntegerField()),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('edited_on', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(to='users.User', on_delete=django.db.models.deletion.SET_NULL, related_name='+', null=True)),
                ('item', models.ForeignKey(to='items.Item')),
                ('user', models.ForeignKey(to='users.User')),
            ],
            options={
                'db_table': 'request',
            },
        ),
        migrations.CreateModel(
            name='RequestInterval',
            fields=[
                ('request_interval_id', models.AutoField(primary_key=True, serialize=False)),
                ('start', models.DateTimeField(help_text='Starting datetime of the request')),
                ('end', models.DateTimeField(help_text='Ending datetime of the request')),
                ('alma_request_id', models.CharField(help_text='The corresponding Alma Request ID', max_length=255)),
                ('state', models.IntegerField(help_text='The state of this request', choices=[(1, 'Reserved'), (2, 'Loaned'), (4, 'Returned')])),
                ('loaned_on', models.DateTimeField(help_text='When the item was actually loaned to the user', null=True, default=None)),
                ('returned_on', models.DateTimeField(help_text='When the item was returned from the user', null=True, default=None)),
                ('request', models.ForeignKey(help_text='The parent request linking one or more intervals together', to='requests.Request')),
            ],
            options={
                'db_table': 'request_interval',
            },
        ),
    ]
