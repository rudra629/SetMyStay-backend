from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('listings', '0024_advertisement_coupon_codes'),
    ]

    operations = [
        migrations.CreateModel(
            name='HeroBannerAd',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.CharField(max_length=140)),
                ('link_url', models.URLField(blank=True, default='', max_length=500)),
                ('image_url', models.URLField(blank=True, default='', max_length=500)),
                ('is_active', models.BooleanField(default=True)),
                ('sort_order', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'ordering': ['sort_order', '-created_at']},
        ),
    ]
