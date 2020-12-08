# Generated by Django 3.1.3 on 2020-12-07 12:21

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('mainapp', '0016_auto_20201207_1438'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tree',
            name='user',
            field=models.ManyToManyField(related_name='users', to=settings.AUTH_USER_MODEL, verbose_name='Пользователь'),
        ),
    ]
