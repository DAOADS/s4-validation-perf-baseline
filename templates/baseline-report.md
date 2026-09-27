# 性能基线报告模板
# 自动生成：hermes skill run s4-validation/perf-baseline --action establish

---
title: "Performance Baseline Report"
suite: "{{suite}}"
timestamp: "{{timestamp_iso}}"
git_commit: "{{git_commit}}"
environment: "{{environment}}"
baseline_version: "{{baseline_version}}"

---

## 基线概览

| 指标 | 值 |
|------|-----|
| 测试套件 | {{suite}} |
| 运行时间 | {{timestamp}} |
| Git 提交 | {{git_commit}} |
| 环境 | {{environment}} |
| 状态 | **{{status}}** |

## 端点指标详情

{% for endpoint in endpoints %}
### {{endpoint.name}} ({{endpoint.method}} {{endpoint.path}})

| 指标 | 目标值 | 实测值 | 状态 |
|------|--------|--------|------|
| 吞吐 (RPS) | {{endpoint.targets.throughput_rps}} | {{endpoint.actual.throughput_rps}} | {{endpoint.status.throughput}} |
| P50 延迟 (ms) | {{endpoint.targets.p50_ms}} | {{endpoint.actual.p50_ms}} | {{endpoint.status.p50}} |
| P90 延迟 (ms) | {{endpoint.targets.p90_ms}} | {{endpoint.actual.p90_ms}} | {{endpoint.status.p90}} |
| P99 延迟 (ms) | {{endpoint.targets.p99_ms}} | {{endpoint.actual.p99_ms}} | {{endpoint.status.p99}} |
| 错误率 | {{endpoint.targets.error_rate}} | {{endpoint.actual.error_rate}} | {{endpoint.status.error_rate}} |
| CPU 占用 (%) | {{endpoint.targets.cpu_percent}} | {{endpoint.actual.cpu_percent}} | {{endpoint.status.cpu}} |
| 内存 (MB) | {{endpoint.targets.mem_mb}} | {{endpoint.actual.mem_mb}} | {{endpoint.status.mem}} |

{% endfor %}

## 判定结果

- **总体状态**: {{overall_status}}
- **通过项**: {{passed_count}}/{{total_count}}
- **失败项**: {{failed_list}}

## 趋势对比（如有历史基线）

| 端点 | 指标 | 上一基线 | 当前基线 | 变化 |
|------|------|----------|----------|------|
{% for trend in trends %}
| {{trend.endpoint}} | {{trend.metric}} | {{trend.previous}} | {{trend.current}} | {{trend.change_pct}}% |
{% endfor %}

## 备注

- 基线建立环境必须与后续对比环境一致
- 重大架构变更后需重新建立基线
- 此报告自动归档至 `.hermes/perf/reports/`