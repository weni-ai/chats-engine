from prometheus_client import Gauge

chats_total_contacts = Gauge(
    name="chats_total_contacts",
    documentation="The number of contacts created in chats",
    labelnames=["total_contacts"],
)

chats_online_contacts = Gauge(
    name="chats_online_contacts",
    documentation="The number of contacts online",
    labelnames=["online_contact"],
)

chats_total_contacts_last_month = Gauge(
    name="chats_total_contacts_last_month",
    documentation="The number of contacts created last month in chats",
    labelnames=["total_contacts_last_month"],
)

chats_total_contacts_last_3_months = Gauge(
    name="chats_total_contacts_last_3_months",
    documentation="The number of contacts created last 3 months in chats",
    labelnames=["total_contacts_last_3_month"],
)

chats_total_contacts_last_6_months = Gauge(
    name="chats_total_contacts_last_6_months",
    documentation="The number of contacts created last 6 months in chats",
    labelnames=["total_contacts_last_6_months"],
)

chats_total_contacts_last_1_year = Gauge(
    name="chats_total_contacts_last_1_year",
    documentation="The number of contacts created last year in chats",
    labelnames=["total_contacts_last_1_year"],
)

chats_offline_contacts = Gauge(
    name="chats_offline_contacts",
    documentation="The number of contacts offline",
    labelnames=["offline_contact"],
)

chats_total_rooms = Gauge(
    name="chats_total_rooms",
    documentation="The number of rooms created in chats",
    labelnames=["total_rooms"],
)

chats_opened_rooms = Gauge(
    name="chats_opened_rooms",
    documentation="The number of rooms opened in chats",
    labelnames=["opened_rooms"],
)

chats_closed_rooms = Gauge(
    name="chats_closed_rooms",
    documentation="The number of rooms closed in chats",
    labelnames=["closed_rooms"],
)

chats_total_message = Gauge(
    name="chats_total_message",
    documentation="The number of messages created in chats",
    labelnames=["total_message"],
)

chats_total_agents = Gauge(
    name="chats_total_agents",
    documentation="The number of agents created in chats",
    labelnames=["total_agents"],
)

chats_total_rooms_last_month = Gauge(
    name="chats_total_rooms_last_month",
    documentation="The number of rooms created last month in chats",
    labelnames=["total_rooms_last_month"],
)

chats_total_rooms_last_3_months = Gauge(
    name="chats_total_rooms_last_3_months",
    documentation="The number of rooms created last 3 months in chats",
    labelnames=["total_rooms_last_3_months"],
)

chats_total_rooms_last_6_months = Gauge(
    name="chats_total_rooms_last_6_months",
    documentation="The number of rooms created last 6 months in chats",
    labelnames=["total_rooms_last_6_months"],
)

chats_total_rooms_last_year = Gauge(
    name="chats_total_rooms_last_year",
    documentation="The number of rooms created last year in chats",
    labelnames=["total_rooms_last_year"],
)

chats_total_msgs_last_month = Gauge(
    name="chats_total_msgs_last_month",
    documentation="The number of msgs created last month in chats",
    labelnames=["total_msgs_last_month"],
)

chats_total_msgs_last_3_months = Gauge(
    name="chats_total_msgs_last_3_months",
    documentation="The number of msgs created last 3 months in chats",
    labelnames=["total_msgs_last_3_months"],
)

chats_total_msgs_last_6_months = Gauge(
    name="chats_total_msgs_last_6_months",
    documentation="The number of msgs created last 6 months in chats",
    labelnames=["total_msgs_last_6_months"],
)

chats_total_msgs_last_year = Gauge(
    name="chats_total_msgs_last_year",
    documentation="The number of msgs created last year in chats",
    labelnames=["total_msgs_last_year"],
)

chats_total_agents_last_month = Gauge(
    name="chats_total_agents_last_month",
    documentation="The number of agents created last month in chats",
    labelnames=["total_msgs_last_month"],
)

chats_total_agents_last_3_months = Gauge(
    name="chats_total_agents_last_3_months",
    documentation="The number of agents created last 3 months in chats",
    labelnames=["total_msgs_last_3_months"],
)

chats_total_agents_last_6_months = Gauge(
    name="chats_total_agents_last_6_months",
    documentation="The number of agents created last 6 months in chats",
    labelnames=["total_msgs_last_6_months"],
)

chats_total_agents_last_year = Gauge(
    name="chats_total_agents_last_year",
    documentation="The number of agents created last year in chats",
    labelnames=["total_msgs_last_year"],
)
