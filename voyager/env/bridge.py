import logging
import os.path
import time
import warnings
from typing import SupportsFloat, Any, Tuple, Dict

import requests
import json

import gymnasium as gym
from gymnasium.core import ObsType

import voyager.utils as U

from .minecraft_launcher import MinecraftInstance
from .process_monitor import SubprocessMonitor

logger = logging.getLogger(__name__)


class VoyagerEnv(gym.Env):
    def __init__(
        self,
        mc_port=None,
        username="bot",
        azure_login=None,
        server_host="http://127.0.0.1",
        server_port=3000,
        request_timeout=10,
        polling_timeout=600,
        polling_interval=1,
        log_path="./logs",
    ):
        if not mc_port and not azure_login:
            raise ValueError("Either mc_port or azure_login must be specified")
        if mc_port and azure_login:
            warnings.warn(
                "Both mc_port and mc_login are specified, mc_port will be ignored"
            )
        self.mc_port = mc_port
        self.username = username
        self.azure_login = azure_login
        self.server = f"{server_host}:{server_port}"
        self.server_port = server_port
        self.request_timeout = request_timeout
        self.polling_timeout = polling_timeout
        self.polling_interval = polling_interval
        self.log_path = log_path
        self.mineflayer = self.get_mineflayer_process(server_port)
        if azure_login:
            self.mc_instance = self.get_mc_instance()
        else:
            self.mc_instance = None
        self.has_reset = False
        self.reset_options = None
        self.connected = False
        self.server_paused = False

    def get_mineflayer_process(self, server_port):
        U.f_mkdir(self.log_path, "mineflayer")
        file_path = os.path.abspath(os.path.dirname(__file__))
        return SubprocessMonitor(
            commands=[
                "node",
                U.f_join(file_path, "mineflayer/index.js"),
                str(server_port),
            ],
            name=self.username,
            ready_match=r"Server started on port (\d+)",
            log_path=U.f_join(self.log_path, "mineflayer"),
        )

    def get_mc_instance(self):
        print("Creating Minecraft server")
        U.f_mkdir(self.log_path, "minecraft")
        return MinecraftInstance(
            **self.azure_login,
            mineflayer=self.mineflayer,
            log_path=U.f_join(self.log_path, "minecraft"),
        )

    def restart_mineflayer(self):
        if self.mc_instance and not self.mc_instance.is_running:
            # if self.mc_instance:
            #     self.mc_instance.check_process()
            #     if not self.mc_instance.is_running:
            print("Starting Minecraft server")
            self.mc_instance.run()
            self.mc_port = self.mc_instance.port
            self.reset_options["port"] = self.mc_instance.port
            print(f"Server started on port {self.reset_options['port']}")
        retry = 0
        while not self.mineflayer.is_running and retry <= 10:
            retry += 1
            print("Mineflayer process has exited, restarting")
            self.mineflayer.run()
            if not self.mineflayer.is_running:
                continue

        for retry in range(10):
            # janky wait to make sure process has started
            try:
                # Maybe mineflayer is not running in subsequent tries
                if not self.mineflayer.is_running:
                    print("Mineflayer process has exited, restarting")
                    self.mineflayer.run()

                res = requests.post(
                    f"{self.server}/start",
                    json=self.reset_options,
                    timeout=10, #self.request_timeout,
                )
                if res.status_code != 200:
                    self.mineflayer.stop()
                    raise RuntimeError(
                        f"Minecraft server reply with code {res.status_code}"
                    )
            except:
                print('bot start failed, retrying...')
                continue
            print(self.mineflayer.ready_line)
            return res.json()

    def check_process(self):
        if self.mc_instance and not self.mc_instance.is_running:
            # if self.mc_instance:
            #     self.mc_instance.check_process()
            #     if not self.mc_instance.is_running:
            print("Starting Minecraft server")
            self.mc_instance.run()
            self.mc_port = self.mc_instance.port
            self.reset_options["port"] = self.mc_instance.port
            print(f"Server started on port {self.reset_options['port']}")
        retry = 0
        while not self.mineflayer.is_running and retry <= 10:
            retry += 1
            print("Mineflayer process has exited, restarting")
            self.mineflayer.run()

            try:
                res = requests.post(
                    f"{self.server}/start",
                    json=self.reset_options,
                    timeout=10, #self.request_timeout,
                )
                if res.status_code != 200:
                    self.mineflayer.stop()
                    raise RuntimeError(
                        f"Minecraft server reply with code {res.status_code}"
                    )
            except:
                print('bot start failed, retrying...')
                continue
            print(self.mineflayer.ready_line)
            return res.json()

    def step(
        self,
        code: str,
        programs: str = "",
    ) -> Tuple[ObsType, SupportsFloat, bool, bool, Dict[str, Any]]:
        if not self.has_reset:
            raise RuntimeError("Environment has not been reset yet")
        self.check_process()
        # self.unpause()
        data = {
            "code": code,
            "programs": programs,
        }

        res = requests.post(f"{self.server}/step", json=data, timeout=self.request_timeout)

        if res.status_code == 200:
            return json.loads(res.json())
        elif res.status_code == 400:
            raise RuntimeError(f"Error in request: {res.json()}")
        elif res.status_code == 202:
            logger.debug("Step is executing. Polling for status...")
            return self.poll_for_status()
        else:
            raise RuntimeError(f"Minecraft server replied with code {res.status_code}")

    def poll_for_status(self):
        start_time = time.time()
        while True:
            try:
                # Polling endpoint (adjust the endpoint as needed)
                res = requests.get(f"{self.server}/status", timeout=self.request_timeout)
                if res.status_code == 200:
                    logger.debug("Step completed.")
                    return json.loads(res.json())
                elif res.status_code == 400:
                    raise RuntimeError(f"Error in request: {res.json()}")
                elif res.status_code != 202:
                    raise RuntimeError(f"Unexpected server response: {res.status_code}")
            except requests.RequestException as e:
                raise RuntimeError(f"Error polling server: {e}")

            # Check for timeout
            if time.time() - start_time > self.polling_timeout:
                raise RuntimeError("Polling timed out.")

            time.sleep(self.polling_interval)

    def render(self):
        raise NotImplementedError("render is not implemented")

    def reset(
        self,
        *,
        seed=None,
        options=None,
    ) -> list[tuple[str, dict[str, any]]]:
        if options is None:
            options = {}

        if options.get("inventory", {}) and options.get("mode", "hard") != "hard":
            raise RuntimeError("inventory can only be set when options is hard")

        self.reset_options = {
            "port": self.mc_port,
            "username": self.username,
            "reset": options.get("mode", "hard"),
            "inventory": options.get("inventory", {}),
            "equipment": options.get("equipment", []),
            "spread": options.get("spread", False),
            "waitTicks": options.get("wait_ticks", 5),
            "position": options.get("position", None),
        }

        # self.unpause()
        self.mineflayer.stop()
        time.sleep(1)  # wait for mineflayer to exit

        returned_data = self.restart_mineflayer()
        self.has_reset = True
        self.connected = True
        # All the reset in step will be soft
        self.reset_options["reset"] = "soft"
        # self.pause()
        return json.loads(returned_data) if returned_data else []

    def close(self):
        logger.info('close')
        # self.unpause()
        if self.connected:
            res = requests.post(f"{self.server}/stop")
            if res.status_code == 200:
                self.connected = False
        if self.mc_instance:
            self.mc_instance.stop()
        self.mineflayer.stop()
        return not self.connected

    def pause(self):
        if self.mineflayer.is_running and not self.server_paused:
            res = requests.post(f"{self.server}/pause")
            if res.status_code == 200:
                self.server_paused = True
        return self.server_paused

    def unpause(self):
        if self.mineflayer.is_running and self.server_paused:
            res = requests.post(f"{self.server}/pause")
            if res.status_code == 200:
                self.server_paused = False
            else:
                print(res.json())
        return self.server_paused
