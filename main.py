#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视觉伺服控制系统 - 主程序
用于比赛中的图像处理和控制指令输出
"""

import sys
import cv2
import numpy as np
from pathlib import Path
import os
import gc
import time

# 配置选项
SAVE_DEBUG_IMAGE = False  # 是否保存调试图像
DEBUG_IMAGE_INTERVAL = 10  # 每N张保存一次调试图像（0表示每张都保存）
VERBOSE_LOG = True  # 是否输出详细日志
DELETE_PNG_AFTER_PROCESS = True  # 是否在处理后删除PNG文件

# 全局计数器
image_count = 0
TASK_ID = 1  # 当前任务ID，用于控制是否开启避障


def log(msg):
    """输出调试信息到 stderr，不影响 stdout 的控制指令"""
    if VERBOSE_LOG:
        sys.stderr.write(f"[Debug] {msg}\n")
        sys.stderr.flush()


def send_command(command):
    """
    发送控制指令到主进程

    Args:
        command: 控制指令字符串，如 "UP", "DOWN", "LEFT", "RIGHT"
    """
    print(command, flush=True)  # flush=True 确保立即发送


def handshake(task_id=1, debug=True):
    """
    执行握手协议
    启动后立即发送必要的初始化信息

    Args:
        task_id: 任务ID (0/1/2/3)
        debug: 是否开启调试模式
    """
    # debug_mode = "true" if debug else "false"
    # log("Debug mode: " + debug_mode)
    print(f"debug=false", flush=True)
    print(f"task {task_id}", flush=True)
    
    # Task 0: 发送姓名
    if task_id == 0:
        print("缪旭", flush=True)
        log("Sent name for task 0")
        print("202510322027",flush=True)
        log("Sent student ID for task 0")


def detect_yellow_obstacle(image):
    """
    检测图像中的黄色障碍物

    Args:
        image: OpenCV 读取的图像（BGR格式）

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
        return None, None, None, 0

    # 5. 找到面积最大的轮廓
    max_contour = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(max_contour)

    # 6. 筛选：面积太小则忽略
    if area < 100:
        return None, None, None, 0

    # 7. 计算质心
    M = cv2.moments(max_contour)
    if M["m00"] == 0:
        return None, None, None, area

    cx = int(M["m10"] / M["m00"])
    cy = int(M["m01"] / M["m00"])

    return cx, cy, max_contour, area


def detect_red_target(image):
    """
    检测图像中的红色标靶，使用最小外接圆找到真正的圆心

    Args:
        image: OpenCV 读取的图像（BGR格式）

    Returns:
        tuple: (cx, cy, contour) - 圆心坐标和最大轮廓，如果未找到则返回 (None, None, None)
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
        return None, None, None

    # 5. 找到面积最大的轮廓
    max_contour = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(max_contour)

    # 6. 筛选：面积太小则忽略
    if area < 100:
        return None, None, None

    # 7. 使用最小外接圆找到靶标的真正圆心（适用于同心圆靶标）
    # 这比质心方法更准确，能精确定位到圆形靶标的中心
    (circle_x, circle_y), radius = cv2.minEnclosingCircle(max_contour)
    cx = int(circle_x)
    cy = int(circle_y)

    return cx, cy, max_contour


def calculate_control_vector(
    image_width, image_height, red_pos, yellow_pos, yellow_area
):
    """
    使用分阶段控制策略：远距离快速接近，近距离势场法微调

    Args:
        image_width: 图像宽度
        image_height: 图像高度
        red_pos: 红色目标位置 (cx, cy)，如果为None则表示未检测到
        yellow_pos: 黄色障碍物位置 (cx, cy)，如果为None则表示未检测到
        yellow_area: 黄色障碍物面积

    Returns:
        tuple: (vx, vy, distance) - 控制向量（x方向和y方向的力）和距离
    """
    # 图像中心坐标
    center_x = image_width // 2
    center_y = image_height // 2

    # 初始化控制向量
    vx, vy = 0.0, 0.0
    target_distance = 0
    
    log(f"=== Task {TASK_ID} ===")
    log(f"Red target: {red_pos}")
    log(f"Yellow obstacle: {yellow_pos}, Area: {yellow_area}")

    # 1. 红色目标产生引力（吸引云台中心靠近）
    if red_pos is not None:
        red_cx, red_cy = red_pos
        # 计算从中心指向红色目标的向量
        dx = red_cx - center_x
        dy = red_cy - center_y
        target_distance = np.sqrt(dx**2 + dy**2)

        if target_distance > 0:
            # === Task 1: 纯比例控制，最简单最快 ===
            if TASK_ID == 1:
                # 直接使用偏移量作为控制向量
                # 距离大→向量大→移动快；距离小→向量小→移动慢
                # 自然收敛，无过冲
                vx = float(dx)
                vy = float(dy)
            
            # === Task 2: 极保守比例控制，杜绝过冲 ===
            elif TASK_ID == 2:
                # 五段式超保守增益，确保平滑减速
                if target_distance > 100:
                    # 远距离：温和加速
                    gain = 1.5
                elif target_distance > 50:
                    # 中远距离：开始减速
                    gain = 1.0
                elif target_distance > 25:
                    # 中距离：持续减速
                    gain = 0.6
                elif target_distance > 10:
                    # 近距离：极小增益
                    gain = 0.4
                else:
                    # 极近距离：微调模式
                    gain = 0.25
                
                vx = gain * float(dx)
                vy = gain * float(dy)
            
            else:
                # === Task 3等：使用势场法 + 安全区域避障 ===
                log(f"Task 3: Target distance = {target_distance:.1f}")
                
                # 定义距离阈值
                FAST_APPROACH_THRESHOLD = 150
                FINE_TUNE_THRESHOLD = 30
                
                # 定义准心安全区域（正方形）
                SAFETY_ZONE_SIZE = 150  # 扩大到150像素，更早触发避障
                
                # 检查障碍物是否在安全区域内
                obstacle_in_safety_zone = False
                bypass_vx = 0  # 绕行向量
                bypass_vy = 0
                
                if yellow_pos is not None:
                    yellow_cx, yellow_cy = yellow_pos
                    dx_obs = yellow_cx - center_x
                    dy_obs = yellow_cy - center_y
                    obs_dist_check = np.sqrt(dx_obs**2 + dy_obs**2)
                    
                    log(f"Obstacle relative pos: dx={dx_obs:.1f}, dy={dy_obs:.1f}, dist={obs_dist_check:.1f}")
                    
                    # 如果障碍物在安全区域内
                    if abs(dx_obs) < SAFETY_ZONE_SIZE and abs(dy_obs) < SAFETY_ZONE_SIZE:
                        obstacle_in_safety_zone = True
                        log(f"!!! OBSTACLE IN SAFETY ZONE !!! Size={SAFETY_ZONE_SIZE}")
                        
                        # 智能绕行策略：判断障碍物在目标路径的哪一侧
                        # 使用叉积：cross = dx * dy_obs - dy * dx_obs
                        # cross > 0: 障碍物在路径左侧，向右绕行
                        # cross < 0: 障碍物在路径右侧，向左绕行
                        cross_product = dx * dy_obs - dy * dx_obs
                        
                        # 计算切向量（垂直于中心->目标的方向）
                        # 向右的切向量: (dy, -dx)
                        # 向左的切向量: (-dy, dx)
                        tangent_len = max(np.sqrt(dx**2 + dy**2), 1.0)
                        
                        if cross_product > 0:
                            # 障碍物在左侧，向右绕行
                            bypass_vx = dy / tangent_len
                            bypass_vy = -dx / tangent_len
                            log(f"Bypass RIGHT (obstacle on left), cross={cross_product:.1f}")
                        else:
                            # 障碍物在右侧，向左绕行
                            bypass_vx = -dy / tangent_len
                            bypass_vy = dx / tangent_len
                            log(f"Bypass LEFT (obstacle on right), cross={cross_product:.1f}")
                        
                        log(f"Tangent vector: vx={bypass_vx:.3f}, vy={bypass_vy:.3f}")
                else:
                    log("No obstacle detected")
                
                if target_distance > FAST_APPROACH_THRESHOLD:
                    log("Stage 1: Far distance")
                    # 阶段1：快速接近模式
                    if obstacle_in_safety_zone:
                        # 障碍物在安全区域内：避障优先
                        bypass_force = 4000.0  # 大幅增强绕行力
                        target_force = 300.0   # 降低目标力
                        
                        vx = bypass_force * bypass_vx + target_force * (dx / target_distance)
                        vy = bypass_force * bypass_vy + target_force * (dy / target_distance)
                        log(f"BYPASS MODE: bypass_force={bypass_force}, target_force={target_force}")
                        log(f"Combined vector: vx={vx:.1f}, vy={vy:.1f}")
                    else:
                        # 正常追踪目标
                        attraction_force = 600.0  # 进一步降低吸引力
                        vx = attraction_force * (dx / target_distance)
                        vy = attraction_force * (dy / target_distance)
                        log(f"Attraction: force={attraction_force}, vx={vx:.1f}, vy={vy:.1f}")

                        # 远距离预防性避障 - 增强
                        if yellow_pos is not None:
                            yellow_cx, yellow_cy = yellow_pos
                            dy_obs = center_y - yellow_cy
                            dx_obs = center_x - yellow_cx
                            obs_distance = np.sqrt(dx_obs**2 + dy_obs**2)
                            log(f"Obstacle distance: {obs_distance:.1f}")

                            if obs_distance < 250:  # 扩大预防范围
                                # 增强斥力，考虑障碍物面积
                                area_factor = min(yellow_area / 300.0, 10.0)
                                repulsion = (1200.0 / max(obs_distance, 2)) * (1 + area_factor)
                                rep_vx = repulsion * (dx_obs / obs_distance)
                                rep_vy = repulsion * (dy_obs / obs_distance)
                                vx += rep_vx
                                vy += rep_vy
                                log(f"Repulsion applied: rep={repulsion:.1f}, rep_vx={rep_vx:.1f}, rep_vy={rep_vy:.1f}")
                                log(f"Final vector: vx={vx:.1f}, vy={vy:.1f}")

                elif target_distance > FINE_TUNE_THRESHOLD:
                    log("Stage 2: Medium distance")
                    # 阶段2：平衡模式
                    if obstacle_in_safety_zone:
                        # 障碍物在安全区域内：避障优先
                        bypass_force = 3000.0
                        target_force = 200.0
                        
                        vx = bypass_force * bypass_vx + target_force * (dx / target_distance)
                        vy = bypass_force * bypass_vy + target_force * (dy / target_distance)
                        log(f"BYPASS MODE: bypass_force={bypass_force}, target_force={target_force}")
                        log(f"Combined vector: vx={vx:.1f}, vy={vy:.1f}")
                    else:
                        attraction_force = min(target_distance / 30.0, 80.0)
                        vx = attraction_force * (dx / target_distance)
                        vy = attraction_force * (dy / target_distance)
                        log(f"Attraction: force={attraction_force:.1f}, vx={vx:.1f}, vy={vy:.1f}")

                        if yellow_pos is not None:
                            yellow_cx, yellow_cy = yellow_pos
                            dy_obs = center_y - yellow_cy
                            dx_obs = center_x - yellow_cx
                            obs_distance = np.sqrt(dx_obs**2 + dy_obs**2)
                            log(f"Obstacle distance: {obs_distance:.1f}")

                            if obs_distance < 180:
                                # 增强面积因子和斥力
                                area_factor = min(yellow_area / 300.0, 10.0)
                                repulsion_force = (1500.0 / max(obs_distance, 5)) * (
                                    1 + area_factor
                                )
                                repulsion_force = min(repulsion_force, 80.0)

                                rep_vx = repulsion_force * (dx_obs / obs_distance)
                                rep_vy = repulsion_force * (dy_obs / obs_distance)
                                vx += rep_vx
                                vy += rep_vy
                                log(f"Repulsion: force={repulsion_force:.1f}, rep_vx={rep_vx:.1f}, rep_vy={rep_vy:.1f}")
                                log(f"Final vector: vx={vx:.1f}, vy={vy:.1f}")

                else:
                    log("Stage 3: Close distance")
                    # 阶段3：精确微调模式
                    if obstacle_in_safety_zone:
                        # 障碍物在安全区域内：避障优先
                        bypass_force = 2000.0
                        target_force = 100.0
                        
                        vx = bypass_force * bypass_vx + target_force * (dx / target_distance)
                        vy = bypass_force * bypass_vy + target_force * (dy / target_distance)
                        log(f"BYPASS MODE: bypass_force={bypass_force}, target_force={target_force}")
                        log(f"Combined vector: vx={vx:.1f}, vy={vy:.1f}")
                    else:
                        attraction_force = min(target_distance / 80.0, 12.0)
                        vx = attraction_force * (dx / target_distance)
                        vy = attraction_force * (dy / target_distance)
                        log(f"Attraction: force={attraction_force:.1f}, vx={vx:.1f}, vy={vy:.1f}")

                        if yellow_pos is not None:
                            yellow_cx, yellow_cy = yellow_pos
                            dy_obs = center_y - yellow_cy
                            dx_obs = center_x - yellow_cx
                            obs_distance = np.sqrt(dx_obs**2 + dy_obs**2)
                            log(f"Obstacle distance: {obs_distance:.1f}")

                            if obs_distance < 120:
                                # 近距离强化避障
                                area_factor = min(yellow_area / 300.0, 8.0)
                                repulsion_force = (1200.0 / max(obs_distance, 10)) * (
                                    1 + area_factor
                                )
                                repulsion_force = min(repulsion_force, 60.0)

                                rep_vx = repulsion_force * (dx_obs / obs_distance)
                                rep_vy = repulsion_force * (dy_obs / obs_distance)
                                vx += rep_vx
                                vy += rep_vy
                                log(f"Repulsion: force={repulsion_force:.1f}, rep_vx={rep_vx:.1f}, rep_vy={rep_vy:.1f}")

                                # 大面积障碍物增强
                                image_area = image_width * image_height
                                yellow_ratio = yellow_area / image_area
                                if yellow_ratio > 0.1:
                                    vx *= 5.0
                                    vy *= 5.0
                                    log(f"Large obstacle boost: 5.0x")
                                elif yellow_ratio > 0.05:
                                    vx *= 3.0
                                    vy *= 3.0
                                    log(f"Medium obstacle boost: 3.0x")
                                log(f"Final vector: vx={vx:.1f}, vy={vy:.1f}")
    else:
        # 没有目标时，只做避障
        if yellow_pos is not None:
            yellow_cx, yellow_cy = yellow_pos
            dx = center_x - yellow_cx
            dy = center_y - yellow_cy
            distance = np.sqrt(dx**2 + dy**2)

            if distance > 0:
                area_factor = min(yellow_area / 800.0, 4.0)
                repulsion_force = (300.0 / max(distance, 40)) * (1 + area_factor)
                repulsion_force = min(repulsion_force, 15.0)

                vx += repulsion_force * (dx / distance)
                vy += repulsion_force * (dy / distance)

    return vx, vy, target_distance


def send_control_command(vx, vy, distance, threshold=0.3):
    """
    根据控制向量和距离发送控制指令（根据距离动态调整阈值）

    Args:
        vx: x方向的控制力（正值向右，负值向左）
        vy: y方向的控制力（正值向下，负值向上）
        distance: 与目标的距离
        threshold: 触发指令的基础阈值
    """
    # Task 1: 像素级阈值 - 避免抖动浪费步数
    if TASK_ID == 1:
        # 偏离>=1像素才移动，避免在目标附近来回抖动
        adjusted_threshold = 1.0
    # Task 2: 适中阈值 - 平衡精度与步数
    elif TASK_ID == 2:
        # 使用1.5像素阈值，避免过冲但不过度微调
        adjusted_threshold = 1.5
    else:
        # 其他任务：根据距离动态调整阈值
        if distance > 100:
            adjusted_threshold = 0.001
        elif distance > 50:
            adjusted_threshold = 0.002
        elif distance > 20:
            adjusted_threshold = 0.003
        elif distance > 5:
            adjusted_threshold = 0.005
        else:
            adjusted_threshold = 0.001

    # 优先处理较大的分量
    abs_vx = abs(vx)
    abs_vy = abs(vy)

    if abs_vx < adjusted_threshold and abs_vy < adjusted_threshold:
        # 向量太小，目标已居中 - 必须发送NOOP避免管道卡死
        print("NOOP", flush=True)
        return

    # 选择主导方向并发送指令
    command = None
    if abs_vx > abs_vy:
        # 水平方向为主
        if vx > adjusted_threshold:
            command = "RIGHT"
        elif vx < -adjusted_threshold:
            command = "LEFT"
    else:
        # 垂直方向为主
        if vy > adjusted_threshold:
            command = "DOWN"
        elif vy < -adjusted_threshold:
            command = "UP"

    # 确保总是发送指令，避免管道卡死
    if command:
        print(command, flush=True)
    else:
        # 如果没有匹配到指令，发送NOOP
        print("NOOP", flush=True)


def process_image(image_path):
    """
    处理单张图像

    Args:
        image_path: 图像文件的绝对路径

    Returns:
        bool: 处理是否成功
    """
    global image_count
    image_count += 1

    try:
        # 检查文件是否存在
        if not Path(image_path).exists():
            return False

        # 使用 OpenCV 读取图像
        image = cv2.imread(image_path)

        if image is None:
            return False

        # 记录图像信息
        height, width = image.shape[:2]

        # ==========================================
        # Task 3: 视觉处理 - 检测目标和障碍物
        # ==========================================

        # 检测红色标靶（目标）
        red_cx, red_cy, red_contour = detect_red_target(image)

        # 检测黄色障碍物
        yellow_cx, yellow_cy, yellow_contour, yellow_area = detect_yellow_obstacle(
            image
        )

        # 计算控制向量
        red_pos = (red_cx, red_cy) if red_cx is not None else None
        yellow_pos = (yellow_cx, yellow_cy) if yellow_cx is not None else None
        vx, vy, distance = calculate_control_vector(
            width, height, red_pos, yellow_pos, yellow_area
        )

        # 发送控制指令（传入距离信息）
        send_control_command(vx, vy, distance, threshold=0.3)

        # 删除PNG文件（在所有处理完成后立即删除）
        if DELETE_PNG_AFTER_PROCESS and image_path.lower().endswith(".png"):
            try:
                os.remove(image_path)
                # 减少日志输出避免stderr缓冲区堵塞
            except Exception:
                # 静默处理删除失败
                pass

        # 决定是否保存调试图像
        should_save_debug = SAVE_DEBUG_IMAGE and (
            DEBUG_IMAGE_INTERVAL == 0
            or image_count % DEBUG_IMAGE_INTERVAL == 0
            or (red_cx is not None or yellow_cx is not None)  # 有目标时保存
        )

        if not should_save_debug:
            # 释放内存
            del image
            gc.collect()
            return True

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

        # 保存调试图像
        debug_path = "debug.jpg"
        cv2.imwrite(debug_path, debug_image)

        # 释放内存
        del image
        del debug_image
        gc.collect()

        return True

    except Exception as e:
        # 发生异常时也要释放内存
        if "image" in locals():
            del image
        if "debug_image" in locals():
            del debug_image
        gc.collect()

        # 异常时也尝试删除PNG文件
        if DELETE_PNG_AFTER_PROCESS and image_path.lower().endswith(".png"):
            try:
                if Path(image_path).exists():
                    os.remove(image_path)
            except:
                pass

        return False


def main():
    """
    主函数 - 程序入口
    """
    global TASK_ID

    # 从命令行参数读取任务ID（可选）
    task_id = 0  # 默认任务1（发挥部分：避障）
    debug_mode = True  # 默认开启调试

    if len(sys.argv) > 1:
        try:
            task_id = int(sys.argv[1])
        except ValueError:
            pass

    if len(sys.argv) > 2:
        debug_mode = sys.argv[2].lower() in ["true", "1", "yes"]

    # 设置全局任务ID
    TASK_ID = task_id

    # 执行握手协议
    handshake(task_id=task_id, debug=debug_mode)
    sys.stderr.write("[System] 视觉伺服控制系统启动\n")
    sys.stderr.flush()

    # 主循环：持续读取 stdin 输入
    try:
        counter = 0
        while True:
            # 读取图像路径
            line = sys.stdin.readline()

            # 如果readline()返回空字符串，说明stdin已关闭（EOF），退出循环
            if not line:
                sys.stderr.write("[System] stdin已关闭，程序正常退出\n")
                sys.stderr.flush()
                break

            image_path = line.strip()
            log("Counter:{}".format(counter))
            counter += 1

            # 跳过空行（只是换行符的情况）
            if not image_path:
                continue

            # 处理图像
            try:
                process_image(image_path)
            except Exception as e:
                # 处理单张图像失败不应导致整个程序崩溃
                if VERBOSE_LOG:
                    sys.stderr.write(f"[Error] 处理图像失败: {e}\n")
                    sys.stderr.flush()
                continue
    except KeyboardInterrupt:
        sys.stderr.write("\n[System] 程序被用户中断\n")
        sys.stderr.flush()
    except Exception as e:
        sys.stderr.write(f"\n[Fatal] 程序异常退出: {e}\n")
        sys.stderr.flush()


if __name__ == "__main__":
    main()
