class CopilotConnectError(Exception):
    def __init__(self, status_code, error):
        self.status_code = status_code
        self.error = error
        super().__init__(str(error))


class CopilotIntegrationAlreadyExists(Exception):
    pass
