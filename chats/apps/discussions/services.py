def create_discussion_message_and_notify(discussion, message):
    msg = discussion.messages.create(user=discussion.user, text=message)
    msg.notify_discussion("create")
