# metrics/ws.py
from prometheus_client import Counter, Gauge, Histogram

ws_connections_total = Counter(
    "ws_connections_total", "Total WebSocket connections", ["consumer"]
)

ws_active_connections = Gauge(
    "ws_active_connections", "Current active WebSocket connections", ["consumer"]
)

ws_disconnects_total = Counter(
    "ws_disconnects_total", "Total WebSocket disconnections", ["consumer"]
)

ws_messages_received_total = Counter(
    "ws_messages_received_total", "WebSocket messages received", ["consumer"]
)

ws_connection_duration = Histogram(
    "ws_connection_duration_seconds", "WebSocket connection duration", ["consumer"]
)
