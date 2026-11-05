from django.db import migrations

from tenancy.rls import CREATE_TENANT_ROLE_SQL, enable_rls


class Migration(migrations.Migration):
    dependencies = [
        ("tenancy", "0001_initial"),
        ("portfolio", "0003_organization_required"),
        ("assessments", "0003_organization_required"),
        ("evidence", "0004_organization_required"),
        ("reports", "0003_organization_required"),
    ]

    operations = [
        migrations.RunSQL(CREATE_TENANT_ROLE_SQL, reverse_sql=migrations.RunSQL.noop),
        enable_rls("portfolio_client"),
        enable_rls("assessments_assessment"),
        enable_rls("evidence_evidence"),
        enable_rls("reports_report"),
    ]
