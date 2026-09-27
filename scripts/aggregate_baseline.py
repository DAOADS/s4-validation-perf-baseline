#!/usr/bin/env python3
"""
统计聚合生成基线
hermes skill run s4-validation/perf-baseline --action establish --spec benchmarks.yaml --output baseline.json
"""

import argparse
import json
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, List

import yaml


def load_benchmarks(spec_path: str) -> Dict[str, Any]:
    with open(spec_path, 'r') as f:
        return yaml.safe_load(f)


def run_benchmarks_tool(spec: Dict[str, Any]) -> Dict[str, Any]:
    """运行基准测试工具，返回原始结果"""
    # 这里调用 run_benchmarks.py 或直接运行 hey/k6
    # 简化实现：返回模拟数据
    results = {
        'suite': spec['suite'],
        'endpoints': []
    }
    
    for endpoint in spec['endpoints']:
        for concurrency in spec.get('concurrency', [1, 10, 50, 100]):
            # 实际应运行 hey/k6 并解析
            # 这里模拟
            results['endpoints'].append({
                'name': endpoint['name'],
                'concurrency': concurrency,
                'raw_runs': [],  # 原始每次运行数据
                'aggregated': {
                    'throughput_rps': endpoint['targets'].get('throughput_rps', 0) * 0.95,
                    'p50_ms': endpoint['targets'].get('p50_ms', 0) * 1.02,
                    'p90_ms': endpoint['targets'].get('p90_ms', 0) * 1.05,
                    'p99_ms': endpoint['targets'].get('p99_ms', 0) * 1.1,
                    'error_rate': endpoint['targets'].get('error_rate', 0) * 1.2,
                    'cpu_percent': endpoint['targets'].get('cpu_percent', 0) * 0.9,
                    'mem_mb': endpoint['targets'].get('mem_mb', 0) * 1.05,
                }
            })
    
    return results


def aggregate_results(raw_results: Dict[str, Any]) -> Dict[str, Any]:
    """聚合原始结果生成基线"""
    aggregated = {
        'suite': raw_results['suite'],
        'timestamp': '',  # 调用者填充
        'git_commit': '',  # 调用者填充
        'environment': 'staging',
        'endpoints': []
    }
    
    for ep in raw_results['endpoints']:
        # 实际聚合逻辑：计算 percentiles、平均值等
        agg = ep['aggregated']
        aggregated['endpoints'].append({
            'name': ep['name'],
            'concurrency': ep['concurrency'],
            'metrics': agg,
            'targets': ep.get('targets', {})
        })
    
    return aggregated


def check_targets(aggregated: Dict[str, Any], spec: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """检查是否达到目标值"""
    all_pass = True
    failures = []
    
    for ep in aggregated['endpoints']:
        targets = ep.get('targets', {})
        metrics = ep['metrics']
        
        for metric, target in targets.items():
            if metric not in metrics:
                continue
            actual = metrics[metric]
            
            # 判定：吞吐越大越好，其他越小越好
            if metric == 'throughput_rps':
                if actual < target:
                    all_pass = False
                    failures.append(f"{ep['name']}: {metric}={actual:.1f} < target={target}")
            else:
                if actual > target:
                    all_pass = False
                    failures.append(f"{ep['name']}: {metric}={actual:.1f} > target={target}")
    
    return all_pass, failures


def generate_baseline_report(aggregated: Dict[str, Any], spec: Dict[str, Any], pass_fail: Tuple[bool, List[str]]) -> str:
    """生成基线报告 Markdown"""
    all_pass, failures = pass_fail
    
    lines = [
        "# Performance Baseline Report",
        f"Suite: {aggregated['suite']}",
        f"Timestamp: {aggregated.get('timestamp', 'N/A')}",
        f"Git Commit: {aggregated.get('git_commit', 'N/A')}",
        f"Environment: {aggregated.get('environment', 'staging')}",
        f"Status: **{'PASS' if all_pass else 'FAIL'}**",
        "",
        "## Endpoint Metrics",
        ""
    ]
    
    for ep in aggregated['endpoints']:
        lines.append(f"### {ep['name']} (concurrency={ep['concurrency']})")
        lines.append("")
        lines.append("| Metric | Target | Actual | Status |")
        lines.append("|--------|--------|--------|--------|")
        
        for metric, target in ep.get('targets', {}).items():
            actual = ep['metrics'].get(metric, 'N/A')
            if metric == 'throughput_rps':
                status = '✅' if actual >= target else '❌'
            else:
                status = '✅' if actual <= target else '❌'
            lines.append(f"| {metric} | {target} | {actual} | {status} |")
        
        lines.append("")
    
    if failures:
        lines.append("## Failures")
        for f in failures:
            lines.append(f"- {f}")
    
    return '\n'.join(lines)


def establish_baseline(spec_path: str, output_path: str):
    """建立基线主流程"""
    spec = load_benchmarks(spec_path)
    
    # 1. 运行基准测试
    raw = run_benchmarks_tool(spec)
    
    # 2. 聚合结果
    baseline = aggregate_results(raw)
    
    # 3. 检查目标
    all_pass, failures = check_targets(baseline, spec)
    
    # 4. 生成报告
    report = generate_baseline_report(baseline, spec, (all_pass, failures))
    
    # 5. 写入文件
    with open(output_path, 'w') as f:
        json.dump(baseline, f, indent=2)
    
    report_path = output_path.replace('.json', '-report.md')
    with open(report_path, 'w') as f:
        f.write(report)
    
    print(f"Baseline written to {output_path}")
    print(f"Report written to {report_path}")
    print(f"Status: {'PASS' if all_pass else 'FAIL'}")
    
    if not all_pass:
        for f in failures:
            print(f"  FAIL: {f}")
        sys.exit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--spec', required=True, help='Path to benchmarks.yaml')
    parser.add_argument('--output', required=True, help='Output baseline JSON path')
    args = parser.parse_args()
    
    establish_baseline(args.spec, args.output)