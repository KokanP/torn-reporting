import requests
import json
import time
from datetime import datetime
import argparse
import sys
import os
import configparser

# --- Configuration ---
def get_api_key():
    """Reads the API key from config.ini."""
    config = configparser.ConfigParser()
    if not os.path.exists('config.ini'):
        print(" -> Error: config.ini file not found.")
        print(" -> Please create it with your API key under the [TornAPI] section.")
        return None
        
    config.read('config.ini')
    
    if 'TornAPI' in config and 'ApiKey' in config['TornAPI']:
        key = config['TornAPI']['ApiKey']
        if key and key != 'YourActualApiKeyHere':
            return key
    
    print(" -> Error: API key not found or not set in config.ini.")
    print(" -> Please ensure your key is under [TornAPI] with the name ApiKey.")
    return None

API_KEY = get_api_key()
if not API_KEY:
    sys.exit(1)


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

def get_war_details(war_id):
    """Fetches the details of a specific ranked war."""
    print(f"Fetching details for War ID: {war_id}...")
    url = f"https://api.torn.com/torn/{war_id}?selections=rankedwarreport&key={API_KEY}"
    return get_api_data(url)

def get_all_attacks(faction_id, start_timestamp, end_timestamp):
    """Fetches all faction attacks within a given timeframe by paginating through the v1 API."""
    start_str = datetime.fromtimestamp(start_timestamp).strftime('%Y-%m-%d %H:%M:%S')
    end_str = datetime.fromtimestamp(end_timestamp).strftime('%Y-%m-%d %H:%M:%S')
    print(f"Fetching all attack logs from {start_str} to {end_str}...")
    all_attacks = []
    current_from = start_timestamp

    while current_from < end_timestamp:
        url = f"https://api.torn.com/faction/{faction_id}?selections=attacks&from={current_from}&to={end_timestamp}&key={API_KEY}"
        data = get_api_data(url)
        if data and 'attacks' in data:
            attacks_chunk = list(data['attacks'].values())
            if not attacks_chunk:
                break
            all_attacks.extend(attacks_chunk)

            last_timestamp = attacks_chunk[-1]['timestamp_ended']
            if last_timestamp > current_from:
                 # **CHANGE 1: Corrected pagination logic**
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

# --- Data Processing and Utility Functions ---

def save_attacks_to_json(attacks_data, filename):
    """Saves a list of attack data to a formatted JSON file."""
    print(f"Saving {len(attacks_data)} counted attacks to {filename} for debugging...")
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(attacks_data, f, indent=2)
        print(f" -> Successfully saved {filename}")
    except IOError as e:
        print(f" -> Error saving JSON file: {e}")


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

    counted_attacks_for_debug = []

    for attack in all_attacks:
        if 'attacker_id' not in attack or 'defender_id' not in attack:
            continue

        is_our_attack = (attack.get('attacker_faction') == our_faction_id and
                         attack.get('defender_faction') == opponent_faction_id)

        is_ranked_war_attack = attack.get('ranked_war') == 1

        # **CHANGE 2: Simplified filter, relying on the 'ranked_war' flag**
        if is_our_attack and is_ranked_war_attack:
            counted_attacks_for_debug.append(attack)

            attacker_id = str(attack['attacker_id'])
            respect_gain = attack.get('respect_gain', 0)

            if attacker_id in member_stats:
                member_stats[attacker_id]['respect_gained'] += respect_gain
            else:
                member_stats[attacker_id] = {'respect_gained': respect_gain, 'name': attack.get('attacker_name', 'Unknown (Ex-member)')}

    save_attacks_to_json(counted_attacks_for_debug, "counted_war_attacks.json")

    active_members = {mid: stats for mid, stats in member_stats.items() if stats['respect_gained'] > 0}
    sorted_stats = sorted(active_members.items(), key=lambda item: item[1]['respect_gained'], reverse=True)

    return {
        'war_details': war_data,
        'member_stats': sorted_stats,
        'our_faction_name': factions.get(str(our_faction_id), {}).get('name', 'Your Faction'),
        'opponent_faction_name': factions.get(str(opponent_faction_id), {}).get('name', 'Opponent')
    }

# --- HTML Generation Functions ---

def generate_war_report_html(processed_data, war_id, prize_total):
    """Generates the final HTML report file."""
    if not processed_data or not processed_data['member_stats']:
        print("No participating members found with respect gained. HTML report will be empty.")
        our_faction_name = processed_data.get('our_faction_name', 'Your Faction')
        opponent_faction_name = processed_data.get('opponent_faction_name', 'Opponent')
        total_respect_gained = 0
        start_str = datetime.fromtimestamp(processed_data['war_details']['war']['start']).strftime('%Y-%m-%d %H:%M:%S') if processed_data.get('war_details') else 'N/A'
        end_str = datetime.fromtimestamp(processed_data['war_details']['war']['end']).strftime('%Y-%m-%d %H:%M:%S') if processed_data.get('war_details') else 'N/A'
        member_rows = '<tr><td colspan="7" class="p-3 text-center text-gray-400">No members gained respect in this war.</td></tr>'
    else:
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
                            <input type="number" id="factionShare" class="config-input w-20 rounded-md p-1 text-white" value="">
                            <span class="ml-1">%</span>
                        </div>
                    </div>
                    <div class="info-row">
                        <label for="guaranteedShare" class="info-label">Guaranteed Share:</label>
                        <div class="flex items-center">
                            <input type="number" id="guaranteedShare" class="config-input w-20 rounded-md p-1 text-white" value="">
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
                        <tbody id="member-table-body">
                            {member_rows}
                        </tbody>
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
            const prizeTotalInput = document.getElementById('prizeTotal');
            const factionShareInput = document.getElementById('factionShare');
            const guaranteedShareInput = document.getElementById('guaranteedShare');
            const memberRows = document.querySelectorAll('#member-table-body tr[data-respect]');
            const lockButton = document.getElementById('lockButton');
            const screenshotButton = document.getElementById('screenshotButton');
            const lockIcon = document.getElementById('lockIcon');
            const unlockIcon = document.getElementById('unlockIcon');
            const inputs = [prizeTotalInput, factionShareInput, guaranteedShareInput];

            function formatNumber(n) {{
                return n.replace(/\\D/g, "").replace(/\\B(?=(\\d{{3}})+(?!\\d))/g, ",");
            }}
            
            function calculatePayouts() {{
                let totalRespect = 0;
                let participantCount = 0;
                
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
                
                let totalGuaranteedPaid = 0;
                let totalParticipationPaid = 0;
                
                memberRows.forEach(row => {{
                    if (row.dataset.enabled === 'true') {{
                        const respect = parseFloat(row.dataset.respect);
                        const respectShare = totalRespect > 0 ? (respect / totalRespect) : 0;
                        const guaranteedPayout = participantCount > 0 ? (guaranteedPool / participantCount) : 0;
                        const participationPayout = participationPool * respectShare;
                        const totalMemberPrize = guaranteedPayout + participationPayout;
                        
                        row.querySelector('.guaranteed-share').textContent = `$` + Math.round(guaranteedPayout).toLocaleString();
                        row.querySelector('.participation-share').textContent = `$` + Math.round(participationPayout).toLocaleString();
                        
                        // Store the total prize amount in a data attribute
                        row.dataset.totalPrize = Math.round(totalMemberPrize);
                        
                        const prizeLink = row.querySelector('.total-prize a');
                        prizeLink.textContent = `$` + Math.round(totalMemberPrize).toLocaleString();
                        prizeLink.href = `https://www.torn.com/factions.php?step=your#/tab=controls&option=give-to-user&addMoneyTo=${{row.dataset.memberId}}&money=${{row.dataset.totalPrize}}`;
                        
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
                if (lastHighlightedRow) {{
                    lastHighlightedRow.classList.remove('highlight-row');
                }}
                row.classList.add('highlight-row');
                lastHighlightedRow = row;
            }}

            function copyMemberInfo(element, memberName, memberId) {{
                highlightRow(element.closest('tr'));
                const textToCopy = `${{memberName}} [${{memberId}}]`;
                navigator.clipboard.writeText(textToCopy).then(() => {{
                    console.log('Copied member info:', textToCopy);
                }}).catch(err => {{
                    console.error('Failed to copy member info: ', err);
                }});
            }}
            
            function takeScreenshot() {{
                const reportContainer = document.getElementById('report-container');
                const buttonsParent = document.querySelector('.mt-8.flex');
                
                // Temporarily hide buttons for the screenshot
                buttonsParent.style.display = 'none';
                
                html2canvas(reportContainer, {{
                    backgroundColor: '#111827',
                    windowWidth: reportContainer.scrollWidth,
                    windowHeight: reportContainer.scrollHeight
                }}).then(canvas => {{
                    const link = document.createElement('a');
                    link.download = 'war_report.png';
                    link.href = canvas.toDataURL('image/png');
                    link.click();
                    
                    // Show buttons again
                    buttonsParent.style.display = 'flex';
                }});
            }}
            
            function toggleLock(isLocked) {{
                inputs.forEach(input => input.readOnly = isLocked);
                lockIcon.classList.toggle('hidden', !isLocked);
                unlockIcon.classList.toggle('hidden', isLocked);
                if(isLocked) {{
                    localStorage.setItem('warReportPrizeTotal', prizeTotalInput.value);
                    localStorage.setItem('warReportFactionShare', factionShareInput.value);
                    localStorage.setItem('warReportGuaranteedShare', guaranteedShareInput.value);
                    localStorage.setItem('warReportLocked', 'true');
                }} else {{
                    localStorage.removeItem('warReportLocked');
                }}
            }}
            
            function loadFromStorage() {{
                const isLocked = localStorage.getItem('warReportLocked') === 'true';
                prizeTotalInput.value = formatNumber(localStorage.getItem('warReportPrizeTotal') || prizeTotalInput.value);
                factionShareInput.value = localStorage.getItem('warReportFactionShare') || '';
                guaranteedShareInput.value = localStorage.getItem('warReportGuaranteedShare') || '';
                toggleLock(isLocked);
                calculatePayouts();
            }}
            
            document.querySelectorAll('.status-toggle').forEach(button => {{
                button.addEventListener('click', () => togglePlayerStatus(button));
            }});
            
            prizeTotalInput.addEventListener('input', (e) => {{
                const formatted = formatNumber(e.target.value);
                e.target.value = formatted;
                calculatePayouts();
            }});
            factionShareInput.addEventListener('input', calculatePayouts);
            guaranteedShareInput.addEventListener('input', calculatePayouts);
            lockButton.addEventListener('click', () => toggleLock(lockIcon.classList.contains('hidden')));
            screenshotButton.addEventListener('click', takeScreenshot);
            
            window.onload = loadFromStorage;
        </script>
    </body>
    </html>
    """
    
    # Generate filename
    opponent_name_safe = processed_data['opponent_faction_name'].replace(' ', '_').replace('[', '').replace(']', '')
    filename = f"war_report_{war_id}_{opponent_name_safe}.html"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)
    print(f" -> Successfully generated {filename}")


# --- Main Execution ---

def main():
    """Main function to generate the war report."""
    parser = argparse.ArgumentParser(description="Generate a ranked war report for Torn.com.")
    parser.add_argument("-w", "--war-id", type=int, help="The ranked war ID.")
    parser.add_argument("-p", "--prize-total", type=int, help="The total prize money for the war.")
    
    args = parser.parse_args()

    war_id = str(args.war_id)
    prize_total = str(args.prize_total)

    # Fallback to interactive input if arguments are not provided
    if args.war_id is None:
        war_id = input("Please enter the Ranked War ID: ")
        if not war_id.isdigit():
            print("Invalid War ID. Please enter a number.")
            sys.exit(1)
            
    if args.prize_total is None:
        prize_total_input = input("Please enter the Prize Total: ")
        if not prize_total_input.isdigit():
            print("Invalid Prize Total. Please enter a number.")
            sys.exit(1)
        prize_total = prize_total_input

    war_report = get_war_details(war_id)
    if not war_report or 'rankedwarreport' not in war_report:
        print("Could not fetch war report. Check the War ID and API key.")
        sys.exit(1)

    user_data = get_api_data(f"https://api.torn.com/user/?selections=profile&key={API_KEY}")
    if not user_data or 'faction' not in user_data or user_data['faction']['faction_id'] == 0:
        print("Could not determine your faction ID. Ensure your API key is correct.")
        sys.exit(1)
        
    our_faction_id = user_data['faction']['faction_id']
    war_start_time = war_report['rankedwarreport']['war']['start']
    war_end_time = war_report['rankedwarreport']['war']['end']
    
    # **CHANGE 3: Increased fetch padding to 330 seconds (5.5 minutes)**
    fetch_start_time = war_start_time - 330
    fetch_end_time = war_end_time + 330
    
    all_attacks = get_all_attacks(our_faction_id, fetch_start_time, fetch_end_time)
    
    # Pass only necessary data, no longer need to pass timestamps for filtering
    processed_data = process_war_data(war_report, all_attacks, our_faction_id)

    if processed_data:
        generate_war_report_html(processed_data, war_id, prize_total)

if __name__ == '__main__':
    main()