import functools
import tornado.web

from pprint import pprint
from json_rpc.tornado_handler import JSONRPCHandler, BasicJSONRPCHandler
from json_rpc.exceptions import MethodNotFound
from json_rpc.jsonrpc import encode, decode
from json_rpc.dispacher import Dispatcher
from funcsigs import signature

import sys


def get_caller_instance(obj):
    print("****************************")
    f = sys._getframe(2)
    while f is not None:
        s = f.f_locals.get('self', None)
        if isinstance(s, obj):
            # print(" - - - ENCONTRE", s)
            return s

        print(" --- ", f.f_code, f.f_locals.get('self', None))
        f = f.f_back

    return None


class MyBackend:
    def subtract(self, minuend, subtrahend):
        return minuend - subtrahend

    def sum(self,  a, b):
        return a+b


class JSONRPCHandler2(BasicJSONRPCHandler):
    def initialize(self, version=None):
        self.compute_result = self.create_response
        self.backend = MyBackend()

    def set_default_headers(self):
        self.set_header('Content-Type', 'application/json')

    async def post(self):
        j = self.request.body
        res = await self.process_jsonrpc(self.request.body)

        print("//////////////////////", res)
        if res:
            self.write(encode(res))

    async def create_response(self, request):
        print("params", request)

        try:
            method = getattr(self.backend, request.method)
        except AttributeError:
            raise MethodNotFound("Method {!r} not found!".format(request.method))

        try:
            params = request.params
        except AttributeError:
            return method()

        if isinstance(params, list):
            # signature(method).bind(*params)
            return method(*params)
        elif isinstance(params, dict):
            signature(method).bind(**params)
            return method(**params)


async def sum(a, b):
    transport: tornado.web.RequestHandler = get_caller_instance(tornado.web.RequestHandler)
    print("caller transport", transport)
    print("current_user:", transport.current_user)
    await publishEvent(a)
    return a+b


async def publishEvent(a):
    await dispatcher.emit_event("evento1", "prueba")


backend = MyBackend()
dispatcher = Dispatcher()

dispatcher.register_event("evento1")

dispatcher.register_method(sum)
dispatcher.register_method(backend)
dispatcher.register_method(sum, "subtract")
print("RESOURCES_RPC")
pprint(dispatcher.RESOURCES_RPC)


class JSONRPCHandler3(BasicJSONRPCHandler):
    def initialize(self, version=None):
        super().initialize(version=version)

    def get_current_user(self):
        user_cookie = self.get_cookie("user")
        if user_cookie:
            return user_cookie
        return "Anoimous"

    def emit_message(self, message):
        if self._finished:
            print("------ EMIT transport finished", self)
            dispatcher.unsubscribe_all(self)
            return

        print("------ EMIT", self, message)
        self.write(encode(message))

    def set_default_headers(self):
        self.set_header('Content-Type', 'application/json')

    async def post(self):
        j = self.request.body
        res = await self.process_jsonrpc(self.request.body)
        print("response", res)
        if res:
            self.write(encode(res))

    async def compute_result(self, request):
        print("*** compute_result", self, request)
        r = await dispatcher.dispatch(self, request)
        return r


def make_app():

    return tornado.web.Application([
        (r"/jsonrpc2", JSONRPCHandler2),
        (r"/jsonrpc3", JSONRPCHandler3),
    ], debug=True)


if __name__ == "__main__":
    app = make_app()
    app.listen(8889)
    tornado.ioloop.IOLoop.current().start()
