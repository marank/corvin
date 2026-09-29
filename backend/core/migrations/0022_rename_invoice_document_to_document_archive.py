# Generated manually

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0021_rename_invoice_template'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='InvoiceDocument',
            new_name='DocumentArchive',
        ),
        migrations.RemoveConstraint(
            model_name='documentarchive',
            name='unique_doc_kind_per_invoice',
        ),
        migrations.AddField(
            model_name='documentarchive',
            name='content_type',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to='contenttypes.contenttype',
            ),
        ),
        migrations.AddField(
            model_name='documentarchive',
            name='object_id',
            field=models.UUIDField(null=True),
        ),
        migrations.RunSQL(
            sql=[
                "UPDATE core_documentarchive SET object_id = invoice_id;",
                "UPDATE core_documentarchive SET content_type_id = (SELECT id FROM django_content_type WHERE app_label='core' AND model='invoice');",
            ],
            reverse_sql=[
                "UPDATE core_documentarchive SET invoice_id = object_id;",
            ],
        ),
        migrations.RemoveField(
            model_name='documentarchive',
            name='invoice',
        ),
        migrations.AlterField(
            model_name='documentarchive',
            name='content_type',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to='contenttypes.contenttype',
            ),
        ),
        migrations.AlterField(
            model_name='documentarchive',
            name='object_id',
            field=models.UUIDField(),
        ),
        migrations.AddConstraint(
            model_name='documentarchive',
            constraint=models.UniqueConstraint(
                fields=('content_type', 'object_id', 'kind'), name='unique_doc_kind_per_object'
            ),
        ),
        migrations.AlterField(
            model_name='documentarchive',
            name='file',
            field=models.FileField(upload_to='document_archives/%Y/%m/'),
        ),
    ]
