# 2.4.2
## Add
  - New feedback messages.
## Change
  - Verify contact via external id on the flowstart validation.

# 2.4.1
## Change
  - Add a recursive retry on the ws message send

# 2.4.0
## Change
  - Order tags by name.

# 2.3.1
## Add
  - Add retrieve_flow_warning action on the project endpoint to check if a start flow contact have a room.
## Change
  - Update dashboard tag filter to verify the uuid instead of the name.

# 2.3.0
## Add
  - Add delete action on the project permission endpoint
## Change
  - Update URN field from charfield to a textfield

# 2.2.0
## Add
  - Add new field "history_contacts_blocklist" to the project config json field, the contacts added to this list won't be shown on the contacts endpoint(history)
  - Add a try/except around the send send_channels_group function for it not to return 4xx/5xx responses when there is a problem on the ws notification(the error will still be logged to sentry)

# 2.1.0
## Add
  - Checking if project exists in template type creation.
  - EDA project consumer.

# 2.0.0
> This CHANGELOG has not been updated since 05/16/2023 so some commits will not appear in this document between version 1.16.4 and 2.0.0. From this version onwards, it will be constantly updated again.
## Add
  - Creating template type using event driven.
  - Filtering active agents in dashboard endpoint.

# 1.16.4
## Add
  - Data exporter getting data from dashboard serializers.
  - New abstract model for soft delete in core (BaseSoftDeleteModel) to Sectors and Queues

# 1.16.2
## Change
  - Compare rooms within the sector instead of the queues when validating the agent room limit on room creation.


# 1.16.1
## Change
  - Remove Room, User and Sector notification groups.


# 1.16.0
## Add
  - New data exporter viewset and presenter for Dashboard app.
  - Add new dependencies: pandas, openpyxl and XlsxWriter


# 1.15.0
## Add
  - `Name` field on FlowStart model.

## Change
  - Restrict room flow start creation to only one active flow start per room(only when starting with a room).


# 1.0.1
## Add
  - Changelog init.
  - Endpoint to list agents for transference between rooms.

## Change
  - Function is attending now uses pendulum to parse timezone in sector.
