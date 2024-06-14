import cv2
import pyautogui
import time
import numpy as np
import uuid


def get_capture():
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")

    # VideoWriterオブジェクトを作成
    id = uuid.uuid4()
    out = cv2.VideoWriter(f"temp/{id}.mp4", fourcc, 30.0, (1920, 1080))

    # 録画開始時間を記録
    start_time = time.time()

    # 1分間録画
    while time.time() - start_time < 15:  # 15秒間
        # スクリーンショットを取得
        img = pyautogui.screenshot()
        # BGR形式に変換 (OpenCVはRGBではなくBGRを使用)
        frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        # フレームを書き込む
        out.write(frame)

    # 保存
    out.release()
    return id


get_capture()
