"""LinkedIn Leads Discovery - Main Application"""

import asyncio
import sys
from linkdapi import AsyncLinkdAPI
from rich.console import Console

from src.utils.config import Config
from src.utils.export import export_to_csv, export_to_json, export_to_tree
from src.utils.input_helpers import safe_input
from src.api.client import LeadsAPIClient
from src.discovery.tree_discovery import ProfileTreeDiscovery
from src.cli.menu import InteractiveMenu
from src.cli.display import (
    show_header,
    show_discovery_summary,
    show_profiles_table,
    show_profiles_tree,
)

console = Console()


class LinkedInLeadsDiscoveryApp:
    """Main application class"""

    def __init__(self):
        self.config = Config()
        self.menu = InteractiveMenu()
        self.discovery_result = None
        self.has_unsaved_data = False

    async def run(self):
        """Main application loop"""
        try:
            while True:
                # Show header with current profiles count and save status
                profiles_count = len(self.discovery_result['profiles']) if self.discovery_result else 0
                show_header(self.config, profiles_count, has_unsaved_data=self.has_unsaved_data)

                try:
                    action = await self.menu.show_main_menu()

                    if action is None:
                        console.print("\n[yellow]Operation cancelled[/]")
                        if await self.handle_exit():
                            break
                        continue

                    if action == "Start discovery from usernames":
                        await self.discover_from_input()
                    elif action == "Start discovery from file":
                        await self.discover_from_file()
                    elif action == "View discovered profiles (table)":
                        await self.view_profiles()
                    elif action == "View discovered profiles (tree)":
                        await self.view_profiles_tree()
                    elif action == "Export profiles":
                        await self.export_profiles()
                    elif action == "Exit":
                        if await self.handle_exit():
                            break

                except KeyboardInterrupt:
                    console.print("\n[yellow]⚠️  Interrupted[/]")
                    # Check if we have unsaved data
                    if self.has_unsaved_data:
                        console.print("[yellow]You have unsaved data![/]")
                        try:
                            save_prompt = await self.menu.confirm_action("Would you like to save before exiting?")
                            if save_prompt:
                                await self.export_profiles()
                        except (KeyboardInterrupt, asyncio.CancelledError):
                            console.print("\n[yellow]⚠️  Save interrupted - exiting anyway[/]")
                    break

                except Exception as e:
                    console.print(f"[red]Unexpected error: {str(e)}[/]")
                    console.print("[yellow]Please try again or exit[/]")

        except KeyboardInterrupt:
            # Final Ctrl+C during exit handling
            console.print("\n[yellow]Force exit[/]")

    async def discover_from_input(self):
        """Start discovery from user input"""
        usernames = await self.menu.get_usernames_input()

        if usernames is None:
            return

        if not usernames:
            console.print("[yellow]No usernames provided[/]")
            return

        await self.start_discovery(usernames)

    async def discover_from_file(self):
        """Start discovery from file"""
        filepath = await self.menu.get_file_path()

        if filepath is None:
            return

        usernames = self.menu.load_usernames_from_file(filepath)

        if not usernames:
            return

        await self.start_discovery(usernames)

    async def start_discovery(self, usernames: list):
        """Execute the discovery process"""
        depth = await self.menu.get_depth(self.config.default_depth)

        if depth is None:
            return

        console.print(f"\n[cyan]Starting discovery for {len(usernames)} usernames with depth {depth}[/]")
        console.print("[dim]This may take a while depending on the depth...\n[/]")

        api_client = LeadsAPIClient(
            api_key=self.config.api_key,
            max_retries=self.config.max_retries,
            retry_delay=self.config.retry_delay
        )

        discovery = ProfileTreeDiscovery(
            api_client=api_client,
            max_concurrent=self.config.max_concurrent
        )

        try:
            async with AsyncLinkdAPI(self.config.api_key) as api:
                self.discovery_result = await discovery.discover_from_usernames(
                    usernames,
                    depth,
                    api
                )

            console.print(f"\n[bold cyan]{'='*60}[/]")
            console.print(f"[bold green]✓ Discovery completed![/]")
            show_discovery_summary(self.discovery_result)
            console.print(f"[bold cyan]{'='*60}[/]\n")

            if self.discovery_result['total_discovered'] > 0:
                self.has_unsaved_data = True

                view_profiles = await self.menu.confirm_action("Would you like to view the profiles?")
                if view_profiles is None:
                    return
                if view_profiles:
                    await self.view_profiles()

                export_profiles = await self.menu.confirm_action("Would you like to export the profiles?")
                if export_profiles is None:
                    return
                if export_profiles:
                    await self.export_profiles()
            else:
                console.print("\n[yellow]No profiles discovered[/]")
                safe_input()

        except KeyboardInterrupt:
            console.print(f"\n\n[yellow]⚠️  Discovery interrupted by user![/]")

            # Save whatever was discovered before interruption
            self.discovery_result = discovery._build_result()

            if self.discovery_result['total_discovered'] > 0:
                console.print(f"[cyan]Discovered {self.discovery_result['total_discovered']} profiles before interruption[/]")
                self.has_unsaved_data = True

                console.print(f"\n[bold cyan]{'='*60}[/]")
                show_discovery_summary(self.discovery_result)
                console.print(f"[bold cyan]{'='*60}[/]\n")

                # Prompt to save
                try:
                    save_prompt = await self.menu.confirm_action("Would you like to save the discovered profiles?")
                    if save_prompt:
                        await self.export_profiles()
                except (KeyboardInterrupt, asyncio.CancelledError):
                    console.print("\n[yellow]⚠️  Save prompt interrupted[/]")
                safe_input()
            else:
                console.print("[yellow]No profiles were discovered before interruption[/]")
                safe_input()

        except Exception as e:
            console.print(f"\n[red]Error during discovery: {str(e)}[/]")

            # Try to save any partial results
            try:
                self.discovery_result = discovery._build_result()
                if self.discovery_result['total_discovered'] > 0:
                    console.print(f"[yellow]Partial results available: {self.discovery_result['total_discovered']} profiles[/]")
                    self.has_unsaved_data = True
                    save_prompt = await self.menu.confirm_action("Would you like to save the partial results?")
                    if save_prompt:
                        await self.export_profiles()
            except:
                pass

    async def view_profiles(self):
        """View discovered profiles in table format"""
        if not self.discovery_result or not self.discovery_result['profiles']:
            console.print("[yellow]No profiles to display. Run a discovery first.[/]")
            safe_input()
            return

        show_profiles_table(self.discovery_result['profiles'])
        safe_input()

    async def view_profiles_tree(self):
        """View discovered profiles in tree format"""
        if not self.discovery_result or not self.discovery_result['profiles']:
            console.print("[yellow]No profiles to display. Run a discovery first.[/]")
            safe_input()
            return

        show_profiles_tree(self.discovery_result['profiles'])
        safe_input()

    async def export_profiles(self):
        """Export discovered profiles"""
        if not self.discovery_result or not self.discovery_result['profiles']:
            console.print("[yellow]No profiles to export. Run a discovery first.[/]")
            return

        export_format = await self.menu.get_export_format()
        if export_format is None:
            return

        filename = await self.menu.get_export_filename()
        if filename is None:
            return

        try:
            if export_format == "CSV":
                filepath = await export_to_csv(
                    self.discovery_result['profiles'],
                    self.config.output_dir,
                    filename
                )
            elif export_format == "JSON":
                filepath = await export_to_json(
                    self.discovery_result['profiles'],
                    self.config.output_dir,
                    filename
                )
            elif export_format == "Tree (TXT)":
                filepath = await export_to_tree(
                    self.discovery_result['profiles'],
                    self.config.output_dir,
                    filename
                )
            else:
                console.print(f"[red]Unknown export format: {export_format}[/]")
                return

            if filepath:
                console.print(f"\n[green]✓ Exported {len(self.discovery_result['profiles'])} profiles to:[/]")
                console.print(f"[cyan]{filepath}[/]")
                self.has_unsaved_data = False
            else:
                console.print("[red]Export failed[/]")

        except Exception as e:
            console.print(f"[red]Error during export: {str(e)}[/]")

    async def handle_exit(self) -> bool:
        """Handle application exit"""
        if self.has_unsaved_data:
            console.print("\n[yellow]⚠️  You have unsaved discovered profiles![/]")
            should_export = await self.menu.confirm_action("Would you like to export before exiting?")
            if should_export is None:
                return False
            if should_export:
                await self.export_profiles()

        console.print("\n[cyan]Thank you for using LinkedIn Leads Discovery![/]")
        console.print("[dim]Made with 💙 by LinkdAPI Team[/]")
        return True


async def main():
    """Entry point"""
    try:
        app = LinkedInLeadsDiscoveryApp()
        await app.run()
    except KeyboardInterrupt:
        console.print("\n[yellow]✓ Application exited[/]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Fatal error: {str(e)}[/]")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())