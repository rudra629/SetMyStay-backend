from django.db import migrations

# A few sample photos didn't fit (a pool villa, a mansion, one with people). Swap them for room / building photos.
SWAPS = {
    '1556909114-f6e7ad7d3136': '1560185893-a55cbc8c57e8',
    '1600596542815-ffad4c1539a9': '1574362848149-11496d93a7c7',
    '1505843513577-22bb7d21e455': '1616594039964-ae9021a400a0',
    '1502005229762-cf1b2da7c5d6': '1460317442991-0ec209397118',
}


def swap(apps, schema_editor):
    ListingImage = apps.get_model('listings', 'ListingImage')
    for old, new in SWAPS.items():
        for img in ListingImage.objects.filter(image_url__contains=f'photo-{old}', property__owner__username='setmystay_samples'):
            img.image_url = img.image_url.replace(old, new)
            img.save(update_fields=['image_url'])


class Migration(migrations.Migration):
    dependencies = [('listings', '0020_sample_listings')]
    operations = [migrations.RunPython(swap, migrations.RunPython.noop)]
