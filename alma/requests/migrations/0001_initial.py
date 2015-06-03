# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('loans', '0001_initial'),
        ('items', '0001_initial'),
        ('users', '__first__'),
    ]

    operations = [
        migrations.CreateModel(
            name='Request',
            fields=[
                ('request_id', models.CharField(primary_key=True, max_length=255, serialize=False)),
                ('start', models.DateTimeField(help_text='Starting datetime of the request')),
                ('end', models.DateTimeField(help_text='Ending datetime of the request')),
                ('loan', models.OneToOneField(to='loans.Loan', null=True, default=None)),
            ],
            options={
                'db_table': 'request',
            },
        ),
        migrations.CreateModel(
            name='Reservation',
            fields=[
                ('reservation_id', models.AutoField(primary_key=True, serialize=False)),
                ('repeat_on', models.IntegerField(default=0)),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('edited_on', models.DateTimeField(auto_now=True)),
                ('bib', models.ForeignKey(to='items.Bib')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='users.User', null=True)),
                ('user', models.ForeignKey(to='users.User')),
            ],
            options={
                'db_table': 'reservation',
            },
        ),
        migrations.AddField(
            model_name='request',
            name='reservation',
            field=models.ForeignKey(to='requests.Reservation', help_text='The parent reservation linking one or more requests together'),
        ),
    ]
