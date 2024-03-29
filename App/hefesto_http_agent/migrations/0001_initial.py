# Generated by Django 3.0.2 on 2020-01-26 15:16

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Client',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('url', models.URLField(default='http://localhost/hefesto/hefesto_web/data')),
                ('username', models.CharField(blank=True, help_text="Nombre de usuario para 'Basic Auth'.", max_length=100)),
                ('password', models.CharField(blank=True, help_text="Contraseña para 'Basic Auth'.", max_length=100)),
                ('habilitado', models.BooleanField(default=False, help_text='Habilitar el agente de envio.')),
                ('gzip_habilitado', models.BooleanField(default=True, help_text='Habilitar compresion.')),
                ('tiempo_entre_envios', models.IntegerField(default=60, help_text='Tiempo en segundos.')),
            ],
            options={
                'verbose_name': 'HTTP CLIENT',
            },
        ),
        migrations.CreateModel(
            name='Header',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.TextField()),
                ('value', models.TextField()),
                ('config', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='hefesto_http_agent.Client')),
            ],
        ),
    ]
