from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='TreinamentoParticipanteExterno',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('treinamento', models.ForeignKey(on_delete=models.CASCADE, to='core.treinamento')),
                ('participanteexterno', models.ForeignKey(on_delete=models.CASCADE, to='core.participanteexterno')),
            ],
            options={
                'db_table': 'core_treinamento_participantes_externos',
            },
        ),
    ]