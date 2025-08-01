import requests
import json
import time
from datetime import datetime
import argparse
import sys
import os
import configparser
import logging
from jinja2 import Environment, FileSystemLoader

# --- Configuration & Profile Management ---

def get_profiles():
    """Reads all [Profile:*] sections from config.ini."""
    config_parser = configparser.ConfigParser()
    if not os.path.exists('config.ini'):
        logging.error("config.ini file not found. Please create it.")
        return None, None

    config_parser.read('config.ini')
    
    # Get API Key
    api_key = config_parser.get('TornAPI', 'ApiKey', fallback=None)
    if not api_key or api_key == 'YourActualApiKeyHere':
        logging.error("API key not set in [TornAPI] section of config.ini.")
        return None, None

    profiles = {}
    for section in config_parser.sections():
        if section.startswith('Profile:'):
            profile_name = section.split(':', 1)[1]
            profiles[profile_name] = dict(config_parser.items(section))
    
    if not profiles:
        logging.error("No profiles found in config.ini. Please define at least one [Profile:*] section.")
        return api_key, None

    return api_key, profiles

def select_profile(profiles):
    """Prompts the user to select a payout profile."""
    profile_names = list(profiles.keys())
    logging.info("Please select a Payout Profile for this report:")
    for i, name in enumerate(profile_names):
        description = profiles[name].get('description', 'No description.')
        print(f"  [{i+1}] {name} - {description}")
    
    # Default to the first profile in the list ('Standard')
    default_choice = 1
    while True:
        choice_input = input(f"Enter your choice (default: {default_choice}): ")
        if choice_input.strip() == "":
            choice = default_choice
            break
        
        if choice_input.isdigit() and 1 <= int(choice_input) <= len(profile_names):
            choice = int(choice_input)
            break
        else:
            logging.warning("Invalid choice. Please enter a number from the list.")
            
    chosen_name = profile_names[choice - 1]
    logging.info(f"Using profile: {chosen_name}")
    return profiles[chosen_name]

# --- Utility Functions ---

def get_unique_filename(base_path):
    """Checks if a file exists and returns a unique name by appending a number."""
    if not os.path.exists(base_path):
        return base_path
    directory, filename = os.path.split(base_path)
    name, ext = os.path.splitext(filename)
    counter = 2
    while True:
        new_name = f"{name}_{counter}{ext}"
        new_path = os.path.join(directory, new_name)
        if not os.path.exists(new_path):
            return new_path
        counter += 1

# --- API Fetching Functions ---

def get_api_data(url):
    """Fetches data from a given Torn API URL."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if 'error' in data:
            logging.error(f"API Error: {data['error']['error']}")
            return None
        return data
    except requests.exceptions.RequestException as e:
        logging.error(f"An HTTP error occurred: {e}")
        return None
    except ValueError:
        logging.error("Error decoding JSON from response.")
        return None

def get_war_details(war_id, api_key):
    """Fetches the details of a specific ranked war."""
    logging.info(f"Fetching details for War ID: {war_id}...")
    url = f"https://api.torn.com/torn/{war_id}?selections=rankedwarreport&key={api_key}"
    return get_api_data(url)

def get_all_attacks(faction_id, start_timestamp, end_timestamp, api_key):
    """Fetches all faction attacks within a given timeframe."""
    logging.info(f"Fetching all faction attack logs...")
    all_attacks = {}
    current_from = start_timestamp

    while current_from < end_timestamp:
        url = f"https://api.torn.com/faction/{faction_id}?selections=attacks,assists&from={current_from}&to={end_timestamp}&key={api_key}"
        data = get_api_data(url)
        if data:
            # Merge attacks and assists
            if 'attacks' in data:
                all_attacks.update(data['attacks'])
            if 'assists' in data:
                # Assists don't have all the same fields, we just need to know they happened
                for assist_id, assist_data in data['assists'].items():
                     if assist_id not in all_attacks: # Avoid overwriting full attack logs
                        all_attacks[assist_id] = assist_data
            
            # Pagination logic for attacks (assists are not paginated the same way)
            attack_logs = [v for v in data.get('attacks', {}).values()]
            if not attack_logs:
                break
            
            last_timestamp = max(v['timestamp_ended'] for v in attack_logs)
            if last_timestamp > current_from:
                 current_from = last_timestamp
            else:
                 break
            logging.info(f"Fetched {len(attack_logs)} attacks in chunk, advancing to timestamp {current_from}")
            time.sleep(3)
        else:
            break
    
    unique_attacks = list(all_attacks.values())
    logging.info(f"Finished fetching. Total unique events: {len(unique_attacks)}")
    return unique_attacks

# --- Data Processing and Payout Calculation ---

def process_and_calculate_payouts(war_report, all_events, our_faction_id, profile, prize_total):
    """Processes events and calculates payouts based on the chosen profile."""
    logging.info("Processing data and calculating payouts...")
    war_data = war_report.get('rankedwarreport', {})
    factions = war_data.get('factions', {})
    opponent_faction_id = None
    for fid, details in factions.items():
        if int(fid) != our_faction_id:
            opponent_faction_id = int(fid)
            break
    if not opponent_faction_id: return None

    # Initialize member data structure
    members_data = {}
    our_members_in_war = war_data.get('members', {}).get(str(our_faction_id), {})
    for member_id, member_details in our_members_in_war.items():
        members_data[int(member_id)] = {
            'name': member_details.get('name', 'Unknown'),
            'respect': 0,
            'chain_hits': 0,
            'assists': 0,
            'payouts': {}
        }

    # Process all events to gather stats
    total_respect = 0
    total_chain_hits = 0
    total_assists = 0
    for event in all_events:
        attacker_id = event.get('attacker_id')
        if attacker_id and attacker_id not in members_data: continue # Only count members who were in the war

        # Count Assists
        if event.get('type') == 'assist':
            members_data[attacker_id]['assists'] += 1
            total_assists += 1
            continue # Move to next event

        # Count Respect and Chain Hits
        is_war_hit = (event.get('defender_faction') == opponent_faction_id and event.get('ranked_war') == 1)
        if is_war_hit:
            respect_gain = event.get('respect_gain', 0)
            members_data[attacker_id]['respect'] += respect_gain
            total_respect += respect_gain
        
        if event.get('chain', 0) > 0:
            members_data[attacker_id]['chain_hits'] += 1
            total_chain_hits += 1

    # --- Payout Calculation ---
    model = profile.get('model_type', 'standard')
    prize_total = float(prize_total)
    
    # 1. Carve out faction pool
    faction_percent = float(profile.get('faction_pool_percent', 0))
    faction_pool = prize_total * (faction_percent / 100)
    remaining_pool = prize_total - faction_pool

    # 2. Handle different models
    if model == 'equal_share':
        active_members = [m for m in members_data.values() if m['respect'] > 0]
        if active_members:
            share = remaining_pool / len(active_members)
            for member in active_members:
                member['payouts']['Main Pool'] = share
    
    elif model == 'multi_pool':
        # Carve out bonus pools from the remaining pool
        chain_percent = float(profile.get('chain_hits_pool_percent', 0))
        assist_percent = float(profile.get('assists_pool_percent', 0))

        chain_pool = remaining_pool * (chain_percent / 100)
        assist_pool = remaining_pool * (assist_percent / 100)
        main_payout_pool = remaining_pool - chain_pool - assist_pool
        
        for member in members_data.values():
            # Main pool (respect-based)
            if total_respect > 0:
                member['payouts']['Main Pool (Respect)'] = main_payout_pool * (member['respect'] / total_respect)
            # Chain pool
            if total_chain_hits > 0:
                member['payouts']['Chain Bonus'] = chain_pool * (member['chain_hits'] / total_chain_hits)
            # Assist pool
            if total_assists > 0:
                member['payouts']['Assist Bonus'] = assist_pool * (member['assists'] / total_assists)

    # Calculate total payout for each member
    for member in members_data.values():
        member['total_payout'] = sum(member['payouts'].values())

    # Sort by total payout
    sorted_members = sorted(members_data.values(), key=lambda x: x['total_payout'], reverse=True)

    # Prepare chart data
    chart_data = {
        'pool_distribution': {
            'Faction': faction_pool,
            'Main Payout': main_payout_pool if model == 'multi_pool' else remaining_pool,
            'Chain Bonus': chain_pool if model == 'multi_pool' else 0,
            'Assist Bonus': assist_pool if model == 'multi_pool' else 0,
        }
    }

    return sorted_members, chart_data


# --- HTML Generation ---

def generate_war_report_html(processed_members, chart_data, war_report, profile):
    """Generates the final HTML report file using a Jinja2 template."""
    if not processed_members:
        logging.warning("No participating members to generate a report for.")
        return

    # Set up Jinja2 environment
    env = Environment(loader=FileSystemLoader('.'))
    try:
        template = env.get_template('report_template.html')
    except FileNotFoundError:
        logging.error("report_template.html not found. Please create it.")
        return

    war_data = war_report['rankedwarreport']
    context = {
        'profile_description': profile.get('description', 'No description available.'),
        'war_id': war_data['war']['id'],
        'our_faction_name': war_data['factions'][str(war_data['faction_id'])]['name'],
        'opponent_faction_name': [v['name'] for k,v in war_data['factions'].items() if k != str(war_data['faction_id'])][0],
        'start_str': datetime.fromtimestamp(war_data['war']['start']).strftime('%Y-%m-%d %H:%M:%S'),
        'end_str': datetime.fromtimestamp(war_data['war']['end']).strftime('%Y-%m-%d %H:%M:%S'),
        'members': processed_members,
        'chart_data_json': json.dumps(chart_data)
    }

    html_content = template.render(context)
    
    opponent_name_safe = context['opponent_faction_name'].replace(' ', '_').replace('[', '').replace(']', '')
    base_filename = f"war_report_{context['war_id']}_{opponent_name_safe}.html"
    unique_filename = get_unique_filename(base_filename)

    with open(unique_filename, "w", encoding="utf-8") as f:
        f.write(html_content)
    logging.info(f"Successfully generated {unique_filename}")


# --- Main Execution ---

def main():
    """Main function to generate the war report."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    API_KEY, profiles = get_profiles()
    if not API_KEY or not profiles:
        sys.exit(1)
    
    chosen_profile = select_profile(profiles)
    
    parser = argparse.ArgumentParser(description="Generate a ranked war report for Torn.com.")
    parser.add_argument("-w", "--war-id", type=str, help="The ranked war ID.")
    args = parser.parse_args()

    if args.war_id:
        war_id = args.war_id
    else:
        war_id = input("Please enter the Ranked War ID: ")
    
    prize_total = input("Please enter the total Prize Pool amount: ")

    war_report = get_war_details(war_id, API_KEY)
    if not war_report: sys.exit(1)

    our_faction_id = war_report['rankedwarreport']['faction_id']
    war_start_time = war_report['rankedwarreport']['war']['start']
    war_end_time = war_report['rankedwarreport']['war']['end']
    
    fetch_start_time = war_start_time - 330
    fetch_end_time = war_end_time + 330
    
    all_events = get_all_attacks(our_faction_id, fetch_start_time, fetch_end_time, API_KEY)
    
    processed_members, chart_data = process_and_calculate_payouts(war_report, all_events, our_faction_id, chosen_profile, prize_total)

    if processed_members:
        generate_war_report_html(processed_members, chart_data, war_report, chosen_profile)

if __name__ == '__main__':
    main()