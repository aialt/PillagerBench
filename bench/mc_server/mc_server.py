import dataclasses
import shutil
from pathlib import Path
from string import Template

from voyager.env.process_monitor import SubprocessMonitor

SERVER_PATH = Path(__file__).parent
SERVER_PROPERTIES_TEMPLATE_PATH = SERVER_PATH / "server_properties_template"
SERVER_JAR_PATH = SERVER_PATH / "server.jar"


@dataclasses.dataclass
class ServerProperties:
    allow_nether: bool = True
    difficulty: str = "peaceful"
    generate_structures: bool = True
    level_name: str = "world"
    level_seed: str = ""
    level_type: str = "normal"
    motd: str = "A PillagerBench Server"
    server_port: int = 3000
    spawn_animals: bool = True
    spawn_monsters: bool = True
    spawn_npcs: bool = True


class McServer:
    def __init__(
            self,
            server_port: int = 3000,
    ):
        self.server_port = server_port
        self.minecraft_server = self.get_minecraft_server_process()

    def get_minecraft_server_process(self):
        return SubprocessMonitor(
            commands=[
                "java",
                "-Xmx1024M",
                "-Xmx1024M",
                "-jar",
                str(SERVER_JAR_PATH),
                "nogui",
            ],
            name="minecraft_server",
            ready_match=r"Done \(\d*\.\d*s\)! For help, type \"help\"",
            callback_match=r": ([a-zA-Z0-9_]{2,16}) joined the game$",
            callback=self._op_everyone_callback,
            cwd=SERVER_PATH,
        )

    def _op_everyone_callback(self, match):
        if match is None:
            return
        self.minecraft_server.process.stdin.write(f"op {match.group(1)}\n")
        self.minecraft_server.process.stdin.flush()

    def run(self, server_properties: ServerProperties, use_temp_world=True, reset_world=False):
        server_properties.server_port = self.server_port

        if use_temp_world:
            # Keep the original level as backup and run the benchmark in a copy
            copy_name = "world"
            copy_path = SERVER_PATH / copy_name
            original_path = SERVER_PATH / server_properties.level_name
            server_properties.level_name = copy_name

            # Step 1: Remove all contents of the copy
            if copy_path.exists() and copy_path.is_dir():
                shutil.rmtree(copy_path)  # Remove the folder and its contents
            copy_path.mkdir()  # Recreate the empty "world" folder

            # Step 2: Copy contents of the original to the copy
            for item in original_path.iterdir():
                dest = copy_path / item.name
                if item.is_dir():
                    shutil.copytree(item, dest)
                else:
                    shutil.copy2(item, dest)

        # Load server_properties_template, replace values with server_properties, and write to server.properties
        with open(SERVER_PROPERTIES_TEMPLATE_PATH, "r") as fp:
            template = Template(fp.read())
            # noinspection PyTypeChecker
            server_properties_dict = dataclasses.asdict(server_properties)
            result = template.safe_substitute(server_properties_dict)

            with open(SERVER_PATH / "server.properties", "w") as f:
                f.write(result)

        # Optionally delete the world folder
        if reset_world:
            world_folder = SERVER_PATH / server_properties.level_name
            if world_folder.exists():
                shutil.rmtree(world_folder)

        # Start the server
        self.minecraft_server.run()

    def stop(self):
        self.minecraft_server.logger.info("Stopping subprocess.")
        if self.minecraft_server.process and self.minecraft_server.process.is_running():
            children = self.minecraft_server.process.children(recursive=True)
            for child in children:
                child.terminate()
                child.wait()
            if self.minecraft_server.process.is_running():
                self.minecraft_server.process.terminate()
                self.minecraft_server.process.wait()

    @property
    def is_running(self):
        return self.minecraft_server.is_running
