#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量测试脚本 - 对Task 1-3各运行10次并统计分析
"""

import subprocess
import json
import time
import sys
from pathlib import Path
from datetime import datetime
import statistics


def run_single_test(task_id, test_number):
    """运行单次测试"""
    print(f"\n{'='*70}")
    print(f"Task {task_id} - 第 {test_number}/10 次测试")
    print(f"{'='*70}")
    
    # 确定Python路径
    venv_python = Path(".venv/Scripts/python.exe")
    if venv_python.exists():
        python_path = str(venv_python)
    else:
        python_path = "python"
    
    # 构建命令
    cmd = ["simulation.exe", python_path, "main.py", str(task_id)]
    
    start_time = time.time()
    
    try:
        # 启动进程
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        # 设置超时
        timeout_map = {1: 120, 2: 150, 3: 180}
        timeout = timeout_map.get(task_id, 120)
        
        # 等待完成
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            print(f"⚠️ 测试超时")
            return None
        
        execution_time = time.time() - start_time
        
        # 统计检测次数
        target_count = stderr.count("Red target:")
        obstacle_count = stderr.count("Yellow obstacle:") if task_id == 3 else 0
        
        # 检查是否成功（有验证码文件）
        task_file = Path(f"task_{task_id}.txt")
        success = task_file.exists()
        
        result = {
            "task_id": task_id,
            "test_number": test_number,
            "timestamp": datetime.now().isoformat(),
            "execution_time": execution_time,
            "target_detected_count": target_count,
            "obstacle_detected_count": obstacle_count,
            "success": success,
            "timeout": timeout
        }
        
        print(f"✓ 完成: {execution_time:.2f}秒, 目标检测:{target_count}次", end="")
        if task_id == 3:
            print(f", 障碍检测:{obstacle_count}次", end="")
        print()
        
        return result
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        return None


def run_batch_tests():
    """运行批量测试"""
    print("""
╔══════════════════════════════════════════════════════════════════╗
║          批量测试 - Task 1-3 各运行10次                          ║
╚══════════════════════════════════════════════════════════════════╝
    """)
    
    all_results = []
    
    # 对每个任务运行10次
    for task_id in [1, 2, 3]:
        print(f"\n{'#'*70}")
        print(f"# 开始测试 Task {task_id} (10次)")
        print(f"{'#'*70}")
        
        task_results = []
        
        for i in range(1, 11):
            result = run_single_test(task_id, i)
            if result:
                task_results.append(result)
                all_results.append(result)
            
            # 测试间隔
            if i < 10:
                time.sleep(2)
        
        # 显示该任务的统计
        if task_results:
            times = [r['execution_time'] for r in task_results]
            detections = [r['target_detected_count'] for r in task_results]
            
            print(f"\n--- Task {task_id} 统计 ---")
            print(f"完成: {len(task_results)}/10")
            print(f"时间: 平均={statistics.mean(times):.2f}s, "
                  f"标准差={statistics.stdev(times) if len(times)>1 else 0:.2f}s, "
                  f"最小={min(times):.2f}s, 最大={max(times):.2f}s")
            print(f"检测: 平均={statistics.mean(detections):.1f}次")
        
        # 任务间隔
        if task_id < 3:
            print("\n等待5秒后继续下一个任务...")
            time.sleep(5)
    
    return all_results


def analyze_results(all_results):
    """分析结果并生成报告"""
    print(f"\n{'='*70}")
    print("开始数据分析...")
    print(f"{'='*70}")
    
    # 按任务分组
    results_by_task = {1: [], 2: [], 3: []}
    for r in all_results:
        results_by_task[r['task_id']].append(r)
    
    # 统计分析
    analysis = {
        "test_date": datetime.now().isoformat(),
        "total_tests": len(all_results),
        "tasks_analysis": {}
    }
    
    for task_id in [1, 2, 3]:
        results = results_by_task[task_id]
        if not results:
            continue
        
        times = [r['execution_time'] for r in results]
        detections = [r['target_detected_count'] for r in results]
        
        task_analysis = {
            "task_id": task_id,
            "runs": len(results),
            "success_rate": sum(1 for r in results if r['success']) / len(results),
            "execution_time": {
                "mean": statistics.mean(times),
                "stdev": statistics.stdev(times) if len(times) > 1 else 0,
                "min": min(times),
                "max": max(times),
                "median": statistics.median(times),
                "all_values": times
            },
            "target_detection": {
                "mean": statistics.mean(detections),
                "stdev": statistics.stdev(detections) if len(detections) > 1 else 0,
                "min": min(detections),
                "max": max(detections),
                "all_values": detections
            }
        }
        
        if task_id == 3:
            obstacles = [r['obstacle_detected_count'] for r in results]
            task_analysis["obstacle_detection"] = {
                "mean": statistics.mean(obstacles),
                "stdev": statistics.stdev(obstacles) if len(obstacles) > 1 else 0,
                "min": min(obstacles),
                "max": max(obstacles),
                "all_values": obstacles
            }
        
        analysis["tasks_analysis"][task_id] = task_analysis
    
    # 保存原始数据
    with open("batch_test_raw_data.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    # 保存分析结果
    with open("batch_test_analysis.json", "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)
    
    print("✓ 原始数据已保存到: batch_test_raw_data.json")
    print("✓ 分析结果已保存到: batch_test_analysis.json")
    
    return analysis


def print_summary(analysis):
    """打印汇总报告"""
    print(f"\n{'='*70}")
    print("批量测试汇总报告")
    print(f"{'='*70}\n")
    
    for task_id in [1, 2, 3]:
        if task_id not in analysis["tasks_analysis"]:
            continue
        
        ta = analysis["tasks_analysis"][task_id]
        et = ta["execution_time"]
        td = ta["target_detection"]
        
        print(f"Task {task_id}:")
        print(f"  测试次数: {ta['runs']}")
        print(f"  成功率: {ta['success_rate']*100:.1f}%")
        print(f"  执行时间: {et['mean']:.2f}±{et['stdev']:.2f}秒 "
              f"[{et['min']:.2f}, {et['max']:.2f}]")
        print(f"  目标检测: {td['mean']:.1f}±{td['stdev']:.1f}次 "
              f"[{td['min']}, {td['max']}]")
        
        if task_id == 3 and "obstacle_detection" in ta:
            od = ta["obstacle_detection"]
            print(f"  障碍检测: {od['mean']:.1f}±{od['stdev']:.1f}次 "
                  f"[{od['min']}, {od['max']}]")
        print()
    
    # 对比分析
    print("对比分析:")
    times = {tid: analysis["tasks_analysis"][tid]["execution_time"]["mean"] 
             for tid in [1, 2, 3] if tid in analysis["tasks_analysis"]}
    
    fastest = min(times, key=times.get)
    slowest = max(times, key=times.get)
    
    print(f"  最快任务: Task {fastest} ({times[fastest]:.2f}秒)")
    print(f"  最慢任务: Task {slowest} ({times[slowest]:.2f}秒)")
    
    if 2 in times and 1 in times:
        ratio = times[1] / times[2]
        print(f"  Task 1 vs Task 2: Task 2快 {ratio:.2f}倍")
    
    if 3 in times and 1 in times:
        diff = times[1] - times[3]
        print(f"  Task 1 vs Task 3: Task 3{'快' if diff>0 else '慢'} {abs(diff):.2f}秒")
    
    print(f"\n总测试时间: {sum(times.values())*10/60:.1f}分钟")


def main():
    """主函数"""
    start_time = time.time()
    
    # 运行批量测试
    all_results = run_batch_tests()
    
    if not all_results:
        print("❌ 没有获取到测试数据")
        return
    
    # 分析结果
    analysis = analyze_results(all_results)
    
    # 打印汇总
    print_summary(analysis)
    
    total_time = time.time() - start_time
    print(f"\n{'='*70}")
    print(f"批量测试完成！总耗时: {total_time/60:.1f}分钟")
    print(f"{'='*70}")
    print("\n请运行以下命令生成详细分析报告:")
    print("  python generate_batch_report.py")


if __name__ == "__main__":
    main()
