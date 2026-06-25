-- Payment sport/activity discriminator.
-- Nullable for legacy rows and non-sport payment types.

ALTER TABLE IF EXISTS payments
  ADD COLUMN IF NOT EXISTS activity_id integer;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'payments_activity_id_fkey'
  ) THEN
    ALTER TABLE payments
      ADD CONSTRAINT payments_activity_id_fkey
      FOREIGN KEY (activity_id)
      REFERENCES activities(id)
      ON DELETE SET NULL;
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_payments_activity_id ON payments(activity_id);
