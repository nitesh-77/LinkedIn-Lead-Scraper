"""Input helpers with KeyboardInterrupt handling"""

from rich.console import Console

console = Console()


def safe_input(prompt: str = "\nPress Enter to continue...") -> bool:
    """
    Safe input that handles KeyboardInterrupt gracefully.

    Returns:
        bool: True if user pressed Enter, False if interrupted
    """
    try:
        input(prompt)
        return True
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Interrupted[/]")
        return False
    except EOFError:
        return False