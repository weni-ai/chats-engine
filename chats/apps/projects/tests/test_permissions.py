from django.urls import get_resolver, Resolver404, URLResolver
from django.test import TestCase
from django.urls import resolve


class EndpointPermissionTestCase(TestCase):
    def test_endpoints_have_permissions(self):
        resolver = get_resolver()

        def get_all_urls(urlpatterns, prefix=""):
            urls = []
            for pattern in urlpatterns:
                if isinstance(pattern, URLResolver):
                    urls.extend(
                        get_all_urls(
                            pattern.url_patterns, prefix + str(pattern.pattern)
                        )
                    )
                else:
                    urls.append(prefix + str(pattern.pattern))
            return urls

        all_urls = get_all_urls(resolver.url_patterns)

        for path in all_urls:
            try:
                match = resolve(path)
                view = match.func.view_class

                self.assertTrue(
                    hasattr(view, "permission_classes"),
                    f"O endpoint {path} não possui permission_classes definidas.",
                )
            except Resolver404:
                continue
            except AttributeError:
                continue
