// DemandForecast rows accumulate forever in the database — every test run,
// every model, every horizon ever generated for a school stays in
// /api/forecast/history/. Rows from one Generate click share (almost)
// exactly the same `generated_at` timestamp, so grouping by that lets us
// show only the most recent coherent batch instead of a chart/table that
// mixes forecasts from unrelated runs made days or months apart.
export function latestForecastBatch(forecasts) {
  if (!forecasts || forecasts.length === 0) return [];
  const maxGeneratedAt = Math.max(
    ...forecasts.map(f => new Date(f.generated_at).getTime()));
  const cutoffMs = maxGeneratedAt - 10000; // 10s window per batch
  return forecasts.filter(f => new Date(f.generated_at).getTime() >= cutoffMs);
}
