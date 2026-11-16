"""Verification documents for the sample listings (owner 'setmystay_samples').

They are clearly marked placeholder images ("SAMPLE DOCUMENT - not a real document"),
not real or realistic IDs. Uploaded once to the normal document storage (Cloudinary),
then attached: Aadhaar to every sample; electricity bill + NOC to sample PGs and rentals;
electricity bill also to roommates who already have a place.
"""
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import migrations

DOCS_DIR = Path(__file__).resolve().parent.parent / 'sample_docs'


def attach(apps, schema_editor):
    Property = apps.get_model('listings', 'Property')
    samples = Property.objects.filter(owner__username='setmystay_samples')
    if not samples.exists():
        return
    try:
        names = {}
        for kind in ('aadhaar', 'electricity', 'noc'):
            data = (DOCS_DIR / f'sample_{kind}.png').read_bytes()
            names[kind] = default_storage.save(f'verification_docs/sample_{kind}.png', ContentFile(data))
    except Exception as exc:  # never block a deploy over sample data
        print(f'\n  Sample documents not uploaded ({exc}); sample listings left without documents.')
        return

    samples.update(document_aadhaar=names['aadhaar'])
    samples.filter(property_type__in=['PG', 'RENTAL']).update(
        document_electricity=names['electricity'], document_noc=names['noc'])
    samples.filter(property_type='ROOMMATE', sharing_status='Living in').update(
        document_electricity=names['electricity'])


def detach(apps, schema_editor):
    Property = apps.get_model('listings', 'Property')
    Property.objects.filter(owner__username='setmystay_samples').update(
        document_aadhaar=None, document_electricity=None, document_noc=None)


class Migration(migrations.Migration):
    dependencies = [('listings', '0021_fix_sample_photos')]
    operations = [migrations.RunPython(attach, detach)]
