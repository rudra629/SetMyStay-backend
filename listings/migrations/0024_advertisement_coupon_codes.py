from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('listings', '0023_undo_slot_listing_fee')]
    operations = [
        migrations.AddField(model_name='advertisement', name='coupon_codes',
                            field=models.CharField(blank=True, default='', max_length=300)),
    ]
