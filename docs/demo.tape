# Renders docs/demo.gif.  From the repo root:
#   uv run python docs/demo/mock_server.py &     # demo WebSocket server on 127.0.0.1:18765
#   vhs docs/demo.tape
# Assumes `wsbrowser` is on PATH (e.g. `uv tool install .` or the built binary).
Output docs/demo.gif
Set Shell "bash"
Set FontSize 18
Set Width 1200
Set Height 700
Set Padding 12
Set TypingSpeed 50ms

Type "wsbrowser" Enter
Sleep 2s
Type "!help" Enter Sleep 3s
Type "!clear" Enter Sleep 500ms
Type "!connect localhost:18765" Enter Sleep 2s
Type "hello" Enter Sleep 1500ms
Type "ping" Enter Sleep 1500ms
Type '{"action": "subscribe", "channel": "prices"}' Enter Sleep 4s
Type "binary" Enter Sleep 2500ms
Type "!disconnect" Enter Sleep 2s
Type "!quit" Enter Sleep 1s
