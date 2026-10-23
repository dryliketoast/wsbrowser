# wsbrowser

An IRC-style terminal client for WebSocket servers: connect to a URL, type messages, and watch the responses scroll by. Useful for poking at and debugging WebSocket endpoints, in the way telnet is for plain TCP.

Built with [Textual](https://textual.textualize.io/) and [websockets](https://websockets.readthedocs.io/); managed with [uv](https://docs.astral.sh/uv/). Requires Python 3.13+.

The screen is a status bar (green with `connected: <url>` when connected), a scrolling timestamped log, and an input line.

## Setup and run

    uv sync
    uv run wsbrowser                      # start disconnected
    uv run wsbrowser ws://localhost:8765  # connect on startup

(`uv run python -m wsbrowser` works too.)

## Usage

| Input | Effect |
|---|---|
| `!connect <url>` (`!c`) | Connect (`ws://` is assumed if no scheme is given); replaces any current connection |
| `!disconnect` (`!dc`) | Close the current connection |
| `!clear` | Clear the message log |
| `!help` (`!h`, `!?`) | Show help |
| `!quit` (`!q`, `!exit`), `Ctrl+Q` | Exit |
| `!!text` | Send `!text` literally |
| anything else | Sent as a text message (including `/...` lines) |
| `Up` / `Down` | Recall previous input |

Log markers: `>>` sent, `<<` received, `*` status, `!` error. Incoming JSON is pretty-printed; binary frames are shown as a byte count plus a hex preview.

## Limitations

- Sends text frames only.
- Connects with a plain URL: no custom headers, subprotocols or other connection options.
- No automatic reconnect, and input history is kept in memory only.

## Test

    uv run pytest

The tests drive the app with Textual's pilot against a local `websockets` echo server.

## Build a single-file binary

    ./scripts/build.sh

This runs the tests, then uses [PyInstaller](https://pyinstaller.org/) to produce `dist/wsbrowser-<version>-<os>-<arch>` (plus a `dist/wsbrowser` copy) and smoke-tests it with `--help`. The executable bundles its own Python interpreter and dependencies, so the target machine needs neither Python nor uv: just copy it over and run it.

It only runs on the OS and CPU architecture it was built on, and on Linux it needs a glibc at least as new as the build machine's, so build on (or for) the oldest system you plan to deploy to.
