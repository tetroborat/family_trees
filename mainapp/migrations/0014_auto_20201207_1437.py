# Generated by Django 3.1.3 on 2020-12-07 11:37

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('mainapp', '0013_tree_creator'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='tree',
            name='creator',
        ),
        migrations.AlterField(
            model_name='tree',
            name='user',
            field=models.ManyToManyField(to=settings.AUTH_USER_MODEL, verbose_name='Пользователь'),
        ),
    ]
