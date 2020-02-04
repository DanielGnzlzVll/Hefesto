# Generated by Django 3.0.2 on 2020-01-26 15:16

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Log',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(default=django.utils.timezone.now)),
                ('modulo', models.CharField(max_length=200)),
                ('nivel', models.PositiveSmallIntegerField(choices=[(0, 'NotSet'), (20, 'Info'), (30, 'Warning'), (10, 'Debug'), (40, 'Error'), (50, 'Fatal')], db_index=True, default=40)),
                ('mensaje', models.TextField()),
                ('trace', models.TextField(blank=True, null=True)),
            ],
            options={
                'verbose_name': 'Logging',
                'verbose_name_plural': 'Logging',
                'ordering': ('-timestamp',),
            },
        ),
        migrations.AddIndex(
            model_name='log',
            index=models.Index(fields=['timestamp', 'nivel', 'modulo'], name='hefesto_log_timesta_74ea3c_idx'),
        ),
    ]
