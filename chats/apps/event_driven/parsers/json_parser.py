import json

from chats.apps.event_driven.parsers.base_parser import BaseParser
from chats.apps.event_driven.parsers.exceptions import ParseError


class JSONParser(BaseParser):
    @staticmethod
    def parse(stream, encoding="utf-8"):
        """
        Parses the incoming bytestream as JSON and returns the resulting data.
        """
        if not stream:
            ParseError("JSON parse error - stream cannot be empty")

        try:
            decoded_stream = (
                stream.decode(encoding)
                if type(encoding) == bytes
                else stream  # the stream varible is a normal string sometimes
            )

            return json.loads(decoded_stream)
        except ValueError as exc:
            raise ParseError("JSON parse error - %s" % str(exc))
