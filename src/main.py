from tomllib import load
from uuid import uuid4
import subprocess
import google.generativeai as genai
from queue import Queue
import time
import os
import httpx
import threading
import concurrent.futures
from loguru import logger

with open("settings.toml", "rb") as f:
    settings = load(f)


class Gemini:
    def __init__(self) -> None:
        self.model = genai.GenerativeModel(
            model_name=settings["gemini"]["model"],
            system_instruction=[settings["gemini"]["prompt"]],
        )
        self.chat = self.model.start_chat()
        self.file_queue = Queue()
        self.all_files = []
        self.rpm = 0
        self.rpm_time = 0

    def generate(self):
        if len(self.chat.history) > settings["gemini"]["max_history_length"] * 2:
            self.chat.history = self.chat.history[
                -settings["gemini"]["max_history_length"] :
            ]

        while self.file_queue.qsize() <= 0:
            logger.info("Waiting for file...")
            time.sleep(1)

        video = self.file_queue.get()
        logger.info("Generating...")
        logger.debug(f"queue size: {self.file_queue.qsize()}")
        response = self.chat.send_message([video])

        return response

    def upload(self, file_name: str):
        upload_file = genai.upload_file(f"temp/{file_name}.mp4")

        while upload_file.state.name == "PROCESSING":
            time.sleep(0.5)
            logger.info("Uploading...")
            upload_file = genai.get_file(upload_file.name)

        if upload_file.state.name == "FAILED":
            raise ValueError("Failed to upload file.")

        self.all_files.append(upload_file.name)
        self.file_queue.put(upload_file)
        os.remove(f"temp/{file_name}.mp4")
        return upload_file

    def rpm_limit(self, add=True):
        if time.time() - self.rpm_time > 60:
            self.rpm = 0
            self.rpm_time = time.time()

        if self.rpm > settings["gemini"]["max_rpm"]:
            logger.warning("RPM limit reached.")
            return True

        if add:
            self.rpm += 1
        return False


class Main:
    def __init__(self) -> None:
        self.upload_thread = None
        self.kill_flag = False
        self.gemini = Gemini()

    def capture(self):
        while not self.kill_flag:
            if not self.gemini.file_queue.empty() or self.gemini.rpm_limit(False):
                logger.info("File queue is not empty or RPM limit reached.")
                time.sleep(1)
                continue

            file_name = self._capture()
            if self.upload_thread is not None:
                self.upload_thread.join()
            threading.Thread(
                target=self.gemini.upload, args=(file_name,), daemon=True
            ).start()

    def generate(self):
        while not self.kill_flag:
            if self.gemini.file_queue.qsize() <= 0:
                logger.info("Waiting for file...")
                time.sleep(1)
                continue
            if self.gemini.rpm_limit():
                time.sleep(1)
                continue

            response = self.gemini.generate()
            logger.info(response.text)
            self.TTS(response.text, speed=280)
            time.sleep(15)

    def TTS(self, text="", volume=-1, speed=-1, tone=-1):
        res = httpx.get(
            "http://localhost:50080/Talk",
            params={
                "text": text,
                "voice": 1,
                "volume": volume,
                "speed": speed,
                "tone": tone,
            },
        )
        if res.status_code != 200:
            logger.critical("Failed to request TTS." + res.status_code)
        return res.status_code

    def exit(self):
        input("Press Enter to exit.")
        self.kill_flag = True

    def delete_files(self):
        for file in self.gemini.all_files:
            genai.delete_file(file)
            logger.debug("Deleted file:", file)
        for file in os.listdir("temp"):
            if file.endswith(".mp4"):
                os.remove(f"temp/{file}")
                logger.debug("Deleted file:", file)

    def _capture(self):
        file_name = str(uuid4())
        logger.info("Capture Starting...")
        status = subprocess.call(  # ffmpegを呼び出し、画面をキャプチャする
            # Windowsのみ対応
            [
                "ffmpeg",
                "-f",
                "gdigrab",
                "-offset_x",
                "0",
                "-offset_y",
                "0",
                "-framerate",
                "24",
                "-video_size",
                "1920x1080",
                "-i",
                "desktop",
                "-vframes",
                "240",
                "-loglevel",
                "quiet",
                f"temp/{file_name}.mp4",
            ]
        )
        logger.info("Capture Finished.")
        if status != 0:
            logger.critical(f"Failed to capture screen. Status code: {status}")
            raise ValueError(f"Failed to capture screen. Status code: {status}")
        return file_name


if __name__ == "__main__":
    main = Main()

    with concurrent.futures.ThreadPoolExecutor() as executor:
        executor.submit(main.capture)
        executor.submit(main.generate)
        executor.submit(main.exit)
    main.delete_files()
