import subprocess


class ClipboardError(RuntimeError):
    pass


def read_clipboard() -> str:
    try:
        return subprocess.check_output(
            ["xclip", "-selection", "clipboard", "-o"],
            stderr=subprocess.PIPE,
        ).decode("utf-8")
    except FileNotFoundError as exc:
        raise ClipboardError("xclip is not installed in this environment.") from exc
    except subprocess.CalledProcessError as exc:
        message = exc.stderr.decode("utf-8", errors="replace").strip()
        raise ClipboardError(message or "Could not read the X clipboard.") from exc


def write_clipboard(text: str) -> None:
    try:
        subprocess.run(
            ["xclip", "-selection", "clipboard"],
            input=text.encode("utf-8"),
            stderr=subprocess.PIPE,
            check=True,
        )
    except FileNotFoundError as exc:
        raise ClipboardError("xclip is not installed in this environment.") from exc
    except subprocess.CalledProcessError as exc:
        message = exc.stderr.decode("utf-8", errors="replace").strip()
        raise ClipboardError(message or "Could not write to the X clipboard.") from exc
