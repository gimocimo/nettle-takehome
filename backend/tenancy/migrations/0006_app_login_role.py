from django.db import migrations

from tenancy.rls import CREATE_APP_ROLE_SQL


class Migration(migrations.Migration):
    """The unprivileged login role for production, and narrower tenant-role grants.
    Created NOLOGIN: `manage.py configure_app_role` enables login with a password."""

    dependencies = [
        ("tenancy", "0005_allowed_ai_models"),
        ("jobs", "0001_initial"),
        ("admin", "0003_logentry_add_action_flag_choices"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
        ("sessions", "0001_initial"),
    ]

    operations = [migrations.RunSQL(sql=CREATE_APP_ROLE_SQL, reverse_sql=migrations.RunSQL.noop)]
