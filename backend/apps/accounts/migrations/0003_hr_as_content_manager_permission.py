from django.db import migrations


CURRENT_PERMISSIONS = (
    ("manage_accounts", "Can manage user accounts"),
    ("manage_access_assignments", "Can manage access assignments"),
    ("manage_content", "Can manage CMS content"),
    ("manage_hr", "Can manage HR operations"),
    ("view_audit_log", "Can view the audit log"),
)

REMOVED_PERMISSIONS = (
    "manage_role_assignments",
    "manage_recruitment",
    "manage_memberships",
)


def use_hr_permission(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    User = apps.get_model("accounts", "User")

    content_type = ContentType.objects.get(app_label="accounts", model="user")
    permissions = {}
    for codename, name in CURRENT_PERMISSIONS:
        permission, _ = Permission.objects.update_or_create(
            content_type=content_type,
            codename=codename,
            defaults={"name": name},
        )
        permissions[codename] = permission

    account_administrator = Group.objects.get(name="account_administrator")
    account_administrator.permissions.set(
        [
            permissions["manage_accounts"],
            permissions["manage_access_assignments"],
            permissions["view_audit_log"],
        ]
    )

    content_manager = Group.objects.get(name="content_manager")
    content_manager.permissions.set([permissions["manage_content"]])

    hr_manager = Group.objects.filter(name="hr_manager").first()
    if hr_manager:
        for user in User.objects.filter(groups=hr_manager):
            user.groups.add(content_manager)
            user.user_permissions.add(permissions["manage_hr"])
        hr_manager.delete()
    Permission.objects.filter(
        content_type=content_type,
        codename__in=REMOVED_PERMISSIONS,
    ).delete()


def restore_hr_role(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    User = apps.get_model("accounts", "User")

    content_type = ContentType.objects.get(app_label="accounts", model="user")
    previous_permissions = {
        "manage_role_assignments": "Can manage global role assignments",
        "manage_recruitment": "Can manage recruitment",
        "manage_memberships": "Can manage memberships",
    }
    permissions = {}
    for codename, name in previous_permissions.items():
        permission, _ = Permission.objects.update_or_create(
            content_type=content_type,
            codename=codename,
            defaults={"name": name},
        )
        permissions[codename] = permission

    account_administrator = Group.objects.get(name="account_administrator")
    account_administrator.permissions.remove(
        Permission.objects.get(
            content_type=content_type,
            codename="manage_access_assignments",
        )
    )
    account_administrator.permissions.add(
        permissions["manage_role_assignments"]
    )

    hr_manager, _ = Group.objects.get_or_create(name="hr_manager")
    hr_manager.permissions.set(
        [
            permissions["manage_recruitment"],
            permissions["manage_memberships"],
        ]
    )

    manage_hr = Permission.objects.get(
        content_type=content_type,
        codename="manage_hr",
    )
    for user in User.objects.filter(user_permissions=manage_hr):
        user.groups.add(hr_manager)
        user.user_permissions.remove(manage_hr)

    Permission.objects.filter(
        content_type=content_type,
        codename__in=("manage_access_assignments", "manage_hr"),
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_access_control_roles"),
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
                        "manage_access_assignments",
                        "Can manage access assignments",
                    ),
                    ("manage_content", "Can manage CMS content"),
                    ("manage_hr", "Can manage HR operations"),
                    ("view_audit_log", "Can view the audit log"),
                ),
            },
        ),
        migrations.RunPython(use_hr_permission, restore_hr_role),
    ]
