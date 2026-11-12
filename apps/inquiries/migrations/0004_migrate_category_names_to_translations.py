
from django.db import migrations


def migrate_category_translations(apps, schema_editor):
    InquiryCategory = apps.get_model(
        "inquiries",
        "InquiryCategory",
    )
    InquiryCategoryTranslation = apps.get_model(
        "inquiries",
        "InquiryCategoryTranslation",
    )

    translations = []

    for category in InquiryCategory.objects.all().iterator():
        translations.append(
            InquiryCategoryTranslation(
                category_id=category.pk,
                language_code="uz",
                name=category.name,
                description=category.description,
            )
        )

    InquiryCategoryTranslation.objects.bulk_create(
        translations,
        ignore_conflicts=True,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("inquiries", "0003_inquirycategorytranslation"),
    ]

    operations = [
        migrations.RunPython(
            migrate_category_translations,
            migrations.RunPython.noop,
        ),
    ]
