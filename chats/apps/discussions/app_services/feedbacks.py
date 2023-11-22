import json


def create_feedback_json(method: str, content: dict):
    return {"method": method, "content": content}


def create_discussion_feedback_message(
    discussion: object, feedback: dict, method: str, notify=True
):
    return discussion.create_discussion_message(
        message=json.dumps(create_feedback_json(method=method, content=feedback)),
        system=True,
        notify=notify,
    )
