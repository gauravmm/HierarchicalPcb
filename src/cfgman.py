import contextlib
import logging
from pathlib import Path
from types import TracebackType
from typing import Any
import json

logger = logging.getLogger("hierpcb")


class ConfigMan(contextlib.AbstractContextManager):
    def __init__(self, path: Path):
        self.path = path

    def __enter__(self) -> "ConfigMan":
        try:
            with self.path.open("r") as fp:
                self.config = json.load(fp)
        except FileNotFoundError:
            logger.warning(f"Config file {self.path} not found. Creating new one.")
            self.config = {}
        return self

    def __exit__(self, *args):
        with self.path.open("w") as fp:
            json.dump(self.config, fp, indent=2)
        return super().__exit__(*args)

    def get(self, *key: str, default=None):
        node = self.config
        for k in key:
            node = node.get(k)
            if node is None:
                return default
        return node

    def clear(self, *key: str):
        node = self.config
        for k in key[:-1]:
            node = node.get(k)
            if node is None:
                return
        node.pop(key[-1], None)

    def set(self, *key: str, value, create_missing=True):
        node = self.config
        terminal = key[-1]
        prefix = []
        for k in key[:-1]:
            prefix.append(k)
            node_next = node.get(k)
            if node_next is None:
                if create_missing:
                    node[k] = node_next = {}
                else:
                    raise KeyError(f"Key {'.'.join(prefix)} not found in config.")
            node = node_next
        node[terminal] = value
