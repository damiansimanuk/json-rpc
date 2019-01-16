from tornado.web import RequestHandler
from tornado.websocket import WebSocketHandler
from .processor import BasicJSONRPCProcessor
from .jsonrpc import encode, decode
from .dispacher import Dispatcher
import logging

logger = logging.getLogger("jsonrpc")

# BasicJSONRPCHandler


class BasicJSONRPCHandler(RequestHandler, BasicJSONRPCProcessor):
    def initialize(self, version=None):
        self.version = version

    def set_default_headers(self):
        self.set_header('Content-Type', 'application/json')


class JSONRPCHandler(BasicJSONRPCHandler):
    def initialize(self, response_creator, version=None):
        super().initialize(version=version)
        self.create_response = response_creator

    async def post(self):
        return await self.process_jsonrpc(self.request.body)

    async def compute_result(self, request):
        return await self.create_response(request)


class BasicJSONRPCHandlerWS(WebSocketHandler, BasicJSONRPCProcessor):
    def initialize(self, version=None):
        self.version = version

    def check_origin(self, origin):
        return True


class JSONRPCHandlerWS(BasicJSONRPCHandlerWS):

    def initialize(self, dispatcher: Dispatcher, version="2.0"):
        super().initialize(version=version)
        self.dispatcher = dispatcher

    async def open(self):
        print("WebSocket opened", self)
        print("check user login")

    async def on_close(self):
        print("WebSocket closed", self)
        self.dispatcher.unsubscribe_all(self)

    async def on_message(self, messagejson):
        await self.process_jsonrpc(messagejson)

    async def compute_result(self, request):
        print("*** compute_result", self, request)
        r = await self.dispatcher.dispatch(self, request)
        return r

    def send_message(self, msg):
        logger.debug("send_message: %r", msg)
        self.write_message(msg)
