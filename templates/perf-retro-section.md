# 性能复盘章节模板
# 自动生成：hermes skill run s4-validation/perf-baseline --action retro

---
title: "Performance Retrospective Section"
period: "{{since}} ~ {{until}}"
generated_at: "{{timestamp_iso}}"
git_range: "{{git_range}}"
---

## 性能指标趋势

| 场景 | 基线 P99 | 当前 P99 | 变化 | 趋势 | 动作 |
|------|---------|---------|------|------|------|
{% for row in trends %}
| {{row.endpoint}} | {{row.baseline_p99}}ms | {{row.current_p99}}ms | {{row.change_pct}}% | {{row.trend_icon}} | {{row.action}} |
{% endfor %}

## 关键发现

{% for finding in findings %}
- {{finding}}
{% endfor %}

## 回写 S5 基线建议

| 场景 | 当前目标 | 建议目标 | 理由 |
|------|----------|----------|------|
{% for suggestion in suggestions %}
| {{suggestion.endpoint}} | {{suggestion.current_target}}ms | {{suggestion.proposed_target}}ms | {{suggestion.reason}} |
{% endfor %}

## 新增基线需求

{% for new_baseline in new_baselines %}
- **{{new_baseline.name}}**: {{new_baseline.description}}（预计 {{new_baseline.estimate}}）
{% endfor %}

## 数据来源

- 基线定义：`.hermes/perf/benchmarks.yaml`
- 当前基线：`.hermes/perf/baseline-latest.json`
- 监控数据：`.hermes/perf/reports/monitor-*.json`
- CI 门禁：`.hermes/perf/reports/gate-*.json`

---
*此章节自动嵌入 `pipeline-stage-guard` 复盘报告*