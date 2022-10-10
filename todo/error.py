class AppError(Exception):
    """Base class for errors in this application."""

    pass


class YamlFileError(AppError):
    """Errors raised for loading/dumping of YAML configurations."""

    def __init__(self, message, path, *args):
        super().__init__(message, *args)
        self.path = path
        self.message = message

    def __str__(self):
        return f"{self.message} ({self.path})"


class SpiderError(AppError):
    """Errors raised for the integrations."""

    def __init__(self, message, url, *args):
        super().__init__(message, *args)
        self.message = message
        self.url = url

    def __str__(self):
        return f"{self.message} ({self.url})"

    @staticmethod
    def check_response(response, msg: str = "Response not OK"):
        """
        Check the response for errors.

        :param response: the response
        """
        if not response.ok:
            raise SpiderError(msg, response.url)


class NeedConfigError(AppError):
    """Errors raised for the integrations. Asking for addition configurations"""

    def __init__(self, key, description):
        self.msg = msg = f'Please check {key} in your config file: {description}'
        super().__init__(msg)
        self.key = key

    def __str__(self):
        return f"{self.msg}"
