import time

import requests


class AIClient:
    def __init__(self, config):
        self.config = config
        self.api_keys = config.AI_API_KEYS
        self.current_key_index = 0
        # Track exhausted keys (403 - insufficient balance)
        self.exhausted_keys = set()

    def _get_headers(self, key_index=None):
        """Get headers with the specified or current API key"""
        if key_index is None:
            key_index = self.current_key_index
        return {
            "Authorization": f"Bearer {self.api_keys[key_index]}",
            "Content-Type": "application/json"
        }

    def _rotate_key(self, skip_exhausted=True):
        """Rotate to the next API key"""
        if len(self.api_keys) <= 1:
            return False

        original_index = self.current_key_index
        for _ in range(len(self.api_keys)):
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
            if not skip_exhausted or self.current_key_index not in self.exhausted_keys:
                return True
            if self.current_key_index == original_index:
                break
        return False

    def _get_available_key_count(self):
        """Get the number of keys that are not exhausted"""
        return len(self.api_keys) - len(self.exhausted_keys)

    def analyze_text(self, prompt, text, max_retries=3, retry_delay=60):
        if text == "":
            text = "No content provided."

        # Track which keys have been tried for rate limit errors
        keys_tried_for_rate_limit = set()

        for attempt in range(max_retries):
            # Check if all keys are exhausted
            if self._get_available_key_count() == 0:
                raise Exception("All API keys are exhausted (insufficient balance)")

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
                            "content": "Please analyze the following content:" + text
                        }
                    ],
                    "stream": False,
                    "response_format": {"type": "text"},
                    "temperature": 1.3
                }

                response = requests.post(
                    self.config.AI_API_URL,
                    json=payload,
                    headers=self._get_headers()
                )

                if response.status_code == 200:
                    return response.json()['choices'][0]['message']['content']

                # Handle 403 - insufficient balance, mark key as exhausted
                if response.status_code == 403:
                    self.exhausted_keys.add(self.current_key_index)
                    if self._rotate_key():
                        # Retry immediately with new key
                        continue
                    else:
                        raise Exception("All API keys are exhausted (insufficient balance)")

                # Handle rate limit (429) - try rotating to another key first
                if response.status_code == 429:
                    keys_tried_for_rate_limit.add(self.current_key_index)

                    # Try rotating to a key that hasn't been rate limited
                    rotated = False
                    original_index = self.current_key_index
                    for _ in range(len(self.api_keys)):
                        if self._rotate_key():
                            if self.current_key_index not in keys_tried_for_rate_limit:
                                rotated = True
                                break

                    if rotated:
                        # Retry immediately with new key
                        continue

                    # All keys rate limited, wait and retry
                    if attempt < max_retries - 1:
                        keys_tried_for_rate_limit.clear()
                        time.sleep(retry_delay)
                        continue

                response.raise_for_status()

            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                raise e

        return None
