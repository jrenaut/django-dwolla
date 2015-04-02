# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django_extensions.db.fields.encrypted


class Migration(migrations.Migration):

    dependencies = [
        ('djdwolla', '0002_auto_20141214_0513'),
    ]

    operations = [
        migrations.AddField(
            model_name='customer',
            name='refresh_token_expiration',
            field=models.DateTimeField(null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='customer',
            name='pin',
            field=django_extensions.db.fields.encrypted.EncryptedCharField(max_length=364, null=True, blank=True),
        ),
    ]
