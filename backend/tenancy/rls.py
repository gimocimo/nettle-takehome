"""Postgres row-level security (RLS): the database's own guarantee that a tenant
only sees and writes its own rows, even if application code forgets a filter.

How it works:
- `nettle_tenant` is an unprivileged role (no superuser, no BYPASSRLS, not the
  table owner), so policies apply to it.
- Each tenant table gets a policy comparing organization_id with the
  `app.current_organization` setting.
- Per transaction, the app switches to that role and sets the organization
  (tenancy.db.activate_tenant). Both are SET LOCAL and end with the transaction.
- With no organization set, the policy matches nothing: it fails closed.

Production note: the app's login role must itself be unprivileged (member of
nettle_tenant, no BYPASSRLS). Docker dev logs in as the image's superuser for
convenience, which is also what Nettle staff tooling (Django admin, migrations,
seeding) uses as a deliberate, audited bypass.
"""
# PROPOSED (not built): composite foreign keys, e.g. (organization_id, client_id) ->
# client(organization_id, id), so the database itself guarantees a child row and its
# parent share an organization (today: model save() checks + RLS WITH CHECK).
from django.db import migrations

TENANT_ROLE = "nettle_tenant"
ORGANIZATION_SETTING = "app.current_organization"

CREATE_TENANT_ROLE_SQL = f"""
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{TENANT_ROLE}') THEN
        CREATE ROLE {TENANT_ROLE} NOLOGIN;
    END IF;
END
$$;
GRANT USAGE ON SCHEMA public TO {TENANT_ROLE};
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {TENANT_ROLE};
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {TENANT_ROLE};
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {TENANT_ROLE};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO {TENANT_ROLE};
"""

# The production login role. Not a superuser, can't bypass row-level security, and
# NOINHERIT: it holds none of nettle_tenant's privileges until a tenant transaction
# switches to that role. Code that forgets tenant_transaction() therefore fails with
# "permission denied" instead of reading every organization's rows.
APP_ROLE = "nettle_app"

# What the app touches outside a tenant transaction: sign-in and sessions, resolving the
# organization from a membership, and workers claiming jobs across organizations.
APP_TABLES_READ_WRITE = [
    "auth_user",
    "auth_user_groups",
    "auth_user_user_permissions",
    "django_session",
    "django_admin_log",
    "jobs_job",
]
APP_TABLES_READ_ONLY = [
    "auth_group",
    "auth_group_permissions",
    "auth_permission",
    "django_content_type",
    "tenancy_organization",
    "tenancy_membership",
]

CREATE_APP_ROLE_SQL = f"""
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{APP_ROLE}') THEN
        CREATE ROLE {APP_ROLE} NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOINHERIT;
    END IF;
END
$$;
GRANT {TENANT_ROLE} TO {APP_ROLE};
GRANT USAGE ON SCHEMA public TO {APP_ROLE};
GRANT SELECT, INSERT, UPDATE, DELETE ON {", ".join(APP_TABLES_READ_WRITE)} TO {APP_ROLE};
GRANT SELECT ON {", ".join(APP_TABLES_READ_ONLY)} TO {APP_ROLE};
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {APP_ROLE};

-- Inside a tenant transaction, nettle_tenant needs the tenant tables (row-level security
-- picks the rows), the job queue, and read access to users, organizations and
-- memberships: not sessions, credentials, permissions or the migration history.
REVOKE ALL ON django_session, django_admin_log, django_migrations, auth_group, auth_group_permissions,
    auth_permission, auth_user_groups, auth_user_user_permissions FROM {TENANT_ROLE};
REVOKE INSERT, UPDATE, DELETE ON auth_user, tenancy_organization, tenancy_membership FROM {TENANT_ROLE};
"""

# NULLIF: once set in a session, a custom setting reads back as '' rather than NULL.
_CURRENT_ORG = f"NULLIF(current_setting('{ORGANIZATION_SETTING}', true), '')::uuid"


def enable_rls(table, shared_rows=False):
    """Migration operation: protect one tenant table with the isolation policy.

    shared_rows: rows with a NULL organization (e.g. Nettle's shared section library)
    are readable by every tenant, but tenants can only write their own rows.
    """
    readable = f"organization_id IS NULL OR organization_id = {_CURRENT_ORG}" if shared_rows else f"organization_id = {_CURRENT_ORG}"
    return migrations.RunSQL(
        sql=f"""
            ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
            CREATE POLICY tenant_isolation ON {table}
                USING ({readable})
                WITH CHECK (organization_id = {_CURRENT_ORG});
        """,
        reverse_sql=f"""
            DROP POLICY IF EXISTS tenant_isolation ON {table};
            ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;
        """,
    )
