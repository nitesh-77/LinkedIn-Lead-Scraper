"""Export functionality for discovered profiles"""

import json
import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict
from rich.console import Console
from collections import defaultdict

console = Console()


async def export_to_json(profiles: List[Dict], output_dir: str, filename: str = None) -> str:
    """Export profiles to JSON file"""
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"linkedin_leads_{timestamp}.json"

    if not filename.endswith('.json'):
        filename += '.json'

    filepath = Path(output_dir) / filename

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(profiles, f, indent=2, ensure_ascii=False)

    return str(filepath)


async def export_to_csv(profiles: List[Dict], output_dir: str, filename: str = None) -> str:
    """Export profiles to CSV file"""
    if not profiles:
        console.print("[yellow]No profiles to export[/]")
        return None

    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"linkedin_leads_{timestamp}.csv"

    if not filename.endswith('.csv'):
        filename += '.csv'

    filepath = Path(output_dir) / filename

    flattened_profiles = [flatten_profile(profile) for profile in profiles]

    if not flattened_profiles:
        console.print("[yellow]No data to write to CSV[/]")
        return None

    all_keys = set()
    for profile in flattened_profiles:
        all_keys.update(profile.keys())

    non_empty_keys = set()
    for key in all_keys:
        if any(profile.get(key) for profile in flattened_profiles):
            non_empty_keys.add(key)

    fieldnames = sorted(non_empty_keys)

    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(flattened_profiles)

    return str(filepath)


def flatten_profile(profile: Dict) -> Dict:
    """Flatten nested profile data for CSV export"""
    flattened = {
        'id': profile.get('id', ''),
        'urn': profile.get('urn', ''),
        'username': profile.get('username', ''),
        'firstName': profile.get('firstName', ''),
        'lastName': profile.get('lastName', ''),
        'headline': profile.get('headline', ''),
        'summary': profile.get('summary', ''),
        'isCreator': profile.get('isCreator', False),
        'isPremium': profile.get('isPremium', False),
        'profilePicture': profile.get('profilePicture', ''),
        'depth_level': profile.get('depth_level', 0),
        'source_urn': profile.get('source_urn', ''),
    }

    # Extract geo info
    geo = profile.get('geo', {})
    if geo:
        flattened['location'] = geo.get('full', '')
        flattened['country'] = geo.get('country', '')
        flattened['city'] = geo.get('city', '')

    # Extract languages
    languages = profile.get('languages', [])
    if languages:
        flattened['languages'] = ', '.join([lang.get('name', '') for lang in languages[:3]])

    # Extract current position (first position in array)
    positions = profile.get('position', [])
    if positions and len(positions) > 0:
        current_pos = positions[0]
        flattened['current_title'] = current_pos.get('title', '')
        flattened['current_company'] = current_pos.get('companyName', '')
        flattened['current_company_url'] = current_pos.get('companyURL', '')

    # Extract skills (first 10)
    skills = profile.get('skills', [])
    if skills:
        flattened['skills'] = ', '.join([skill.get('name', '') for skill in skills[:10]])

    # Extract education (first one)
    educations = profile.get('educations', [])
    if educations and len(educations) > 0:
        edu = educations[0]
        flattened['education'] = edu.get('schoolName', '')

    return flattened


async def export_to_tree(profiles: List[Dict], output_dir: str, filename: str = None, max_children_per_node: int = 10) -> str:
    """Export profiles as tree structure to TXT file"""
    if not profiles:
        console.print("[yellow]No profiles to export[/]")
        return None

    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"linkedin_leads_tree_{timestamp}.txt"

    if not filename.endswith('.txt'):
        filename += '.txt'

    filepath = Path(output_dir) / filename

    # Build parent-child relationships
    children_map = defaultdict(list)
    for profile in profiles:
        source = profile.get('source_urn', '')
        if source:
            children_map[source].append(profile)

    # Find root profiles (depth 0)
    root_profiles = [p for p in profiles if p.get('depth_level', 0) == 0]

    if not root_profiles:
        console.print("[yellow]No root profiles found[/]")
        return None

    # Generate tree text
    tree_lines = []
    tree_lines.append("=" * 80)
    tree_lines.append("LinkedIn Discovery Tree")
    tree_lines.append(f"Total Profiles: {len(profiles)}")
    tree_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    tree_lines.append("=" * 80)
    tree_lines.append("")

    def get_profile_text(profile: Dict) -> str:
        """Generate text representation of profile"""
        name = f"{profile.get('firstName', '')} {profile.get('lastName', '')}".strip()
        if not name:
            name = profile.get('username', 'Unknown')

        headline = profile.get('headline', 'No headline')
        username = profile.get('username', 'N/A')
        children_count = len(children_map.get(profile['urn'], []))

        # Get location
        geo = profile.get('geo', {})
        location = geo.get('full', '') if geo else ''

        text = f"{name} | {headline}"
        if location:
            text += f" | {location}"
        if children_count > 0:
            text += f" ({children_count} discovered)"
        text += f"\n    LinkedIn: linkedin.com/in/{username}"

        return text

    def add_children_to_tree(profile: Dict, prefix: str = "", is_last: bool = True, current_depth: int = 0, max_depth: int = 5):
        """Recursively add children to tree text"""
        if current_depth >= max_depth:
            return

        children = children_map.get(profile['urn'], [])
        if not children:
            return

        # Show first N children
        visible_children = children[:max_children_per_node]
        hidden_count = len(children) - len(visible_children)

        for i, child in enumerate(visible_children):
            is_child_last = (i == len(visible_children) - 1) and (hidden_count == 0)

            # Determine the branch characters
            if is_child_last:
                tree_lines.append(f"{prefix}└── {get_profile_text(child)}")
                child_prefix = prefix + "    "
            else:
                tree_lines.append(f"{prefix}├── {get_profile_text(child)}")
                child_prefix = prefix + "│   "

            # Recursively add grandchildren
            add_children_to_tree(child, child_prefix, is_child_last, current_depth + 1, max_depth)

        # Add summary for hidden children
        if hidden_count > 0:
            tree_lines.append(f"{prefix}└── ... and {hidden_count} more profiles")

    # Build tree for each root profile
    for i, root in enumerate(root_profiles):
        is_last_root = (i == len(root_profiles) - 1)

        tree_lines.append(get_profile_text(root))
        add_children_to_tree(root, "", is_last_root, current_depth=0, max_depth=5)
        tree_lines.append("")

    tree_lines.append("")
    tree_lines.append("=" * 80)
    tree_lines.append(f"End of Tree - {len(profiles)} total profiles")
    tree_lines.append("=" * 80)

    # Write to file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(tree_lines))

    return str(filepath)