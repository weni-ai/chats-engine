from prometheus_client import Gauge

total_contacts = Gauge(
    name="total_contacts",
    documentation="The number of contacts created in chats",
    labelnames=["total_contacts"],
)

online_contacts = Gauge(
    name="online_contacts",
    documentation="The number of contacts online",
    labelnames=["online_contact"],
)

total_contacts_last_month = Gauge(
    name="total_contacts_last_month",
    documentation="The number of contacts created last month in chats",
    labelnames=["total_contacts_last_month"],
)

total_contacts_last_3_months = Gauge(
    name="total_contacts_last_3_month",
    documentation="The number of contacts created last 3 months in chats",
    labelnames=["total_contacts_last_3_month"],
)

total_contacts_last_6_months = Gauge(
    name="total_contacts_last_6_months",
    documentation="The number of contacts created last 6 months in chats",
    labelnames=["total_contacts_last_6_months"],
)

total_contacts_last_1_year = Gauge(
    name="total_contacts_last_1_year",
    documentation="The number of contacts created last year in chats",
    labelnames=["total_contacts_last_1_year"],
)

offline_contacts = Gauge(
    name="offline_contacts",
    documentation="The number of contacts offline",
    labelnames=["offline_contact"],
)

total_rooms = Gauge(
    name="total_rooms",
    documentation="The number of rooms created in chats",
    labelnames=["total_rooms"],
)

opened_rooms = Gauge(
    name="opened_rooms",
    documentation="The number of rooms opened in chats",
    labelnames=["opened_rooms"],
)

closed_rooms = Gauge(
    name="closed_rooms",
    documentation="The number of rooms closed in chats",
    labelnames=["closed_rooms"],
)

total_message = Gauge(
    name="total_message",
    documentation="The number of messages created in chats",
    labelnames=["total_message"],
)

total_agents = Gauge(
    name="total_agents",
    documentation="The number of agents created in chats",
    labelnames=["total_agents"],
)

total_rooms_last_month = Gauge(
    name="total_rooms_last_month",
    documentation="The number of rooms created last month in chats",
    labelnames=["total_rooms_last_month"],
)

total_rooms_last_3_months = Gauge(
    name="total_rooms_last_3_months",
    documentation="The number of rooms created last 3 months in chats",
    labelnames=["total_rooms_last_3_months"],
)

total_rooms_last_6_months = Gauge(
    name="total_rooms_last_6_months",
    documentation="The number of rooms created last 6 months in chats",
    labelnames=["total_rooms_last_6_months"],
)

total_rooms_last_year = Gauge(
    name="total_rooms_last_year",
    documentation="The number of rooms created last year in chats",
    labelnames=["total_rooms_last_year"],
)

total_msgs_last_month = Gauge(
    name="total_msgs_last_month",
    documentation="The number of msgs created last month in chats",
    labelnames=["total_msgs_last_month"],
)

total_msgs_last_3_months = Gauge(
    name="total_msgs_last_3_months",
    documentation="The number of msgs created last 3 months in chats",
    labelnames=["total_msgs_last_3_months"],
)

total_msgs_last_6_months = Gauge(
    name="total_msgs_last_6_months",
    documentation="The number of msgs created last 6 months in chats",
    labelnames=["total_msgs_last_6_months"],
)

total_msgs_last_year = Gauge(
    name="total_msgs_last_year",
    documentation="The number of msgs created last year in chats",
    labelnames=["total_msgs_last_year"],
)

total_agents_last_month = Gauge(
    name="total_agents_last_month",
    documentation="The number of agents created last month in chats",
    labelnames=["total_msgs_last_month"],
)

total_agents_last_3_months = Gauge(
    name="total_agents_last_3_months",
    documentation="The number of agents created last 3 months in chats",
    labelnames=["total_msgs_last_3_months"],
)

total_agents_last_6_months = Gauge(
    name="total_agents_last_6_months",
    documentation="The number of agents created last 6 months in chats",
    labelnames=["total_msgs_last_6_months"],
)

total_agents_last_year = Gauge(
    name="total_agents_last_year",
    documentation="The number of agents created last year in chats",
    labelnames=["total_msgs_last_year"],
)