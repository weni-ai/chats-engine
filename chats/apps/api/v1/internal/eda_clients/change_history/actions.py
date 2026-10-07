from enum import Enum


class Action(str, Enum):
    ADD = "ADD"
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
