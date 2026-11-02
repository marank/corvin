# Generated manually

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0020_allow_blank_body_html"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="InvoiceTemplate",
            new_name="DocumentTemplate",
        ),
        migrations.AlterModelOptions(
            name="documenttemplate",
            options={"ordering": ["name"]},
        ),
    ]
