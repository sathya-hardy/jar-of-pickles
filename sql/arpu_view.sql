-- arpu_view.sql
-- ARPPU (Average Revenue Per Paying User) per month.
-- Uses paying customers only (excludes free tier) for actionable pricing insight.
--
-- IMPORTANT: Replace PROJECT_ID with your actual GCP project ID.

CREATE OR REPLACE VIEW `PROJECT_ID.stripe_mrr.arppu_monthly` AS
SELECT
  month,
  mrr_amount,
  paying_customers,
  CASE
    WHEN paying_customers > 0 THEN ROUND(mrr_amount / paying_customers, 2)
    ELSE 0
  END AS arppu
FROM
  `PROJECT_ID.stripe_mrr.mrr_monthly`
ORDER BY
  month ASC;
