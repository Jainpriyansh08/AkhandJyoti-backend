from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('bookings', '0003_alter_bookingmember_unique_together'),
    ]

    operations = [
        migrations.RenameField(
            model_name='bookingmember',
            old_name='booking_order',
            new_name='booking',
        ),
        migrations.AddField(
            model_name='bookingorder',
            name='final_amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
            preserve_default=False,
        ),
    ] 