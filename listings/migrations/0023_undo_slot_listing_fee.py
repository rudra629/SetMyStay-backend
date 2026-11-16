from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def mark_old_fees_used(apps, schema_editor):
    # Listing fees paid before this rule were already used for the listings that exist
    Purchase = apps.get_model('listings', 'Purchase')
    Purchase.objects.filter(plan_name__icontains='listing').update(consumed=True)


class Migration(migrations.Migration):

    dependencies = [
        ('listings', '0022_sample_listing_documents'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(model_name='purchase', name='consumed', field=models.BooleanField(default=False)),
        migrations.AddField(model_name='purchase', name='listing', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='fee_purchases', to='listings.property')),
        migrations.AddField(model_name='swipeusage', name='can_undo', field=models.BooleanField(default=False)),
        migrations.CreateModel(
            name='SlotSpin',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('last_spin_at', models.DateTimeField(blank=True, null=True)),
                ('lucky_next', models.BooleanField(default=False)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='slot_spin', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.RunPython(mark_old_fees_used, migrations.RunPython.noop),
    ]
