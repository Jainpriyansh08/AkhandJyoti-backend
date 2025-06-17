from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('bookings', '0004_add_final_amount'),
    ]

    operations = [
        migrations.RunSQL(
            sql='ALTER TABLE bookings_bookingorder DROP CONSTRAINT bookings_bookingorder_pkey CASCADE;',
            reverse_sql='ALTER TABLE bookings_bookingorder ADD CONSTRAINT bookings_bookingorder_pkey PRIMARY KEY (id);'
        ),
        migrations.RunSQL(
            sql='ALTER TABLE bookings_bookingorder DROP COLUMN id;',
            reverse_sql='ALTER TABLE bookings_bookingorder ADD COLUMN id uuid NOT NULL DEFAULT uuid_generate_v4();'
        ),
        migrations.RunSQL(
            sql='ALTER TABLE bookings_bookingorder ADD COLUMN id SERIAL PRIMARY KEY;',
            reverse_sql='ALTER TABLE bookings_bookingorder DROP COLUMN id;'
        ),
    ] 