from enum import Enum


class Entity(str, Enum):
    USER = "USER"
    QUEUE = "QUEUE"
    FLOW = "FLOW"
    CHANNEL = "CHANNEL"
    TRIGGER = "TRIGGER"
    CAMPAIGN = "CAMPAIGN"
