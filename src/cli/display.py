"""Display utilities for CLI"""

import os
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.tree import Tree
from rich import box
from typing import List, Dict
from collections import defaultdict

console = Console()


def clear_terminal():
    """Clear the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')


def show_header(config, profiles_count: int = 0, title: str = "Main Menu", has_unsaved_data: bool = False):
    """Display application header with configuration"""
    clear_terminal()

    header = Text()
    header.append("LinkedIn Leads Discovery", style="bold cyan")
    header.append(f"  •  {title}", style="bold white")

    if profiles_count > 0:
        header.append(f"  •  ", style="dim")
        header.append(f"{profiles_count} leads discovered", style="bold cyan")
        header.append(f"  •  ", style="dim")
        if has_unsaved_data:
            header.append("⚠ Unsaved", style="bold yellow")
        else:
            header.append("✓ Saved", style="bold green")

    # Config section
    api_key = config.api_key
    masked = f"{api_key[:8]}...{api_key[-6:]}" if len(api_key) > 14 else "***...***"

    header.append("\n\n", style="dim")
    header.append("⚙️  Configuration\n", style="bold white")
    header.append(f"   API Key: ", style="dim")
    header.append(f"{masked}", style="cyan")
    header.append(f"  •  ", style="dim")
    header.append(f"Concurrent: ", style="dim")
    header.append(f"{config.max_concurrent}", style="cyan")
    header.append(f"  •  ", style="dim")
    header.append(f"Retries: ", style="dim")
    header.append(f"{config.max_retries}", style="cyan")

    # Branding section
    header.append("\n\n", style="dim")
    header.append("💙 Made with love by ", style="dim")
    header.append("LinkdAPI Team", style="bold cyan")
    header.append("\n", style="dim")
    header.append("   📧 support@linkdapi.com  •  ", style="dim")
    header.append("🌐 linkdapi.com  •  ", style="dim")
    header.append("⭐ github.com/linkdapi", style="dim")

    console.print(Panel(header, box=box.DOUBLE, border_style="cyan", padding=(1, 2)))
    console.print()


def show_discovery_summary(result: Dict):
    """Display discovery summary"""
    console.print("\n[bold cyan]═══ Discovery Summary ═══[/]")

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="cyan")
    table.add_column(style="green bold")

    table.add_row("Total Profiles Discovered", str(result['total_discovered']))
    table.add_row("Unique URNs Found", str(result['unique_urns']))
    table.add_row("Failed Usernames", str(len(result['failed_usernames'])))
    table.add_row("Failed URNs", str(len(result['failed_urns'])))

    console.print(table)

    if result['failed_usernames']:
        console.print(f"\n[yellow]Failed usernames: {', '.join(result['failed_usernames'][:5])}")
        if len(result['failed_usernames']) > 5:
            console.print(f"[dim]... and {len(result['failed_usernames']) - 5} more[/]")


def show_profiles_table(profiles: List[Dict], max_rows: int = 20):
    """Display profiles in a table"""
    if not profiles:
        console.print("[yellow]No profiles to display[/]")
        return

    table = Table(title="Discovered Profiles", show_lines=False)
    table.add_column("Depth", style="cyan", width=6)
    table.add_column("Name", style="green", width=22)
    table.add_column("Headline", style="white", width=35)
    table.add_column("Location", style="yellow", width=20)
    table.add_column("Company", style="magenta", width=20)

    for i, profile in enumerate(profiles[:max_rows]):
        depth = str(profile.get('depth_level', 0))
        name = f"{profile.get('firstName', '')} {profile.get('lastName', '')}".strip() or "N/A"
        headline = profile.get('headline', 'N/A')[:32] + "..." if len(profile.get('headline', '')) > 35 else profile.get('headline', 'N/A')

        # Get location
        geo = profile.get('geo', {})
        location = geo.get('city', 'N/A') if geo else 'N/A'
        if len(location) > 20:
            location = location[:17] + "..."

        # Get current company
        positions = profile.get('position', [])
        company = 'N/A'
        if positions and len(positions) > 0:
            company = positions[0].get('companyName', 'N/A')
        if len(company) > 20:
            company = company[:17] + "..."

        table.add_row(depth, name, headline, location, company)

    console.print(table)

    if len(profiles) > max_rows:
        console.print(f"[dim]... and {len(profiles) - max_rows} more profiles[/]")


def show_profiles_tree(profiles: List[Dict], max_children_per_node: int = 5):
    """Display profiles in an optimized tree structure showing discovery hierarchy"""
    if not profiles:
        console.print("[yellow]No profiles to display[/]")
        return

    children_map = defaultdict(list)
    for profile in profiles:
        source = profile.get('source_urn', '')
        if source:
            children_map[source].append(profile)

    # Find root profiles (depth 0 or no source)
    root_profiles = [p for p in profiles if p.get('depth_level', 0) == 0]

    if not root_profiles:
        console.print("[yellow]No root profiles found (depth 0)[/]")
        return

    # Create main tree
    tree = Tree(
        f"[bold cyan]LinkedIn Discovery Tree[/] [dim]({len(profiles)} total profiles)[/]",
        guide_style="cyan dim"
    )

    def get_profile_label(profile: Dict) -> str:
        """Generate a readable label for a profile node"""
        name = f"{profile.get('firstName', '')} {profile.get('lastName', '')}".strip()
        if not name:
            name = profile.get('username', 'Unknown')

        headline = profile.get('headline', '')[:40] + "..." if len(profile.get('headline', '')) > 43 else profile.get('headline', '')

        # Get location
        geo = profile.get('geo', {})
        location = geo.get('city', '') if geo else ''

        # Count children for this profile
        children_count = len(children_map.get(profile['urn'], []))

        label_parts = [f"[green]{name}[/]", f"[dim]│[/]", f"[yellow]{headline}[/]"]
        if location:
            label_parts.extend([f"[dim]│[/]", f"[cyan]{location}[/]"])
        if children_count > 0:
            label_parts.append(f"[dim]({children_count} discovered)[/]")

        return " ".join(label_parts)

    def add_children_to_node(parent_node, parent_profile: Dict, current_depth: int = 0, max_depth: int = 3):
        """Recursively add children to a tree node with optimization"""
        # Prevent infinite depth
        if current_depth >= max_depth:
            return

        parent_urn = parent_profile['urn']
        children = children_map.get(parent_urn, [])

        if not children:
            return

        # Show first N children
        visible_children = children[:max_children_per_node]
        hidden_count = len(children) - len(visible_children)

        for child in visible_children:
            child_label = get_profile_label(child)
            child_node = parent_node.add(child_label)
            # Recursively add grandchildren
            add_children_to_node(child_node, child, current_depth + 1, max_depth)

        # Add summary for hidden children
        if hidden_count > 0:
            summary_label = f"[dim]... and {hidden_count} more profiles[/]"
            parent_node.add(summary_label)

    # Add root profiles to tree
    for i, root in enumerate(root_profiles[:10]):  # Show max 10 root profiles
        root_label = get_profile_label(root)
        root_node = tree.add(f"[bold]{root_label}[/]")
        add_children_to_node(root_node, root, current_depth=0, max_depth=3)

    # Show summary if there are more root profiles
    if len(root_profiles) > 10:
        tree.add(f"[dim]... and {len(root_profiles) - 10} more starting profiles[/]")

    console.print()
    console.print(tree)
    console.print()
    console.print(f"[dim]Note: Showing up to {max_children_per_node} profiles per node and 3 levels deep for readability[/]")
    console.print()