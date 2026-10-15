from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_treinamento_tipo_participante'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE TABLE IF NOT EXISTS core_treinamento_participantes_externos (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                treinamento_id BIGINT NOT NULL,
                participanteexterno_id BIGINT NOT NULL,
                CONSTRAINT fk_treinamento
                    FOREIGN KEY (treinamento_id)
                    REFERENCES core_treinamento(id)
                    ON DELETE CASCADE,
                CONSTRAINT fk_participanteexterno
                    FOREIGN KEY (participanteexterno_id)
                    REFERENCES core_participanteexterno(id)
                    ON DELETE CASCADE
            );
            """,
            reverse_sql="""
            DROP TABLE IF EXISTS core_treinamento_participantes_externos;
            """
        )
    ]
