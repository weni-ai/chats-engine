from chats.celery import app
from chats.apps.feature_flags.integrations.growthbook.instance import GROWTHBOOK_CLIENT


@app.task
def update_growthbook_feature_flags():
    """
    Update the growthbook feature flags definitions.
    """
    GROWTHBOOK_CLIENT.update_feature_flags_definitions()
