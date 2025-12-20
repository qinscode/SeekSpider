"""
AI Client with multi-key support and automatic rotation.

Features:
- Automatic key rotation on 403 (insufficient balance)
- Automatic key rotation on 429 (rate limit)
- Auto-reset exhausted keys after cooldown period
- Logging for key rotation events
- Tracks exhausted keys with timestamps
"""

import logging
import time
import requests
from datetime import datetime, timedelta


class AIClient:
    """AI API client with multi-key support and automatic rotation"""

    def __init__(self, config, logger: logging.Logger = None):
        self.config = config
        self.api_keys = config.AI_API_KEYS
        self.current_key_index = 0
        self.logger = logger or logging.getLogger('ai_client')

        # Track exhausted keys with timestamp: {key_index: exhausted_time}
        self.exhausted_keys = {}

        # Cooldown period before retrying exhausted keys (5 minutes)
        self.exhausted_cooldown = timedelta(minutes=5)

        # Track key usage statistics
        self.key_stats = {i: {'requests': 0, 'errors': 0, 'exhausted_count': 0} for i in range(len(self.api_keys))}

        # Track continuous failure time for stopping condition
        self.continuous_failure_start = None
        self.max_continuous_failure_time = timedelta(minutes=5)  # Stop after 5 minutes of continuous failures
        self.all_keys_exhausted_wait = 60  # Wait 1 minute (60s) when all keys exhausted

        if len(self.api_keys) > 1:
            self.logger.info(f"AI Client initialized with {len(self.api_keys)} API keys")
        elif len(self.api_keys) == 1:
            self.logger.info("AI Client initialized with 1 API key")
        else:
            self.logger.warning("AI Client initialized with no API keys!")

    def _get_key_preview(self, key_index: int) -> str:
        """Get a preview of the API key for logging (first 8 chars...last 4 chars)"""
        if key_index < 0 or key_index >= len(self.api_keys):
            return "invalid"
        key = self.api_keys[key_index]
        if len(key) > 12:
            return f"{key[:8]}...{key[-4:]}"
        return key[:4] + "..."

    def _get_headers(self, key_index=None):
        """Get headers with the specified or current API key"""
        if key_index is None:
            key_index = self.current_key_index
        return {
            "Authorization": f"Bearer {self.api_keys[key_index]}",
            "Content-Type": "application/json"
        }

    def _check_and_reset_cooled_keys(self):
        """Check if any exhausted keys have cooled down and can be retried"""
        now = datetime.now()
        cooled_keys = []

        for key_index, exhausted_time in list(self.exhausted_keys.items()):
            if now - exhausted_time > self.exhausted_cooldown:
                cooled_keys.append(key_index)

        if cooled_keys:
            for key_index in cooled_keys:
                del self.exhausted_keys[key_index]
            self.logger.info(
                f"Reset {len(cooled_keys)} exhausted keys after cooldown: {cooled_keys}. "
                f"Available keys: {self._get_available_key_count()}/{len(self.api_keys)}"
            )

    def _rotate_key(self, skip_exhausted=True, reason: str = None) -> bool:
        """
        Rotate to the next API key.

        Args:
            skip_exhausted: If True, skip keys that are marked as exhausted
            reason: Reason for rotation (for logging)

        Returns:
            True if successfully rotated to a new key, False if no keys available
        """
        if len(self.api_keys) <= 1:
            return False

        # Check if any exhausted keys have cooled down
        self._check_and_reset_cooled_keys()

        original_index = self.current_key_index
        for _ in range(len(self.api_keys)):
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
            if not skip_exhausted or self.current_key_index not in self.exhausted_keys:
                reason_str = f" ({reason})" if reason else ""
                self.logger.info(
                    f"Rotated API key{reason_str}: "
                    f"Key #{original_index} ({self._get_key_preview(original_index)}) -> "
                    f"Key #{self.current_key_index} ({self._get_key_preview(self.current_key_index)})"
                )
                return True
            if self.current_key_index == original_index:
                break
        return False

    def _mark_key_exhausted(self, key_index: int):
        """Mark a key as exhausted (insufficient balance)"""
        self.exhausted_keys[key_index] = datetime.now()
        self.key_stats[key_index]['exhausted_count'] += 1
        self.logger.warning(
            f"API Key #{key_index} ({self._get_key_preview(key_index)}) marked as EXHAUSTED "
            f"(insufficient balance). "
            f"Available keys: {self._get_available_key_count()}/{len(self.api_keys)}"
        )

    def _get_available_key_count(self) -> int:
        """Get the number of keys that are not exhausted"""
        return len(self.api_keys) - len(self.exhausted_keys)

    def _try_reset_all_keys(self) -> bool:
        """
        When all keys are exhausted after full rotation, wait and reset to retry.

        Logic:
        - Only called when ALL keys have been tried and ALL are EXHAUSTED
        - Wait 1 minute (60s), then reset all keys and retry
        - Continue retrying until manually stopped or 5 minutes of continuous failures
        - Any successful request resets the 5-minute timer

        Returns:
            True if keys were reset and should retry, False if max failure time exceeded
        """
        now = datetime.now()

        # Track continuous failure start time
        if self.continuous_failure_start is None:
            self.continuous_failure_start = now

        # Check if we've been failing continuously for too long
        failure_duration = now - self.continuous_failure_start
        if failure_duration > self.max_continuous_failure_time:
            self.logger.error(
                f"All API keys have been failing for {failure_duration.total_seconds():.0f} seconds "
                f"(> {self.max_continuous_failure_time.total_seconds():.0f}s limit). "
                f"Please check API key balances or network connectivity."
            )
            return False

        self.logger.warning(
            f"All {len(self.api_keys)} keys exhausted. "
            f"Waiting {self.all_keys_exhausted_wait}s before retry... "
            f"(continuous failure: {failure_duration.total_seconds():.0f}s / "
            f"{self.max_continuous_failure_time.total_seconds():.0f}s)"
        )
        time.sleep(self.all_keys_exhausted_wait)

        # Reset all exhausted keys
        self.exhausted_keys.clear()
        self.current_key_index = 0
        self.logger.info(
            f"Reset all exhausted keys. Retrying from Key #0 ({self._get_key_preview(0)})"
        )
        return True

    def _reset_continuous_failure_timer(self):
        """Reset the continuous failure timer on successful request"""
        if self.continuous_failure_start is not None:
            self.logger.info("Successful request - resetting continuous failure timer")
            self.continuous_failure_start = None

    def get_key_status(self) -> dict:
        """Get status of all API keys"""
        return {
            'total_keys': len(self.api_keys),
            'available_keys': self._get_available_key_count(),
            'exhausted_keys': list(self.exhausted_keys.keys()),
            'current_key_index': self.current_key_index,
            'continuous_failure_start': self.continuous_failure_start.isoformat() if self.continuous_failure_start else None,
            'key_stats': self.key_stats.copy()
        }

    def analyze_text(self, prompt: str, text: str, max_retries: int = 3, retry_delay: int = 60) -> str:
        """
        Analyze text using the AI API.

        Args:
            prompt: System prompt for the AI
            text: Text content to analyze
            max_retries: Maximum number of retries
            retry_delay: Delay between retries in seconds

        Returns:
            AI response content

        Raises:
            Exception: If all keys are exhausted or max retries exceeded
        """
        if text == "":
            text = "No content provided."

        # Track which keys have been tried for rate limit errors
        keys_tried_for_rate_limit = set()
        # Track the starting key when exhausted rotation begins (None = not in rotation)
        exhausted_rotation_start_key = None

        for attempt in range(max_retries):
            # Check if any exhausted keys have cooled down
            self._check_and_reset_cooled_keys()

            current_key = self.current_key_index
            self.key_stats[current_key]['requests'] += 1

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
                    headers=self._get_headers(),
                    timeout=60
                )

                if response.status_code == 200:
                    # Reset continuous failure timer on success
                    self._reset_continuous_failure_timer()
                    # Clear exhausted rotation tracking on success
                    exhausted_rotation_start_key = None
                    return response.json()['choices'][0]['message']['content']

                # Handle 403 - insufficient balance, mark key as exhausted
                if response.status_code == 403:
                    self.key_stats[current_key]['errors'] += 1
                    self._mark_key_exhausted(current_key)

                    # Record starting key if this is the first 403 in this rotation
                    if exhausted_rotation_start_key is None:
                        exhausted_rotation_start_key = current_key
                        self.logger.info(f"Starting exhausted key rotation from Key #{current_key}")

                    # Calculate next key
                    next_key = (current_key + 1) % len(self.api_keys)

                    # Check if we've completed a full rotation (back to start)
                    if next_key == exhausted_rotation_start_key:
                        # Completed full rotation, all keys exhausted, enter wait
                        self.logger.warning(
                            f"Completed full rotation: all {len(self.api_keys)} keys EXHAUSTED"
                        )
                        if self._try_reset_all_keys():
                            exhausted_rotation_start_key = None  # Reset for next round
                            continue
                        else:
                            raise Exception("All API keys are exhausted (insufficient balance)")
                    else:
                        # Still have keys to try in this rotation
                        self.logger.info(
                            f"Trying next key: Key #{current_key} ({self._get_key_preview(current_key)}) -> "
                            f"Key #{next_key} ({self._get_key_preview(next_key)})"
                        )
                        self.current_key_index = next_key
                        continue

                # Handle rate limit (429) - try rotating to another key first
                if response.status_code == 429:
                    self.key_stats[current_key]['errors'] += 1
                    keys_tried_for_rate_limit.add(current_key)
                    self.logger.warning(
                        f"Rate limited on Key #{current_key} ({self._get_key_preview(current_key)})"
                    )

                    # Try rotating to a key that hasn't been rate limited
                    rotated = False
                    for _ in range(len(self.api_keys)):
                        if self._rotate_key(reason="rate limit"):
                            if self.current_key_index not in keys_tried_for_rate_limit:
                                rotated = True
                                break

                    if rotated:
                        continue  # Retry with new key

                    # All keys rate limited, wait and retry
                    if attempt < max_retries - 1:
                        self.logger.info(
                            f"All keys rate limited. Waiting {retry_delay}s before retry "
                            f"(attempt {attempt + 1}/{max_retries})"
                        )
                        keys_tried_for_rate_limit.clear()
                        time.sleep(retry_delay)
                        continue

                # Handle other errors
                self.key_stats[current_key]['errors'] += 1
                error_msg = f"API error {response.status_code}"
                try:
                    error_data = response.json()
                    if 'error' in error_data:
                        error_msg = f"{error_msg}: {error_data['error']}"
                except:
                    error_msg = f"{error_msg}: {response.text[:100]}"

                self.logger.warning(f"Key #{current_key}: {error_msg}")

                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue

                response.raise_for_status()

            except requests.exceptions.Timeout:
                self.key_stats[current_key]['errors'] += 1
                self.logger.warning(f"Request timeout on Key #{current_key}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                raise Exception("Request timed out after all retries")

            except requests.exceptions.RequestException as e:
                self.key_stats[current_key]['errors'] += 1
                self.logger.warning(f"Request error on Key #{current_key}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                raise

            except Exception as e:
                if "exhausted" in str(e).lower():
                    raise  # Re-raise exhaustion errors
                self.key_stats[current_key]['errors'] += 1
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                raise

        return None

    def reset_exhausted_keys(self):
        """Reset exhausted keys (call this if keys have been recharged)"""
        if self.exhausted_keys:
            self.logger.info(f"Resetting {len(self.exhausted_keys)} exhausted keys")
            self.exhausted_keys.clear()
            self.continuous_failure_start = None
