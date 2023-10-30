def create_discussion_message_and_notify(discussion, message):
    msg = discussion.messages.create(user=discussion.user, text=message)
    msg.notify_discussion("create")


def create_discussion_and_initial_message(
    discussion_data: dict, create_function, *args, **kwargs
):
    msg_content = discussion_data.pop("initial_message")
    discussion = create_function(discussion_data, *args, **kwargs)
    discussion.notify("create")
    create_discussion_message_and_notify(discussion, msg_content)
    return discussion
