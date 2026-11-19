from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('listings', '0027_coupon_scope'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='property',
            index=models.Index(fields=['status', '-created_at'], name='prop_status_created_idx'),
        ),
        migrations.AddIndex(
            model_name='property',
            index=models.Index(fields=['property_type', 'status'], name='prop_type_status_idx'),
        ),
    ]
