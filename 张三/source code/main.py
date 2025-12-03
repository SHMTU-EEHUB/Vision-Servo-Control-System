import sys
import cv2
import numpy as np
import os

def log(msg):
    """输出调试信息到 stderr，不影响 stdout 的控制指令"""
    sys.stderr.write(f"[Debug] {msg}\n")
    sys.stderr.flush()

def main():
    # 启用debug
    print("debug=true", flush=True)

    log("开始！")

    print("task 1",flush=True)


    while True:

        img_path = sys.stdin.readline().strip()
        log(f"读取到图片路径: {img_path}")
        img = cv2.imread(img_path)
        
        print("LEFT", flush=True)
        print("UP", flush=True)
        print("DOWN", flush=True)
        print("RIGHT", flush=True)

if __name__ == "__main__":
    main()