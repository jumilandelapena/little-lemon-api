"""Create the Manager and Delivery Crew groups used for role checks."""

from django.db import migrations

GROUPS = ["Manager", "Delivery Crew"]


def create_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    for name in GROUPS:
        Group.objects.get_or_create(name=name)


def remove_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name__in=GROUPS).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("LittleLemonAPI", "0001_initial"),
    ]

    operations = [migrations.RunPython(create_groups, remove_groups)]
