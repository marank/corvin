from django.db import migrations


def normalize_sequences(apps, schema_editor):
    NumberSequence = apps.get_model("core", "NumberSequence")
    legacy = NumberSequence.objects.filter(scope_key__startswith="legacy:")
    for sequence in legacy:
        year = sequence.scope_key.rsplit(":", 1)[-1]
        existing = NumberSequence.objects.filter(
            owner_id=sequence.owner_id,
            entity="invoice",
            scope_key=year,
        ).exclude(pk=sequence.pk).first()
        if existing:
            if sequence.last_number > existing.last_number:
                existing.last_number = sequence.last_number
                existing.save(update_fields=["last_number"])
            sequence.delete()
        else:
            sequence.scope_key = year
            sequence.save(update_fields=["scope_key"])


class Migration(migrations.Migration):
    dependencies = [("core", "0003_remove_invoice_unique_invoice_number_per_owner_and_more")]
    operations = [migrations.RunPython(normalize_sequences, migrations.RunPython.noop)]
