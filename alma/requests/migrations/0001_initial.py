# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
        ('items', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Request',
            fields=[
                ('request_id', models.AutoField(primary_key=True, serialize=False)),
                ('repeat_on', models.IntegerField(default=0)),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('edited_on', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'request',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='RequestView',
            fields=[
                ('request', models.OneToOneField(to='requests.Request', primary_key=True, serialize=False)),
            ],
            options={
                'db_table': 'request_view',
                'managed': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='RequestInterval',
            fields=[
                ('request_interval_id', models.AutoField(primary_key=True, serialize=False)),
                ('start', models.DateTimeField(help_text='Starting datetime of the request')),
                ('end', models.DateTimeField(help_text='Ending datetime of the request')),
                ('alma_request_id', models.CharField(max_length=255, help_text='The corresponding Alma Request ID')),
                ('state', models.IntegerField(help_text='The state of this request', choices=[(1, 'Reserved'), (2, 'Loaned'), (4, 'Returned')], default=1)),
                ('loaned_on', models.DateTimeField(help_text='When the item was actually loaned to the user', default=None, null=True)),
                ('returned_on', models.DateTimeField(help_text='When the item was returned from the user', default=None, null=True)),
                ('request', models.ForeignKey(to='requests.Request', help_text='The parent request linking one or more intervals together')),
            ],
            options={
                'db_table': 'request_interval',
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='request',
            name='created_by',
            field=models.ForeignKey(related_name='+', null=True, to='users.User', on_delete=django.db.models.deletion.SET_NULL),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='request',
            name='item',
            field=models.ForeignKey(to='items.Item'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='request',
            name='user',
            field=models.ForeignKey(to='users.User'),
            preserve_default=True,
        ),
    ]
