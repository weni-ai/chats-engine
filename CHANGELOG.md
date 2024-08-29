# 3.7.9
## Add
 - feature retail
   
# 3.7.8
## Add
  - adding health check view and doc endpoint

# 3.7.7
## Fix
  - passing user when transfer to user
    
# 3.7.6
## Fix
  -  passing user to ws notify

# 3.7.5
## Fix
  -  ws message when transfer queue
    
# 3.7.4
## Add
  -  returning 400 if project uuid its not provided
    
# 3.7.3
## Add
  - flag for offline agents in transfer 
    
# 3.7.2
## Add
  - formating history name 
    
# 3.7.1
## Add
  - verify if the given queue is part of the project
    
# 3.7.0
## Add
  - rooms count endpoint 

# 3.6.5
## Fix
  - remove timezone parse
    
# 3.6.4
## Add
  - queue and agent in flow warning

# 3.6.3
## Add
  - add agents_can_see_queue_history config flag into project

# 3.6.2
## Fix
  - fix tags filter
    
# 3.6.1
## Fix
  - remove ':' from the url string

# 3.6.0
## Add
  - New feature, internal dash endpoints

# 3.5.7
## Fix
  - Removing uuid from sector info when exporting.
   
# 3.5.6
## Fix
  - Verify if data frame exists before translate, to avoid translating an empty dataframe in export dashboard.

# 3.5.5
## Fix
  - Removing deleted queue from metrics.

# 3.5.4
## Fix
  - Passing generic Exception in "ProjectAnyPermission" permission.

# 3.5.3
## Add
  - New feature, queue priorization.

# 3.5.2
## Add
  - Verify if chat gpt token in project config.

# 3.5.1
## Add
  - New endpoint to make bulk transfer.
  - New function to edit config field in project.
  - New endpoint to transfer agents.
## Fix
  - Calculating waiting time metric in new endpoint to get rooms.

# 3.5.0
## Add
  - New EDA consumer to create project permissions.
  - New mixin in flows rest client to delete ticketer when chats delete a sector.

# 3.4.1
## Add
  - Change queue and sectors model managers to list only activated objects.

# 3.4.0
## Add
  - New endpoint for the agent to get a room.

# 3.3.0
## Add
  - Error handling on the contact creation.
## Change
  - Removal of the 'last_interaction' property on the user model and serializers.

# 3.2.5
## Add
  - New feature, room protocol.

# 3.2.4
## Fix
  - External rooms filter sector.
    
# 3.2.3
## Fix
  - Passing underscore to rooms data results.
    
# 3.2.2
## Fix
  - Passing gte to live filters in dashboard.

# 3.2.1
## Change
  - Consider room creation date if the room has no messages in the 24h close validation.

# 3.2.0
## Change
  - Refactoring in dashboard endpoints, applying solid and the design pattern repository with service. 
    
# 3.1.0
## Add
  - New endpoint for creating sector and queue authorization, giving only the user email.

# 3.0.0
## Add
  - New Discussions app, responsible for internal communication between agents.

# 2.6.2
## Change
  - Check contact id when starting a flow on a room. Won't consider the room if the contact id is different.

# 2.6.1
## Change
  - Filter flowstart query to exclude old data.
  - Reverse order on the flowstart list endpoint.

# 2.6.0
## Add
  - FlowStart model refactor.
  - New endpoint to list flow starts.
## Change
  - Fix history detail permissions.

# 2.5.0
## Add
  - New endpoint to return rooms for the history.

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
