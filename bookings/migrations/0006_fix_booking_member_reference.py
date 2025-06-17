from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('bookings', '0005_fix_booking_order_id'),
    ]

    operations = [
        migrations.RunSQL(
            sql='ALTER TABLE bookings_bookingmember DROP CONSTRAINT IF EXISTS bookings_bookingmember_pkey CASCADE;',
            reverse_sql='ALTER TABLE bookings_bookingmember ADD CONSTRAINT bookings_bookingmember_pkey PRIMARY KEY (id);'
        ),
        migrations.RunSQL(
            sql='ALTER TABLE bookings_bookingmember DROP COLUMN id;',
            reverse_sql='ALTER TABLE bookings_bookingmember ADD COLUMN id uuid NOT NULL DEFAULT uuid_generate_v4();'
        ),
        migrations.RunSQL(
            sql='ALTER TABLE bookings_bookingmember ADD COLUMN id SERIAL PRIMARY KEY;',
            reverse_sql='ALTER TABLE bookings_bookingmember DROP COLUMN id;'
        ),
        migrations.RunSQL(
            sql='ALTER TABLE bookings_bookingmember DROP CONSTRAINT IF EXISTS bookings_bookingmember_booking_id_fkey;',
            reverse_sql='ALTER TABLE bookings_bookingmember ADD CONSTRAINT bookings_bookingmember_booking_id_fkey FOREIGN KEY (booking_id) REFERENCES bookings_bookingorder(id) DEFERRABLE INITIALLY DEFERRED;'
        ),
        migrations.RunSQL(
            sql='ALTER TABLE bookings_bookingmember ALTER COLUMN booking_id TYPE integer USING booking_id::text::integer;',
            reverse_sql='ALTER TABLE bookings_bookingmember ALTER COLUMN booking_id TYPE uuid USING booking_id::text::uuid;'
        ),
        migrations.RunSQL(
            sql='ALTER TABLE bookings_bookingmember ADD CONSTRAINT bookings_bookingmember_booking_id_fkey FOREIGN KEY (booking_id) REFERENCES bookings_bookingorder(id) DEFERRABLE INITIALLY DEFERRED;',
            reverse_sql='ALTER TABLE bookings_bookingmember DROP CONSTRAINT bookings_bookingmember_booking_id_fkey;'
        ),
    ] 