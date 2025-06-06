import os
import time
import re
import warnings
from typing import List, Optional, Callable

import psutil
import subprocess
import logging
import threading

import voyager.utils as U


class SubprocessMonitor:
    def __init__(
        self,
        commands: List[str],
        name: str,
        ready_match: str = r".*",
        log_path: Optional[str] = None,
        callback_match: str = r"^(?!x)x$",  # regex that will never match
        callback: Callable = None,
        finished_callback: callable = None,
        cwd: os.PathLike = None,
    ):
        self.commands = commands
        start_time = time.strftime("%Y%m%d_%H%M%S")
        self.name = name
        self.logger = logging.getLogger(name)
        # Clear existing handlers from previous runs
        for handler in self.logger.handlers:
            self.logger.removeHandler(handler)
        if log_path is not None:
            handler = logging.FileHandler(U.f_join(log_path, f"{name}_{start_time}.log"))
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
        self.process: Optional[psutil.Popen] = None
        self.ready_match = ready_match
        self.ready_event = None
        self.ready_line = None
        self.callback_match = callback_match
        self.callback = callback
        self.finished_callback = finished_callback
        self.cwd = cwd
        self.thread = None

    def _start(self):
        self.logger.info(f"Starting subprocess with commands: {self.commands}")

        self.process = psutil.Popen(
            self.commands,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            cwd=self.cwd,
        )
        self.logger.info(f"Subprocess {self.name} started with PID {self.process.pid}.")
        for line in iter(self.process.stdout.readline, ""):
            self.logger.info(line.strip())
            if re.search(self.ready_match, line):
                self.ready_line = line
                self.logger.info("Subprocess is ready.")
                self.ready_event.set()
            if match := re.search(self.callback_match, line):
                self.callback(match)
        if not self.ready_event.is_set():
            self.ready_event.set()
            warnings.warn(f"Subprocess {self.name} failed to start.")
        if self.finished_callback:
            self.finished_callback()

    def run(self):
        self.ready_event = threading.Event()
        self.ready_line = None
        self.thread = threading.Thread(target=self._start)
        self.thread.start()
        self.ready_event.wait()

    def stop(self):
        self.logger.info("Stopping subprocess.")
        if self.process and self.process.is_running():
            self.process.terminate()
            self.process.wait()

    # def __del__(self):
    #     if self.process.is_running():
    #         self.stop()

    @property
    def is_running(self):
        if self.process is None:
            return False
        return self.process.is_running()
