# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('requests', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL("""
        CREATE OR REPLACE VIEW request_view AS
        SELECT
            request.*,
            rqs.last_interval_id,
            rqs.first_interval_id
        FROM
            request
        JOIN (
            SELECT max(request_interval.request_interval_id) AS last_interval_id,
            min(request_interval.request_interval_id) AS first_interval_id,
            request_interval.request_id
        FROM
            request_interval
        GROUP BY
            request_interval.request_id
        ) rqs USING (request_id);
        """)
    ]
