def validate_queue_and_room(queue, room):
    return queue.sector.project == room.queue.sector.project
