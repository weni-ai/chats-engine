"""Renders the room export data into HTML and/or PDF documents.

The use case is deliberately dumb: it takes the dict produced by
`BuildRoomExportData` plus a list of requested output types and returns the
corresponding bytes. Network I/O (media fetching, base64 embedding) is the
responsibility of the caller, kept out of here so the renderer stays
deterministic and side-effect free.
"""

from typing import Dict, Iterable, Set

from django.template.loader import render_to_string

FORMAT_HTML = "html"
FORMAT_PDF = "pdf"
SUPPORTED_FORMATS = (FORMAT_HTML, FORMAT_PDF)

DEFAULT_TEMPLATE = "rooms/exports/conversation.html"


class UnsupportedExportFormatError(ValueError):
    """Raised when an unknown export format is requested."""


class RenderRoomExport:
    """Renders room export data into the requested document formats."""

    def __init__(self, template_name: str = DEFAULT_TEMPLATE):
        self.template_name = template_name

    def execute(self, data: dict, types: Iterable[str]) -> Dict[str, bytes]:
        normalized = self._normalize_types(types)
        output: dict[str, bytes] = {}

        if FORMAT_HTML in normalized:
            output[FORMAT_HTML] = self._render_html(data, embed_media=True)

        if FORMAT_PDF in normalized:
            output[FORMAT_PDF] = self._render_pdf(data)

        return output

    def _normalize_types(self, types: Iterable[str]) -> Set[str]:
        if not types:
            raise UnsupportedExportFormatError("At least one export format is required")

        normalized = {str(t).lower() for t in types if t}
        invalid = normalized - set(SUPPORTED_FORMATS)
        if invalid:
            raise UnsupportedExportFormatError(
                f"Unsupported export format(s): {sorted(invalid)}"
            )
        return normalized

    def _render_template(self, data: dict, embed_media: bool) -> str:
        context = {**data, "embed_media": embed_media}
        return render_to_string(self.template_name, context)

    def _render_html(self, data: dict, embed_media: bool) -> bytes:
        html_str = self._render_template(data, embed_media=embed_media)
        return html_str.encode("utf-8")

    def _render_pdf(self, data: dict) -> bytes:
        # PDF uses external URLs for medias; embed_media is False so the
        # template references media.url instead of media.data_uri.
        html_str = self._render_template(data, embed_media=False)
        # Import lazily so projects that don't need PDF rendering (and don't
        # have weasyprint's native deps installed) can still import this
        # module without crashing.
        from weasyprint import HTML

        return HTML(string=html_str).write_pdf()


__all__ = [
    "RenderRoomExport",
    "UnsupportedExportFormatError",
    "FORMAT_HTML",
    "FORMAT_PDF",
    "SUPPORTED_FORMATS",
    "DEFAULT_TEMPLATE",
]
