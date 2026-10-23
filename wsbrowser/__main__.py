import argparse

from wsbrowser.app import WSBrowserApp


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="wsbrowser", description="IRC-style terminal client for WebSocket servers."
    )
    parser.add_argument("url", nargs="?", help="WebSocket URL to connect to on startup")
    args = parser.parse_args()
    WSBrowserApp(url=args.url).run()


if __name__ == "__main__":
    main()
