---
name: s4-validation-perf-baseline
description: "性能基线建立与回归守门：S4 建立/更新基线、CI 门禁回归检测、S6 持续监控告警、复盘量化回写。"
version: "1.0.0"
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [performance, baseline, regression, s4, s6, gate]
    category: validation
    skill_type: tool
    requires_toolsets: [terminal, file, python]
    local_override: true
---

# Performance Baseline Skill

> **职责**：性能基线全生命周期 — S4 建立/更新、S4 CI 门禁回归检测、S6 持续监控告警、S6 复盘量化回写

## When to Use

- **S4 验收阶段结束前**：首次建立基线、或重大架构变更后重设基线
- **每次 CI 构建**：自动跑基准测试，对比基线判定 PASS/WARN/FAIL
- **S6 运维巡检/复盘**：长周期趋势分析、容量规划输入、回归事件复盘
- **发布前门禁（S5）**：`ci-cd` 调用 `--action gate` 作为性能门禁一环

## Don't Use For

- 功能正确性测试（见 `test-runner`、`quality-gate`）
- 单次临时压测（用 `locust`/`k6` 手工脚本）
- 业务指标监控（见 `operations-monitor` 若存在）

## Procedure

### 1. 定义基线指标模板（`benchmarks.yaml`）

```yaml
# .hermes/perf/benchmarks.yaml
suite: "api-latency"
warmup_runs: 10
measure_runs: 100
concurrency: [1, 10, 50, 100]
environment: "staging"  # 必须与基线建立环境一致

endpoints:
  - name: "api_search_books"
    method: "GET"
    path: "/api/v1/books/search"
    params: {q: "python", limit: 20}
    targets:
      throughput_rps: 200
      p50_ms: 80
      p90_ms: 150
      p99_ms: 200
      error_rate: 0.001
      cpu_percent: 60
      mem_mb: 512
  - name: "api_download_audio"
    method: "GET"
    path: "/api/v1/books/{id}/download"
    targets:
      throughput_rps: 50
      p50_ms: 150
      p90_ms: 400
      p99_ms: 500
      error_rate: 0.0005

thresholds:
  # 核心路径：5% 退化即 FAIL；非核心：15%
  core: {max_regression: 5, alert: 3}
  non_core: {max_regression: 15, alert: 10}
  new_endpoint: {establish_only: true}
```

### 2. 建立/更新基线（S4 `--action establish`）

```bash
# 入口
hermes skill run s4-validation/perf-baseline --action establish \
  --spec .hermes/perf/benchmarks.yaml \
  --output .hermes/perf/baseline-$(date +%Y%m%dT%H%M%SZ).json

# 内部执行 establish_baseline():
# 1) 跑基准套件（封装 locust/k6/hey/wrk，统一 JSON 输出）
# 2) 聚合统计 → baseline.json（含 p50/p90/p99/吞吐/错误率/资源占用）
# 3) 生成 baseline-report.md（含 Git commit、环境、指标表、趋势对比）
# 4) Git 归档：提交 baseline-<timestamp>.json + baseline-latest.json 软链接
```

**判定**：
- 全部指标 ≤ 目标值 → **PASS**，写入基线库
- 任一指标 > 目标值 → **FAIL**，阻断，输出差异报告

### 3. CI 门禁回归检测（S4 `--action gate` / S5 发布门禁）

```bash
# CI 集成
hermes skill run s4-validation/perf-baseline --action gate \
  --baseline .hermes/perf/baseline-latest.json \
  --spec .hermes/perf/benchmarks.yaml \
  --threshold-profile core  # core/non_core/new_endpoint

# .github/workflows/perf-gate.yml
jobs:
  perf-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Performance Regression Gate
        run: |
          hermes skill run s4-validation/perf-baseline --action gate \
            --baseline .hermes/perf/baseline-latest.json \
            --spec .hermes/perf/benchmarks.yaml \
            --threshold-profile core
      - name: Upload Perf Report
        uses: actions/upload-artifact@v4
        with:
          name: perf-report
          path: .hermes/perf/reports/gate-*.json
```

**退出码**：
- `0` = PASS（全指标 ≤ 阈值）
- `1` = WARN（有指标触发 alert 阈值但未达 FAIL）
- `2` = FAIL（任一指标 ≥ max_regression 阈值）

### 4. S6 持续监控与告警（`--action monitor`）

```bash
# 定时任务（cron / GH Actions schedule / K8s CronJob）
hermes skill run s4-validation/perf-baseline --action monitor \
  --baseline .hermes/perf/baseline-latest.json \
  --spec .hermes/perf/benchmarks.yaml \
  --window "5m" \
  --alert-webhook "https://hooks.slack.com/xxx"

# 告警规则：
# - 任一指标连续 3 个窗口 > 1.2× 基线 → P1 告警
# - 错误率 > 1% → P0 告警
# 产出：monitor-<timestamp>.json
```

### 5. 复盘量化回写（S6 `--action retro` → `pipeline-stage-guard`）

```bash
# 迭代复盘自动生成性能章节
hermes skill run s4-validation/perf-baseline --action retro \
  --since "2026-09-01" --until "2026-09-26" \
  --output reports/perf-retro-20260926.md
```

**产出模板**（自动嵌入 `pipeline-stage-guard` 复盘报告）：

```markdown
## 性能指标趋势（2026-09-01 ~ 2026-09-26）

| 场景 | 基线 P99 | 当前 P99 | 变化 | 趋势 | 动作 |
|------|---------|---------|------|------|------|
| api_search_books | 200ms | 210ms | +5% | ↗️ 微升 | 关注，下版本优化索引 |
| api_download_audio | 500ms | 480ms | -4% | ↘️ 优化 | CDN 缓存生效 |

**关键发现**：
- 搜索接口 P99 连续 3 周微升，累计 +12%，建议下迭代纳入优化任务
- 下载接口 CDN 生效，吞吐提升 18%

**回写 S5 基线建议**：
- 将 `api_search_books` P99 目标从 200ms 调整为 180ms（倒逼优化）
- 新增 `api_recommend` 场景基线（下版本新功能）
```

### 6. 基线库管理与升级流程

```
.hermes/perf/
├── benchmarks.yaml              # 指标定义（版本控制，入 Git）
├── baseline-latest.json         # 当前生效基线（软链接）
├── baseline-20260926.json       # 历史快照
├── baseline-20260925.json
└── reports/
    ├── gate-20260926-1430.json  # CI 门禁报告
    ├── monitor-20260926-0600.json
    └── retro-20260926.md        # 复盘章节
```

**升级基线**（PR 通过门禁 + 审核确认）：
```bash
hermes skill run s4-validation/perf-baseline --action promote \
  --from baseline-20260926.json
# 更新 baseline-latest.json 软链接，Git 提交
```

## Output

| 产物 | 路径 | 用途 |
|------|------|------|
| 基线定义 | `.hermes/perf/benchmarks.yaml` | 版本控制，指标单一事实源 |
| 当前基线 | `.hermes/perf/baseline-latest.json` | 门禁/监控/复盘的比对基准 |
| 历史基线 | `.hermes/perf/baseline-*.json` | 可追溯、可回滚 |
| 门禁报告 | `.hermes/perf/reports/gate-*.json` | CI 判定证据 |
| 监控报告 | `.hermes/perf/reports/monitor-*.json` | S6 告警证据 |
| 复盘章节 | `reports/perf-retro-*.md` | 嵌入 `pipeline-stage-guard` 复盘 |

## Verification

- `benchmarks.yaml` 语法校验通过（`yamllint`）
- CI 门禁在基线 ± 阈值内稳定 PASS
- 监控告警无误报（连续 3 窗口规则验证）
- 复盘报告自动嵌入 `pipeline-stage-guard` 产出
- `promote` 后 `baseline-latest.json` 指向正确版本

## Pitfalls

1. **基线环境不一致**：必须在同规格环境（staging 同配置）建基线与对比
2. **冷启动干扰**：预热 `warmup_runs` 再采样，丢弃前 10% 请求
3. **指标漂移未处理**：业务增长导致合理漂移，需定期「有意识升级基线」而非盲目告警
4. **单机 vs 集群**：基线需标注部署拓扑（单实例/多副本/规格），对比时对齐
5. **数据丢失**：基线库必须纳入 Git 版本控制，禁止仅存本地
6. **阈值写死不更新**：重大重构后必须 `establish` 重设

## Integration

| 技能 | 咬合方式 |
|------|----------|
| `quality-gate` (S4) | 调用 `--action gate` 作为性能门禁一环 |
| `ci-cd` (S5) | 发布流水线集成 `--action gate`；读取 `baseline-report.md` 作为发布判据 |
| `pipeline-stage-guard` (S6) | 复盘触发 `--action retro`，报告嵌入复盘文档 |
| `context-keeper` | 同步 `baseline.json` 关键指标到 `MEMORY.md` |

## References

- [references/benchmark-methodology.md](references/benchmark-methodology.md)
- [references/regression-detection.md](references/regression-detection.md)
- [references/capacity-planning.md](references/capacity-planning.md)

## Templates

- [templates/benchmarks.yaml](templates/benchmarks.yaml)
- [templates/baseline-report.md](templates/baseline-report.md)
- [templates/perf-retro-section.md](templates/perf-retro-section.md)

## Scripts

- [scripts/run_benchmarks.py](scripts/run_benchmarks.py) —— 封装 locust/k6/hey 统一入口
- [scripts/aggregate_baseline.py](scripts/aggregate_baseline.py) —— 统计聚合生成基线
- [scripts/compare_baseline.py](scripts/compare_baseline.py) —— 基线对比判定逻辑
- [scripts/promote_baseline.py](scripts/promote_baseline.py) —— 基线升级自动化
- [scripts/gen_retro_md.py](scripts/gen_retro_md.py) —— 复盘章节生成