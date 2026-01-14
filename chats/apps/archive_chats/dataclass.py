from dataclasses import dataclass


@dataclass(frozen=True)
class ArchiveMessageMedia:
    url: str
    content_type: str
