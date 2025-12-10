from drf_yasg.inspectors import SwaggerAutoSchema


class TaggedSwaggerAutoSchema(SwaggerAutoSchema):
    """Allow viewsets to declare a single tag/summary per method via attributes."""

    def get_tags(self, operation_keys=None):
        tag = getattr(self.view, "swagger_tag", None)
        if isinstance(tag, (list, tuple)):
            return list(tag)
        if isinstance(tag, str):
            return [tag]
        return super().get_tags(operation_keys)

    def get_summary_and_description(self):
        summary_attr = getattr(self.view, "swagger_summary", None)
        description_attr = getattr(self.view, "swagger_description", None)
        method = self.method.lower()

        summary = (
            summary_attr.get(method) if isinstance(summary_attr, dict) else summary_attr
        )
        description = (
            description_attr.get(method)
            if isinstance(description_attr, dict)
            else description_attr
        )

        parent_summary, parent_description = super().get_summary_and_description()
        return summary or parent_summary, description or parent_description
