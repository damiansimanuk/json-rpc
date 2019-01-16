import logging
from .jsonrpc import decode, encode, JSONRPCStyleError, JSONRPCResponse
from .exceptions import (JSONRPCError, ParseError, InvalidRequest, MethodNotFound,
                         InvalidParams, InternalError, EmptyBatchRequest)

__all__ = ("BasicJSONRPCProcessor")

logger = logging.getLogger("jsonrpc")


class BasicJSONRPCProcessor():

    version = None

    async def process_jsonrpc(self, request_json):
        try:
            request = decode(request_json, version=self.version)
        except (InvalidRequest, ParseError, EmptyBatchRequest) as ex:
            logger.error("decode error: %r", ex)
            return(JSONRPCResponse(self.version, exception=ex))
        except Exception:
            return

        # process_jsonrpc_request
        if isinstance(request, list):  # batch request
            return await self.process_jsonrpc_batch_request(request)
        else:
            return await self.process_jsonrpc_single_request(request)

    async def process_jsonrpc_batch_request(self, request):
        responses = []
        for call in request:
            if isinstance(call, JSONRPCError):
                responses.append(JSONRPCResponse(self.version, exception=call))
                continue

            response = await self.process_jsonrpc_single_request(call)
            if response:
                responses.append(response)

        return responses

    async def process_jsonrpc_single_request(self, request):
        logger.warning("Procesar request:%r", request)

        try:
            request.validate()
        except InvalidRequest as e:
            return JSONRPCResponse(self.version, id=request.id, exception=e)

        try:
            method_result = await self.compute_result(request)
            if not request.is_notification:
                return JSONRPCResponse(self.version, id=request.id, result=method_result)

        except (MethodNotFound, InvalidParams) as e:
            if not request.is_notification:
                return JSONRPCResponse(self.version, id=request.id, exception=e)
        except Exception as error:
            if not request.is_notification:
                return JSONRPCResponse(self.version, id=request.id, exception=InternalError(str(error)))

    async def compute_result(self, request):
        raise NotImplementedError("Handler does not create an result.")
