#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析报告生成器 - 从测试结果生成Markdown分析文档
"""

import json
import os
from datetime import datetime
from pathlib import Path


def load_test_results(filename="test_results.json"):
    """加载测试结果"""
    if not os.path.exists(filename):
        print(f"❌ 找不到测试结果文件: {filename}")
        return None
    
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_task_analysis(data):
    """生成单个任务的分析"""
    task_id = data["task_id"]
    test_name = data["test_name"]
    
    md = f"### Task {task_id}: {test_name}\n\n"
    
    # 基本信息
    md += "#### 📊 基本信息\n\n"
    md += f"- **测试时间**: {data['timestamp']}\n"
    md += f"- **执行时长**: {data['execution_time']:.2f}秒\n"
    md += f"- **总步数**: {data['total_steps']}\n"
    md += f"- **有效步数**: {data['effective_steps']} (非NOOP)\n"
    md += f"- **NOOP占比**: {data['noop_ratio']*100:.1f}%\n\n"
    
    # 检测性能
    md += "#### 🎯 目标检测性能\n\n"
    md += f"- **红色目标检测次数**: {data['target_detected_count']}\n"
    md += f"- **黄色障碍物检测次数**: {data['obstacle_detected_count']}\n"
    
    if data['target_detected_count'] > 0:
        detection_rate = data['target_detected_count'] / data['total_steps'] * 100
        md += f"- **目标检测率**: {detection_rate:.1f}%\n"
    md += "\n"
    
    # 控制性能
    md += "#### 🎮 控制性能\n\n"
    if data.get('convergence_steps'):
        md += f"- **收敛步数**: {data['convergence_steps']}\n"
        md += f"- **最终误差**: {data['final_error']:.2f}像素\n"
        if data['effective_steps'] > 0:
            efficiency = (data['convergence_steps'] / data['effective_steps']) * 100
            md += f"- **收敛效率**: {efficiency:.1f}%\n"
    else:
        md += "- **收敛状态**: 未收敛或未检测到目标\n"
    md += "\n"
    
    # 指令分布
    md += "#### 📈 指令分布统计\n\n"
    md += "| 指令 | 次数 | 占比 |\n"
    md += "|------|------|------|\n"
    
    cmd_stats = data.get('command_statistics', {})
    total = sum(cmd_stats.values())
    
    for cmd in ["UP", "DOWN", "LEFT", "RIGHT", "NOOP"]:
        count = cmd_stats.get(cmd, 0)
        ratio = (count / total * 100) if total > 0 else 0
        md += f"| {cmd} | {count} | {ratio:.1f}% |\n"
    
    md += "\n"
    
    # 错误信息
    if data.get('errors'):
        md += "#### ⚠️ 错误与警告\n\n"
        for error in data['errors']:
            md += f"- {error}\n"
        md += "\n"
    
    return md


def generate_comparison_table(results):
    """生成任务对比表"""
    md = "## 📊 任务性能对比\n\n"
    md += "| Task | 总步数 | 有效步数 | NOOP占比 | 收敛步数 | 最终误差 | 执行时间 |\n"
    md += "|------|--------|----------|----------|----------|----------|----------|\n"
    
    for data in results:
        task_id = data['task_id']
        total = data['total_steps']
        effective = data['effective_steps']
        noop_ratio = f"{data['noop_ratio']*100:.1f}%"
        convergence = data.get('convergence_steps', 'N/A')
        error = f"{data['final_error']:.2f}px" if data.get('final_error') else 'N/A'
        exec_time = f"{data['execution_time']:.2f}s"
        
        md += f"| Task {task_id} | {total} | {effective} | {noop_ratio} | {convergence} | {error} | {exec_time} |\n"
    
    md += "\n"
    return md


def generate_analysis_insights(results):
    """生成分析洞察"""
    md = "## 🔍 系统性能分析\n\n"
    
    # 按任务分析
    for data in results:
        task_id = data['task_id']
        
        md += f"### Task {task_id} 分析\n\n"
        
        if task_id == 0:
            md += "**任务特点**: 基础握手与身份验证\n\n"
            md += "- 此任务主要测试系统初始化和通信协议\n"
            md += "- 不涉及视觉处理和控制，步数应该很少\n"
        
        elif task_id == 1:
            md += "**任务特点**: 基础目标跟踪（无避障）\n\n"
            md += "- 使用纯比例控制策略\n"
            md += "- 理论上应该是最快收敛的任务\n"
            
            noop_ratio = data['noop_ratio']
            if noop_ratio > 0.3:
                md += f"- ⚠️ **NOOP占比过高** ({noop_ratio*100:.1f}%)，可能表示控制阈值设置过严\n"
            elif noop_ratio < 0.1:
                md += f"- ✓ **NOOP占比合理** ({noop_ratio*100:.1f}%)，控制效率较高\n"
            
            if data.get('convergence_steps'):
                conv = data['convergence_steps']
                eff = data['effective_steps']
                if conv / eff < 0.5:
                    md += f"- ✓ **快速收敛**，在有效步数的{conv/eff*100:.0f}%内达到目标\n"
                else:
                    md += f"- ⚠️ **收敛较慢**，可能需要优化控制参数\n"
        
        elif task_id == 2:
            md += "**任务特点**: 精确控制（无避障）\n\n"
            md += "- 使用保守的分段比例控制\n"
            md += "- 重点是精度而非速度\n"
            
            if data.get('final_error') and data['final_error'] < 2.0:
                md += f"- ✓ **高精度控制**，最终误差仅{data['final_error']:.2f}像素\n"
            elif data.get('final_error') and data['final_error'] < 5.0:
                md += f"- ✓ **精度良好**，最终误差{data['final_error']:.2f}像素\n"
            else:
                md += f"- ⚠️ **精度待提升**，最终误差{data.get('final_error', 'N/A')}像素\n"
        
        elif task_id == 3:
            md += "**任务特点**: 避障目标跟踪（最复杂）\n\n"
            md += "- 使用势场法 + 智能绕行策略\n"
            md += "- 需要平衡目标吸引力和障碍物斥力\n"
            
            obs_count = data['obstacle_detected_count']
            total_steps = data['total_steps']
            
            if obs_count > 0:
                md += f"- ✓ **成功检测障碍物** ({obs_count}次，{obs_count/total_steps*100:.1f}%的步数)\n"
                
                if data.get('convergence_steps'):
                    md += f"- ✓ **避障成功**，在{data['convergence_steps']}步内完成目标跟踪\n"
                else:
                    md += f"- ⚠️ **可能陷入局部最优**，未能在规定步数内收敛\n"
            else:
                md += f"- ℹ️ 本次测试未遇到障碍物，或障碍物未被检测到\n"
        
        md += "\n"
    
    return md


def generate_recommendations(results):
    """生成优化建议"""
    md = "## 💡 优化建议\n\n"
    
    # 分析所有任务的共性问题
    avg_noop_ratio = sum(r['noop_ratio'] for r in results) / len(results)
    
    md += "### 控制策略优化\n\n"
    
    if avg_noop_ratio > 0.25:
        md += "1. **降低NOOP占比**\n"
        md += f"   - 当前平均NOOP占比: {avg_noop_ratio*100:.1f}%\n"
        md += "   - 建议: 适当放宽控制阈值，减少无效等待\n"
        md += "   - 修改位置: `send_control_command()` 函数的 `adjusted_threshold` 参数\n\n"
    
    # 分析收敛性能
    converged_tasks = [r for r in results if r.get('convergence_steps')]
    if converged_tasks:
        avg_convergence = sum(r['convergence_steps'] for r in converged_tasks) / len(converged_tasks)
        md += "2. **提高收敛速度**\n"
        md += f"   - 当前平均收敛步数: {avg_convergence:.0f}\n"
        md += "   - 建议: 在远距离阶段增大吸引力系数\n"
        md += "   - 修改位置: `calculate_control_vector()` 中的 `attraction_force` 参数\n\n"
    
    # Task 3 特定建议
    task3_results = [r for r in results if r['task_id'] == 3]
    if task3_results:
        task3 = task3_results[0]
        if task3['obstacle_detected_count'] > 0:
            md += "3. **优化避障策略**\n"
            md += "   - 当前使用势场法 + 智能绕行\n"
            md += "   - 建议: 根据障碍物位置动态调整安全区域大小\n"
            md += "   - 考虑: 实现路径记忆，避免重复探索同一区域\n\n"
    
    md += "### 图像处理优化\n\n"
    md += "1. **颜色检测鲁棒性**\n"
    md += "   - 当前使用固定HSV阈值\n"
    md += "   - 建议: 实现自适应阈值调整，应对不同光照条件\n\n"
    
    md += "2. **形态学操作优化**\n"
    md += "   - 当前使用5x5卷积核\n"
    md += "   - 建议: 根据图像分辨率动态调整核大小\n\n"
    
    return md


def generate_markdown_report(results, output_file="analysis.md"):
    """生成完整的Markdown分析报告"""
    
    md = "# 视觉伺服控制系统 - 性能测试与分析报告\n\n"
    md += f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    md += "---\n\n"
    
    # 目录
    md += "## 📑 目录\n\n"
    md += "1. [测试概述](#测试概述)\n"
    md += "2. [测试用例与工况设计](#测试用例与工况设计)\n"
    md += "3. [详细测试结果](#详细测试结果)\n"
    md += "4. [任务性能对比](#任务性能对比)\n"
    md += "5. [系统性能分析](#系统性能分析)\n"
    md += "6. [优化建议](#优化建议)\n"
    md += "7. [结论](#结论)\n\n"
    md += "---\n\n"
    
    # 1. 测试概述
    md += "## 📋 测试概述\n\n"
    md += "本报告对视觉伺服控制系统进行了全面的性能测试和分析，涵盖以下方面：\n\n"
    md += "- **目标跟踪精度**: 测量控制系统将目标居中的精确度\n"
    md += "- **收敛速度**: 评估系统从初始状态到达目标所需的步数\n"
    md += "- **控制效率**: 分析有效指令占比和NOOP指令频率\n"
    md += "- **避障性能**: 评估系统在存在障碍物时的导航能力\n\n"
    
    md += f"**测试任务数量**: {len(results)}\n\n"
    for r in results:
        md += f"- Task {r['task_id']}: {r['test_name']}\n"
    md += "\n---\n\n"
    
    # 2. 测试用例与工况设计
    md += "## 🎯 测试用例与工况设计\n\n"
    
    md += "### Task 0: 姓名验证\n\n"
    md += "**测试目标**: 验证系统握手协议和基础通信功能\n\n"
    md += "**工况设置**:\n"
    md += "- 无视觉处理\n"
    md += "- 仅测试协议通信\n"
    md += "- 预期步数: < 10步\n\n"
    md += "**评价指标**:\n"
    md += "- 通信成功率\n"
    md += "- 响应时间\n\n"
    
    md += "### Task 1: 基础目标跟踪\n\n"
    md += "**测试目标**: 评估纯比例控制策略的跟踪性能\n\n"
    md += "**工况设置**:\n"
    md += "- 单一红色目标\n"
    md += "- 无障碍物干扰\n"
    md += "- 控制策略: 直接比例控制（`vx = dx`, `vy = dy`）\n"
    md += "- 控制阈值: 1.0像素\n\n"
    md += "**评价指标**:\n"
    md += "- 总步数（越少越好）\n"
    md += "- 收敛速度\n"
    md += "- 最终误差\n"
    md += "- NOOP占比（应较低）\n\n"
    
    md += "### Task 2: 精确控制\n\n"
    md += "**测试目标**: 评估保守控制策略的精度表现\n\n"
    md += "**工况设置**:\n"
    md += "- 单一红色目标\n"
    md += "- 无障碍物干扰\n"
    md += "- 控制策略: 五段式保守比例控制\n"
    md += "  - 远距离(>100px): gain=1.5\n"
    md += "  - 中远距离(50-100px): gain=1.0\n"
    md += "  - 中距离(25-50px): gain=0.6\n"
    md += "  - 近距离(10-25px): gain=0.4\n"
    md += "  - 极近距离(<10px): gain=0.25\n"
    md += "- 控制阈值: 1.5像素\n\n"
    md += "**评价指标**:\n"
    md += "- 最终误差（应 < 2像素）\n"
    md += "- 过冲情况（应无过冲）\n"
    md += "- 步数（可接受较多步数换取精度）\n\n"
    
    md += "### Task 3: 避障目标跟踪\n\n"
    md += "**测试目标**: 评估势场法避障策略的综合性能\n\n"
    md += "**工况设置**:\n"
    md += "- 红色目标 + 黄色障碍物\n"
    md += "- 控制策略: 人工势场法\n"
    md += "  - 目标吸引力场\n"
    md += "  - 障碍物斥力场\n"
    md += "  - 智能绕行策略（基于叉积判断绕行方向）\n"
    md += "- 安全区域: 150像素正方形\n"
    md += "- 三阶段控制:\n"
    md += "  - 远距离(>150px): 快速接近模式\n"
    md += "  - 中距离(30-150px): 平衡模式\n"
    md += "  - 近距离(<30px): 精确微调模式\n\n"
    md += "**评价指标**:\n"
    md += "- 避障成功率\n"
    md += "- 总步数\n"
    md += "- 障碍物检测率\n"
    md += "- 收敛性能\n"
    md += "- 路径效率\n\n"
    
    md += "---\n\n"
    
    # 3. 详细测试结果
    md += "## 📊 详细测试结果\n\n"
    
    for data in results:
        md += generate_task_analysis(data)
        md += "---\n\n"
    
    # 4. 任务性能对比
    md += generate_comparison_table(results)
    md += "---\n\n"
    
    # 5. 系统性能分析
    md += generate_analysis_insights(results)
    md += "---\n\n"
    
    # 6. 优化建议
    md += generate_recommendations(results)
    md += "---\n\n"
    
    # 7. 结论
    md += "## 🎓 结论\n\n"
    md += "### 系统优势\n\n"
    
    # 分析优势
    task1_results = [r for r in results if r['task_id'] == 1]
    if task1_results and task1_results[0].get('convergence_steps'):
        md += f"1. **快速响应**: Task 1在{task1_results[0]['convergence_steps']}步内完成目标跟踪\n"
    
    task2_results = [r for r in results if r['task_id'] == 2]
    if task2_results and task2_results[0].get('final_error') and task2_results[0]['final_error'] < 5:
        md += f"2. **高精度控制**: Task 2实现了{task2_results[0]['final_error']:.2f}像素的最终误差\n"
    
    task3_results = [r for r in results if r['task_id'] == 3]
    if task3_results and task3_results[0]['obstacle_detected_count'] > 0:
        md += "3. **有效避障**: Task 3成功检测并规避障碍物\n"
    
    md += "4. **模块化设计**: 清晰的函数分离，易于维护和扩展\n"
    md += "5. **自适应控制**: 根据距离动态调整控制策略\n\n"
    
    md += "### 改进空间\n\n"
    
    # 分析改进点
    avg_noop = sum(r['noop_ratio'] for r in results) / len(results)
    if avg_noop > 0.2:
        md += f"1. **控制效率**: 平均NOOP占比{avg_noop*100:.1f}%，存在优化空间\n"
    
    unconverged = [r for r in results if not r.get('convergence_steps') and r['task_id'] > 0]
    if unconverged:
        md += f"2. **收敛保证**: {len(unconverged)}个任务未在规定时间内收敛\n"
    
    md += "3. **参数调优**: 控制参数可通过系统辨识方法优化\n"
    md += "4. **路径规划**: Task 3可引入更智能的路径规划算法\n\n"
    
    md += "### 总体评价\n\n"
    md += "本视觉伺服控制系统展现了良好的基础性能，成功实现了目标跟踪和避障功能。"
    md += "系统采用了分层控制策略，在不同任务场景下表现出较好的适应性。"
    md += "通过进一步优化控制参数和引入更先进的算法，系统性能有望进一步提升。\n\n"
    
    md += "---\n\n"
    
    # 附录
    md += "## 📎 附录\n\n"
    md += "### 测试环境\n\n"
    md += "- **操作系统**: Windows\n"
    md += "- **Python版本**: 3.x\n"
    md += "- **主要依赖**: OpenCV, NumPy\n"
    md += "- **仿真平台**: simulation.exe\n\n"
    
    md += "### 代码结构\n\n"
    md += "```\n"
    md += "main.py                 # 主控制程序\n"
    md += "├── handshake()         # 握手协议\n"
    md += "├── detect_red_target() # 红色目标检测\n"
    md += "├── detect_yellow_obstacle() # 黄色障碍物检测\n"
    md += "├── calculate_control_vector() # 控制向量计算\n"
    md += "└── send_control_command() # 指令发送\n"
    md += "```\n\n"
    
    md += "### 测试工具\n\n"
    md += "- `test_performance.py`: 自动化性能测试脚本\n"
    md += "- `generate_analysis.py`: 分析报告生成工具\n\n"
    
    # 写入文件
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(md)
    
    print(f"✓ 分析报告已生成: {output_file}")
    return output_file


def main():
    """主函数"""
    print("正在生成分析报告...")
    
    # 加载测试结果
    results = load_test_results()
    
    if not results:
        print("\n❌ 请先运行 test_performance.py 生成测试数据")
        return
    
    print(f"✓ 找到 {len(results)} 条测试记录")
    
    # 生成报告
    output_file = generate_markdown_report(results)
    
    print(f"\n{'='*60}")
    print("分析报告生成完成!")
    print(f"{'='*60}")
    print(f"文件位置: {output_file}")
    print(f"\n可以使用Markdown阅读器查看报告，或直接在VS Code中打开。")


if __name__ == "__main__":
    main()
