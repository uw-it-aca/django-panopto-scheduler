# Generated by Django 2.1.15 on 2020-02-26 22:37

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('scheduler', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='recordercacheentry',
            name='cache',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='+', to='scheduler.RecorderCache'),
        ),
    ]
