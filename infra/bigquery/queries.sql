-- Sample FinOps analytics queries for llm_usage table
-- Replace {project} with your GCP project ID

-- Daily LLM spend by model
SELECT
  DATE(recorded_at) AS usage_date,
  model,
  COUNT(*) AS calls,
  SUM(input_tokens) AS input_tokens,
  SUM(output_tokens) AS output_tokens,
  ROUND(SUM(cost_usd), 6) AS total_cost_usd
FROM `{project}.finops_analytics.llm_usage`
GROUP BY 1, 2
ORDER BY 1 DESC, total_cost_usd DESC;

-- Cost per task type (token economy view)
SELECT
  task_type,
  model,
  COUNT(*) AS calls,
  ROUND(AVG(input_tokens), 1) AS avg_input_tokens,
  ROUND(AVG(output_tokens), 1) AS avg_output_tokens,
  ROUND(SUM(cost_usd), 6) AS total_cost_usd,
  ROUND(SUM(estimated_savings_usd), 2) AS total_savings_usd
FROM `{project}.finops_analytics.llm_usage`
GROUP BY 1, 2
ORDER BY total_cost_usd DESC;

-- Pipeline run ROI summary
SELECT
  pipeline_run_id,
  COUNT(*) AS llm_calls,
  ROUND(SUM(cost_usd), 6) AS pipeline_cost_usd,
  ROUND(MAX(estimated_savings_usd), 2) AS est_savings_usd,
  ROUND(SAFE_DIVIDE(MAX(estimated_savings_usd), SUM(cost_usd)), 2) AS roi
FROM `{project}.finops_analytics.llm_usage`
WHERE pipeline_run_id IS NOT NULL
GROUP BY 1
ORDER BY pipeline_cost_usd DESC;

-- Detect expensive outliers (calls above 2x median cost)
WITH stats AS (
  SELECT APPROX_QUANTILES(cost_usd, 100)[OFFSET(50)] AS median_cost
  FROM `{project}.finops_analytics.llm_usage`
)
SELECT u.*
FROM `{project}.finops_analytics.llm_usage` u, stats s
WHERE u.cost_usd > s.median_cost * 2
ORDER BY u.cost_usd DESC
LIMIT 20;
