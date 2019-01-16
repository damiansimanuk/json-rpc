from .jsonrpc import JSONRPCRequest, JSONRPCResponse, JSONRPCEvent
from .exceptions import JSONRPCError, MethodNotFound, InvalidEvent
from funcsigs import signature
import inspect


class Dispatcher:
    def __init__(self, has_hevents=True):
        self.has_hevents = has_hevents
        self.EVENTS = {}
        self.RESOURCES_RPC = {}

    async def emit_event(self, event_name, *params):
        if not event_name or not (event_name in self.EVENTS.keys()):
            raise InvalidEvent

        notification = JSONRPCEvent(notification=event_name, params=params)

        print("*** emit:", notification)
        for transport in [*self.EVENTS[event_name]]:
            if callable(getattr(transport, "emit_message", None)):
                transport.emit_message(notification)

    def register_event(self, event_name):
        if isinstance(event_name, list):
            for ev in event_name:
                if ev not in self.EVENTS.keys():
                    self.EVENTS[ev] = set()

        elif event_name not in self.EVENTS.keys():
            self.EVENTS[event_name] = set()

    async def method_subscribe(self, transport, event_name):
        if not event_name or not (event_name in self.EVENTS.keys()):
            raise InvalidEvent("Event '%s' not found!" % event_name)

        self.EVENTS[event_name].add(transport)
        return {event_name: "ok"}

    async def method_unsubscribe(self, transport, event_name):
        if not event_name or not (event_name in self.EVENTS.keys()):
            raise InvalidEvent("Event '%s' not found or not subscribed!" % event_name)

        self.EVENTS[event_name].remove(transport)
        return {event_name: "ok"}

    def unsubscribe_all(self, transport):
        for transports in self.EVENTS.values():
            if transport in transports:
                transports.remove(transport)

    def register_method(self, resource, name=None):
        if callable(resource):
            name = name or resource.__name__
            self.RESOURCES_RPC[name] = resource
        else:
            name = name or resource.__class__.__name__
            mts = inspect.getmembers(resource, predicate=inspect.ismethod)
            methods = dict([("%s.%s" % (name, m[0]), m[1]) for m in mts if not m[0].startswith("_")])
            self.RESOURCES_RPC.update(methods)

    def get_method(self, method_name):
        if method_name in self.RESOURCES_RPC:
            return self.RESOURCES_RPC[method_name]
        raise MethodNotFound("method: '%s' not found" % (method_name))

    async def dispatch(self, transport, request: JSONRPCRequest):

        if self.has_hevents and request.method == 'rpc.on':
            return await self.method_subscribe(transport, request.params[0])
        elif self.has_hevents and request.method == 'rpc.off':
            return await self.method_unsubscribe(transport, request.params[0])

        method = self.get_method(request.method)

        try:
            params = request.params
        except AttributeError:
            params = None

        if inspect.isawaitable(method) or inspect.iscoroutinefunction(method):
            # print("is awaitable", method)
            if params is None:
                return await method()
            if isinstance(params, list):
                signature(method).bind(*params)
                return await method(*params)
            elif isinstance(params, dict):
                signature(method).bind(**params)
                return await method(**params)
        else:
            # print("not awaitable", method)
            if params is None:
                return method()
            if isinstance(params, list):
                signature(method).bind(*params)
                return method(*params)
            elif isinstance(params, dict):
                signature(method).bind(**params)
                return method(**params)
