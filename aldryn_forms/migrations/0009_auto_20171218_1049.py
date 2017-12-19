# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2017-12-18 12:49
from __future__ import unicode_literals

import aldryn_forms.storage_backends
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('aldryn_forms', '0008_auto_20170316_0845'),
    ]

    operations = [
        migrations.AddField(
            model_name='formplugin',
            name='storage_backend',
            field=models.CharField(choices=aldryn_forms.utils.storage_backend_choices(), default='default', max_length=15, verbose_name='Storage backend'),
        ),
    ]