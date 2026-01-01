#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能测试脚本 - 用于分析视觉伺服控制系统的性能
"""

import subprocess
import os
import sys
import time
import json
import re
from pathlib import Path
from datetime import datetime
import threading
import queue


class PerformanceAnalyzer:
    """性能分析器"""

    def __init__(self, task_id, test_name="default"):
        self.task_id = task_id
        self.test_name = test_name
        self.data = {
            "task_id": task_id,
            "test_name": test_name,
            "timestamp": datetime.now().isoformat(),
            "total_steps": 0,
            "target_detected_count": 0,
            "obstacle_detected_count": 0,
            "commands": [],
            "errors": [],
            "convergence_steps": None,
            "final_error": None,
            "execution_time": 0,
        }
        self.start_time = None
        self.stderr_logs = []

    def parse_stderr_line(self, line):
        """解析stderr输出获取调试信息"""
        self.stderr_logs.append(line)
        
        # 提取检测信息
        if "Red target:" in line:
            if "None" not in line:
                self.data["target_detected_count"] += 1
        
        if "Yellow obstacle:" in line:
            if "Area:" in line and "0" not in line.split("Area:")[-1]:
                self.data["obstacle_detected_count"] += 1
        
        # 提取距离信息
        if "Target distance" in line:
            match = re.search(r"distance = ([\d.]+)", line)
            if match:
                distance = float(match.group(1))
                if distance < 5 and self.data["convergence_steps"] is None:
                    self.data["convergence_steps"] = self.data["total_steps"]
                    self.data["final_error"] = distance

    def parse_stdout_line(self, line):
        """解析stdout获取控制指令"""
        line = line.strip()
        # 调试输出
        if line and not line.startswith("[") and not line.startswith("debug"):
            sys.stderr.write(f"[Parser] Received: '{line}'\n")
            sys.stderr.flush()
        
        if line in ["UP", "DOWN", "LEFT", "RIGHT", "NOOP"]:
            self.data["commands"].append(line)
            self.data["total_steps"] += 1
            sys.stderr.write(f"[Parser] Command recognized: {line} (total: {self.data['total_steps']})\n")
            sys.stderr.flush()

    def start(self):
        """开始计时"""
        self.start_time = time.time()

    def finish(self):
        """结束计时"""
        if self.start_time:
            self.data["execution_time"] = time.time() - self.start_time
        
        # 计算统计信息
        command_counts = {}
        for cmd in self.data["commands"]:
            command_counts[cmd] = command_counts.get(cmd, 0) + 1
        
        self.data["command_statistics"] = command_counts
        
        # 计算NOOP占比
        noop_ratio = command_counts.get("NOOP", 0) / max(self.data["total_steps"], 1)
        self.data["noop_ratio"] = noop_ratio
        
        # 计算有效步数（非NOOP）
        self.data["effective_steps"] = self.data["total_steps"] - command_counts.get("NOOP", 0)
        
        return self.data

    def save_to_file(self, filename="test_results.json"):
        """保存结果到JSON文件"""
        # 加载现有数据
        results = []
        if os.path.exists(filename):
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    results = json.load(f)
            except:
                pass
        
        # 添加新数据
        results.append(self.data)
        
        # 保存
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"✓ 测试结果已保存到 {filename}")


def run_simulation_test(task_id, test_name, timeout=120):
    """
    运行仿真测试
    
    Args:
        task_id: 任务ID (0/1/2/3)
        test_name: 测试名称
        timeout: 超时时间（秒）
    
    Returns:
        PerformanceAnalyzer: 性能数据分析器
    """
    print(f"\n{'='*60}")
    print(f"开始测试: Task {task_id} - {test_name}")
    print(f"{'='*60}")
    
    # 检查必需文件
    if not os.path.exists("simulation.exe"):
        print("❌ 错误: 找不到 simulation.exe")
        return None
    
    if not os.path.exists("main.py"):
        print("❌ 错误: 找不到 main.py")
        return None
    
    # 确定Python路径
    venv_python = Path(".venv/Scripts/python.exe")
    if venv_python.exists():
        python_path = str(venv_python)
        print(f"✓ 使用虚拟环境: {python_path}")
    else:
        python_path = "python"
        print(f"⚠ 使用系统Python: {python_path}")
    
    # 创建分析器
    analyzer = PerformanceAnalyzer(task_id, test_name)
    analyzer.start()
    
    # 构建命令
    cmd = ["simulation.exe", python_path, "main.py", str(task_id)]
    
    print(f"执行命令: {' '.join(cmd)}")
    print(f"超时设置: {timeout}秒")
    print(f"-" * 60)
    
    try:
        # 启动进程
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            encoding='utf-8',
            errors='replace'
        )
        
        # 使用线程读取stderr避免阻塞
        stderr_queue = queue.Queue()
        
        def read_stderr():
            try:
                for line in process.stderr:
                    stderr_queue.put(line)
            except:
                pass
        
        stderr_thread = threading.Thread(target=read_stderr, daemon=True)
        stderr_thread.start()
        
        # 读取stdout和stderr
        start_time = time.time()
        while True:
            # 检查超时
            if time.time() - start_time > timeout:
                print(f"\n⚠ 测试超时（{timeout}秒），终止进程")
                process.terminate()
                time.sleep(1)
                if process.poll() is None:
                    process.kill()
                analyzer.data["errors"].append(f"Timeout after {timeout}s")
                break
            
            # 读取stdout
            stdout_line = process.stdout.readline()
            if stdout_line:
                analyzer.parse_stdout_line(stdout_line)
                # 实时显示关键命令
                if analyzer.data["total_steps"] % 50 == 0 and analyzer.data["total_steps"] > 0:
                    print(f"步数: {analyzer.data['total_steps']}", end='\r')
            
            # 读取stderr（非阻塞）
            try:
                while True:
                    stderr_line = stderr_queue.get_nowait()
                    analyzer.parse_stderr_line(stderr_line)
            except queue.Empty:
                pass
            
            # 检查进程是否结束
            if process.poll() is not None:
                # 读取剩余输出
                remaining_stdout = process.stdout.read()
                for line in remaining_stdout.splitlines():
                    analyzer.parse_stdout_line(line)
                
                # 读取剩余stderr
                try:
                    while True:
                        stderr_line = stderr_queue.get_nowait()
                        analyzer.parse_stderr_line(stderr_line)
                except queue.Empty:
                    pass
                
                break
            
            time.sleep(0.01)
        
        # 等待进程完全结束
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        
        # 完成分析
        results = analyzer.finish()
        
        # 显示结果摘要
        print(f"\n{'='*60}")
        print(f"测试完成 - Task {task_id}")
        print(f"{'='*60}")
        print(f"总步数: {results['total_steps']}")
        print(f"有效步数: {results['effective_steps']}")
        print(f"NOOP占比: {results['noop_ratio']*100:.1f}%")
        print(f"目标检测次数: {results['target_detected_count']}")
        print(f"障碍物检测次数: {results['obstacle_detected_count']}")
        if results['convergence_steps']:
            print(f"收敛步数: {results['convergence_steps']}")
            print(f"最终误差: {results['final_error']:.2f}像素")
        print(f"执行时间: {results['execution_time']:.2f}秒")
        print(f"指令统计: {results['command_statistics']}")
        
        return analyzer
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        analyzer.data["errors"].append(str(e))
        analyzer.finish()
        return analyzer


def main():
    """主测试函数"""
    print("""
╔══════════════════════════════════════════════════════════╗
║     视觉伺服控制系统 - 性能测试与分析工具              ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    # 测试配置
    test_configs = [
        {"task_id": 0, "name": "Task0-姓名验证", "timeout": 30},
        {"task_id": 1, "name": "Task1-基础跟踪", "timeout": 120},
        {"task_id": 2, "name": "Task2-精确控制", "timeout": 150},
        {"task_id": 3, "name": "Task3-避障跟踪", "timeout": 180},
    ]
    
    # 询问用户要测试哪些任务
    print("可用测试:")
    for i, config in enumerate(test_configs):
        print(f"  {i+1}. {config['name']}")
    print(f"  5. 运行全部测试")
    
    choice = input("\n请选择 (1-5, 默认5): ").strip()
    
    if choice in ["1", "2", "3", "4"]:
        test_list = [test_configs[int(choice)-1]]
    else:
        test_list = test_configs
    
    # 运行测试
    all_results = []
    for config in test_list:
        analyzer = run_simulation_test(
            task_id=config["task_id"],
            test_name=config["name"],
            timeout=config["timeout"]
        )
        
        if analyzer:
            analyzer.save_to_file("test_results.json")
            all_results.append(analyzer.data)
        
        # 测试间隔
        if len(test_list) > 1:
            print("\n等待5秒后继续下一个测试...")
            time.sleep(5)
    
    # 生成总结
    print(f"\n{'='*60}")
    print("所有测试完成!")
    print(f"{'='*60}")
    print(f"测试结果已保存到: test_results.json")
    print(f"请运行以下命令生成分析报告:")
    print(f"  python generate_analysis.py")


if __name__ == "__main__":
    main()
