import functools
import tornado.web

from pprint import pprint
from json_rpc.handler import JSONRPCHandler, BasicJSONRPCHandler
from json_rpc.exceptions import MethodNotFound
from json_rpc.jsonrpc import encode, decode
from json_rpc.dispacher import Dispatcher
from funcsigs import signature


class MyBackend:
    def subtract(self, minuend, subtrahend):
        return minuend - subtrahend

    async def sum(self,  a, b):
        return a+b


class JSONRPCHandler2(tornado.web.RequestHandler):
    def initialize(self, version=None):
        self.handler = BasicJSONRPCHandler(version)
        self.handler.compute_result = self.create_response
        self.backend = MyBackend()

    def set_default_headers(self):
        self.set_header('Content-Type', 'application/json')

    async def post(self):
        j = self.request.body
        res = await self.handler.handle_jsonrpc(self.request.body)
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


class JSONRPCHandler3(tornado.web.RequestHandler):
    def initialize(self, version=None):
        self.handler = BasicJSONRPCHandler(version)
        self.handler.compute_result = self.compute_result

    def set_default_headers(self):
        self.set_header('Content-Type', 'application/json')

    async def post(self):
        j = self.request.body
        res = await self.handler.handle_jsonrpc(self.request.body)
        print("response", res)
        if res:
            self.write(encode(res))

    async def compute_result(self, request):
        print("*** compute_result", request)
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
