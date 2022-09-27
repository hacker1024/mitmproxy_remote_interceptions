# WebSocket API

This is the WebSocket API specification.

# Message format

Bidirectional messages are implemented in the form of JSON objects. Each API request sent from this addon has a
transaction ID in the `id` field, which should be duplicated in the API response from the client.

_This `id` field isn't mentioned in any object documentation - remember to include it in the responses, or else the
addon won't know what to do with them._

Alongside the `id` field, the various flow stage API requests have some common fields. See the
[Flow stages](#flow-stages) section for more information.

# Multiple clients
This addon supports chaining multiple clients. Requests and responses will be sent through each client in the order of
connection, such that the modifications done by one client become the input of the next.

# Flow stages

The WebSocket API sends an API request object at four stages in every HTTP flow. At each stage, the client is expected
to send a certain API response object back.

While the type of API request object varies with each stage, they each have the following common fields:

| Key       | Type                                       |
|-----------|--------------------------------------------|
| `stage`   | The stage of the flow (e.g. `pre-request`) |
| `flow_id` | An ID unique to the flow                   |

Failure to respond to an API request will leave the flow hanging indefinitely.

The following is a brief overview of the interception flow.
> `>` indicates a message sent from the addon to the
> client  
`<` indicates a message sent from the client to the addon

`>` Pre-request stage (summarised request and existing fake response messages)  
`<` Pre-request settings (which complete messages to send to the client)  
`>` Request stage (the complete request and existing fake response messages)  
`<` Request overwrites (request and response modifications)

`>` Pre-response stage (summarised request and response messages)  
`<` Pre-response settings (which complete messages to send to the client)  
`>` Response stage (the complete request and response messages)  
`<` Response overwrites (request and response modifications)

The next few sections describe each stage in detail.

## Pre-request stage

At the `pre_request` stage, message set settings are requested from the client. These settings determine which HTTP
messages are sent to the client at the request stage.

This allows for the client to prevent being sent messages that it doesn't need, which can minimize resource usage.

If the sending of both the request and the response messages is disabled, the request stage will be skipped.

### API request object

| Key                | Type                      | Optional?                                  |
|--------------------|---------------------------|--------------------------------------------|
| `request_summary`  | A request summary object  | No                                         |
| `response_summary` | A response summary object | Yes (provided if set by an earlier client) |

### API response object

The client should respond to this API request with a message set settings object.

## Request stage

At the request stage, the complete request (and any response set by earlier clients) can be sent to the client. At this
point, the client can replace both the request and response data.

If response data is provided by the client, the request will never be sent.

### API request object

The addon will send a message set object to the client.

### API response object

The client must respond to this API request with another message set object.
Any messages in the new message set will overwrite the corresponding messages in the original message set if provided.

## Pre-response stage

This stage serves a similar purpose to the pre-request stage, but it occurs after a request has been sent and a response
has been received.

As with the pre-request stage, if the sending of both the request and the response messages is disabled, the response
stage will be skipped.

### API request object

| Key                | Type                      | Optional? |
|--------------------|---------------------------|-----------|
| `request_summary`  | A request summary object  | No        |
| `response_summary` | A response summary object | No        |

### API response object

The client must respond to this API request with a message set settings object.

## Response stage

This stage works in the same way as the request stage.

### API request object

The addon will send a message set object to the client.

### API response object

The client must respond to this API request with another message set object.
Any messages in the new message set will overwrite the corresponding messages in the original message set if provided.

Setting request data at this stage will affect the mitmproxy UI and later clients.

# JSON objects

## Message set settings

| Key             | Value                                                    | Type    | Optional?                |
|-----------------|----------------------------------------------------------|---------|--------------------------|
| `send_request`  | `true` if the full request should be sent to the client  | Boolean | Yes (default is `false`) |
| `send_response` | `true` if the full response should be sent to the client | Boolean | Yes (default is `false`) |

## Message set

| Key        | Type              | Optional?                                                                                                   |
|------------|-------------------|-------------------------------------------------------------------------------------------------------------|
| `request`  | A request object  | Yes (provided by the addon if requested in the message set settings, or by the client to set request data)  |
| `response` | A response object | Yes (provided by the addon if requested in the message set settings, or by the client to set response data) |

## Request summary

| Key      | Value                                  | Type         | Optional? |
|----------|----------------------------------------|--------------|-----------|
| `method` | The HTTP method (e.g. "GET" or "POST") | String       | No        |
| `url`    | The request URL                        | String (URI) | No        |

## Request

| Key               | Value                                                                         | Type                         | Optional? |
|-------------------|-------------------------------------------------------------------------------|------------------------------|-----------|
| `http_version`    | The HTTP version (e.g. "HTTP/1.1"). Can be left out to use a sensible option. | String                       | Yes       |
| `method`          | The HTTP method (e.g. "GET" or "POST")                                        | String                       | No        |
| `url`             | The request URL                                                               | String (URI)                 | No        |
| `headers`         | The request headers                                                           | Object(String: List(String)) | No        |
| `body`            | The request body                                                              | String (base64)              | No        |
| `trailers`        | The request trailers                                                          | Object(String: List(String)) | Yes       |
| `timestamp_start` | The time of the start of the request (UNIX epoch time, seconds)               | Number                       |           |
| `timestamp_end`   | The time of the end of the request (UNIX epoch time, seconds)                 | Number                       |           |

## Response summary

| Key           | Value                      | Type    | Optional?                                                  |
|---------------|----------------------------|---------|------------------------------------------------------------|
| `status_code` | The response status code   | Integer | No                                                         |
| `reason`      | The response reason phrase | String  | Yes (a default value based on the status code may be used) |

## Response

| Key               | Value                                                                         | Type                         | Optional?                                                  |
|-------------------|-------------------------------------------------------------------------------|------------------------------|------------------------------------------------------------|
| `http_version`    | The HTTP version (e.g. "HTTP/1.1"). Can be left out to use a sensible option. | String                       | Yes                                                        |
| `status_code`     | The response status code                                                      | Integer                      | No                                                         |
| `reason`          | The response reason phrase                                                    | String                       | Yes (a default value based on the status code may be used) |
| `headers`         | The response headers                                                          | Object(String: List(String)) | No                                                         |
| `body`            | The response body                                                             | String (base64)              | No                                                         |
| `trailers`        | The response trailers                                                         | Object(String: List(String)) | Yes                                                        |
| `timestamp_start` | The time of the start of the response (UNIX epoch time, seconds)              | Number                       |                                                            |
| `timestamp_end`   | The time of the end of the response (UNIX epoch time, seconds)                | Number                       |                                                            |