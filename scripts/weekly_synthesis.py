#!/usr/bin/env python3
import os
import yaml
from pathlib import Path

def generate_weekly_synthesis(log_dir):
    """
    Weekly Synthesis Protocol:
    1. Scan all templates in /daily for the week.
    2. Aggregate YAML biometrics and stats.
    3. Generate the finalized prompt for the Weekly Review Agent.
    """
    total_deep_work = 0.0
    sleep_records = []
    energy_levels = []
    total_spend = 0.0
    incidents = 0
    days_logged = 0

    logs_compiled = []

    # 遍历所有的 template 文件
    for file_path in sorted(Path(log_dir).glob("*-template.md")):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                parts = content.split("---")
                if len(parts) >= 3:
                    metadata = yaml.safe_load(parts[1]) or {}
                    
                    # 聚合生命体征与工作时长 (Biometrics Aggregation)
                    deep_work = metadata.get("deep_work_hours", 0)
                    if deep_work is not None:
                        total_deep_work += float(deep_work)
                    
                    sleep = metadata.get("sleep_quality")
                    if sleep is not None:
                        sleep_records.append(sleep)
                        if sleep == "Poor":
                            incidents += 1 # Poor sleep 记入微型事故 (Micro-incident)
    
                    energy = metadata.get("energy_level")
                    if energy is not None:
                        energy_levels.append(float(energy))
    
                    # 聚合财务流 (Financials)
                    spends = metadata.get("daily_spend", [])
                    if spends:
                        for item in spends:
                            if isinstance(item, dict):
                                amount = item.get("amount", 0)
                                if amount is not None:
                                    total_spend += float(amount)
                    
                    days_logged += 1
                    # 抽样提取每日 Highlights，以降低大模型 Token 负担
                    logs_compiled.append(f"### 文件名: {file_path.name}\n```markdown\n{parts[1].strip()}\n```\n核心摘录：\n{parts[2].strip()[:400]}...\n")
        except Exception as e:
            print(f"[Warning] Failed to parse {file_path.name}: {e}")

    if days_logged == 0:
        print("[Status: Warning] No daily templates found to synthesize.")
        return

    avg_energy = sum(energy_levels) / len(energy_levels) if energy_levels else 0

    print("=========================================")
    print("[Status: OK] 🧠 WEEKLY SYNTHESIS COMPLETE")
    print("=========================================")
    print(f"- Days Logged      : {days_logged} days")
    print(f"- Total Deep Work  : {total_deep_work:.1f} hours")
    print(f"- Average Energy   : {avg_energy:.1f} / 10")
    print(f"- Sleep Incidents  : {incidents} days of 'Poor' sleep detected")
    print(f"- Total Spend      : ${total_spend:.2f}")
    print("=========================================")
    
    # 导出给 Weekly Review Agent 的 Context
    prompt_context = f"""[System Instructions]
你现在是系统配置的 `Weekly Review Agent`。
请依据这份汇总数据与日志切片，分析用户本周的行为模式，输出极客风格的《本周工程师分析报告》。要求给出核心产出总结、警报项（如失眠/高压），以及针对下周的 Action Items。

## 1. Context: 过去 7 天的宏观聚合数据 (Aggregated Metrics)
- 总专注工作时长：{total_deep_work:.1f} 小时
- 平均精力值：{avg_energy:.1f}/10
- 睡眠红色告警天数：{incidents} 天
- 总量化显性支出：${total_spend:.2f}

## 2. Context: 每日日志切片采样 (Daily Slices)
{''.join(logs_compiled)}
"""
    
    output_path = Path(log_dir).parent / "weekly_report_prompt.md"
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(prompt_context)
        print(f"\n[Action Required] 聚合报告已写入 {output_path.absolute()}")
        print("请将该文件内容直接粘贴给你的大语言模型 (ChatGPT/Claude)，生成最终长篇分析周报。")
    except Exception as e:
         print(f"[Error] Could not write report file: {e}")

if __name__ == "__main__":
    # 解析 ../daily 目录
    analyze_dir = Path(__file__).parent.parent / "daily"
    generate_weekly_synthesis(analyze_dir)
