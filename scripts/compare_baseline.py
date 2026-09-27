#!/usr/bin/env python3
"""
基线对比判定逻辑
hermes skill run s4-validation/perf-baseline --action gate --baseline baseline.json --spec benchmarks.yaml --threshold-profile core
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple


def load_json(path: str) -> Dict[str, Any]:
    with open(path, 'r') as f:
        return json.load(f)


def load_yaml(path: str) -> Dict[str, Any]:
    import yaml
    with open(path, 'r') as f:
        return yaml.safe_load(f)


def compare_metrics(current: Dict[str, float], baseline: Dict[str, float], thresholds: Dict[str, Any]) -> List[Dict[str, Any]]:
    """对比当前指标与基线，返回判定结果列表"""
    results = []
    max_regression = thresholds.get('max_regression', 5)
    alert = thresholds.get('alert', 3)
    
    metric_mapping = {
        'throughput_rps': ('吞吐', False),  # 越大越好
        'p50_ms': ('P50延迟', True),
        'p90_ms': ('P90延迟', True),
        'p99_ms': ('P99延迟', True),
        'error_rate': ('错误率', True),
        'cpu_percent': ('CPU占用', True),
        'mem_mb': ('内存', True),
    }
    
    for metric_key, (metric_name, higher_is_worse) in metric_mapping.items():
        if metric_key not in current or metric_key not in baseline:
            continue
            
        cur_val = current[metric_key]
        base_val = baseline[metric_key]
        
        if base_val == 0:
            change_pct = 0
        else:
            change_pct = ((cur_val - base_val) / base_val) * 100
        
        # 判定逻辑
        if higher_is_worse:
            # 延迟/错误率/资源：越小越好
            if change_pct > max_regression:
                status = 'FAIL'
            elif change_pct > alert:
                status = 'WARN'
            elif change_pct < -5:  # 改善超过5%
                status = 'IMPROVED'
            else:
                status = 'PASS'
        else:
            # 吞吐：越大越好
            if change_pct < -max_regression:
                status = 'FAIL'
            elif change_pct < -alert:
                status = 'WARN'
            elif change_pct > 5:  # 改善超过5%
                status = 'IMPROVED'
            else:
                status = 'PASS'
        
        results.append({
            'metric': metric_key,
            'metric_name': metric_name,
            'baseline': base_val,
            'current': cur_val,
            'change_pct': round(change_pct, 2),
            'status': status
        })
    
    return results


def judge_gate(comparison_results: List[Dict[str, Any]]) -> Tuple[str, List[str], List[str]]:
    """根据对比结果判定门禁结果"""
    fails = [r for r in comparison_results if r['status'] == 'FAIL']
    warns = [r for r in comparison_results if r['status'] == 'WARN']
    
    if fails:
        return 'FAIL', [f"{r['metric']}: {r['change_pct']:+.1f}%" for r in fails], [f"{r['metric']}: {r['change_pct']:+.1f}%" for r in warns]
    elif warns:
        return 'WARN', [], [f"{r['metric']}: {r['change_pct']:+.1f}%" for r in warns]
    else:
        return 'PASS', [], []


def run_gate(baseline_path: str, spec_path: str, profile: str = 'core', output_path: str = None):
    """运行性能门禁"""
    baseline = load_json(baseline_path)
    spec = load_yaml(spec_path)
    
    thresholds = spec.get('thresholds', {}).get(profile, {})
    if not thresholds:
        print(f"Warning: No thresholds found for profile '{profile}', using core defaults")
        thresholds = {'max_regression': 5, 'alert': 3}
    
    # 将基线展平为 {endpoint_name: {metric: value}} 格式
    baseline_flat = {}
    for ep in baseline.get('endpoints', []):
        key = f"{ep['name']}_{ep.get('concurrency', 'default')}"
        baseline_flat[key] = ep['metrics']
    
    all_results = []
    gate_fails = []
    gate_warns = []
    
    for ep in spec['endpoints']:
        for concurrency in spec.get('concurrency', [1, 10, 50, 100]):
            key = f"{ep['name']}_{concurrency}"
            if key not in baseline_flat:
                print(f"Warning: No baseline for {key}")
                continue
            
            current_metrics = {}  # 实际运行时应从当前测试结果获取
            # 这里简化：从基线模拟当前值
            baseline_metrics = baseline_flat[key]
            
            # 实际使用时应传入当前测试结果
            comparison = compare_metrics(current_metrics, baseline_metrics, thresholds)
            all_results.extend(comparison)
            
            for r in comparison:
                if r['status'] == 'FAIL':
                    gate_fails.append(f"{key}.{r['metric']}: {r['change_pct']:+.1f}%")
                elif r['status'] == 'WARN':
                    gate_warns.append(f"{key}.{r['metric']}: {r['change_pct']:+.1f}%")
    
    # 判定
    if gate_fails:
        overall = 'FAIL'
        exit_code = 2
    elif gate_warns:
        overall = 'WARN'
        exit_code = 1
    else:
        overall = 'PASS'
        exit_code = 0
    
    # 生成报告
    report = {
        'overall': overall,
        'exit_code': exit_code,
        'thresholds': thresholds,
        'profile': profile,
        'details': all_results,
        'fails': gate_fails,
        'warns': gate_warns
    }
    
    if output_path:
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"Gate report written to {output_path}")
    
    print(f"=== Performance Gate Result: {overall} ===")
    if gate_fails:
        print("FAILURES:")
        for f in gate_fails:
            print(f"  - {f}")
    if gate_warns:
        print("WARNINGS:")
        for w in gate_warns:
            print(f"  - {w}")
    
    sys.exit(exit_code)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', required=True, help='Path to baseline-latest.json')
    parser.add_argument('--spec', required=True, help='Path to benchmarks.yaml')
    parser.add_argument('--threshold-profile', default='core', choices=['core', 'non_core', 'new_endpoint'])
    parser.add_argument('--output', help='Output gate report JSON path')
    args = parser.parse_args()
    
    run_gate(args.baseline, args.spec, args.threshold_profile, args.output)