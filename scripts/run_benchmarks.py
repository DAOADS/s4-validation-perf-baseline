#!/usr/bin/env python3
"""
运行性能基准测试
封装 locust/k6/hey/wrk 统一入口
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any


def load_benchmarks(spec_path: str) -> Dict[str, Any]:
    """加载基准测试定义"""
    import yaml
    with open(spec_path, 'r') as f:
        return yaml.safe_load(f)


def run_hey(endpoint: Dict[str, Any], runs: int, concurrency: int) -> Dict[str, Any]:
    """使用 hey 运行基准测试"""
    url = f"http://localhost:8000{endpoint['path']}"
    if endpoint.get('params'):
        params = '&'.join(f"{k}={v}" for k, v in endpoint['params'].items())
        url += f"?{params}"
    
    cmd = [
        'hey', '-n', str(runs), '-c', str(concurrency),
        '-m', endpoint['method'], url
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    return parse_hey_output(result.stdout)


def parse_hey_output(output: str) -> Dict[str, Any]:
    """解析 hey 输出"""
    # 简化解析，实际应更完善
    import re
    metrics = {}
    for line in output.split('\n'):
        if 'Requests/sec:' in line:
            metrics['throughput_rps'] = float(line.split(':')[1].strip())
        elif '50% in' in line:
            metrics['p50_ms'] = float(line.split('in')[1].split('ms')[0].strip())
        elif '90% in' in line:
            metrics['p90_ms'] = float(line.split('in')[1].split('ms')[0].strip())
        elif '99% in' in line:
            metrics['p99_ms'] = float(line.split('in')[1].split('ms')[0].strip())
        elif 'Error distribution:' in line:
            # 下一行是错误详情
            pass
    return metrics


def run_benchmarks(spec_path: str, output_path: str):
    """运行完整基准套件"""
    spec = load_benchmarks(spec_path)
    results = {
        'suite': spec['suite'],
        'timestamp': '',  # 由调用者填充
        'git_commit': '',  # 由调用者填充
        'environment': spec.get('environment', 'staging'),
        'endpoints': []
    }
    
    for endpoint in spec['endpoints']:
        print(f"Running benchmark for {endpoint['name']}...")
        # 预热
        run_hey(endpoint, spec.get('warmup_runs', 10), 1)
        # 正式测试
        for concurrency in spec.get('concurrency', [1, 10, 50, 100]):
            metrics = run_hey(endpoint, spec.get('measure_runs', 100), concurrency)
            results['endpoints'].append({
                'name': endpoint['name'],
                'concurrency': concurrency,
                'metrics': metrics,
                'targets': endpoint['targets']
            })
    
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Results written to {output_path}")
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--spec', required=True, help='Path to benchmarks.yaml')
    parser.add_argument('--output', required=True, help='Output JSON path')
    args = parser.parse_args()
    
    run_benchmarks(args.spec, args.output)