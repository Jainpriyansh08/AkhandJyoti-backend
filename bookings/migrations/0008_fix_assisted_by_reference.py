from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('bookings', '0007_fix_booking_member_id'),
    ]

    operations = [
        migrations.RunSQL(
            sql='ALTER TABLE bookings_bookingorder_assisted_by DROP CONSTRAINT IF EXISTS bookings_bookingorder_assisted_by_bookingorder_id_fkey;',
            reverse_sql='ALTER TABLE bookings_bookingorder_assisted_by ADD CONSTRAINT bookings_bookingorder_assisted_by_bookingorder_id_fkey FOREIGN KEY (bookingorder_id) REFERENCES bookings_bookingorder(id) DEFERRABLE INITIALLY DEFERRED;'
        ),
        migrations.RunSQL(
            sql='ALTER TABLE bookings_bookingorder_assisted_by ALTER COLUMN bookingorder_id TYPE integer USING bookingorder_id::text::integer;',
            reverse_sql='ALTER TABLE bookings_bookingorder_assisted_by ALTER COLUMN bookingorder_id TYPE uuid USING bookingorder_id::text::uuid;'
        ),
        migrations.RunSQL(
            sql='ALTER TABLE bookings_bookingorder_assisted_by ADD CONSTRAINT bookings_bookingorder_assisted_by_bookingorder_id_fkey FOREIGN KEY (bookingorder_id) REFERENCES bookings_bookingorder(id) DEFERRABLE INITIALLY DEFERRED;',
            reverse_sql='ALTER TABLE bookings_bookingorder_assisted_by DROP CONSTRAINT bookings_bookingorder_assisted_by_bookingorder_id_fkey;'
        ),
    ] 