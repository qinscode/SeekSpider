import logging


class Logger:
    def __init__(self, name, level='INFO'):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level))

        # Only add handler if none exists
        if not self.logger.handlers:
            # Console handler
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)

    def info(self, msg):
        self.logger.info(msg)

    def error(self, msg):
        self.logger.error(msg)

    def warning(self, msg):
        self.logger.warning(msg)

    def debug(self, msg):
        self.logger.debug(msg)

    def exception(self, msg):
        self.logger.exception(msg)
