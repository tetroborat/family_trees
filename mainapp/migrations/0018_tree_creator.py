# Generated by Django 3.1.3 on 2020-12-07 17:50

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('mainapp', '0017_auto_20201207_1521'),
    ]

    operations = [
        migrations.AddField(
            model_name='tree',
            name='creator',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.RESTRICT, related_name='creator', to=settings.AUTH_USER_MODEL),
        ),
    ]
