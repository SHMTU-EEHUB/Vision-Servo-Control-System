#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视觉伺服控制系统 - 主程序
用于比赛中的图像处理和控制指令输出
"""

import sys
import cv2
import numpy as np
import logging
from pathlib import Path


def setup_logging():
    """
    配置日志系统
    所有日志输出到 stderr，避免干扰 stdout 的通信协议
    """
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,  # 关键：使用 stderr 输出日志，不干扰 stdout
    )
    return logging.getLogger(__name__)


def send_command(command):
    """
    发送控制指令到主进程

    Args:
        command: 控制指令字符串，如 "UP", "DOWN", "LEFT", "RIGHT"
    """
    print(command, flush=True)  # flush=True 确保立即发送


def handshake():
    """
    执行握手协议
    启动后立即发送必要的初始化信息
    """
    send_command("debug=true")
    send_command("task 0")


def detect_yellow_obstacle(image, logger):
    """
    检测图像中的黄色障碍物

    Args:
        image: OpenCV 读取的图像（BGR格式）
        logger: 日志对象

    Returns:
        tuple: (cx, cy, contour, area) - 质心坐标、最大轮廓和面积，如果未找到则返回 (None, None, None, 0)
    """
    # 1. 转换到 HSV 色彩空间
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    # 2. 定义黄色的HSV阈值范围 (H: 20-30)
    lower_yellow = np.array([20, 100, 100])
    upper_yellow = np.array([30, 255, 255])
    mask = cv2.inRange(hsv, lower_yellow, upper_yellow)

    # 3. 形态学操作去噪
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    # 4. 查找轮廓
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        logger.debug("未检测到黄色障碍物")
        return None, None, None, 0

    # 5. 找到面积最大的轮廓
    max_contour = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(max_contour)

    # 6. 筛选：面积太小则忽略
    if area < 100:
        logger.debug(f"检测到的黄色区域面积太小: {area} 像素")
        return None, None, None, 0

    # 7. 计算质心
    M = cv2.moments(max_contour)
    if M["m00"] == 0:
        logger.warning("无法计算黄色障碍物质心：m00为0")
        return None, None, None, area

    cx = int(M["m10"] / M["m00"])
    cy = int(M["m01"] / M["m00"])

    logger.info(f"检测到黄色障碍物 - 质心: ({cx}, {cy}), 面积: {area:.0f} 像素")

    return cx, cy, max_contour, area


def detect_red_target(image, logger):
    """
    检测图像中的红色标靶

    Args:
        image: OpenCV 读取的图像（BGR格式）
        logger: 日志对象

    Returns:
        tuple: (cx, cy, contour) - 质心坐标和最大轮廓，如果未找到则返回 (None, None, None)
    """
    # 1. 转换到 HSV 色彩空间
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    # 2. 定义红色的HSV阈值范围
    # 红色在HSV中横跨0度和180度，需要两个范围
    # 范围1：0-10度（偏橙红）
    lower_red1 = np.array([0, 100, 100])
    upper_red1 = np.array([10, 255, 255])
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)

    # 范围2：170-180度（偏紫红）
    lower_red2 = np.array([170, 100, 100])
    upper_red2 = np.array([180, 255, 255])
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)

    # 合并两个掩码
    mask = cv2.bitwise_or(mask1, mask2)

    # 3. 形态学操作（开运算）去除噪点
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    # 可选：闭运算填充空洞
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    # 4. 查找轮廓
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        logger.warning("未检测到红色区域")
        return None, None, None

    # 5. 找到面积最大的轮廓
    max_contour = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(max_contour)

    # 6. 筛选：面积太小则忽略
    if area < 100:
        logger.warning(f"检测到的红色区域面积太小: {area} 像素")
        return None, None, None

    # 7. 计算质心（使用图像矩）
    M = cv2.moments(max_contour)
    if M["m00"] == 0:
        logger.warning("无法计算质心：m00为0")
        return None, None, None

    cx = int(M["m10"] / M["m00"])
    cy = int(M["m01"] / M["m00"])

    logger.info(f"检测到红色标靶 - 质心: ({cx}, {cy}), 面积: {area:.0f} 像素")

    return cx, cy, max_contour


def calculate_control_vector(
    image_width, image_height, red_pos, yellow_pos, yellow_area, logger
):
    """
    使用势场法计算控制向量

    Args:
        image_width: 图像宽度
        image_height: 图像高度
        red_pos: 红色目标位置 (cx, cy)，如果为None则表示未检测到
        yellow_pos: 黄色障碍物位置 (cx, cy)，如果为None则表示未检测到
        yellow_area: 黄色障碍物面积
        logger: 日志对象

    Returns:
        tuple: (vx, vy) - 控制向量（x方向和y方向的力）
    """
    # 图像中心坐标
    center_x = image_width // 2
    center_y = image_height // 2

    # 初始化控制向量
    vx, vy = 0.0, 0.0

    # 1. 红色目标产生引力（吸引云台中心靠近）
    if red_pos is not None:
        red_cx, red_cy = red_pos
        # 计算从中心指向红色目标的向量
        dx = red_cx - center_x
        dy = red_cy - center_y
        distance = np.sqrt(dx**2 + dy**2)

        if distance > 0:
            # 引力大小与距离成正比（距离越远，引力越大）
            attraction_force = min(distance / 100.0, 5.0)  # 限制最大引力
            vx += attraction_force * (dx / distance)
            vy += attraction_force * (dy / distance)
            logger.debug(
                f"红色引力向量: ({attraction_force * (dx / distance):.2f}, {attraction_force * (dy / distance):.2f})"
            )

    # 2. 黄色障碍物产生斥力（排斥远离）
    if yellow_pos is not None:
        yellow_cx, yellow_cy = yellow_pos
        # 计算从黄色障碍物指向中心的向量（斥力方向）
        dx = center_x - yellow_cx
        dy = center_y - yellow_cy
        distance = np.sqrt(dx**2 + dy**2)

        if distance > 0:
            # 斥力与距离成反比（距离越近，斥力越大）
            # 同时考虑障碍物面积，面积越大斥力越强
            area_factor = min(yellow_area / 1000.0, 3.0)  # 面积影响因子
            repulsion_force = (200.0 / max(distance, 50)) * (1 + area_factor)
            repulsion_force = min(repulsion_force, 10.0)  # 限制最大斥力

            vx += repulsion_force * (dx / distance)
            vy += repulsion_force * (dy / distance)
            logger.debug(
                f"黄色斥力向量: ({repulsion_force * (dx / distance):.2f}, {repulsion_force * (dy / distance):.2f})"
            )

            # 如果黄色区域占据屏幕中心较大比例，增强斥力
            image_area = image_width * image_height
            yellow_ratio = yellow_area / image_area
            if yellow_ratio > 0.1:  # 占据超过10%的屏幕
                logger.warning(f"黄色障碍物占据屏幕 {yellow_ratio*100:.1f}%，增强斥力")
                vx *= 2.0
                vy *= 2.0

    logger.info(f"最终控制向量: ({vx:.2f}, {vy:.2f})")
    return vx, vy


def send_control_command(vx, vy, threshold=0.5):
    """
    根据控制向量发送控制指令

    Args:
        vx: x方向的控制力（正值向右，负值向左）
        vy: y方向的控制力（正值向下，负值向上）
        threshold: 触发指令的最小阈值
    """
    # 优先处理较大的分量
    abs_vx = abs(vx)
    abs_vy = abs(vy)

    if abs_vx < threshold and abs_vy < threshold:
        # 向量太小，不发送指令（目标已居中）
        send_command("HOLD")
        return

    # 选择主导方向
    if abs_vx > abs_vy:
        # 水平方向为主
        if vx > threshold:
            send_command("RIGHT")
        elif vx < -threshold:
            send_command("LEFT")
    else:
        # 垂直方向为主
        if vy > threshold:
            send_command("DOWN")
        elif vy < -threshold:
            send_command("UP")


def process_image(image_path, logger):
    """
    处理单张图像

    Args:
        image_path: 图像文件的绝对路径
        logger: 日志对象

    Returns:
        bool: 处理是否成功
    """
    try:
        # 检查文件是否存在
        if not Path(image_path).exists():
            logger.error(f"图像文件不存在: {image_path}")
            return False

        # 使用 OpenCV 读取图像
        image = cv2.imread(image_path)

        if image is None:
            logger.error(f"无法读取图像: {image_path}")
            return False

        # 记录图像信息
        height, width = image.shape[:2]
        logger.info(f"Image received - 尺寸: {width}x{height}")

        # ==========================================
        # Task 3: 视觉处理 - 检测目标和障碍物
        # ==========================================

        # 检测红色标靶（目标）
        red_cx, red_cy, red_contour = detect_red_target(image, logger)

        # 检测黄色障碍物
        yellow_cx, yellow_cy, yellow_contour, yellow_area = detect_yellow_obstacle(
            image, logger
        )

        # 创建调试图像
        debug_image = image.copy()

        # 绘制图像中心十字线（白色虚线）
        center_x, center_y = width // 2, height // 2
        cv2.line(
            debug_image,
            (center_x - 30, center_y),
            (center_x + 30, center_y),
            (255, 255, 255),
            1,
        )
        cv2.line(
            debug_image,
            (center_x, center_y - 30),
            (center_x, center_y + 30),
            (255, 255, 255),
            1,
        )

        # 绘制红色目标
        if red_cx is not None and red_cy is not None:
            # 绘制轮廓（绿色）
            cv2.drawContours(debug_image, [red_contour], -1, (0, 255, 0), 2)

            # 绘制质心（蓝色圆点）
            cv2.circle(debug_image, (red_cx, red_cy), 10, (255, 0, 0), -1)

            # 绘制十字准线
            cv2.line(
                debug_image,
                (red_cx - 20, red_cy),
                (red_cx + 20, red_cy),
                (255, 0, 0),
                2,
            )
            cv2.line(
                debug_image,
                (red_cx, red_cy - 20),
                (red_cx, red_cy + 20),
                (255, 0, 0),
                2,
            )

            # 标注坐标
            text = f"RED ({red_cx}, {red_cy})"
            cv2.putText(
                debug_image,
                text,
                (red_cx + 15, red_cy - 15),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                2,
            )

        # 绘制黄色障碍物
        if yellow_cx is not None and yellow_cy is not None:
            # 绘制轮廓（青色）
            cv2.drawContours(debug_image, [yellow_contour], -1, (255, 255, 0), 2)

            # 绘制质心（红色圆点）
            cv2.circle(debug_image, (yellow_cx, yellow_cy), 8, (0, 0, 255), -1)

            # 标注坐标和面积
            text = f"YELLOW ({yellow_cx}, {yellow_cy}) A={yellow_area:.0f}"
            cv2.putText(
                debug_image,
                text,
                (yellow_cx + 15, yellow_cy + 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 255),
                2,
            )

        # ==========================================
        # Task 3: 势场法控制逻辑
        # ==========================================
        red_pos = (red_cx, red_cy) if red_cx is not None else None
        yellow_pos = (yellow_cx, yellow_cy) if yellow_cx is not None else None

        # 计算控制向量
        vx, vy = calculate_control_vector(
            width, height, red_pos, yellow_pos, yellow_area, logger
        )

        # 在调试图像上绘制控制向量（从中心出发的箭头）
        if abs(vx) > 0.1 or abs(vy) > 0.1:
            arrow_scale = 20  # 箭头长度缩放
            end_x = int(center_x + vx * arrow_scale)
            end_y = int(center_y + vy * arrow_scale)
            cv2.arrowedLine(
                debug_image,
                (center_x, center_y),
                (end_x, end_y),
                (255, 0, 255),
                3,
                tipLength=0.3,
            )

        # 根据控制向量发送指令
        send_control_command(vx, vy, threshold=0.5)

        # 保存调试图像
        debug_path = "debug.jpg"
        cv2.imwrite(debug_path, debug_image)
        logger.info(f"调试图像已保存: {debug_path}")

        return True

    except Exception as e:
        logger.error(f"处理图像时发生异常: {e}", exc_info=True)
        return False


def main():
    """
    主函数 - 程序入口
    """
    # 初始化日志系统
    logger = setup_logging()
    logger.info("视觉伺服控制系统启动")

    try:
        # 执行握手协议
        handshake()
        logger.info("握手协议完成")

        # 主循环：持续读取 stdin 输入
        logger.info("进入主循环，等待图像路径...")

        for line in sys.stdin:
            # 去除行尾的换行符和空格
            image_path = line.strip()

            # 跳过空行
            if not image_path:
                continue

            logger.info(f"接收到图像路径: {image_path}")

            # 处理图像
            process_image(image_path, logger)

    except KeyboardInterrupt:
        logger.info("接收到中断信号，程序退出")
    except Exception as e:
        logger.error(f"主循环发生异常: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("程序结束")


if __name__ == "__main__":
    main()
