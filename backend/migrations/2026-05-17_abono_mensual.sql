-- Abono mensual: columnas de vigencia y vínculo Booking -> Subscription
-- Ejecutar en Supabase (Postgres) sobre la DB existente.

ALTER TABLE IF EXISTS subscriptions
  ADD COLUMN IF NOT EXISTS price_paid double precision;

ALTER TABLE IF EXISTS subscriptions
  ADD COLUMN IF NOT EXISTS purchase_date timestamptz;

ALTER TABLE IF EXISTS subscriptions
  ADD COLUMN IF NOT EXISTS valid_to date;

ALTER TABLE IF EXISTS bookings
  ADD COLUMN IF NOT EXISTS subscription_id integer;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'bookings_subscription_id_fkey'
  ) THEN
    ALTER TABLE bookings
      ADD CONSTRAINT bookings_subscription_id_fkey
      FOREIGN KEY (subscription_id)
      REFERENCES subscriptions(id)
      ON DELETE SET NULL;
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_bookings_subscription_id ON bookings(subscription_id);
