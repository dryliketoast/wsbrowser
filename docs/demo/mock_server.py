"""Tiny WebSocket server on 127.0.0.1:18765 for rendering docs/demo.gif.

Sends a JSON welcome, answers `ping` with `pong`, streams a few JSON price ticks on a
subscribe message, sends a binary frame on `binary`, and echoes anything else.
"""
import asyncio
import json

import websockets

PRICES = [101.25, 101.40, 101.18, 101.62]


async def handler(ws):
    await ws.send(json.dumps({"type": "welcome", "server": "demo-ws/1.0", "session": "a1b2c3"}))
    async for msg in ws:
        if isinstance(msg, bytes):
            await ws.send(msg)
            continue
        if msg == "ping":
            await ws.send("pong")
        elif msg == "binary":
            await ws.send(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + bytes(range(20)))
        else:
            try:
                req = json.loads(msg)
            except ValueError:
                await ws.send(f"echo: {msg}")
                continue
            if req.get("action") == "subscribe":
                channel = req.get("channel", "prices")
                await ws.send(json.dumps({"type": "subscribed", "channel": channel}))
                for i, price in enumerate(PRICES, 1):
                    await asyncio.sleep(0.6)
                    await ws.send(json.dumps({"type": "tick", "symbol": "EXMP", "seq": i, "price": price}))
            else:
                await ws.send(json.dumps({"type": "error", "reason": "unknown action"}))


async def main():
    async with websockets.serve(handler, "127.0.0.1", 18765):
        await asyncio.Future()


asyncio.run(main())
