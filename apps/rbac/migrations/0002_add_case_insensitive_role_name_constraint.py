from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("rbac", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                CREATE UNIQUE INDEX auth_group_name_lower_uniq
                ON auth_group (LOWER(name));
            """,
            reverse_sql="""
                DROP INDEX auth_group_name_lower_uniq;
            """,
        ),
    ]