    async def connect(self, *args, **kwargs):
        """
        Called when the websocket is handshaking as part of initial connection.
        """
        self.added_groups = []
        self.user = None
        # Are they logged in?
        close = False
        self.permission = None

        try:
            self.user = self.scope["user"]
            self.project = self.scope["query_params"].get("project")[0]
        except (KeyError, TypeError):
            close = True
        if self.user.is_anonymous or close is True or self.project is None:
            # Reject the connection
            await self.close()
        else:
            # Accept the connection
            try:
                self.permission = await self.get_permission()
            except ObjectDoesNotExist:
                close = True
            if close:
                await self.close()
            else:
                await self.accept()
                await self.load_queues()
                await self.load_user()
                self.last_ping = timezone.now()
                
                # Notify other channels about this new connection
                await self.channel_layer.group_send(
                    f"permission_{self.permission.pk}",
                    {
                        "type": "notify",
                        "action": "connection_check",
                        "content": self.channel_name
                    }
                )

    async def notify(self, event):
        """Handle notifications including connection checks"""
        if event.get("action") == "connection_check":
            # If this is a connection check message and it's not from our own channel
            if event["content"] != self.channel_name:
                await self.send_json({
                    "type": "notify",
                    "action": "multiple_connections",
                    "content": "You are connected in multiple tabs/windows"
                })
        else:
            await self.send_json(event) 