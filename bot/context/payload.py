from dataclasses import dataclass
from typing import Dict


@dataclass
class Payload:
    message: str
    callback: Dict
