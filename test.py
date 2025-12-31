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
from pathlib import Path


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
    cv2.imwrite(filename, image)

    # 返回绝对路径
    return str(Path(filename).absolute())


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
    print("=" * 60)
    print("视觉伺服控制系统 - 测试程序")
    print("=" * 60)

    # 定义测试场景
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
        image_path = generate_test_image(
            red_pos=scenario["red_pos"],
            yellow_pos=scenario["yellow_pos"],
            yellow_radius=yellow_radius,
            filename=scenario["filename"],
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

            # 等待处理
            time.sleep(1.0)

            # 尝试读取控制指令
            try:
                # 使用 readline 可能会阻塞，这里只是尝试
                command = process.stdout.readline().strip()
                if command:
                    print(f"→ 控制指令: {command}")
                else:
                    print("→ (未收到指令)")
            except Exception as e:
                print(f"→ (读取指令时出错: {e})")

            # 检查 stderr 是否有日志输出
            # 注意：这里只是示例，实际可能需要异步读取

        print("\n" + "=" * 60)
        print("测试完成")
        print("=" * 60)
        print(f"\n生成的测试图像和 debug.jpg 已保存在当前目录")
        print(f"请查看 debug.jpg 以查看最后一个场景的处理结果")

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

    print("\n测试程序结束\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
