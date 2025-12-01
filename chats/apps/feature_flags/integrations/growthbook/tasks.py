from chats.celery import app


@app.task
def update_growthbook_feature_flags():
    """
    Update the growthbook feature flags definitions.
    This task is now handled by weni-commons internally.
    """
    from chats.apps.feature_flags.integrations.growthbook.instance import (
        FEATURE_FLAGS_SERVICE,
    )

    if hasattr(FEATURE_FLAGS_SERVICE, 'update_feature_flags_definitions'):
        FEATURE_FLAGS_SERVICE.update_feature_flags_definitions()
