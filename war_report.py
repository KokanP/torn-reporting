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

# --- Configuration ---
def get_config():
    """Reads configuration from config.ini and returns it as a dictionary."""
    config_parser = configparser.ConfigParser()
    config = {
        'api_key': None,
        'faction_share_default': '30',
        'guaranteed_share_default': '10'
    }

    if not os.path.exists('config.ini'):
        logging.error("config.ini file not found. Please create it.")
        return None

    config_parser.read('config.ini')

    # Read API Key
    if 'TornAPI' in config_parser and 'ApiKey' in config_parser['TornAPI']:
        key = config_parser['TornAPI']['ApiKey']
        if key and key.strip() and key != 'YourActualApiKeyHere':
            config['api_key'] = key
        else:
            logging.error("API key not set in config.ini.")
            return None
    else:
        logging.error("[TornAPI] section or ApiKey not found in config.ini.")
        return None

    # Read Defaults, but don't fail if they're missing
    if 'Defaults' in config_parser:
        config['faction_share_default'] = config_parser['Defaults'].get('FactionShare', config['faction_share_default'])
        config['guaranteed_share_default'] = config_parser['Defaults'].get('GuaranteedShare', config['guaranteed_share_default'])

    return config

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

def prompt_for_numeric_input(prompt_message, default=None):
    """Prompts the user for numeric input, allowing an optional default value."""
    while True:
        prompt_suffix = f" (default: {default})" if default is not None else ""
        user_input = input(f"{prompt_message}{prompt_suffix}: ")

        if user_input.strip() == "" and default is not None:
            return str(default)
        
        cleaned_input = user_input.replace(',', '').replace('$', '').strip()

        if cleaned_input.isdigit():
            return cleaned_input
        else:
            logging.warning("Invalid input. Please enter a whole number or press Enter to use the default.")

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
    start_str = datetime.fromtimestamp(start_timestamp).strftime('%Y-%m-%d %H:%M:%S')
    end_str = datetime.fromtimestamp(end_timestamp).strftime('%Y-%m-%d %H:%M:%S')
    logging.info(f"Fetching all attack logs from {start_str} to {end_str}...")
    all_attacks = []
    current_from = start_timestamp

    while current_from < end_timestamp:
        url = f"https://api.torn.com/faction/{faction_id}?selections=attacks&from={current_from}&to={end_timestamp}&key={api_key}"
        data = get_api_data(url)
        if data and 'attacks' in data:
            attacks_chunk = list(data['attacks'].values())
            if not attacks_chunk:
                break
            all_attacks.extend(attacks_chunk)

            last_timestamp = attacks_chunk[-1]['timestamp_ended']
            if last_timestamp > current_from:
                 current_from = last_timestamp
            else:
                 break
            logging.info(f"Fetched {len(attacks_chunk)} attacks, advancing to timestamp {current_from}")
            time.sleep(1)
        else:
            break

    logging.info(f"Finished fetching. Total attacks: {len(all_attacks)}")
    unique_attacks = list({attack['code']: attack for attack in all_attacks}.values())
    logging.info(f"Unique attacks after de-duplication: {len(unique_attacks)}")
    return unique_attacks

# --- Data Processing Functions ---
def process_war_data(war_report, all_attacks, our_faction_id):
    """Processes the raw API data to calculate member contributions."""
    logging.info("Processing war data...")
    war_data = war_report.get('rankedwarreport', {})

    factions = war_data.get('factions', {})
    opponent_faction_id = None
    for fid, details in factions.items():
        if int(fid) != our_faction_id:
            opponent_faction_id = int(fid)
            break

    if not opponent_faction_id:
        logging.error("Could not determine opponent faction.")
        return None

    member_stats = {}
    our_members_in_war = war_data.get('members', {}).get(str(our_faction_id), {})
    for member_id, member_details in our_members_in_war.items():
        member_stats[member_id] = {'respect_gained': 0, 'name': member_details.get('name', 'Unknown')}

    for attack in all_attacks:
        is_our_attack = (attack.get('attacker_faction') == our_faction_id and
                         attack.get('defender_faction') == opponent_faction_id)
        is_ranked_war_attack = attack.get('ranked_war') == 1

        if is_our_attack and is_ranked_war_attack:
            attacker_id = str(attack['attacker_id'])
            respect_gain = attack.get('respect_gain', 0)

            if attacker_id in member_stats:
                member_stats[attacker_id]['respect_gained'] += respect_gain
            else:
                member_stats[attacker_id] = {'respect_gained': respect_gain, 'name': attack.get('attacker_name', 'Unknown (Ex-member)')}

    active_members = {mid: stats for mid, stats in member_stats.items() if stats['respect_gained'] > 0}
    sorted_stats = sorted(active_members.items(), key=lambda item: item[1]['respect_gained'], reverse=True)

    return {
        'war_details': war_data,
        'member_stats': sorted_stats,
        'our_faction_name': factions.get(str(our_faction_id), {}).get('name', 'Your Faction'),
        'opponent_faction_name': factions.get(str(opponent_faction_id), {}).get('name', 'Opponent')
    }

# --- HTML Generation Functions ---
def generate_war_report_html(processed_data, war_id, prize_total, faction_share, guaranteed_share):
    """Generates the final HTML report file using a Jinja2 template."""
    if not processed_data or not processed_data.get('member_stats'):
        logging.warning("No participating members found with respect gained. Report generation skipped.")
        return

    # Set up Jinja2 environment
    env = Environment(loader=FileSystemLoader('.'))
    try:
        template = env.get_template('report_template.html')
    except FileNotFoundError:
        logging.error("report_template.html not found in the script's directory.")
        return

    # Prepare data for the template
    war_details = processed_data['war_details']
    context = {
        'war_id': war_id,
        'prize_total': prize_total,
        'faction_share': faction_share,
        'guaranteed_share': guaranteed_share,
        'our_faction_name': processed_data['our_faction_name'],
        'opponent_faction_name': processed_data['opponent_faction_name'],
        'start_str': datetime.fromtimestamp(war_details['war']['start']).strftime('%Y-%m-%d %H:%M:%S'),
        'end_str': datetime.fromtimestamp(war_details['war']['end']).strftime('%Y-%m-%d %H:%M:%S'),
        'member_stats': processed_data['member_stats'],
        'total_respect_gained': sum(stats['respect_gained'] for _, stats in processed_data['member_stats'])
    }

    # Render the template with the data
    html_content = template.render(context)
    
    # Generate a unique filename
    opponent_name_safe = processed_data['opponent_faction_name'].replace(' ', '_').replace('[', '').replace(']', '')
    base_filename = f"war_report_{war_id}_{opponent_name_safe}.html"
    unique_filename = get_unique_filename(base_filename)

    # Write the rendered HTML to the file
    with open(unique_filename, "w", encoding="utf-8") as f:
        f.write(html_content)
    logging.info(f"Successfully generated {unique_filename}")


# --- Main Execution ---
def main():
    """Main function to generate the war report."""
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    config = get_config()
    if not config or not config.get('api_key'):
        sys.exit(1)
    
    API_KEY = config['api_key']

    parser = argparse.ArgumentParser(description="Generate a ranked war report for Torn.com.")
    parser.add_argument("-w", "--war-id", type=str, help="The ranked war ID.")
    args = parser.parse_args()

    # --- Get War ID ---
    if args.war_id:
        war_id = args.war_id
    else:
        war_id = prompt_for_numeric_input("Please enter the Ranked War ID")
    
    # --- Get War Data ---
    war_report = get_war_details(war_id, API_KEY)
    if not war_report or 'rankedwarreport' not in war_report:
        logging.error("Could not fetch war report. Check the War ID and API key.")
        sys.exit(1)

    user_data = get_api_data(f"https://api.torn.com/user/?selections=profile&key={API_KEY}")
    if not user_data or 'faction' not in user_data or user_data['faction']['faction_id'] == 0:
        logging.error("Could not determine your faction ID from the API key provided.")
        sys.exit(1)
        
    our_faction_id = user_data['faction']['faction_id']
    war_start_time = war_report['rankedwarreport']['war']['start']
    war_end_time = war_report['rankedwarreport']['war']['end']
    
    fetch_start_time = war_start_time - 330
    fetch_end_time = war_end_time + 330
    
    all_attacks = get_all_attacks(our_faction_id, fetch_start_time, fetch_end_time, API_KEY)
    
    processed_data = process_war_data(war_report, all_attacks, our_faction_id)

    if processed_data:
        # --- Get Optional Payout Parameters ---
        logging.info("Please provide payout details (press Enter to use defaults):")
        prize_total = prompt_for_numeric_input("Prize Total", default="0")
        faction_share = prompt_for_numeric_input("Faction Share %", default=config['faction_share_default'])
        guaranteed_share = prompt_for_numeric_input("Guaranteed Share %", default=config['guaranteed_share_default'])
        
        generate_war_report_html(processed_data, war_id, prize_total, faction_share, guaranteed_share)

if __name__ == '__main__':
    main()