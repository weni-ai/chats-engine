from rest_framework.throttling import UserRateThrottle


class AITextImprovementThrottle(UserRateThrottle):
    scope = "ai_text_improvement"
