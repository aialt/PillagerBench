import threading
from pathlib import Path
from string import Template
from typing import Optional, Iterable


def load_script(path: Path, info: Optional[dict[str, any]]) -> str:
    with open(path, "r") as fp:
        script = fp.read()

    if info is not None:
        script = inject_info(script, info)

    return script


def inject_info(script: str, info: dict[str, any]) -> str:
    # Replace tuples with strings
    replaced_dict = {}
    for key, value in info.items():
        if isinstance(value, tuple):
            replaced_dict[key] = ", ".join(str(x) for x in value)
        else:
            replaced_dict[key] = value

    template = Template(script)
    result = template.safe_substitute(replaced_dict)
    return result


def run_threads(targets, args: Optional[list[Iterable]] = None, shared_args: Optional[list] = None,
                shared_kwargs: Optional[dict] = None, join: bool = True):
    if args is None:
        args = [[] for _ in targets]
    if shared_args:
        args = [shared_args for _ in targets]

    threads = []
    for i, target in enumerate(targets):
        thread = threading.Thread(target=target, args=args[i], kwargs=shared_kwargs, daemon=True)
        threads.append(thread)
        thread.start()
    if join:
        for thread in threads:
            thread.join()
