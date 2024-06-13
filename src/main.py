import google.generativeai as genai
from time import sleep
import capture
import requests
import os
import logging

logger = logging.getLogger(__name__)


class Gemini:
    def __init__(self) -> None:
        self.model = genai.GenerativeModel(model_name="models/gemini-1.5-pro")
        self.chat = self.model.start_chat()
        self.file = None
        self.all_files = []

    def upload(self, path, display_name):
        self.file = genai.upload_file(path=path, display_name=display_name)
        while self.file.state.name == "PROCESSING":
            logger.debug(self.file.state.name)
            sleep(1.25)
            self.file = genai.get_file(self.file.name)

        if self.file.state.name == "FAILED":
            logger.error("Upload failed.")
            raise ValueError(self.file.state.name)

        self.all_files.append(self.file.name)
        return self.file

    def generate(self, prompt: str, file: bool = False):
        if file:
            if not self.file:
                raise ValueError("No file uploaded.")
            response = self.chat.send_message([self.file, prompt])
            sleep(3)
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


gemini = Gemini()

if __name__ == "__main__":
    try:
        while True:
            capture.get_capture()
            logger.info("Capture Completed.")

            gemini.upload("temp/output.mp4", "output")
            response = gemini.generate(
                "この試合を日本語で実況してください。ゲームはギルティギアです。",
                file=True,
            )

            print(response.text)
            # speak(response.text, volume=30, speed=250)

            os.remove("temp/output.mp4")
            sleep(3)
    except KeyboardInterrupt:
        logger.info("Exiting...")
        for file in gemini.all_files:
            genai.delete_file(file)
            print(f"Deleted {file}.")
        exit(0)
