"""Classes containing the exceptions for reporting errors."""

__all__ = ['Warning', 'Error', 'RESTError', 'RESTNotAvailableError']


class Warning(StandardError):
    def __init__(self, value):
        self.__value = value

    def __str__(self):
        return repr(self.__value)


class Error(StandardError):
    def __init__(self, value):
        self.__value = value

    def __str__(self):
        return repr(self.__value)


class RESTError(StandardError):
  def __init__(self, value):
    self.__value = value

  def __str__(self):
    return repr(self.__value)

class RESTNotAvailableError(StandardError):
  def __init__(self, value):
    self.__value = value

  def __str__(self):
    return repr(self.__value)