# mitmproxy Remote Interceptions
A [mitmproxy] addon that provides a WebSocket-based API for remote interceptions.

## Usage
This addon requires [Python] 3.10 or newer.
```shell
# Install the addon requirements
pip install -r requirements.txt

# Launch mitmdump (or any addon-capable mitmproxy tool) with the addon
mitmdump -s src/mitmproxy_remote_interceptions.py
```
The addon will start a WebSocket server on port `8082` by default, but this can be customized with the `ws_port` option.
```shell
mitmdump -s src/mitmproxy_remote_interceptions.py --set ws_port=8000
```

### Nix
A [Nix](https://nixos.org) derivation is included.

```shell
nix-shell -p 'callPackage ./. { }'
mitmridump
```

### WebSocket API
WebSocket API documentation can be found in [`API.md`](API.md).

## Known client libraries

| Language/framework                       | Client library                                                      |
|------------------------------------------|---------------------------------------------------------------------|
| [Dart](https://dart.dev) (native and JS) | [mitmproxy_ri_client](https://pub.dev/packages/mitmproxy_ri_client) |

[mitmproxy]: https://mitmproxy.org
[python]: https://www.python.org
