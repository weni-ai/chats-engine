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
