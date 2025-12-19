"""
Chrome driver management for backfill module.
"""

import logging
import os
import platform
from typing import Optional

from .config import BackfillConfig


class DriverManager:
    """Manages Chrome driver instances for web scraping"""

    def __init__(self, config: BackfillConfig, logger: logging.Logger = None):
        self.config = config
        self.logger = logger or logging.getLogger('backfill.drivers')
        self.virtual_display = None
        self._xvfb_started = False

    def _is_macos(self) -> bool:
        return platform.system() == 'Darwin'

    def _has_real_display(self) -> bool:
        """Check if we have a real display available"""
        if self._is_macos():
            return True
        return bool(os.environ.get('DISPLAY'))

    def _is_in_container(self) -> bool:
        """Check if running in a container with Chromium"""
        return os.path.exists('/usr/bin/chromium') or os.path.exists('/usr/bin/chromium-browser')

    def _get_chromium_path(self) -> str:
        """Get path to Chromium binary"""
        if os.path.exists('/usr/bin/chromium'):
            return '/usr/bin/chromium'
        return '/usr/bin/chromium-browser'

    def _start_virtual_display(self) -> bool:
        """Start virtual display if needed"""
        if self._xvfb_started or self.virtual_display:
            return True

        need_xvfb = self.config.use_xvfb or (not self._has_real_display() and not self.config.headless)

        if not need_xvfb:
            return False

        try:
            from pyvirtualdisplay import Display
            self.virtual_display = Display(visible=False, size=(1920, 1080))
            self.virtual_display.start()
            self._xvfb_started = True
            self.logger.info("Virtual display started (Xvfb)")
            return True
        except ImportError:
            self.logger.warning("pyvirtualdisplay not installed")
            if not self._has_real_display():
                self.logger.warning("No display available, using headless mode")
                self.config.headless = True
            return False
        except Exception as e:
            self.logger.warning(f"Failed to start virtual display: {e}")
            if not self._has_real_display():
                self.logger.warning("No display available, using headless mode")
                self.config.headless = True
            return False

    def stop_virtual_display(self):
        """Stop virtual display if running"""
        if self.virtual_display:
            try:
                self.virtual_display.stop()
                self.logger.info("Virtual display stopped")
            except:
                pass
            self.virtual_display = None
            self._xvfb_started = False

    def create_driver(self):
        """Create a new Chrome driver instance"""
        self._start_virtual_display()
        in_container = self._is_in_container()

        if in_container:
            return self._create_container_driver()
        else:
            return self._create_local_driver()

    def _create_container_driver(self):
        """Create driver for container environment"""
        chromium_path = self._get_chromium_path()

        # Try undetected-chromedriver first
        try:
            import undetected_chromedriver as uc

            options = uc.ChromeOptions()
            if self.config.headless:
                options.add_argument('--headless=new')

            self._add_common_options(options)
            options.binary_location = chromium_path

            driver = uc.Chrome(
                options=options,
                version_main=None,
                browser_executable_path=chromium_path
            )
            driver.set_page_load_timeout(self.config.page_load_timeout)
            self.logger.info(f"Created undetected-chromedriver with Chromium at: {chromium_path}")
            return driver

        except Exception as e:
            self.logger.warning(f"Failed to use undetected-chromedriver: {e}")
            return self._create_selenium_driver(chromium_path)

    def _create_selenium_driver(self, chromium_path: str):
        """Create standard Selenium driver as fallback"""
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options

        options = Options()
        if self.config.headless:
            options.add_argument('--headless=new')

        self._add_common_options(options)
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)
        options.binary_location = chromium_path

        self.logger.info(f"Using Chromium at: {chromium_path}")

        chromedriver_path = '/usr/bin/chromedriver'
        if os.path.exists(chromedriver_path):
            service = Service(executable_path=chromedriver_path)
            self.logger.info(f"Using chromedriver at: {chromedriver_path}")
        else:
            service = Service()

        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(self.config.page_load_timeout)

        self.logger.info(f"Chrome driver initialized (headless={self.config.headless}, xvfb={self._xvfb_started})")
        return driver

    def _create_local_driver(self):
        """Create driver for local development"""
        import undetected_chromedriver as uc

        options = uc.ChromeOptions()
        if self.config.headless:
            options.add_argument('--headless=new')

        self._add_common_options(options)

        driver = uc.Chrome(options=options, version_main=None)
        driver.set_page_load_timeout(self.config.page_load_timeout)
        return driver

    def _add_common_options(self, options):
        """Add common Chrome options"""
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--lang=en-AU')
        options.add_argument('--disable-blink-features=AutomationControlled')

    @staticmethod
    def is_driver_alive(driver) -> bool:
        """Check if the Chrome driver is still alive"""
        try:
            _ = driver.current_url
            return True
        except:
            return False

    @staticmethod
    def close_driver(driver):
        """Safely close a driver instance"""
        if driver:
            try:
                driver.quit()
            except:
                pass
