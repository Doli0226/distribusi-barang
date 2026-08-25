from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("distribution", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="distribution",
            name="arrival_photo",
            field=models.TextField(blank=True, help_text="Data URL (base64) atau URL bukti kirim"),
        ),
    ]
