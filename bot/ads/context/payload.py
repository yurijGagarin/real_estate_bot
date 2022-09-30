from dataclasses import dataclass
from typing import Dict, Optional

from telegram import File, Contact


@dataclass
class Payload:
    message: Optional[str]
    callback: Dict
    file: Optional[File]
    contact: Optional[Contact]
