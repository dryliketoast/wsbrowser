"""Textual app: a scrolling message log, an input line and a status bar."""

import json
from datetime import datetime

from rich.text import Text
from textual import events, work
from textual.app import App, ComposeResult
from textual.widgets import Input, RichLog, Static
from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import (
    ConnectionClosed,
    ConnectionClosedError,
    InvalidHandshake,
    InvalidURI,
)

# Prefix for client-side commands; everything else is sent to the server.
CMD_PREFIX = "!"

HELP = f"""\
Commands:
  {CMD_PREFIX}connect <url>   connect to a WebSocket server (ws:// is assumed if no scheme)
  {CMD_PREFIX}disconnect      close the current connection
  {CMD_PREFIX}clear           clear the message log
  {CMD_PREFIX}help            show this help
  {CMD_PREFIX}quit            exit
Anything else is sent as a text message, including lines starting with '/'.
Start a line with {CMD_PREFIX}{CMD_PREFIX} to send a literal '{CMD_PREFIX}'. Up/Down recall previous input."""


class HistoryInput(Input):
    """An Input that recalls previously submitted lines with Up/Down."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.history: list[str] = []
        self._pos = 0

    def remember(self, line: str) -> None:
        if line and (not self.history or self.history[-1] != line):
            self.history.append(line)
        self._pos = len(self.history)

    def on_key(self, event: events.Key) -> None:
        if event.key not in ("up", "down") or not self.history:
            return
        event.prevent_default()
        event.stop()
        step = -1 if event.key == "up" else 1
        self._pos = max(0, min(len(self.history), self._pos + step))
        self.value = self.history[self._pos] if self._pos < len(self.history) else ""
        self.cursor_position = len(self.value)


class WSBrowserApp(App):
    TITLE = "wsbrowser"
    CSS = """
    #status { height: 1; padding: 0 1; background: $error-darken-2; color: $text; }
    #status.connected { background: $success-darken-2; }
    #log { height: 1fr; border: none; padding: 0 1; }
    #input { dock: bottom; }
    """
    BINDINGS = [("ctrl+q", "quit", "Quit")]

    def __init__(self, url: str | None = None) -> None:
        super().__init__()
        self.initial_url = url
        self.ws: ClientConnection | None = None
        self.url: str | None = None

    def compose(self) -> ComposeResult:
        yield Static(id="status")
        yield RichLog(id="log", wrap=True, markup=False, highlight=False)
        yield HistoryInput(placeholder=f"{CMD_PREFIX}connect ws://host:port/path  —  {CMD_PREFIX}help", id="input")

    def on_mount(self) -> None:
        self._set_status()
        self.query_one("#input", HistoryInput).focus()
        self._log_system(f"wsbrowser — type {CMD_PREFIX}help for commands")
        if self.initial_url:
            self._connect(self.initial_url)

    # ---- logging -------------------------------------------------------

    def _write(self, marker: str, style: str, body: str) -> None:
        line = Text(datetime.now().strftime("%H:%M:%S "), style="dim")
        line.append(f"{marker} ", style=f"bold {style}")
        line.append(body, style=style if marker in ("*", "!") else "")
        self.query_one("#log", RichLog).write(line)

    def _log_system(self, msg: str) -> None:
        self._write("*", "cyan", msg)

    def _log_error(self, msg: str) -> None:
        self._write("!", "red", msg)

    def _log_out(self, msg: str) -> None:
        self._write(">>", "yellow", msg)

    def _log_in(self, msg: str | bytes) -> None:
        if isinstance(msg, bytes):
            self._write("<<", "green", f"[binary {len(msg)} bytes] {msg[:64].hex(' ')}")
            return
        try:
            body = json.dumps(json.loads(msg), indent=2)
        except ValueError:
            body = msg
        self._write("<<", "green", body)

    def _set_status(self) -> None:
        status = self.query_one("#status", Static)
        if self.ws is not None:
            status.update(f"● connected: {self.url}")
            status.add_class("connected")
        elif self.url:
            status.update(f"○ connecting: {self.url}")
            status.remove_class("connected")
        else:
            status.update("○ disconnected")
            status.remove_class("connected")

    # ---- input handling ------------------------------------------------

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        line = event.value
        box = self.query_one("#input", HistoryInput)
        box.remember(line)
        box.value = ""
        if not line.strip():
            return
        if line.startswith(CMD_PREFIX * 2):
            await self._send(line[len(CMD_PREFIX) :])
        elif line.startswith(CMD_PREFIX):
            await self._command(line)
        else:
            await self._send(line)

    async def _command(self, line: str) -> None:
        cmd, _, arg = line[len(CMD_PREFIX) :].partition(" ")
        arg = arg.strip()
        match cmd.lower():
            case "connect" | "c":
                if not arg:
                    self._log_error(f"usage: {CMD_PREFIX}connect <url>")
                else:
                    self._connect(arg)
            case "disconnect" | "dc":
                if self.ws is None and not self.url:
                    self._log_error("not connected")
                else:
                    await self._disconnect()
            case "clear":
                self.query_one("#log", RichLog).clear()
            case "help" | "h" | "?":
                for help_line in HELP.splitlines():
                    self._log_system(help_line)
            case "quit" | "q" | "exit":
                await self._disconnect(quiet=True)
                self.exit()
            case _:
                self._log_error(f"unknown command: {CMD_PREFIX}{cmd} (try {CMD_PREFIX}help)")

    async def _send(self, msg: str) -> None:
        if self.ws is None:
            self._log_error(f"not connected — use {CMD_PREFIX}connect <url>")
            return
        try:
            await self.ws.send(msg)
        except ConnectionClosed as e:
            self._log_error(f"send failed: {e}")
            return
        self._log_out(msg)

    # ---- connection ----------------------------------------------------

    def _connect(self, url: str) -> None:
        if "://" not in url:
            url = f"ws://{url}"
        self.ws = None
        self.url = url
        self._set_status()
        self._log_system(f"connecting to {url} …")
        self._run_connection(url)

    async def _disconnect(self, quiet: bool = False) -> None:
        self.workers.cancel_group(self, "ws")
        if self.ws is not None:
            await self.ws.close()
        self.ws = None
        if self.url and not quiet:
            self._log_system(f"disconnected from {self.url}")
        self.url = None
        self._set_status()

    @work(exclusive=True, group="ws")
    async def _run_connection(self, url: str) -> None:
        # exclusive=True cancels any previous connection worker, whose
        # `async with` then closes that socket.
        try:
            async with connect(url) as ws:
                self.ws = ws
                self._set_status()
                self._log_system(f"connected to {url}")
                async for msg in ws:
                    self._log_in(msg)
                self._log_system(f"connection closed by server ({ws.close_code})")
        except ConnectionClosedError as e:
            self._log_error(f"connection lost: {e}")
        except (OSError, InvalidURI, InvalidHandshake, TimeoutError) as e:
            self._log_error(f"could not connect to {url}: {e}")
        if self.url == url:
            self.ws = None
            self.url = None
            self._set_status()
