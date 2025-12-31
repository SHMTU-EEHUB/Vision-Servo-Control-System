#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试程序 - 为 main.py 生成测试图像
生成包含红色标靶和黄色障碍物的图像，通过子进程与 main.py 通信
"""

import cv2
import numpy as np
import subprocess
import time
import sys
import random
import argparse
from pathlib import Path
from datetime import datetime
import os


# ==========================================
# 配置参数 - 在这里修改测试参数
# ==========================================
DEFAULT_TEST_COUNT = 20  # 默认生成的测试图片数量
DEFAULT_USE_RANDOM = True  # 默认使用随机生成模式 (True) 或预定义场景 (False)
DEFAULT_INTERVAL = 1.0  # 默认测试间隔时间（秒）

# 目录配置
TEST_OUTPUT_DIR = "test_output"
TEST_IMAGES_DIR = "test_images"
DEBUG_IMAGES_DIR = "debug_images"


def setup_directories():
    """
    创建测试输出目录结构

    Returns:
        dict: 包含各个目录路径的字典
    """
    # 创建带时间戳的输出目录
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = Path(TEST_OUTPUT_DIR) / f"session_{timestamp}"

    # 创建子目录
    images_dir = session_dir / TEST_IMAGES_DIR
    debug_dir = session_dir / DEBUG_IMAGES_DIR

    # 确保目录存在
    images_dir.mkdir(parents=True, exist_ok=True)
    debug_dir.mkdir(parents=True, exist_ok=True)

    dirs = {"session": session_dir, "images": images_dir, "debug": debug_dir}

    print(f"✓ 创建测试目录: {session_dir}")
    print(f"  - 测试图像: {images_dir}")
    print(f"  - 调试图像: {debug_dir}")

    return dirs


def generate_test_image(
    width=640,
    height=480,
    red_pos=None,
    red_radius=30,
    yellow_pos=None,
    yellow_radius=40,
    filename="test_image.jpg",
):
    """
    生成测试图像

    Args:
        width: 图像宽度
        height: 图像高度
        red_pos: 红色标靶位置 (x, y)，如果为None则不绘制
        red_radius: 红色标靶半径
        yellow_pos: 黄色障碍物位置 (x, y)，如果为None则不绘制
        yellow_radius: 黄色障碍物半径
        filename: 保存的文件名

    Returns:
        str: 生成的图像文件的绝对路径
    """
    # 创建白色背景图像
    image = np.ones((height, width, 3), dtype=np.uint8) * 255

    # 绘制网格线（辅助参考）
    grid_color = (220, 220, 220)
    for x in range(0, width, 50):
        cv2.line(image, (x, 0), (x, height), grid_color, 1)
    for y in range(0, height, 50):
        cv2.line(image, (0, y), (width, y), grid_color, 1)

    # 绘制中心十字线
    center_x, center_y = width // 2, height // 2
    cv2.line(
        image, (center_x - 20, center_y), (center_x + 20, center_y), (200, 200, 200), 2
    )
    cv2.line(
        image, (center_x, center_y - 20), (center_x, center_y + 20), (200, 200, 200), 2
    )

    # 绘制黄色障碍物（先绘制，避免遮挡红色）
    if yellow_pos is not None:
        cv2.circle(image, yellow_pos, yellow_radius, (0, 255, 255), -1)  # BGR: 黄色
        cv2.circle(image, yellow_pos, yellow_radius, (0, 200, 200), 2)  # 边框
        cv2.putText(
            image,
            "YELLOW",
            (yellow_pos[0] - 30, yellow_pos[1] - yellow_radius - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 0, 0),
            2,
        )

    # 绘制红色标靶
    if red_pos is not None:
        cv2.circle(image, red_pos, red_radius, (0, 0, 255), -1)  # BGR: 红色
        cv2.circle(image, red_pos, red_radius, (0, 0, 200), 2)  # 边框
        cv2.putText(
            image,
            "TARGET",
            (red_pos[0] - 30, red_pos[1] - red_radius - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 0, 0),
            2,
        )

    # 保存图像
    filepath = Path(filename)
    cv2.imwrite(str(filepath), image)

    # 返回绝对路径
    return str(filepath.absolute())


def generate_random_scenarios(num_scenarios=10, width=640, height=480):
    """
    随机生成测试场景

    Args:
        num_scenarios: 要生成的场景数量
        width: 图像宽度
        height: 图像高度

    Returns:
        list: 包含场景配置的列表
    """
    scenarios = []

    # 边界边距（避免物体太靠近边缘）
    margin = 80

    for i in range(num_scenarios):
        scenario = {"name": f"随机场景{i+1}", "filename": f"random_test_{i+1}.jpg"}

        # 随机决定是否有红色目标（90%概率）
        if random.random() < 0.9:
            red_x = random.randint(margin, width - margin)
            red_y = random.randint(margin, height - margin)
            scenario["red_pos"] = (red_x, red_y)
            scenario["red_radius"] = random.randint(20, 40)
        else:
            scenario["red_pos"] = None

        # 随机决定是否有黄色障碍物（70%概率）
        if random.random() < 0.7:
            # 确保黄色障碍物不与红色目标重叠
            attempts = 0
            while attempts < 10:
                yellow_x = random.randint(margin, width - margin)
                yellow_y = random.randint(margin, height - margin)
                yellow_radius = random.randint(30, 80)

                # 检查是否与红色目标距离足够远
                if scenario["red_pos"] is None:
                    break

                red_x, red_y = scenario["red_pos"]
                distance = np.sqrt((yellow_x - red_x) ** 2 + (yellow_y - red_y) ** 2)
                min_distance = yellow_radius + scenario.get("red_radius", 30) + 20

                if distance > min_distance:
                    break
                attempts += 1

            scenario["yellow_pos"] = (yellow_x, yellow_y)
            scenario["yellow_radius"] = yellow_radius
        else:
            scenario["yellow_pos"] = None

        # 添加场景描述
        desc_parts = []
        if scenario["red_pos"]:
            desc_parts.append(
                f"红色@({scenario['red_pos'][0]},{scenario['red_pos'][1]})"
            )
        else:
            desc_parts.append("无红色目标")

        if scenario["yellow_pos"]:
            desc_parts.append(
                f"黄色@({scenario['yellow_pos'][0]},{scenario['yellow_pos'][1]})"
            )
        else:
            desc_parts.append("无障碍物")

        scenario["name"] = f"随机场景{i+1}: {', '.join(desc_parts)}"
        scenarios.append(scenario)

    return scenarios


def run_test_scenario(process, image_path, scenario_name):
    """
    运行单个测试场景

    Args:
        process: main.py 的子进程对象
        image_path: 测试图像的绝对路径
        scenario_name: 场景名称
    """
    print(f"\n{'='*60}")
    print(f"测试场景: {scenario_name}")
    print(f"图像路径: {image_path}")
    print(f"{'='*60}")

    # 发送图像路径到 main.py
    process.stdin.write(image_path + "\n")
    process.stdin.flush()

    # 给 main.py 一些时间处理
    time.sleep(0.5)

    # 尝试读取一行输出（控制指令）
    # 注意：这里使用非阻塞读取可能更好，但为简单起见使用 readline
    # 实际应用中可能需要更复杂的通信机制
    try:
        # 设置较短的超时，避免长时间阻塞
        pass
    except:
        pass


def main():
    """
    主测试函数
    """
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="视觉伺服控制系统测试程序")
    parser.add_argument(
        "--random",
        "-r",
        action="store_true",
        default=DEFAULT_USE_RANDOM,
        help=f"使用随机生成的测试场景 (默认: {DEFAULT_USE_RANDOM})",
    )
    parser.add_argument(
        "--count",
        "-n",
        type=int,
        default=DEFAULT_TEST_COUNT,
        help=f"随机生成的场景数量（默认：{DEFAULT_TEST_COUNT}）",
    )
    parser.add_argument(
        "--continuous", "-c", action="store_true", help="连续模式：持续生成随机场景"
    )
    parser.add_argument(
        "--interval",
        "-i",
        type=float,
        default=DEFAULT_INTERVAL,
        help=f"连续模式下每个场景的间隔时间（秒，默认：{DEFAULT_INTERVAL}）",
    )
    parser.add_argument(
        "--seed", "-s", type=int, default=None, help="随机种子（用于可重复的随机生成）"
    )
    args = parser.parse_args()

    # 设置随机种子
    if args.seed is not None:
        random.seed(args.seed)
        np.random.seed(args.seed)
        print(f"随机种子: {args.seed}")

    print("=" * 60)
    print("视觉伺服控制系统 - 测试程序")
    if args.random:
        print("模式: 随机生成")
        if args.continuous:
            print("类型: 连续随机生成")
    else:
        print("模式: 预定义场景")
    print("=" * 60)

    # 创建输出目录
    dirs = setup_directories()

    # 定义或生成测试场景
    if args.random:
        # 随机生成场景
        print(f"\n随机生成 {args.count} 个测试场景...")
        scenarios = generate_random_scenarios(num_scenarios=args.count)
    else:
        # 预定义测试场景
        scenarios = [
            {
                "name": "场景1: 红色目标在右上方",
                "red_pos": (500, 150),
                "yellow_pos": None,
                "filename": "test_scenario_1.jpg",
            },
            {
                "name": "场景2: 红色目标在左下方",
                "red_pos": (150, 350),
                "yellow_pos": None,
                "filename": "test_scenario_2.jpg",
            },
            {
                "name": "场景3: 红色目标居中，黄色障碍物在左侧",
                "red_pos": (320, 240),
                "yellow_pos": (150, 240),
                "filename": "test_scenario_3.jpg",
            },
            {
                "name": "场景4: 红色在右侧，黄色障碍物在中间偏左",
                "red_pos": (500, 240),
                "yellow_pos": (280, 240),
                "filename": "test_scenario_4.jpg",
            },
            {
                "name": "场景5: 红色在上方，黄色障碍物在中心（大面积）",
                "red_pos": (320, 100),
                "yellow_pos": (320, 300),
                "yellow_radius": 80,
                "filename": "test_scenario_5.jpg",
            },
            {
                "name": "场景6: 复杂场景 - 红色右下，黄色中间",
                "red_pos": (450, 350),
                "yellow_pos": (320, 200),
                "yellow_radius": 60,
                "filename": "test_scenario_6.jpg",
            },
        ]

    # 生成所有测试图像
    print("\n生成测试图像...")
    image_paths = []
    for scenario in scenarios:
        yellow_radius = scenario.get("yellow_radius", 40)
        # 将图像保存到测试图像目录
        filename = dirs["images"] / scenario["filename"]
        image_path = generate_test_image(
            red_pos=scenario["red_pos"],
            yellow_pos=scenario["yellow_pos"],
            yellow_radius=yellow_radius,
            filename=str(filename),
        )
        image_paths.append((scenario["name"], image_path))
        print(f"  ✓ {scenario['filename']}")

    print(f"\n已生成 {len(image_paths)} 个测试图像")

    # 启动 main.py 作为子进程
    print("\n启动 main.py 子进程...")
    try:
        # 使用 Python 解释器运行 main.py
        process = subprocess.Popen(
            [sys.executable, "main.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # 行缓冲
        )

        print("✓ main.py 已启动")

        # 读取握手协议的输出
        print("\n等待握手协议...")
        time.sleep(0.5)

        # 读取前两行（握手协议）
        try:
            line1 = process.stdout.readline().strip()
            line2 = process.stdout.readline().strip()
            print(f"  收到: {line1}")
            print(f"  收到: {line2}")
        except Exception as e:
            print(f"  警告: 读取握手协议失败: {e}")

        # 运行每个测试场景
        print("\n" + "=" * 60)
        print("开始测试场景")
        print("=" * 60)

        for i, (scenario_name, image_path) in enumerate(image_paths, 1):
            print(f"\n[场景 {i}/{len(image_paths)}] {scenario_name}")
            print(f"图像: {image_path}")

            # 发送图像路径
            process.stdin.write(image_path + "\n")
            process.stdin.flush()

            # 等待处理（使用命令行参数指定的间隔时间）
            time.sleep(args.interval)

            # 尝试读取控制指令（添加超时保护）
            try:
                # Windows: 简单的超时读取
                time.sleep(0.1)  # 给一点时间让输出到达
                command = process.stdout.readline().strip()
                
                if command:
                    print(f"→ 控制指令: {command}")
                else:
                    print("→ (未收到指令或HOLD)")
            except Exception as e:
                print(f"→ (读取指令时出错: {e})")
                # 继续执行，不中断测试

            # 检查 stderr 是否有日志输出
            # 注意：这里只是示例，实际可能需要异步读取

        print("\n" + "=" * 60)
        print("测试完成")
        print("=" * 60)
        print(f"\n所有输出文件已保存到: {dirs['session']}")
        print(f"  - 测试图像: {dirs['images']}")
        print(f"  - 调试图像: debug.jpg (当前目录)")
        print(
            f"\n注意: main.py 生成的 debug.jpg 仍在当前目录，请手动查看或移动到 {dirs['debug']}"
        )

        # 关闭子进程
        print("\n正在关闭 main.py...")
        process.stdin.close()
        process.wait(timeout=3)
        print("✓ 子进程已关闭")

    except FileNotFoundError:
        print("❌ 错误: 找不到 main.py 文件")
        return 1
    except subprocess.TimeoutExpired:
        print("⚠ 警告: 子进程未正常退出，强制终止")
        process.kill()
    except KeyboardInterrupt:
        print("\n\n用户中断测试")
        process.kill()
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback

        traceback.print_exc()
        return 1

    print("\n" + "=" * 60)
    print("测试程序结束")
    if "dirs" in locals():
        print(f"测试会话目录: {dirs['session']}")
    print("=" * 60 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
