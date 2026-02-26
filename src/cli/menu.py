"""Menu system for CLI"""

import os
import asyncio
import questionary
from rich.console import Console

console = Console()


class InteractiveMenu:
    """Interactive menu system"""

    def __init__(self):
        self.style = questionary.Style([
            ('question', 'bold cyan'),
            ('answer', 'bold green'),
            ('pointer', 'bold cyan'),
            ('highlighted', 'bold cyan'),
            ('selected', 'bold green'),
        ])

    async def show_main_menu(self) -> str:
        """Show main menu and return selected action"""
        choices = [
            "Start discovery from file",
            "Start discovery from usernames",
            "View discovered profiles (table)",
            "View discovered profiles (tree)",
            "Export profiles",
            "Exit"
        ]

        try:
            return await questionary.select(
                "Choose action:",
                choices=choices,
                style=self.style
            ).ask_async()
        except (KeyboardInterrupt, asyncio.CancelledError):
            console.print("\n[yellow]⚠️  Interrupted[/]")
            return None

    async def get_usernames_input(self) -> list:
        """Get usernames from user input"""
        try:
            usernames_input = await questionary.text(
                "Enter LinkedIn usernames (comma-separated):",
                style=self.style
            ).ask_async()

            if not usernames_input:
                return []

            usernames = [u.strip() for u in usernames_input.split(',') if u.strip()]
            return usernames
        except (KeyboardInterrupt, asyncio.CancelledError):
            console.print("\n[yellow]⚠️  Interrupted[/]")
            return None

    async def get_file_path(self, default: str = "usernames.txt") -> str:
        """Get file path from user"""
        try:
            filepath = await questionary.text(
                "Enter file path:",
                default=default,
                style=self.style
            ).ask_async()

            return filepath
        except (KeyboardInterrupt, asyncio.CancelledError):
            console.print("\n[yellow]⚠️  Interrupted[/]")
            return None

    async def get_depth(self, default: int = 3) -> int:
        """Get discovery depth from user"""
        try:
            depth = await questionary.text(
                f"Enter discovery depth (1-10, recommended: {default}):",
                default=str(3),
                style=self.style,
                validate=lambda x: x.isdigit() and 1 <= int(x) <= 10
            ).ask_async()

            return int(depth)
        except (KeyboardInterrupt, asyncio.CancelledError):
            console.print("\n[yellow]⚠️  Interrupted[/]")
            return None

    async def get_export_format(self) -> str:
        """Get export format choice"""
        choices = ["CSV", "JSON", "Tree (TXT)"]

        try:
            return await questionary.select(
                "Choose export format:",
                choices=choices,
                style=self.style
            ).ask_async()
        except (KeyboardInterrupt, asyncio.CancelledError):
            console.print("\n[yellow]⚠️  Interrupted[/]")
            return None

    async def get_export_filename(self, default: str = "") -> str:
        """Get custom filename for export"""
        try:
            filename = await questionary.text(
                "Enter filename (or press Enter for auto-generated):",
                default=default,
                style=self.style
            ).ask_async()

            return filename
        except (KeyboardInterrupt, asyncio.CancelledError):
            console.print("\n[yellow]⚠️  Interrupted[/]")
            return None

    async def confirm_action(self, message: str) -> bool:
        """Ask for confirmation"""
        try:
            return await questionary.confirm(
                message,
                default=True,
                style=self.style
            ).ask_async()
        except (KeyboardInterrupt, asyncio.CancelledError):
            console.print("\n[yellow]⚠️  Interrupted[/]")
            return None

    def load_usernames_from_file(self, filepath: str) -> list:
        """Load usernames from a file"""
        if not os.path.exists(filepath):
            console.print(f"[red]File not found: {filepath}[/]")
            return []

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                usernames = [line.strip() for line in f if line.strip()]

            console.print(f"[green]Loaded {len(usernames)} usernames from {filepath}[/]")
            return usernames

        except Exception as e:
            console.print(f"[red]Error reading file: {str(e)}[/]")
            return []