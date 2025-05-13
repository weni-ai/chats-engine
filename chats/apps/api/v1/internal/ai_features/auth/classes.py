from chats.apps.accounts.authentication.classes import BaseHMACSignatureAuthentication


class AIFeaturesAuthentication(BaseHMACSignatureAuthentication):
    """
    Authentication class for the AI Features API.
    """

    _secret_setting_key = "AI_FEATURES_PROMPTS_API_SECRET"
