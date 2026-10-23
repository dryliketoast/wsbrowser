import asyncio

from textual.widgets import RichLog, Static
from websockets.asyncio.server import serve

from wsbrowser.app import WSBrowserApp


async def echo(ws):
    async for msg in ws:
        await ws.send(f"echo: {msg}" if msg != "json" else '{"a": 1}')


def log_text(app: WSBrowserApp) -> str:
    return "\n".join(line.text for line in app.query_one("#log", RichLog).lines)


async def wait_for(app, pilot, needle: str, timeout: float = 3.0) -> None:
    for _ in range(int(timeout / 0.05)):
        if needle in log_text(app):
            return
        await pilot.pause(0.05)
    raise AssertionError(f"{needle!r} not in log:\n{log_text(app)}")


async def type_line(pilot, line: str) -> None:
    await pilot.click("#input")
    for ch in line:
        await pilot.press("space" if ch == " " else ch)
    await pilot.press("enter")


def test_send_receive_and_disconnect():
    async def run():
        async with serve(echo, "127.0.0.1", 0) as server:
            port = server.sockets[0].getsockname()[1]
            app = WSBrowserApp(url=f"127.0.0.1:{port}")
            async with app.run_test() as pilot:
                await wait_for(app, pilot, "connected to ws://127.0.0.1")
                assert "connected:" in str(app.query_one("#status", Static).render())

                await type_line(pilot, "hello")
                await wait_for(app, pilot, "echo: hello")

                await type_line(pilot, "json")
                await wait_for(app, pilot, '"a": 1')

                await type_line(pilot, "/server cmd")
                await wait_for(app, pilot, "echo: /server cmd")

                await type_line(pilot, "!!bang")
                await wait_for(app, pilot, "echo: !bang")

                await type_line(pilot, "!disconnect")
                await wait_for(app, pilot, "disconnected from")
                assert app.ws is None

                await type_line(pilot, "hello")
                await wait_for(app, pilot, "not connected")

    asyncio.run(run())


def test_connect_failure_is_reported():
    async def run():
        app = WSBrowserApp(url="ws://127.0.0.1:1")
        async with app.run_test() as pilot:
            await wait_for(app, pilot, "could not connect")
            assert app.ws is None

    asyncio.run(run())
