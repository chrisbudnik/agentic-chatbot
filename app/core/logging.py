import logging
from logging import LogRecord
from uvicorn.logging import DefaultFormatter
from app.core.config import settings
import re


class Ansi:
	RESET = "\x1b[0m"
	BOLD = "\x1b[1m"

	RED = "\x1b[31m"
	GREEN = "\x1b[32m"
	YELLOW = "\x1b[33m"
	BLUE = "\x1b[34m"
	MAGENTA = "\x1b[35m"
	CYAN = "\x1b[36m"


LEVEL_COLORS = {
	"DEBUG": Ansi.CYAN,
	"INFO": Ansi.GREEN,
	"WARNING": Ansi.YELLOW,
	"ERROR": Ansi.RED,
	"CRITICAL": Ansi.RED + Ansi.BOLD,
}


def color_status(status: int) -> str:
	if 200 <= status < 300:
		return f"{Ansi.GREEN}{status}{Ansi.RESET}"
	if 300 <= status < 400:
		return f"{Ansi.CYAN}{status}{Ansi.RESET}"
	if 400 <= status < 500:
		return f"{Ansi.YELLOW}{status}{Ansi.RESET}"
	return f"{Ansi.RED}{status}{Ansi.RESET}"


class CustomDefaultFormatter(DefaultFormatter):
	def format(self, record):
		if settings.LOG_MODE == "json":
			log_record = {
				"time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
				"severity": record.levelname,
				"logger": record.name,
				"message": record.getMessage(),
			}

		else:
			color = LEVEL_COLORS.get(record.levelname, "")
			log_record = (
				f"{color}{record.levelname}{Ansi.RESET} | "
				f"{self.formatTime(record, '%Y-%m-%d %H:%M:%S')} | "
				f"{Ansi.BLUE}{record.name}{Ansi.RESET} | "
				f"{record.getMessage()}"
			)

		return str(log_record)


class CustomAccessFormatter(DefaultFormatter):
	_request_re = re.compile(r'"(.*?)" (\d{3})')

	def format(self, record: LogRecord) -> str:
		if settings.LOG_MODE == "json":
			return str(
				{
					"severity": record.levelname,
					"time": self.formatTime(record, "%Y-%m-%d %H:%M:%S"),
					"logger": record.name,
					"message": record.getMessage(),
				}
			)

		message = record.getMessage()

		# --- color severity ---
		level_color = LEVEL_COLORS.get(record.levelname, "")
		level = f"{level_color}{record.levelname}{Ansi.RESET}"

		# --- bold request + color status ---
		match = self._request_re.search(message)
		if match:
			request, status = match.groups()
			status_colored = color_status(int(status))
			request_bold = f'{Ansi.BOLD}"{request}"{Ansi.RESET}'

			message = self._request_re.sub(
				f"{request_bold} {status_colored}", message
			)

		return (
			f"{level} | "
			f"{self.formatTime(record, '%Y-%m-%dT%H:%M:%S')} | "
			f"{message}"
		)


def get_logger(name: str) -> logging.Logger:
	"""
	Get a logger that uses Uvicorn's default formatting.
	"""
	logger = logging.getLogger(name)
	return logger
