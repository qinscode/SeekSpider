import time

import requests


class AIClient:
    def __init__(self, config):
        self.config = config
        self.headers = {
            "Authorization": f"Bearer {config.AI_API_KEY}",
            "Content-Type": "application/json"
        }

    def analyze_text(self, prompt, text, max_retries=3, retry_delay=60):
        for attempt in range(max_retries):
            try:
                payload = {
                    "model": self.config.AI_MODEL,
                    "messages": [
                        {
                            "role": "system",
                            "content": prompt
                        },
                        {
                            "role": "user",
                            "content": text
                        }
                    ],
                    "stream": False,
                    "response_format": {"type": "text"}
                }

                response = requests.post(
                    self.config.AI_API_URL,
                    json=payload,
                    headers=self.headers
                )

                if response.status_code == 200:
                    return response.json()['choices'][0]['message']['content']

                if response.status_code == 429 and attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue

                response.raise_for_status()

            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                raise e

        return None
