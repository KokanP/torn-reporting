import requests
import json
import time
from datetime import datetime
import argparse
import sys
import os
import configparser

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
        print(" -> Error: config.ini file not found. Please create it.")
        return None

    config_parser.read('config.ini')

    # Read API Key
    if 'TornAPI' in config_parser and 'ApiKey' in config_parser['TornAPI']:
        key = config_parser['TornAPI']['ApiKey']
        if key and key.strip() and key != 'YourActualApiKeyHere':
            config['api_key'] = key
        else:
            print(" -> Error: API key not set in config.ini.")
            return None
    else:
        print(" -> Error: [TornAPI] section or ApiKey not found in config.ini.")
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
            print(" -> Invalid input. Please enter a whole number or press Enter to use the default.")

# --- API Fetching Functions ---
def get_api_data(url):
    """Fetches data from a given Torn API URL."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if 'error' in data:
            print(f" -> API Error: {data['error']['error']}")
            return None
        return data
    except requests.exceptions.RequestException as e:
        print(f" -> An HTTP error occurred: {e}")
        return None
    except ValueError:
        print(" -> Error decoding JSON from response.")
        return None

def get_war_details(war_id, api_key):
    """Fetches the details of a specific ranked war."""
    print(f"Fetching details for War ID: {war_id}...")
    url = f"https://api.torn.com/torn/{war_id}?selections=rankedwarreport&key={api_key}"
    return get_api_data(url)

def get_all_attacks(faction_id, start_timestamp, end_timestamp, api_key):
    """Fetches all faction attacks within a given timeframe."""
    start_str = datetime.fromtimestamp(start_timestamp).strftime('%Y-%m-%d %H:%M:%S')
    end_str = datetime.fromtimestamp(end_timestamp).strftime('%Y-%m-%d %H:%M:%S')
    print(f"Fetching all attack logs from {start_str} to {end_str}...")
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
            print(f" -> Fetched {len(attacks_chunk)} attacks, advancing to timestamp {current_from}")
            time.sleep(1)
        else:
            break

    print(f"Finished fetching. Total attacks: {len(all_attacks)}")
    unique_attacks = list({attack['code']: attack for attack in all_attacks}.values())
    print(f"Unique attacks after de-duplication: {len(unique_attacks)}")
    return unique_attacks

# --- Data Processing Functions ---
def process_war_data(war_report, all_attacks, our_faction_id):
    """Processes the raw API data to calculate member contributions."""
    print("Processing war data...")
    war_data = war_report.get('rankedwarreport', {})

    factions = war_data.get('factions', {})
    opponent_faction_id = None
    for fid, details in factions.items():
        if int(fid) != our_faction_id:
            opponent_faction_id = int(fid)
            break

    if not opponent_faction_id:
        print("Could not determine opponent faction.")
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
    """Generates the final HTML report file."""
    if not processed_data or not processed_data['member_stats']:
        print("No participating members found with respect gained. Report generation skipped.")
        return

    war_details = processed_data['war_details']
    member_stats = processed_data['member_stats']
    our_faction_name = processed_data['our_faction_name']
    opponent_faction_name = processed_data['opponent_faction_name']

    start_str = datetime.fromtimestamp(war_details['war']['start']).strftime('%Y-%m-%d %H:%M:%S')
    end_str = datetime.fromtimestamp(war_details['war']['end']).strftime('%Y-%m-%d %H:%M:%S')
    total_respect_gained = sum(stats['respect_gained'] for _, stats in member_stats)

    member_rows = ""
    for member_id, stats in member_stats:
        respect_gained = stats['respect_gained']
        respect_percent = (respect_gained / total_respect_gained * 100) if total_respect_gained > 0 else 0
        member_rows += f"""
            <tr class="table-row-light" data-respect="{respect_gained:.2f}" data-enabled="true" data-member-id="{member_id}" data-member-name="{stats['name']}">
                <td class="p-3">
                    <button class="status-toggle p-1 rounded-full bg-green-500 hover:bg-green-600">
                        <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
                    </button>
                </td>
                <td class="p-3 cursor-pointer" onclick="copyMemberInfo(this, '{stats['name']}', '{member_id}')">
                    <a href="https://www.torn.com/profiles.php?XID={member_id}" target="_blank" class="text-cyan-400 hover:underline">{stats['name']} [{member_id}]</a>
                </td>
                <td class="p-3 text-right">{respect_gained:,.2f}</td>
                <td class="p-3 text-right">{respect_percent:.2f}%</td>
                <td class="p-3 text-right text-yellow-400 font-semibold guaranteed-share">$0</td>
                <td class="p-3 text-right text-green-400 font-semibold participation-share">$0</td>
                <td class="p-3 text-right text-white font-bold total-prize">
                    <a href="#" class="text-white hover:underline" onclick="event.preventDefault(); window.open('https://www.torn.com/factions.php?step=your#/tab=controls&option=give-to-user&addMoneyTo={member_id}&money=' + Math.round(parseFloat(this.closest('tr').dataset.totalPrize)), '_blank'); highlightRow(this.closest('tr'));">
                        $0
                    </a>
                </td>
            </tr>
        """

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>War Report: {our_faction_name} vs {opponent_faction_name} (War ID: {war_id})</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
        <style>
            body {{ font-family: 'Inter', sans-serif; }}
            .card {{ background-color: #1f2937; border: 1px solid #374151; border-radius: 0.5rem; padding: 1.5rem; margin-bottom: 1.5rem; }}
            .table-header {{ background-color: #374151; }}
            .table-row-light {{ background-color: #2b3544; }}
            .config-input {{ background-color: #374151; border: 1px solid #4b5563; }}
            .config-input:read-only {{ background-color: #1f2937; border-color: #1f2937; cursor: not-allowed; }}
            .info-row {{ display: flex; align-items: center; padding: 0.5rem 0; }}
            .info-label {{ font-weight: bold; color: #9ca3af; margin-right: 1rem; flex-shrink: 0; min-width: 150px; }}
            .info-value {{ color: #ffffff; flex-grow: 1; }}
            .highlight-row {{ background-color: #4b5563; }}
        </style>
    </head>
    <body class="bg-gray-900 text-gray-300 p-4 sm:p-8">
        <div class="max-w-7xl mx-auto" id="report-container">
            <header class="text-center mb-8">
                <h1 class="text-4xl font-bold text-white">Ranked War Report</h1>
                <h2 class="text-2xl text-cyan-400">{our_faction_name} vs {opponent_faction_name} (War ID: {war_id})</h2>
            </header>

            <div class="card">
                <div class="mb-4">
                    <div class="info-row">
                        <span class="info-label">Start Date:</span>
                        <span class="info-value">{start_str}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">End Date:</span>
                        <span class="info-value">{end_str}</span>
                    </div>
                    <div class="info-row">
                        <label for="prizeTotal" class="info-label">Prize Total:</label>
                        <input type="text" id="prizeTotal" class="config-input w-2/3 rounded-md p-1 text-white" value="{prize_total}">
                    </div>
                    <div class="info-row">
                        <label for="factionShare" class="info-label">Faction Share:</label>
                        <div class="flex items-center">
                            <input type="number" id="factionShare" class="config-input w-20 rounded-md p-1 text-white" value="{faction_share}">
                            <span class="ml-1">%</span>
                        </div>
                    </div>
                    <div class="info-row">
                        <label for="guaranteedShare" class="info-label">Guaranteed Share:</label>
                        <div class="flex items-center">
                            <input type="number" id="guaranteedShare" class="config-input w-20 rounded-md p-1 text-white" value="{guaranteed_share}">
                            <span class="ml-1">%</span>
                        </div>
                    </div>
                </div>
            </div>

            <div class="card">
                <h3 class="text-xl font-semibold text-white mb-4">Member Contributions & Payouts</h3>
                <div class="overflow-x-auto">
                    <table class="w-full text-left">
                        <thead class="table-header">
                            <tr>
                                <th class="p-3">Status</th>
                                <th class="p-3">Member</th>
                                <th class="p-3 text-right">Respect Gained</th>
                                <th class="p-3 text-right">Respect Share</th>
                                <th class="p-3 text-right">Guaranteed Share</th>
                                <th class="p-3 text-right">Participation Share</th>
                                <th class="p-3 text-right">Total Prize</th>
                            </tr>
                        </thead>
                        <tbody id="member-table-body">{member_rows}</tbody>
                        <tfoot>
                            <tr class="table-header font-bold">
                                <td class="p-3" colspan="2">Total</td>
                                <td class="p-3 text-right">{total_respect_gained:,.2f}</td>
                                <td class="p-3 text-right">100.00%</td>
                                <td id="total-guaranteed" class="p-3 text-right">$0</td>
                                <td id="total-participation" class="p-3 text-right">$0</td>
                                <td id="total-payout" class="p-3 text-right">$0</td>
                            </tr>
                        </tfoot>
                    </table>
                </div>
            </div>

            <div class="mt-8 flex justify-center space-x-4">
                 <button id="screenshotButton" class="p-4 rounded-md bg-blue-600 hover:bg-blue-700" title="Download Screenshot">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-white" viewBox="0 0 20 20" fill="currentColor">
                        <path fill-rule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clip-rule="evenodd" />
                    </svg>
                </button>
                <button id="lockButton" class="p-4 rounded-md bg-cyan-600 hover:bg-cyan-700" title="Lock/Unlock Inputs">
                    <svg id="lockIcon" xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-white" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clip-rule="evenodd" /></svg>
                    <svg id="unlockIcon" xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-white hidden" viewBox="0 0 20 20" fill="currentColor"><path d="M10 2a5 5 0 00-5 5v2a2 2 0 00-2 2v5a2 2 0 002 2h10a2 2 0 002-2v-5a2 2 0 00-2-2V7a5 5 0 00-5-5zm0 2a3 3 0 00-3 3v2h6V7a3 3 0 00-3-3z" /></svg>
                </button>
            </div>
        </div>
        <script>
            const warId = '{war_id}';
            const storagePrefix = `warReport_${{warId}}_`;

            const prizeTotalInput = document.getElementById('prizeTotal');
            const factionShareInput = document.getElementById('factionShare');
            const guaranteedShareInput = document.getElementById('guaranteedShare');
            const memberRows = document.querySelectorAll('#member-table-body tr[data-respect]');
            const lockButton = document.getElementById('lockButton');
            const screenshotButton = document.getElementById('screenshotButton');
            const lockIcon = document.getElementById('lockIcon');
            const unlockIcon = document.getElementById('unlockIcon');
            const inputs = [prizeTotalInput, factionShareInput, guaranteedShareInput];

            function formatNumber(n) {{ return n.toString().replace(/\\D/g, "").replace(/\\B(?=(\\d{{3}})+(?!\\d))/g, ","); }}
            
            function calculatePayouts() {{
                let totalRespect = 0, participantCount = 0;
                memberRows.forEach(row => {{
                    if (row.dataset.enabled === 'true') {{
                        totalRespect += parseFloat(row.dataset.respect) || 0;
                        participantCount++;
                    }}
                }});
                
                const prizeTotal = parseFloat(prizeTotalInput.value.replace(/,/g, '')) || 0;
                const factionSharePercent = parseFloat(factionShareInput.value) || 0;
                const guaranteedSharePercent = parseFloat(guaranteedShareInput.value) || 0;
                
                const factionTake = prizeTotal * (factionSharePercent / 100);
                const memberPool = prizeTotal - factionTake;
                const guaranteedPool = memberPool * (guaranteedSharePercent / 100);
                const participationPool = memberPool - guaranteedPool;
                
                let totalGuaranteedPaid = 0, totalParticipationPaid = 0;
                
                memberRows.forEach(row => {{
                    if (row.dataset.enabled === 'true') {{
                        const respect = parseFloat(row.dataset.respect);
                        const respectShare = totalRespect > 0 ? (respect / totalRespect) : 0;
                        const guaranteedPayout = participantCount > 0 ? (guaranteedPool / participantCount) : 0;
                        const participationPayout = participationPool * respectShare;
                        const totalMemberPrize = guaranteedPayout + participationPayout;
                        
                        row.querySelector('.guaranteed-share').textContent = `$` + Math.round(guaranteedPayout).toLocaleString();
                        row.querySelector('.participation-share').textContent = `$` + Math.round(participationPayout).toLocaleString();
                        row.dataset.totalPrize = Math.round(totalMemberPrize);
                        
                        const prizeLink = row.querySelector('.total-prize a');
                        prizeLink.textContent = `$` + Math.round(totalMemberPrize).toLocaleString();
                        prizeLink.href = `https://www.torn.com/factions.php?step=your#/tab=controls&option=give-to-user&addMoneyTo=${{row.dataset.memberId}}&money=${{Math.round(totalMemberPrize)}}`;
                        
                        totalGuaranteedPaid += Math.round(guaranteedPayout);
                        totalParticipationPaid += Math.round(participationPayout);
                    }} else {{
                        row.querySelector('.guaranteed-share').textContent = '$0';
                        row.querySelector('.participation-share').textContent = '$0';
                        const prizeLink = row.querySelector('.total-prize a');
                        prizeLink.textContent = '$0';
                        prizeLink.href = '#';
                        row.dataset.totalPrize = '0';
                    }}
                }});
                
                document.getElementById('total-guaranteed').textContent = `$` + totalGuaranteedPaid.toLocaleString();
                document.getElementById('total-participation').textContent = `$` + totalParticipationPaid.toLocaleString();
                document.getElementById('total-payout').textContent = `$` + (totalGuaranteedPaid + totalParticipationPaid).toLocaleString();
            }}
            
            function togglePlayerStatus(button) {{
                const row = button.closest('tr');
                const isEnabled = row.dataset.enabled === 'true';
                if (isEnabled) {{
                    row.dataset.enabled = 'false';
                    button.classList.remove('bg-green-500', 'hover:bg-green-600');
                    button.classList.add('bg-red-500', 'hover:bg-red-600');
                    button.innerHTML = `<svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>`;
                }} else {{
                    row.dataset.enabled = 'true';
                    button.classList.remove('bg-red-500', 'hover:bg-red-600');
                    button.classList.add('bg-green-500', 'hover:bg-green-600');
                    button.innerHTML = `<svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>`;
                }}
                calculatePayouts();
            }}

            let lastHighlightedRow = null;
            function highlightRow(row) {{
                if (lastHighlightedRow) {{ lastHighlightedRow.classList.remove('highlight-row'); }}
                row.classList.add('highlight-row');
                lastHighlightedRow = row;
            }}

            function copyMemberInfo(element, memberName, memberId) {{
                highlightRow(element.closest('tr'));
                navigator.clipboard.writeText(`${{memberName}} [${{memberId}}]`);
            }}
            
            function takeScreenshot() {{
                const reportContainer = document.getElementById('report-container');
                const buttonsParent = document.querySelector('.mt-8.flex');
                buttonsParent.style.display = 'none';
                html2canvas(reportContainer, {{ backgroundColor: '#111827', windowWidth: reportContainer.scrollWidth, windowHeight: reportContainer.scrollHeight }})
                    .then(canvas => {{
                        const link = document.createElement('a');
                        link.download = `war_report_${{warId}}.png`;
                        link.href = canvas.toDataURL('image/png');
                        link.click();
                        buttonsParent.style.display = 'flex';
                    }});
            }}
            
            function toggleLock(isLocked) {{
                inputs.forEach(input => input.readOnly = isLocked);
                lockIcon.classList.toggle('hidden', isLocked);
                unlockIcon.classList.toggle('hidden', !isLocked);
                if (isLocked) {{
                    localStorage.setItem(storagePrefix + 'prizeTotal', prizeTotalInput.value);
                    localStorage.setItem(storagePrefix + 'factionShare', factionShareInput.value);
                    localStorage.setItem(storagePrefix + 'guaranteedShare', guaranteedShareInput.value);
                    localStorage.setItem(storagePrefix + 'locked', 'true');
                }} else {{
                    localStorage.removeItem(storagePrefix + 'locked');
                }}
            }}
            
            function loadFromStorage() {{
                const isLocked = localStorage.getItem(storagePrefix + 'locked') === 'true';
                prizeTotalInput.value = formatNumber(localStorage.getItem(storagePrefix + 'prizeTotal') || prizeTotalInput.value);
                factionShareInput.value = localStorage.getItem(storagePrefix + 'factionShare') || factionShareInput.value;
                guaranteedShareInput.value = localStorage.getItem(storagePrefix + 'guaranteedShare') || guaranteedShareInput.value;
                toggleLock(isLocked);
                calculatePayouts();
            }}
            
            document.querySelectorAll('.status-toggle').forEach(button => {{ button.addEventListener('click', () => togglePlayerStatus(button)); }});
            
            prizeTotalInput.addEventListener('input', (e) => {{
                const formatted = formatNumber(e.target.value);
                e.target.value = formatted;
                calculatePayouts();
            }});
            factionShareInput.addEventListener('input', calculatePayouts);
            guaranteedShareInput.addEventListener('input', calculatePayouts);
            lockButton.addEventListener('click', () => toggleLock(!lockIcon.classList.contains('hidden')));
            screenshotButton.addEventListener('click', takeScreenshot);
            
            window.onload = loadFromStorage;
        </script>
    </body>
    </html>
    """
    
    # Generate base filename
    opponent_name_safe = processed_data['opponent_faction_name'].replace(' ', '_').replace('[', '').replace(']', '')
    base_filename = f"war_report_{war_id}_{opponent_name_safe}.html"
    
    # Get a unique filename
    unique_filename = get_unique_filename(base_filename)

    with open(unique_filename, "w", encoding="utf-8") as f:
        f.write(html)
    print(f" -> Successfully generated {unique_filename}")


# --- Main Execution ---
def main():
    """Main function to generate the war report."""
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
        print("Could not fetch war report. Check the War ID and API key.")
        sys.exit(1)

    user_data = get_api_data(f"https://api.torn.com/user/?selections=profile&key={API_KEY}")
    if not user_data or 'faction' not in user_data or user_data['faction']['faction_id'] == 0:
        print("Could not determine your faction ID from the API key provided.")
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
        print("\nPlease provide payout details (press Enter to use defaults):")
        prize_total = prompt_for_numeric_input("Prize Total", default="0")
        faction_share = prompt_for_numeric_input("Faction Share %", default=config['faction_share_default'])
        guaranteed_share = prompt_for_numeric_input("Guaranteed Share %", default=config['guaranteed_share_default'])
        
        generate_war_report_html(processed_data, war_id, prize_total, faction_share, guaranteed_share)

if __name__ == '__main__':
    main()