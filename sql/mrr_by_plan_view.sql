-- mrr_by_plan_view.sql
-- MRR broken down by plan tier per month.
-- Uses price_id from invoice line items for historically accurate plan attribution.
--
-- IMPORTANT: Replace PROJECT_ID with your actual GCP project ID.
-- IMPORTANT: Replace the price_XXXXX values with actual Price IDs from seed_prices.py output.

CREATE OR REPLACE VIEW `PROJECT_ID.stripe_mrr.mrr_by_plan` AS
SELECT
  DATE_TRUNC(DATE(period_start), MONTH) AS month,
  CASE price_id
    WHEN 'price_XXXXX' THEN 'Free'
    WHEN 'price_XXXXX' THEN 'Standard'
    WHEN 'price_XXXXX' THEN 'Pro Plus'
    WHEN 'price_XXXXX' THEN 'Engage'
    WHEN 'price_XXXXX' THEN 'Enterprise'
    ELSE 'Unknown'
  END AS plan_name,
  ROUND(SUM(amount_paid) / 100.0, 2) AS mrr_amount
FROM
  `PROJECT_ID.stripe_mrr.raw_invoices`
WHERE
  status = 'paid'
  AND subscription_id IS NOT NULL
GROUP BY
  month,
  plan_name
ORDER BY
  month ASC,
  plan_name ASC;
