# Generated by Django 3.1.3 on 2020-12-07 11:29

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mainapp', '0005_auto_20201206_2032'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='tree',
            name='creator',
        ),
    ]
