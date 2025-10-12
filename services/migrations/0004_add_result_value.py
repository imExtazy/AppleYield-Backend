from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("services", "0003_rename_models"),
    ]

    operations = [
        migrations.AddField(
            model_name="months_calculation",
            name="result_value",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
    ]


