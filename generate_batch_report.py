#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量测试报告生成器
"""

import json
import statistics
from datetime import datetime
from pathlib import Path


def load_data():
    """加载测试数据"""
    raw_file = Path("batch_test_raw_data.json")
    analysis_file = Path("batch_test_analysis.json")
    
    if not raw_file.exists():
        print("❌ 未找到测试数据文件: batch_test_raw_data.json")
        print("请先运行: python batch_test.py")
        return None, None
    
    with open(raw_file, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
    
    if analysis_file.exists():
        with open(analysis_file, 'r', encoding='utf-8') as f:
            analysis = json.load(f)
    else:
        analysis = None
    
    return raw_data, analysis


def generate_markdown_report(raw_data, analysis):
    """生成Markdown报告"""
    
    md = "# 批量测试数据分析报告 (Task 1-3 × 10次)\n\n"
    md += f"**测试日期**: {datetime.now().strftime('%Y年%m月%d日')}\n"
    md += f"**系统ID**: 2EE26A58\n"
    md += f"**测试规模**: Task 1-3 各10次，共30次测试\n\n"
    md += "---\n\n"
    
    # 执行摘要
    md += "## 📊 执行摘要\n\n"
    
    for task_id in [1, 2, 3]:
        if task_id not in analysis["tasks_analysis"]:
            continue
        
        ta = analysis["tasks_analysis"][task_id]
        et = ta["execution_time"]
        
        md += f"### Task {task_id}\n\n"
        md += f"- **测试次数**: {ta['runs']}\n"
        md += f"- **成功率**: {ta['success_rate']*100:.1f}%\n"
        md += f"- **平均时间**: {et['mean']:.2f} ± {et['stdev']:.2f}秒\n"
        md += f"- **时间范围**: [{et['min']:.2f}, {et['max']:.2f}]秒\n"
        md += f"- **中位数**: {et['median']:.2f}秒\n"
        
        td = ta["target_detection"]
        md += f"- **平均检测**: {td['mean']:.1f} ± {td['stdev']:.1f}次\n"
        
        if task_id == 3 and "obstacle_detection" in ta:
            od = ta["obstacle_detection"]
            md += f"- **障碍检测**: {od['mean']:.1f} ± {od['stdev']:.1f}次\n"
        
        md += "\n"
    
    md += "---\n\n"
    
    # 详细数据表格
    md += "## 📈 详细测试数据\n\n"
    
    for task_id in [1, 2, 3]:
        task_data = [r for r in raw_data if r['task_id'] == task_id]
        if not task_data:
            continue
        
        md += f"### Task {task_id} - 所有测试记录\n\n"
        md += "| 测试# | 执行时间(秒) | 目标检测 | "
        if task_id == 3:
            md += "障碍检测 | "
        md += "状态 |\n"
        
        md += "|-------|-------------|---------|"
        if task_id == 3:
            md += "---------|"
        md += "------|\n"
        
        for r in task_data:
            md += f"| {r['test_number']} | {r['execution_time']:.2f} | {r['target_detected_count']} | "
            if task_id == 3:
                md += f"{r['obstacle_detected_count']} | "
            md += f"{'✅' if r['success'] else '❌'} |\n"
        
        md += "\n"
    
    # 统计图表
    md += "---\n\n"
    md += "## 📊 统计分析\n\n"
    
    # 对比表格
    md += "### 三任务对比\n\n"
    md += "| 指标 | Task 1 | Task 2 | Task 3 |\n"
    md += "|------|--------|--------|--------|\n"
    
    metrics = [
        ("平均时间", lambda ta: f"{ta['execution_time']['mean']:.2f}s"),
        ("标准差", lambda ta: f"{ta['execution_time']['stdev']:.2f}s"),
        ("最小时间", lambda ta: f"{ta['execution_time']['min']:.2f}s"),
        ("最大时间", lambda ta: f"{ta['execution_time']['max']:.2f}s"),
        ("稳定性", lambda ta: f"{(1-ta['execution_time']['stdev']/ta['execution_time']['mean'])*100:.1f}%"),
    ]
    
    for metric_name, metric_func in metrics:
        md += f"| {metric_name} | "
        for task_id in [1, 2, 3]:
            if task_id in analysis["tasks_analysis"]:
                md += f"{metric_func(analysis['tasks_analysis'][task_id])} | "
            else:
                md += "N/A | "
        md += "\n"
    
    md += "\n"
    
    # 关键发现
    md += "---\n\n"
    md += "## 🎯 关键发现\n\n"
    
    times = {tid: analysis["tasks_analysis"][tid]["execution_time"]["mean"] 
             for tid in [1, 2, 3] if tid in analysis["tasks_analysis"]}
    
    if times:  # 检查是否有数据
        fastest = min(times, key=times.get)
        slowest = max(times, key=times.get)
        
        md += f"1. **最快任务**: Task {fastest} (平均{times[fastest]:.2f}秒)\n"
        md += f"2. **最慢任务**: Task {slowest} (平均{times[slowest]:.2f}秒)\n"
    else:
        md += "❌ 无有效数据\n"
    
    if 2 in times and 1 in times:
        ratio = times[1] / times[2]
        md += f"3. **Task 2效率**: 比Task 1快 {ratio:.2f}倍\n"
    
    if 3 in times and 1 in times:
        diff = times[1] - times[3]
        md += f"4. **Task 3 vs Task 1**: Task 3{'快' if diff>0 else '慢'} {abs(diff):.2f}秒\n"
    
    # 计算变异系数
    if times:  # 只有有数据时才计算
        md += "\n### 稳定性排名\n\n"
        stability = []
        for task_id in [1, 2, 3]:
            if task_id in analysis["tasks_analysis"]:
                ta = analysis["tasks_analysis"][task_id]
                cv = ta['execution_time']['stdev'] / ta['execution_time']['mean']
                stability.append((task_id, cv, 1-cv))
        
        stability.sort(key=lambda x: x[1])  # 按变异系数排序
        
        for rank, (task_id, cv, stability_score) in enumerate(stability, 1):
            md += f"{rank}. Task {task_id}: {stability_score*100:.1f}% (CV={cv:.3f})\n"
    
    md += "\n---\n\n"
    
    # 数据可视化建议
    md += "## 📉 数据分布\n\n"
    
    for task_id in [1, 2, 3]:
        if task_id not in analysis["tasks_analysis"]:
            continue
        
        ta = analysis["tasks_analysis"][task_id]
        times = ta["execution_time"]["all_values"]
        
        md += f"### Task {task_id} 执行时间分布\n\n"
        md += "```\n"
        
        # 简单的ASCII直方图
        min_t = min(times)
        max_t = max(times)
        bins = 5
        bin_width = (max_t - min_t) / bins if max_t > min_t else 1
        
        if bin_width > 0:
            hist = [0] * bins
            for t in times:
                bin_idx = min(int((t - min_t) / bin_width), bins - 1)
                hist[bin_idx] += 1
            
            for i, count in enumerate(hist):
                bin_start = min_t + i * bin_width
                bin_end = bin_start + bin_width
                md += f"[{bin_start:.1f}-{bin_end:.1f}s]: {'█' * count} ({count})\n"
        
        md += "```\n\n"
    
    # 保存报告
    with open("批量测试分析报告.md", "w", encoding="utf-8") as f:
        f.write(md)
    
    print("✓ 报告已生成: 批量测试分析报告.md")


def generate_csv_export(raw_data, analysis):
    """生成CSV导出"""
    import csv
    
    # 汇总数据
    with open("批量测试汇总.csv", "w", encoding="utf-8-sig", newline='') as f:
        writer = csv.writer(f)
        
        # 标题
        writer.writerow(["Task", "测试次数", "成功率", "平均时间", "标准差", "最小时间", "最大时间", "中位数"])
        
        for task_id in [1, 2, 3]:
            if task_id not in analysis["tasks_analysis"]:
                continue
            
            ta = analysis["tasks_analysis"][task_id]
            et = ta["execution_time"]
            
            writer.writerow([
                f"Task {task_id}",
                ta['runs'],
                f"{ta['success_rate']*100:.1f}%",
                f"{et['mean']:.2f}",
                f"{et['stdev']:.2f}",
                f"{et['min']:.2f}",
                f"{et['max']:.2f}",
                f"{et['median']:.2f}"
            ])
    
    # 详细数据
    with open("批量测试详细数据.csv", "w", encoding="utf-8-sig", newline='') as f:
        writer = csv.writer(f)
        
        writer.writerow(["Task", "测试#", "时间戳", "执行时间", "目标检测", "障碍检测", "状态"])
        
        for r in sorted(raw_data, key=lambda x: (x['task_id'], x['test_number'])):
            writer.writerow([
                f"Task {r['task_id']}",
                r['test_number'],
                r['timestamp'],
                f"{r['execution_time']:.2f}",
                r['target_detected_count'],
                r.get('obstacle_detected_count', 0),
                "成功" if r['success'] else "失败"
            ])
    
    print("✓ CSV已导出: 批量测试汇总.csv, 批量测试详细数据.csv")


def main():
    """主函数"""
    print("正在生成批量测试分析报告...\n")
    
    raw_data, analysis = load_data()
    
    if not raw_data or not analysis:
        return
    
    # 生成Markdown报告
    generate_markdown_report(raw_data, analysis)
    
    # 生成CSV导出
    generate_csv_export(raw_data, analysis)
    
    print("\n✅ 所有报告生成完成！")
    print("\n文件清单:")
    print("  - 批量测试分析报告.md")
    print("  - 批量测试汇总.csv")
    print("  - 批量测试详细数据.csv")
    print("  - batch_test_raw_data.json")
    print("  - batch_test_analysis.json")


if __name__ == "__main__":
    main()
