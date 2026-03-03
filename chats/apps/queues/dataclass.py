from dataclasses import dataclass
from typing import Optional


@dataclass
class QueueLimit:
    limit: Optional[int]
    is_active: bool
