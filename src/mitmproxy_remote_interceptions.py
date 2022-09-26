from __future__ import annotations

import asyncio
import base64
import json
import typing
import uuid

import websockets
from mitmproxy import addonmanager
from mitmproxy import ctx
from mitmproxy import http


class RemoteInterceptions:
    def __init__(self):
        self._server: websockets.WebSocketServer = None
        self._websockets: list[websockets.WebSocketServerProtocol] = []
        self._pendingTransactions: dict[str, asyncio.Future[dict[str, object]]] = {}

    @staticmethod
    def load(loader: addonmanager.Loader) -> None:
        loader.add_option(
            "ws_port",
            int,
            8082,
            "The port to use for the WebSocket server.",
        )

    async def running(self) -> None:
        self._server = await websockets.serve(
            self._ws_handler, "localhost", ctx.options.ws_port,
            compression=None,
            max_size=1024 * 1024 * 1024,  # 1 GiB
        )
        ctx.log.info(f"WebSocket API server listening at http://localhost:{ctx.options.ws_port}")

    async def done(self) -> None:
        if self._server is None:
            return

        self._server.close()
        await self._server.wait_closed()

    async def request(self, flow: http.HTTPFlow) -> None:
        await self._handle_http_message(flow, is_request=True)

    async def response(self, flow: http.HTTPFlow) -> None:
        await self._handle_http_message(flow, is_request=False)

    async def _ws_handler(self, websocket: websockets.WebSocketServerProtocol) -> None:
        ctx.log.info(f"WebSocket API client connected (CID: \"{str(websocket.id)}\")")
        self._websockets.append(websocket)

        while True:
            try:
                message = await websocket.recv()
            except (websockets.ConnectionClosedOK, websockets.ConnectionClosedError):
                self._websockets.remove(websocket)
                ctx.log.info(f"WebSocket API client disconnected (CID: \"{str(websocket.id)}\")")
                break

            try:
                api_response: dict[str, object] = json.loads(message)
            except json.JSONDecodeError:
                ctx.log.warn(
                    f"Invalid JSON received from WebSocket API client (CID: \"{str(websocket.id)}\"). Ignoring.")
                continue

            transaction_id: str | None = api_response.get("id")
            if transaction_id is None:
                ctx.log.warn(
                    f"Received response from WebSocket API client without a transaction ID"
                    f" (CID: \"{str(websocket.id)}\")"
                    f". Ignoring.")
                continue

            if transaction_id in self._pendingTransactions:
                ctx.log.debug(f"Received response from WebSocket API client"
                              f" (CID: \"{str(websocket.id)}\", TID: {transaction_id})")
                self._pendingTransactions[transaction_id].set_result(api_response)
            else:
                ctx.log.warn(f"Received response from WebSocket API with an unknown transaction ID"
                             f" (CID: \"{str(websocket.id)}\", TID: \"{transaction_id}\")"
                             f". Ignoring.")

    async def _perform_transaction(
            self,
            websocket: websockets.WebSocketServerProtocol,
            api_request: dict[str, object]
    ) -> dict[str, object]:
        # Create a transaction ID, and prepare to receive a response.
        transaction_id: str = str(uuid.uuid4())
        pending_interception = \
            self._pendingTransactions[transaction_id] = asyncio.get_running_loop().create_future()

        # Add the transaction ID to the API request, wait for a response, and then remove the ID from the response.
        api_request["id"] = transaction_id
        ctx.log.debug(
            f"Sending request to WebSocket API client (CID: \"{str(websocket.id)}\", TID: \"{transaction_id}\")")
        await websocket.send(json.dumps(api_request))
        api_response: dict[str, object] = await pending_interception
        del api_response["id"]

        # Remove the relevant future from the pending transactions.
        del self._pendingTransactions[transaction_id]

        return api_response

    async def _handle_http_message(self, flow: http.HTTPFlow, is_request: bool):
        # Iterate over every connected client, allowing them to intercept the message one by one such that the output
        # of the previous client (accepted by the provided handler) is the input of the next client.
        # Copy the websocket list to avoid modification during iteration.
        for websocket in self._websockets.copy():
            # As clients may disconnect during the iteration, ensure that the websocket is still connected.
            if websocket.closed:
                continue

            # Determine which full messages to send to the client.
            requested_message_settings: MessageSetSettings = MessageSetSettings.from_json(
                await self._perform_transaction(websocket, {
                    "stage": "pre_request" if is_request else "pre_response",
                    "flow_id": flow.id,
                    "request_summary": _request_to_summary_json(flow.request),
                    "response_summary":
                        _response_to_summary_json(flow.response) if flow.response is not None else None,
                })
            )

            # If no messages are requested, skip to the next client.
            if not (requested_message_settings.send_request or requested_message_settings.send_response):
                continue

            # Send and receive the relevant messages.
            message_set: MessageSet = MessageSet.from_json(
                await self._perform_transaction(websocket, {
                    "stage": "request" if is_request else "response",
                    "flow_id": flow.id,
                    "request": _request_to_json(flow.request) if requested_message_settings.send_request else None,
                    "response": _response_to_json(flow.response) if (requested_message_settings.send_response
                                                                     and flow.response is not None) else None,
                })
            )

            # Use the received messages.
            if message_set.request is not None:
                flow.request = message_set.request
            if message_set.response is not None:
                flow.response = message_set.response


addons: list[object] = [
    RemoteInterceptions()
]


def _headers_to_json(headers: http.Headers) -> dict[str, list[str]]:
    return {header: headers.get_all(header) for header in headers.keys()}


def _headers_from_json(headers_json: dict[str, list[str]]) -> http.Headers:
    headers: http.Headers = http.Headers()
    for header, values in headers_json.items():
        headers.set_all(header, values)
    return headers


def _request_to_json(request: http.Request) -> dict[str, object]:
    return {
        "method": request.method,
        "url": request.url,
        "headers": _headers_to_json(request.headers),
        "body": base64.b64encode(request.get_content(strict=False)).decode("utf-8"),
    }


def _request_to_summary_json(request: http.Request) -> dict[str, object]:
    return {
        "method": request.method,
        "url": request.url,
    }


def _request_from_json(request_json: dict[str, object]) -> http.Request:
    return http.Request.make(
        method=typing.cast(str, request_json["method"]),
        url=typing.cast(str, request_json["url"]),
        content=base64.b64decode(typing.cast(str, request_json["body"])),
        headers=_headers_from_json(typing.cast(dict[str, list[str]], request_json["headers"])),
    )


def _response_to_json(response: http.Response) -> dict[str, object]:
    return {
        "status_code": response.status_code,
        "reason": response.reason,
        "headers": _headers_to_json(response.headers),
        "body": base64.b64encode(response.get_content(strict=False)).decode("utf-8"),
    }


def _response_to_summary_json(response: http.Response) -> dict[str, object]:
    return {
        "status_code": response.status_code,
        "reason": response.reason,
    }


def _response_from_json(response_json: dict[str, object]) -> http.Response:
    response = http.Response.make(
        status_code=typing.cast(int, response_json["status_code"]),
        content=base64.b64decode(typing.cast(str, response_json["body"])),
        headers=_headers_from_json(typing.cast(dict[str, list[str]], response_json["headers"])),
    )
    reason: str | None = response_json.get("reason")
    if reason is not None:
        response.reason = reason
    return response


class MessageSetSettings:
    def __init__(self, send_request: bool, send_response: bool):
        self.send_request = send_request
        self.send_response = send_response

    @staticmethod
    def from_json(json_dict: dict[str, object]) -> MessageSetSettings:
        return MessageSetSettings(
            send_request=json_dict.get("send_request", False),
            send_response=json_dict.get("send_response", False),
        )


class MessageSet:
    def __init__(self, request: http.Request | None, response: http.Response | None):
        self.request = request
        self.response = response

    @staticmethod
    def from_json(json_dict: dict[str, object]) -> MessageSet:
        return MessageSet(
            request=_request_from_json(
                typing.cast(dict[str, object], json_dict["request"]))
            if json_dict.get("request") is not None else None,
            response=_response_from_json(
                typing.cast(dict[str, object], json_dict["response"]))
            if json_dict.get("response") is not None else None,
        )
