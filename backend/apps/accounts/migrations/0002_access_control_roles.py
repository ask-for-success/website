from django.db import migrations


PERMISSIONS = (
    ("manage_accounts", "Can manage user accounts"),
    ("manage_role_assignments", "Can manage global role assignments"),
    ("manage_content", "Can manage CMS content"),
    ("manage_recruitment", "Can manage recruitment"),
    ("manage_memberships", "Can manage memberships"),
    ("view_audit_log", "Can view the audit log"),
)

ROLE_PERMISSIONS = {
    "account_administrator": (
        "manage_accounts",
        "manage_role_assignments",
        "view_audit_log",
    ),
    "content_manager": ("manage_content",),
    "hr_manager": (
        "manage_recruitment",
        "manage_memberships",
    ),
}


def create_access_control_roles(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")

    content_type, _ = ContentType.objects.get_or_create(
        app_label="accounts",
        model="user",
    )

    permissions = {}
    for codename, name in PERMISSIONS:
        permission, _ = Permission.objects.update_or_create(
            content_type=content_type,
            codename=codename,
            defaults={"name": name},
        )
        permissions[codename] = permission

    for role_key, permission_codes in ROLE_PERMISSIONS.items():
        group, _ = Group.objects.get_or_create(name=role_key)
        group.permissions.set(
            [permissions[permission_code] for permission_code in permission_codes]
        )


def remove_access_control_roles(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")

    Group.objects.filter(name__in=ROLE_PERMISSIONS).delete()
    content_type = ContentType.objects.filter(
        app_label="accounts",
        model="user",
    ).first()
    if content_type:
        Permission.objects.filter(
            content_type=content_type,
            codename__in=[codename for codename, _ in PERMISSIONS],
        ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="user",
            options={
                "db_table": "users",
                "ordering": ("email",),
                "permissions": (
                    ("manage_accounts", "Can manage user accounts"),
                    (
                        "manage_role_assignments",
                        "Can manage global role assignments",
                    ),
                    ("manage_content", "Can manage CMS content"),
                    ("manage_recruitment", "Can manage recruitment"),
                    ("manage_memberships", "Can manage memberships"),
                    ("view_audit_log", "Can view the audit log"),
                ),
            },
        ),
        migrations.RunPython(
            create_access_control_roles,
            remove_access_control_roles,
        ),
    ]
