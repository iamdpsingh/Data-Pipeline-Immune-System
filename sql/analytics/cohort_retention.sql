-- Customer Monthly Cohort Retention Analysis
SELECT
  DATE_TRUNC(c.signup_date, MONTH) AS signup_cohort,
  DATE_DIFF(DATE(o.order_timestamp), c.signup_date, MONTH) AS months_since_signup,
  COUNT(DISTINCT o.customer_id) AS active_cohort_customers,
  SUM(o.amount_usd) AS cohort_gross_revenue
FROM `data-pipeline-immune-system.dpis_silver_dev.customers` c
JOIN `data-pipeline-immune-system.dpis_silver_dev.orders` o
  ON c.customer_id = o.customer_id
GROUP BY 1, 2
ORDER BY 1, 2;
