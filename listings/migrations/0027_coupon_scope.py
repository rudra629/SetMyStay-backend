from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('listings', '0026_roommate_details_listing_edits'),
    ]

    operations = [
        migrations.AddField(
            model_name='coupon',
            name='scope',
            field=models.CharField(choices=[('plans', 'Unlock plans'), ('listings', 'Listing fees')], default='plans', max_length=10),
        ),
    ]
