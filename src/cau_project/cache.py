import hashlib
from pathlib import Path

import ee
from geemap.cartoee import *

CACHE_DIR = Path(".ee_cache/")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def ee_hash(obj: ee.ComputedObject) -> str:
    serialized = obj.serialize()  # string JSON do grafo de computação
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
