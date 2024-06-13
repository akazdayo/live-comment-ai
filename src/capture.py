import cv2
import pyautogui
import time
import numpy as np


def get_capture():
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")

    # VideoWriterオブジェクトを作成
    out = cv2.VideoWriter("temp/output.mp4", fourcc, 30.0, (1920, 1080))

    # 録画開始時間を記録
    start_time = time.time()

    # 1分間録画
    while time.time() - start_time < 5:  # 60秒間
        # スクリーンショットを取得
        img = pyautogui.screenshot()
        # BGR形式に変換 (OpenCVはRGBではなくBGRを使用)
        frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        # フレームを書き込む
        out.write(frame)

    # 保存
    out.release()


get_capture()
