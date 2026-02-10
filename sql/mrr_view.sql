-- mrr_view.sql
-- Monthly MRR aggregation from paid subscription invoices.
-- Amounts are stored in cents in Stripe; converted to dollars here.
--
-- IMPORTANT: Replace PROJECT_ID with your actual GCP project ID.

CREATE OR REPLACE VIEW `PROJECT_ID.stripe_mrr.mrr_monthly` AS
WITH paid_invoices AS (
  SELECT
    invoice_id,
    customer_id,
    subscription_id,
    amount_paid,
    DATE_TRUNC(DATE(period_start), MONTH) AS invoice_month
  FROM
    `PROJECT_ID.stripe_mrr.raw_invoices`
  WHERE
    status = 'paid'
    AND subscription_id IS NOT NULL
    AND amount_paid > 0
),
-- Count all customers with subscriptions (including free) per month
all_customer_months AS (
  SELECT DISTINCT
    customer_id,
    DATE_TRUNC(DATE(period_start), MONTH) AS invoice_month
  FROM
    `PROJECT_ID.stripe_mrr.raw_invoices`
  WHERE
    status = 'paid'
    AND subscription_id IS NOT NULL
)
SELECT
  p.invoice_month AS month,
  ROUND(SUM(p.amount_paid) / 100.0, 2) AS mrr_amount,
  COUNT(DISTINCT p.customer_id) AS paying_customers,
  (
    SELECT COUNT(DISTINCT a.customer_id)
    FROM all_customer_months a
    WHERE a.invoice_month = p.invoice_month
  ) AS total_customers,
  COUNT(DISTINCT p.subscription_id) AS active_subscriptions
FROM
  paid_invoices p
GROUP BY
  p.invoice_month
ORDER BY
  p.invoice_month ASC;
