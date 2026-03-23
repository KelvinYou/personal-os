#!/usr/bin/env python3
import os
import yaml
from pathlib import Path

def analyze_daily_logs(log_dir):
    """
    伪代码：分析日记并执行逻辑引擎告警。
    """
    recent_sleep_quality = []
    weekly_spend = 0.0
    
    print("[Status: OK] System check started.")
    
    for file_path in sorted(Path(log_dir).glob("*-template.md")):
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
            # 解析 YAML 前缀
            if content.startswith("---"):
                try:
                    parts = content.split("---")
                    if len(parts) >= 3:
                        yaml_part = parts[1]
                        metadata = yaml.safe_load(yaml_part)
                        
                        # 关联性检查
                        deep_work = metadata.get("deep_work_hours", 0)
                        if deep_work is not None and deep_work < 4.0:
                            print(f"[Warning] {file_path.name}: Deep work hours ({deep_work}) < 4. Check for Interruptions or Low Energy.")
                            
                        # 财务对账
                        spends = metadata.get("daily_spend", [])
                        if spends:
                            for item in spends:
                                amount = item.get("amount", 0)
                                if amount is not None:
                                    weekly_spend += float(amount)
                                
                        # 健康预警 (简化提取)
                        sleep = metadata.get("sleep_quality", "Fair")
                        recent_sleep_quality.append(sleep)
                except Exception as e:
                    print(f"[Critical] Failed to parse metadata in {file_path.name}: {e}")
                    
    # 健康预警逻辑
    if len(recent_sleep_quality) >= 3 and all(s == 'Poor' for s in recent_sleep_quality[-3:]):
         print("[Critical] Health Warning: Sleep quality is 'Poor' for 3 consecutive days. REST STRONGLY ADVISED.")
         
    print(f"[Status: OK] Analysis complete. Current weekly spend sum: {weekly_spend}")

if __name__ == "__main__":
    analyze_daily_logs("../daily")
