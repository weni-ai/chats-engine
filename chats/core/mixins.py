class LanguageViewMixin:
    """
    Mixin to get the language from the request headers or the user language.
    """

    def get_language(self) -> str:
        """
        Get the language from the request headers.
        """
        user_language = None
        headers_language = self.request.headers.get("Accept-Language")

        if self.request.user.is_authenticated and not headers_language:
            user_language = self.request.user.language

        return headers_language or user_language or "en"
