#!/usr/bin/env python3
"""
基线升级自动化
hermes skill run s4-validation/perf-baseline --action promote --from baseline-20260926.json
"""

import argparse
import json
import shutil
import sys
from pathlib import Path


def promote_baseline(from_path: str, perf_dir: str = ".hermes/perf"):
    """升级基线：将指定版本设为 latest"""
    perf_path = Path(perf_dir)
    
    from_file = Path(from_path)
    if not from_file.exists():
        # 尝试在 perf 目录下查找
        from_file = perf_path / from_path
        if not from_file.exists():
            print(f"Error: Baseline file not found: {from_path}")
            sys.exit(1)
    
    latest_link = perf_path / "baseline-latest.json"
    
    # 备份当前 latest
    if latest_link.exists():
        if latest_link.is_symlink():
            current_target = latest_link.resolve()
            backup_name = f"baseline-backup-{current_target.stem}.json"
            shutil.copy2(current_target, perf_path / backup_name)
            print(f"Backed up current baseline to {backup_name}")
        else:
            backup_name = f"baseline-backup-{latest_link.stem}.json"
            shutil.copy2(latest_link, perf_path / backup_name)
            print(f"Backed up current baseline to {backup_name}")
    
    # 更新软链接
    if latest_link.exists() or latest_link.is_symlink():
        latest_link.unlink()
    
    latest_link.symlink_to(from_file.name)
    print(f"Promoted {from_file.name} to baseline-latest.json")
    
    # 验证
    with open(latest_link, 'r') as f:
        data = json.load(f)
        print(f"New baseline: suite={data.get('suite')}, endpoints={len(data.get('endpoints', []))}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--from', dest='from_file', required=True, help='Baseline file to promote')
    parser.add_argument('--perf-dir', default='.hermes/perf', help='Performance directory')
    args = parser.parse_args()
    
    promote_baseline(args.from_file, args.perf_dir)