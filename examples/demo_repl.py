"""最小演示：python examples/demo_repl.py"""

from __future__ import annotations

from xrk_readline import Readline, backend_name


def main() -> None:
    print("backend:", backend_name())
    words = ["help", "exit", "list", "clear"]

    def completer(text: str, state: int):
        hits = [w for w in words if w.startswith(text)]
        return hits[state] if state < len(hits) else None

    rl = Readline()
    rl.set_completer(completer)
    print("Tab 补全 · Ctrl+C 取消行 · Ctrl+D / exit 退出")
    while True:
        try:
            line = rl.readline("demo> ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            break
        if not line:
            continue
        if line in ("exit", "quit", "q"):
            break
        if line == "help":
            print("commands:", ", ".join(words))
            continue
        print("echo:", line)


if __name__ == "__main__":
    main()
