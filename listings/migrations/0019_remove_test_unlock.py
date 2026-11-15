from django.db import migrations


def remove_invalid_unlocks(apps, schema_editor):
    """Remove the unlock entry for listing 99999 created while testing (that listing does not exist)."""
    UserUnlock = apps.get_model('listings', 'UserUnlock')
    Property = apps.get_model('listings', 'Property')
    if not Property.objects.filter(id=99999).exists():
        UserUnlock.objects.filter(property_id='99999').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('listings', '0018_adminloginotp_purpose'),
    ]

    operations = [
        migrations.RunPython(remove_invalid_unlocks, migrations.RunPython.noop),
    ]
