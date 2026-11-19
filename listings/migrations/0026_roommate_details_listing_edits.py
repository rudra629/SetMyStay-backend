from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('listings', '0025_herobannerad'),
    ]

    operations = [
        migrations.AddField(
            model_name='property',
            name='roommate_details',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='property',
            name='edited_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name='ListingEdit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('changes', models.JSONField(default=list)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('cleared', models.BooleanField(default=False)),
                ('cleared_at', models.DateTimeField(blank=True, null=True)),
                ('cleared_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='cleared_listing_edits', to=settings.AUTH_USER_MODEL)),
                ('editor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='listing_edits', to=settings.AUTH_USER_MODEL)),
                ('property', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='edits', to='listings.property')),
            ],
            options={'ordering': ['-created_at']},
        ),
    ]
