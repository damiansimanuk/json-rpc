import json
from .exceptions import JSONRPCError, InvalidRequest, ParseError, EmptyBatchRequest

SUPPORTED_VERSIONS = {'2.0', '1.0'}


def encode(value):
    """JSON-encodes the given Python object."""
    return json.dumps(value, default=lambda o: o.toJson()).replace("</", "<\\/")


def decode(request_json, version=None):
    """JSON-decodes the given string to Python object."""
    try:
        if isinstance(request_json, bytes):
            request_json = request_json.decode("utf-8")

        obj = json.loads(request_json)

    except json.JSONDecodeError as jsonError:
        raise ParseError(str(jsonError))

    if isinstance(obj, list):  # Batch request
        requests = [process_request(data, version=version) for data in obj]
        if not requests:
            raise EmptyBatchRequest("Empty batch request")

        return requests
    else:  # Single request
        request = process_request(obj, version=version)
        # if isinstance(request, Exception):
        #     raise request

        return request


def process_request(request, version=None):
    try:
        request_version = request.get('jsonrpc', '1.0')
        if version is not None and request_version != version:
            raise InvalidRequest("Refusing to handle version {}".format(request_version))

        if request_version == '2.0':
            return JSONRPC2Request(**request)
        elif request_version == '1.0':
            return JSONRPC1Request(**request)
        elif request_version not in SUPPORTED_VERSIONS:
            return JSONRPCRequest(**request)
    except KeyError as kerr:
        return InvalidRequest('Missing member {!s}'.format(kerr),
                              JSONRPCStyleRequest(**request))
    except InvalidRequest as inverr:
        return InvalidRequest(str(inverr), JSONRPCStyleRequest(**request))
    except Exception as err:
        return InvalidRequest(str(err))


class JSONRPCStyleError:
    def __init__(self, exception: JSONRPCError):
        assert isinstance(exception, JSONRPCError)
        self._code = exception.error_code
        self._message = "{}: {}".format(exception.short_message, str(exception))

    @property
    def code(self):
        return self._code

    @property
    def message(self):
        return self._message

    def __repr__(self):
        return '{}(code={!r})'.format(self.__class__.__name__, self._code)

    def toJson(self):
        return dict(code=self._code, message=self._message)


class JSONRPCResponse:
    def __init__(self, version, id=None, result=None, error: JSONRPCStyleError= None, exception: JSONRPCError=None):
        self._version = version
        self._id = id
        self._result = result
        self._error = error
        if exception:
            try:
                request = exception.args[1]
                exception = exception.__class__(exception.args[0])
                try:
                    self._id = request.id
                except AttributeError:
                    pass
            except (IndexError, TypeError):
                pass

            self._error = JSONRPCStyleError(exception)

    @property
    def version(self) -> int:
        return self._version

    @property
    def id(self) -> int:
        return self._id

    @property
    def result(self) -> object:
        return self._result

    @property
    def error(self) -> JSONRPCStyleError:
        return self._error

    def __repr__(self):
        return '{}(version={!r}, result={!r}, error={!r}, id={!r})'.format(
            self.__class__.__name__, self._version, self._result, self._error, self._id)

    def toJson(self):
        if self._error:
            if self.version == '1.0':
                return {"id": self._id,
                        "result": None,
                        "error": self._error}
            else:
                return {"jsonrpc": "2.0",
                        "id": self._id,
                        "error": self._error}
        else:
            if self.version == '1.0':
                return {"id": self._id,
                        "result": self._result,
                        "error": None}
            else:
                return {"jsonrpc": "2.0",
                        "id": self._id,
                        "result": self._result}


class JSONRPCEvent:
    def __init__(self, notification: str, params: (list, dict)):
        self._params = params
        self._notification = notification

    @property
    def notification(self) -> str:
        return self._notification

    @property
    def params(self) -> (list, dict):
        return self._params

    def toJson(self):
        return {"jsonrpc": "2.0",
                "notification": self._notification,
                "params": self._params}

    def __repr__(self):
        return '{}(notification={!r}, params={!r})'.format(self.__class__.__name__, self._notification, self._params)


class JSONRPCStyleRequest:

    def __init__(self, **kwargs):
        self._id = kwargs.get('id')
        self._method = kwargs.get('method')
        self._params = kwargs.get('params')
        self._version = kwargs.get('jsonrpc', '1.0')

    @property
    def id(self):
        return self._id

    @property
    def method(self):
        return self._method

    @property
    def params(self):
        return self._params

    @property
    def version(self):
        return self._version


class JSONRPCRequest(JSONRPCStyleRequest):
    """
    A request in style of JSON-RPC.

    This is a request not following of a specific version.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._method = kwargs['method']

        self._is_notification = False

    def __repr__(self):
        return '{}(version={!r}, method={!r}, params={!r}, id={!r})'.format(
            self.__class__.__name__, self._version, self._method, self._params, self._id)

    @property
    def id(self):
        return self._id

    @property
    def is_notification(self):
        return self._is_notification

    @property
    def params(self):
        if self._params is None:
            raise AttributeError("No params given.")

        return self._params

    @property
    def version(self):
        return self._version

    def validate(self):
        if self.version not in SUPPORTED_VERSIONS:
            raise InvalidRequest("Unsupported JSONRPC version!")

        if not isinstance(self._method, str):
            raise InvalidRequest('"method" must be a string!')


class JSONRPC1Request(JSONRPCRequest):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        if 'id' not in kwargs:
            raise InvalidRequest('Missing member "id"')

        if self._id is None:
            self._is_notification = True

    def validate(self):
        super().validate()

        if not isinstance(self._params, list):
            raise InvalidRequest('Invalid type for "params"!')


class JSONRPC2Request(JSONRPCRequest):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        if 'id' not in kwargs:
            self._is_notification = True

    def validate(self):
        super().validate()

        if (self._params is not None and
                not isinstance(self._params, (list, dict))):

            raise InvalidRequest('Invalid type for "params"!')
