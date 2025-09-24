from django.db import models


class FeedbackRate(models.IntegerChoices):
    """
    Feedback rate choices
    """

    BAD = 1
    NEUTRAL = 2
    GOOD = 3
