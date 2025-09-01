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

# Define constants for directories
CACHE_DIR = 'cache'
REPORTS_DIR = 'reports'

# --- Configuration ---
def get_config(config_filename="v3_config.ini"):
    """Reads configuration from a given .ini file and returns it as a dictionary."""
    config_parser = configparser.ConfigParser()
    config = {
        'api_key': None,
        'faction_share_default': '30',
        'guaranteed_share_default': '10',
        'presets': {}
    }

    if not os.path.exists(config_filename):
        logging.error(f"{config_filename} file not found. Please create it.")
        return None

    config_parser.read(config_filename)

    # Read API Key
    if 'TornAPI' in config_parser and 'ApiKey' in config_parser['TornAPI']:
        key = config_parser['TornAPI']['ApiKey']
        if key and key.strip() and key != 'YourActualApiKeyHere':
            config['api_key'] = key
        else:
            logging.error(f"API key not set in {config_filename}.")
            return None
    else:
        logging.error(f"[TornAPI] section or ApiKey not found in {config_filename}.")
        return None

    # Read Defaults, but don't fail if they're missing
    if 'Defaults' in config_parser:
        config['faction_share_default'] = config_parser['Defaults'].get('FactionShare', config['faction_share_default'])
        config['guaranteed_share_default'] = config_parser['Defaults'].get('GuaranteedShare', config['guaranteed_share_default'])

    # Read Presets
    for section in config_parser.sections():
        if section.startswith('Preset_'):
            config['presets'][section] = dict(config_parser.items(section))

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
            time.sleep(3)
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

    logging.info(f"Our Faction ID: {our_faction_id}, Opponent Faction ID: {opponent_faction_id}")

    member_stats = {}
    our_members_in_war = war_data.get('factions', {}).get(str(our_faction_id), {}).get('members', {})
    logging.info(f"Found {len(our_members_in_war)} members from our faction in the war report.")
    for member_id, member_details in our_members_in_war.items():
        member_stats[member_id] = {
            'name': member_details.get('name', 'Unknown'),
            'respect_gained': 0.0,
            'base_respect_gained': 0.0,
            'hits_made': 0,
            'assists': 0,
            'hits_taken': 0,
            'defends': 0,
            'stalemates': 0
        }

    if all_attacks:
        offensive_hits = 0
        defensive_hits = 0
        for attack in all_attacks:
            if attack.get('ranked_war') != 1:
                continue

            attacker_id_str = str(attack.get('attacker_id'))
            defender_id_str = str(attack.get('defender_id'))

            is_offensive = (attack.get('attacker_faction') == our_faction_id and
                            attack.get('defender_faction') == opponent_faction_id)

            if is_offensive and attacker_id_str in member_stats:
                offensive_hits += 1
                member_stats[attacker_id_str]['hits_made'] += 1
                respect_gain = float(attack.get('respect_gain', 0.0))
                member_stats[attacker_id_str]['respect_gained'] += respect_gain

                chain_bonus = float(attack.get('modifiers', {}).get('chain_bonus', 1.0) or 1.0)
                base_respect = respect_gain / chain_bonus
                member_stats[attacker_id_str]['base_respect_gained'] += base_respect

                if attack.get('result') == 'Assist':
                    member_stats[attacker_id_str]['assists'] += 1

            is_defensive = (attack.get('defender_faction') == our_faction_id and
                            attack.get('attacker_faction') == opponent_faction_id)

            if is_defensive and defender_id_str in member_stats:
                defensive_hits += 1
                result = attack.get('result')
                if result == 'Lost':
                    member_stats[defender_id_str]['hits_taken'] += 1
                elif result == 'Stalemate':
                    member_stats[defender_id_str]['stalemates'] += 1
                else:
                    member_stats[defender_id_str]['defends'] += 1

        logging.info(f"Processed {offensive_hits} offensive attacks and {defensive_hits} defensive actions.")

    active_members = {mid: stats for mid, stats in member_stats.items() if stats['respect_gained'] > 0}
    sorted_stats = sorted(active_members.items(), key=lambda item: item[1]['respect_gained'], reverse=True)

    return {
        'war_details': war_data,
        'member_stats': sorted_stats,
        'our_faction_name': factions.get(str(our_faction_id), {}).get('name', 'Your Faction'),
        'opponent_faction_name': factions.get(str(opponent_faction_id), {}).get('name', 'Opponent')
    }

def calculate_final_payouts(settings, member_stats, prize_total_str, faction_share_str, guaranteed_share_str):
    """Calculates final dollar amounts for each member based on selected settings."""
    logging.info("Calculating final payouts based on settings...")

    try:
        prize_total = int(str(prize_total_str).replace(',', '').replace('$', '').strip())
        faction_share_percent = int(faction_share_str)
        guaranteed_share_percent = int(guaranteed_share_str)
    except (ValueError, TypeError):
        logging.error("Invalid numeric value provided for payout calculation.")
        return member_stats

    use_bonus_respect = settings.get('use_bonus_respect', 'true').lower() == 'true'
    assist_payment_type = settings.get('assist_payment_type', 'none')
    assist_payment_value = int(settings.get('assist_payment_value', '0'))
    penalty_per_hit_taken = int(settings.get('penalty_per_hit_taken', '0'))

    member_data = dict(member_stats)
    if not member_data:
        logging.warning("No member data to calculate payouts for.")
        return []

    participant_count = len(member_data)

    faction_take = prize_total * (faction_share_percent / 100)
    member_pool = prize_total - faction_take

    guaranteed_pool = member_pool * (guaranteed_share_percent / 100)
    guaranteed_payout_per_member = guaranteed_pool / participant_count if participant_count > 0 else 0

    adjustable_pool = member_pool - guaranteed_pool

    total_assists = sum(stats['assists'] for stats in member_data.values())
    total_hits_taken = sum(stats['hits_taken'] for stats in member_data.values())

    total_assist_payout = 0
    if assist_payment_type == 'flat':
        total_assist_payout = total_assists * assist_payment_value

    total_penalty_deductions = total_hits_taken * penalty_per_hit_taken

    participation_pool = adjustable_pool - total_assist_payout - total_penalty_deductions
    if participation_pool < 0:
        logging.warning(f"Participation pool is negative (${participation_pool:,.2f}). Payouts from respect share will be zero.")
        participation_pool = 0

    respect_key = 'respect_gained' if use_bonus_respect else 'base_respect_gained'
    total_respect_to_share = sum(stats[respect_key] for stats in member_data.values())

    for _, stats in member_data.items():
        stats['guaranteed_payout'] = guaranteed_payout_per_member
        stats['penalty_amount'] = stats['hits_taken'] * penalty_per_hit_taken

        stats['assist_payout'] = 0
        if assist_payment_type == 'flat':
            stats['assist_payout'] = stats['assists'] * assist_payment_value

        member_respect = stats[respect_key]
        respect_share_percent = (member_respect / total_respect_to_share) if total_respect_to_share > 0 else 0
        stats['participation_payout'] = participation_pool * respect_share_percent

        stats['adjustments'] = stats['assist_payout'] - stats['penalty_amount']
        stats['respect_payout'] = stats['guaranteed_payout'] + stats['participation_payout']
        stats['final_payout'] = stats['respect_payout'] + stats['adjustments']

    sorted_member_data = sorted(member_data.items(), key=lambda item: item[1]['final_payout'], reverse=True)

    logging.info("Finished calculating payouts.")
    return sorted_member_data

# --- HTML Generation Functions ---
def generate_war_report_html(processed_data, war_id, prize_total, faction_share, guaranteed_share):
    """Generates the final simple HTML report file using a Jinja2 template."""
    if not processed_data or not processed_data.get('member_stats'):
        logging.warning("No participating members found with respect gained. Report generation skipped.")
        return

    env = Environment(loader=FileSystemLoader('.'))
    try:
        template = env.get_template('v3_report_template.html')
    except FileNotFoundError:
        logging.error("v3_report_template.html not found in the script's directory.")
        return

    member_stats = processed_data['member_stats']
    total_respect_payout = sum(stats.get('respect_payout', 0) for _, stats in member_stats)
    total_adjustments = sum(stats.get('adjustments', 0) for _, stats in member_stats)
    total_final_payout = sum(stats.get('final_payout', 0) for _, stats in member_stats)

    war_details = processed_data['war_details']
    context = {
        'war_id': war_id,
        'our_faction_name': processed_data['our_faction_name'],
        'opponent_faction_name': processed_data['opponent_faction_name'],
        'start_str': datetime.fromtimestamp(war_details['war']['start']).strftime('%Y-%m-%d %H:%M:%S'),
        'end_str': datetime.fromtimestamp(war_details['war']['end']).strftime('%Y-%m-%d %H:%M:%S'),
        'member_stats': member_stats,
        'total_respect_gained': sum(stats['respect_gained'] for _, stats in member_stats),
        'total_respect_payout': total_respect_payout,
        'total_adjustments': total_adjustments,
        'total_final_payout': total_final_payout
    }

    html_content = template.render(context)

    opponent_name_safe = processed_data['opponent_faction_name'].replace(' ', '_').replace('[', '').replace(']', '')
    base_filename = f"v3_war_report_{war_id}_{opponent_name_safe}.html"
    report_path = os.path.join(REPORTS_DIR, base_filename)
    unique_filename = get_unique_filename(report_path)

    with open(unique_filename, "w", encoding="utf-8") as f:
        f.write(html_content)
    logging.info(f"Successfully generated simple report: {unique_filename}")


def generate_advanced_report_html(processed_data, war_id):
    """Generates the final advanced HTML report file using a Jinja2 template."""
    if not processed_data or not processed_data.get('member_stats'):
        logging.warning("No data for advanced report. Generation skipped.")
        return

    env = Environment(loader=FileSystemLoader('.'))
    try:
        template = env.get_template('v3_advanced_report_template.html')
    except FileNotFoundError:
        logging.error("v3_advanced_report_template.html not found in the script's directory.")
        return

    member_stats = processed_data['member_stats']

    # Calculate totals for all columns
    totals = {
        key: sum(stats.get(key, 0) for _, stats in member_stats)
        for key in ['hits_made', 'defends', 'assists', 'hits_taken', 'stalemates', 'respect_gained',
                    'guaranteed_payout', 'participation_payout', 'assist_payout', 'penalty_amount', 'final_payout']
    }

    # Find top performers
    top_earner_stats = member_stats[0][1] if member_stats else {'name': 'N/A', 'final_payout': 0}
    top_hitter = max(member_stats, key=lambda item: item[1]['hits_made']) if member_stats else ('', {'name': 'N/A', 'hits_made': 0})

    war_details = processed_data['war_details']
    context = {
        'war_id': war_id,
        'our_faction_name': processed_data['our_faction_name'],
        'opponent_faction_name': processed_data['opponent_faction_name'],
        'start_str': datetime.fromtimestamp(war_details['war']['start']).strftime('%Y-%m-%d %H:%M:%S'),
        'end_str': datetime.fromtimestamp(war_details['war']['end']).strftime('%Y-%m-%d %H:%M:%S'),
        'member_stats': member_stats,
        'totals': totals,
        'top_earner': {'name': top_earner_stats['name'], 'payout': top_earner_stats['final_payout']},
        'top_hitter': {'name': top_hitter[1]['name'], 'hits': top_hitter[1]['hits_made']}
    }

    html_content = template.render(context)

    opponent_name_safe = processed_data['opponent_faction_name'].replace(' ', '_').replace('[', '').replace(']', '')
    base_filename = f"v3_advanced_report_{war_id}_{opponent_name_safe}.html"
    report_path = os.path.join(REPORTS_DIR, base_filename)
    unique_filename = get_unique_filename(report_path)

    with open(unique_filename, "w", encoding="utf-8") as f:
        f.write(html_content)
    logging.info(f"Successfully generated advanced report: {unique_filename}")


# --- Main Execution ---
def main():
    """Main function to generate the war report."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    os.makedirs(CACHE_DIR, exist_ok=True)
    os.makedirs(REPORTS_DIR, exist_ok=True)

    config = get_config("v3_config.ini")
    if not config or not config.get('api_key'):
        sys.exit(1)

    API_KEY = config['api_key']

    # --- Argument Parsing ---
    parser = argparse.ArgumentParser(
        description="Generate a ranked war report for Torn.com.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Usage Examples:
-----------------
1. Interactive Mode (will prompt for all inputs):
   python v3_war_report.py

2. Basic Report (using default shares from config.ini):
   python v3_war_report.py 28997

3. Report with Custom Payouts:
   python v3_war_report.py 28997 --prize-total 1000000000 --faction-share 25 --guaranteed-share 5

4. Force Refresh (ignore and overwrite cache):
   python v3_war_report.py 28997 --no-cache

5. Using a Payout Preset from config.ini:
   python v3_war_report.py 28997 --prize-total 1b --preset Preset_NoBonus_AssistsFlat
"""
    )
    parser.add_argument('war_id', nargs='?', default=None, help='The ranked war ID. Required for non-interactive mode.')
    parser.add_argument('-p', '--prize-total', type=str, help='The total prize money for the war (e.g., 1000000000).')
    parser.add_argument('-f', '--faction-share', type=str, help=f"The percentage of the prize the faction keeps. Default: {config['faction_share_default']}%%")
    parser.add_argument('-g', '--guaranteed-share', type=str, help=f"The percentage of the member pool for guaranteed payouts. Default: {config['guaranteed_share_default']}%%")
    parser.add_argument('--preset', type=str, help='The name of the payout preset to use from config.ini (e.g., Preset_Standard).')
    parser.add_argument('--no-cache', action='store_true', help='Ignore existing cache and fetch fresh attack data from the API.')

    args = parser.parse_args()

    # --- Determine Mode (Interactive vs. Argument-driven) ---
    if args.war_id:
        # Argument-driven mode
        war_id = args.war_id
        prize_total = args.prize_total if args.prize_total is not None else "0"
        faction_share = args.faction_share if args.faction_share is not None else config['faction_share_default']
        guaranteed_share = args.guaranteed_share if args.guaranteed_share is not None else config['guaranteed_share_default']
    else:
        # Interactive mode
        logging.info("No War ID provided. Entering interactive mode.")
        war_id = prompt_for_numeric_input("Please enter the Ranked War ID")
        logging.info("Please provide payout details (press Enter to use defaults):")
        prize_total = prompt_for_numeric_input("Prize Total", default="0")
        faction_share = prompt_for_numeric_input("Faction Share %", default=config['faction_share_default'])
        guaranteed_share = prompt_for_numeric_input("Guaranteed Share %", default=config['guaranteed_share_default'])

    # --- Start processing and API calls ---
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

    # --- Caching logic for attack logs ---
    cache_file_path = os.path.join(CACHE_DIR, f"v3_war_hits_cache_{war_id}.json")
    all_attacks = None

    if not args.no_cache and os.path.exists(cache_file_path):
        logging.info(f"Loading attack data from cache: {cache_file_path}")
        try:
            with open(cache_file_path, 'r', encoding='utf-8') as f:
                all_attacks = json.load(f)
            logging.info(f"Successfully loaded {len(all_attacks)} unique attacks from cache.")
        except (json.JSONDecodeError, IOError) as e:
            logging.warning(f"Could not read cache file {cache_file_path}: {e}. Refetching from API.")
            all_attacks = None

    if all_attacks is None:
        logging.info("Cache not found or invalid. Fetching attacks from API...")
        fetch_start_time = war_start_time - 330
        fetch_end_time = war_end_time + 330
        all_attacks = get_all_attacks(our_faction_id, fetch_start_time, fetch_end_time, API_KEY)

        if all_attacks:
            logging.info(f"Saving attack data to cache: {cache_file_path}")
            with open(cache_file_path, 'w', encoding='utf-8') as f:
                json.dump(all_attacks, f, indent=4)

    processed_data = process_war_data(war_report, all_attacks, our_faction_id)

    if processed_data:
        # --- Payout Calculation ---
        if processed_data.get('member_stats'):
            active_preset = {}
            if args.preset:
                if args.preset in config['presets']:
                    active_preset = config['presets'][args.preset]
                    logging.info(f"Using '{args.preset}' preset for payout calculations.")
                else:
                    logging.warning(f"Preset '{args.preset}' not found in config.ini. Using default calculation logic.")

            calculated_stats = calculate_final_payouts(
                settings=active_preset,
                member_stats=processed_data['member_stats'],
                prize_total_str=prize_total,
                faction_share_str=faction_share,
                guaranteed_share_str=guaranteed_share
            )
            processed_data['member_stats'] = calculated_stats

        # --- Report Generation ---
        generate_war_report_html(processed_data, war_id, prize_total, faction_share, guaranteed_share)
        generate_advanced_report_html(processed_data, war_id)

if __name__ == '__main__':
    main()
