from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('listings', '0017_admin_2fa'),
    ]

    operations = [
        migrations.AddField(
            model_name='adminloginotp',
            name='purpose',
            field=models.CharField(default='login', max_length=10),
        ),
    ]
