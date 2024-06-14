import google.generativeai as genai
import time
import capture
import requests
import os
import logging
from queue import Queue
import threading

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Add a logging handler
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
logger.addHandler(handler)


class Gemini:
    def __init__(self) -> None:
        self.model = genai.GenerativeModel(
            model_name="models/gemini-1.5-flash",
            system_instruction=[
                """
あなたは世界的に有名なプロのゲーム実況者(解説)です。
私が進行中のゲーム、GUILTY GEAR -STRIVE-の試合の動画を送信するので、あなたはその試合を解説し、これまでに起こったことの分析と試合の結末を予測してください。
また、実況なので視聴者を楽しませるようなコメントもお願いします。
例えば、視聴者に対する問いかけや、面白いエピソード、プレイヤーの特徴などを交えて解説してください。
ゲームの専門用語、戦術、各試合に関わる選手／チームの知識が必要で、単なる実況ナレーションではなく、知的な解説をすることに主眼を置いてください。
送信される動画は、途中で途切れるものがありますがすぐに次の動画が送信されますので、気にせず解説を続けてください。
"""
            ],
        )
        self.chat = self.model.start_chat()
        self.file_queue = Queue()
        self.all_files = []
        self.rpm = 0
        self.rpm_time = 0

    def rpm_limit(self):
        if time.time() - self.rpm_time > 60:
            self.rpm = 0
            self.rpm_time = time.time()
            logger.info("RPM reset.")
        if self.rpm > 15:
            logger.warning("RPM limit reached.")
            return True
        logger.debug(f"RPM: {self.rpm}")
        self.rpm += 1
        return False

    def upload(self, path, display_name):
        file = genai.upload_file(path=path, display_name=display_name)
        while file.state.name == "PROCESSING":
            logger.debug(file.state.name)
            time.sleep(0.5)
            file = genai.get_file(file.name)

        if file.state.name == "FAILED":
            logger.error("Upload failed.")
            raise ValueError(file.state.name)

        self.all_files.append(file.name)
        self.file_queue.put(file)
        os.remove(path)
        return file

    def generate(self, prompt: str, file: bool = False):
        # TODO: チャットができているか怪しいので確認

        if file:
            video = self.file_queue.get()
            if not video:
                raise ValueError("No file uploaded.")
            logger.info(f"Generating content from {video.name}.")
            response = self.chat.send_message([video])
        else:
            response = self.model.generate_content([prompt])

        return response


def speak(text="", volume=-1, speed=-1, tone=-1):
    res = requests.get(
        "http://localhost:50080/Talk",
        params={
            "text": text,
            "voice": 1,
            "volume": volume,
            "speed": speed,
            "tone": tone,
        },
    )
    return res.status_code


def capture_and_upload():
    global upload_thread
    while True:
        if kill_flag:
            break
        while not gemini.file_queue.empty() and not video_stack:
            if kill_flag:
                break
            time.sleep(1)
            logger.info("Waiting for queue to empty...")
        file_name = str(capture.capture())
        logger.info("Capture Completed.")
        if upload_thread:
            upload_thread.join()

        upload_thread = threading.Thread(
            target=gemini.upload, args=(f"temp/{file_name}.mp4", file_name), daemon=True
        )
        upload_thread.start()
    logger.info("Capture thread exited.")


def main():
    while True:
        if kill_flag:
            break
        while gemini.file_queue.empty():
            logger.info("Waiting for file...")
            time.sleep(1)
        while gemini.rpm_limit():
            logger.info("RPM limit reached. Waiting...")
            time.sleep(1)
        logger.debug(f"{gemini.file_queue.qsize()} files in queue.")
        response = gemini.generate(
            "この試合を日本語で実況してください。ゲームはGUILTY GEAR -STRIVE-です。また、あなたの出力はそのまま視聴者に提供されます。",
            file=True,
        )
        print(response.text)

        try:
            speak(
                response.text, volume=30, speed=250
            )  # 棒読みちゃんのインストール、起動が必要
        except Exception as e:
            logger.error("Could not connect to the TTS server.")
            logger.error(str(e))
    logger.info("Main thread exited.")


if __name__ == "__main__":
    kill_flag = False
    video_stack = False
    gemini = Gemini()
    upload_thread = None

    capture_thread = threading.Thread(target=capture_and_upload, daemon=True)
    main_thread = threading.Thread(target=main, daemon=True)

    capture_thread.start()
    main_thread.start()

    input("Press Enter to exit.")
    logger.info("Exiting...")
    kill_flag = True
    capture_thread.join()
    main_thread.join()

    for file in gemini.all_files:
        genai.delete_file(file)
        print(f"Deleted {file}.")
    exit(0)
