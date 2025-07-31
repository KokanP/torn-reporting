import requests
import json
import time
from datetime import datetime

# --- API Fetching Functions ---

def get_data_from_torn_api(api_key, endpoint, object_id='', selections='', api_version='v2'):
    """
    Generic function to fetch data from the Torn API, supporting both v1 and v2.
    """
    if api_version == 'v2':
        base_url = f'https://api.torn.com/v2/{endpoint}/'
    else: # v1
        base_url = f'https://api.torn.com/{endpoint}/'

    url = f"{base_url}{object_id}?selections={selections}&key={api_key}"

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if 'error' in data:
            print(f" -> API Error for selection '{selections}' ({api_version.upper()}): {data['error']['error']}")
            return None
        return data
    except requests.exceptions.RequestException as e:
        print(f" -> An HTTP error occurred for selection '{selections}' ({api_version.upper()}): {e}")
        return None
    except ValueError:
        print(f" -> Error decoding JSON from response for selection '{selections}' ({api_version.upper()}).")
        return None

# --- HTML Generation Functions ---

def generate_html_report(data):
    """
    Generates a full HTML report from the consolidated faction data.
    """
    # Extract main data points for easier access
    v1_basic = data.get('v1_basic', {})
    v2_basic = data.get('v2_basic', {}).get('basic', {})
    v1_donations = data.get('v1_donations', {}).get('donations', {})
    v2_attacks = data.get('v2_attacks', {}).get('attacks', [])
    v2_crimes = data.get('v2_crimes', {}).get('crimes', [])
    v2_upgrades = data.get('v2_upgrades', {}).get('upgrades', {})
    
    faction_name = v2_basic.get('name', 'N/A')
    faction_tag = v2_basic.get('tag', 'N/A')
    
    # Assemble HTML content
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Faction Report: {faction_name}</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            body {{ font-family: 'Inter', sans-serif; }}
            .card {{ background-color: #1f2937; border: 1px solid #374151; border-radius: 0.5rem; padding: 1.5rem; margin-bottom: 1.5rem; }}
            .table-header {{ background-color: #374151; }}
            .table-row-dark {{ background-color: #1f2937; }}
            .table-row-light {{ background-color: #2b3544; }}
        </style>
    </head>
    <body class="bg-gray-900 text-gray-300 p-4 sm:p-8">
        <div class="max-w-7xl mx-auto">
            <header class="text-center mb-8">
                <h1 class="text-4xl font-bold text-white">Faction Report</h1>
                <h2 class="text-2xl text-cyan-400">{faction_name} [{faction_tag}]</h2>
                <p class="text-gray-400">Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </header>

            {generate_summary_section(v2_basic, v1_donations)}
            {generate_members_section(v1_basic.get('members', {}))}
            {generate_attacks_section(v2_attacks, faction_name)}
            {generate_crimes_section(v2_crimes, v1_basic.get('members', {}))}
            {generate_upgrades_section(v2_upgrades)}

        </div>
    </body>
    </html>
    """
    
    # Write to file
    try:
        with open("faction_report.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        print("\n -> Successfully generated HTML report: faction_report.html")
    except IOError as e:
        print(f"\n -> Error writing HTML file: {e}")

def generate_summary_section(v2_basic, v1_donations):
    rank_info = v2_basic.get('rank', {})
    total_money = sum(details.get('money_balance', 0) for _, details in v1_donations.items())
    total_points = sum(details.get('points_balance', 0) for _, details in v1_donations.items())

    return f"""
    <div class="card">
        <h3 class="text-xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">Faction Summary</h3>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
            <div><p class="text-gray-400">Respect</p><p class="text-2xl font-bold text-cyan-400">{v2_basic.get('respect', 0):,}</p></div>
            <div><p class="text-gray-400">Members</p><p class="text-2xl font-bold text-cyan-400">{v2_basic.get('members', 0)} / {v2_basic.get('capacity', 0)}</p></div>
            <div><p class="text-gray-400">Rank</p><p class="text-2xl font-bold text-cyan-400">{rank_info.get('name', 'N/A')} {rank_info.get('division', '')}</p></div>
            <div><p class="text-gray-400">Best Chain</p><p class="text-2xl font-bold text-cyan-400">{v2_basic.get('best_chain', 0):,}</p></div>
            <div><p class="text-gray-400">Total Money</p><p class="text-xl font-bold text-green-400">${total_money:,}</p></div>
            <div><p class="text-gray-400">Total Points</p><p class="text-xl font-bold text-yellow-400">{total_points:,}</p></div>
        </div>
    </div>
    """

def generate_members_section(members_data):
    rows_html = ""
    # Sort members by days in faction, descending. Handle potential missing data.
    sorted_members = sorted(members_data.items(), key=lambda item: item[1].get('days_in_faction', 0), reverse=True)

    for member_id, details in sorted_members:
        status_color = {
            "Okay": "text-green-400",
            "Abroad": "text-blue-400",
            "Traveling": "text-blue-400",
            "Hospital": "text-red-500",
            "Jail": "text-yellow-500"
        }.get(details.get('status', {}).get('state', 'Okay'), "text-gray-400")

        rows_html += f"""
        <tr class="table-row-light hover:bg-gray-700">
            <td class="p-3"><a href="https://www.torn.com/profiles.php?XID={member_id}" target="_blank" class="text-cyan-400 hover:underline">{details.get('name', 'N/A')} [{member_id}]</a></td>
            <td class="p-3 text-center">{details.get('level', 'N/A')}</td>
            <td class="p-3 text-center">{details.get('days_in_faction', 'N/A')}</td>
            <td class="p-3">{details.get('position', 'N/A')}</td>
            <td class="p-3 {status_color}">{details.get('status', {}).get('description', 'N/A')}</td>
            <td class="p-3 text-gray-400">{details.get('last_action', {}).get('relative', 'N/A')}</td>
        </tr>
        """
    return f"""
    <div class="card">
        <h3 class="text-xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">Member Roster</h3>
        <div class="overflow-x-auto">
            <table class="w-full text-left">
                <thead class="table-header">
                    <tr>
                        <th class="p-3">Name</th>
                        <th class="p-3 text-center">Level</th>
                        <th class="p-3 text-center">Days in Faction</th>
                        <th class="p-3">Position</th>
                        <th class="p-3">Status</th>
                        <th class="p-3">Last Action</th>
                    </tr>
                </thead>
                <tbody>{rows_html}</tbody>
            </table>
        </div>
    </div>
    """

def generate_attacks_section(attacks, faction_name):
    rows_html = ""
    for attack in attacks[:25]: # Limit to latest 25 attacks for brevity
        attacker_html = "N/A"
        if attack.get('attacker'):
            attacker_name = attack['attacker'].get('name', 'Unknown')
            attacker_id = attack['attacker']['id']
            attacker_faction = attack['attacker'].get('faction', {}).get('name') if attack['attacker'].get('faction') else ''
            attacker_color = "text-green-400" if attacker_faction == faction_name else "text-red-400"
            attacker_html = f'<a href="https://www.torn.com/profiles.php?XID={attacker_id}" target="_blank" class="{attacker_color} hover:underline">{attacker_name}</a>'

        defender_html = "N/A"
        if attack.get('defender'):
            defender_name = attack['defender'].get('name', 'Unknown')
            defender_id = attack['defender']['id']
            defender_faction = attack['defender'].get('faction', {}).get('name') if attack['defender'].get('faction') else ''
            defender_color = "text-green-400" if defender_faction == faction_name else "text-red-400"
            defender_html = f'<a href="https://www.torn.com/profiles.php?XID={defender_id}" target="_blank" class="{defender_color} hover:underline">{defender_name}</a>'
        
        result_color = "text-green-400" if attack.get('respect_gain', 0) > 0 else "text-red-400"
        
        rows_html += f"""
        <tr class="table-row-light hover:bg-gray-700">
            <td class="p-3">{datetime.fromtimestamp(attack['started']).strftime('%Y-%m-%d %H:%M')}</td>
            <td class="p-3">{attacker_html}</td>
            <td class="p-3">{defender_html}</td>
            <td class="p-3 {result_color}">{attack['result']}</td>
            <td class="p-3 text-green-400 text-center">+{attack.get('respect_gain', 0):.2f}</td>
        </tr>
        """
    return f"""
    <div class="card">
        <h3 class="text-xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">Recent Attacks</h3>
        <div class="overflow-x-auto">
            <table class="w-full text-left">
                <thead class="table-header">
                    <tr>
                        <th class="p-3">Date</th>
                        <th class="p-3">Attacker</th>
                        <th class="p-3">Defender</th>
                        <th class="p-3">Result</th>
                        <th class="p-3 text-center">Respect Gain</th>
                    </tr>
                </thead>
                <tbody>{rows_html}</tbody>
            </table>
        </div>
    </div>
    """

def generate_crimes_section(crimes, members_data):
    crimes_html = ""
    for crime in crimes:
        status_color = {"Successful": "text-green-400", "Failure": "text-red-500", "Planning": "text-yellow-400", "Recruiting": "text-blue-400"}.get(crime['status'], "text-gray-400")
        
        participants = []
        for slot in crime.get('slots', []):
            if slot.get('user'):
                user_id = str(slot['user']['id'])
                # Look up the member's name from the members data dictionary
                user_name = members_data.get(user_id, {}).get('name', f"ID: {user_id}")
                participants.append(user_name)
        
        participants_str = ", ".join(participants)
        
        crimes_html += f"""
        <div class="table-row-light p-4 rounded-md mb-2">
            <p class="font-bold"><span class="{status_color}">{crime['status']}</span>: {crime['name']}</p>
            <p class="text-sm text-gray-400">Participants: {participants_str if participants_str else 'None'}</p>
        </div>
        """
    return f"""
     <div class="card">
        <h3 class="text-xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">Organized Crimes</h3>
        <div>{crimes_html}</div>
    </div>
    """

def generate_upgrades_section(upgrades):
    core_html = "".join([f"<li class='ml-4'>{up['name']} {up['level']}</li>" for up in upgrades.get('core', {}).get('upgrades', [])])
    peace_html = ""
    for branch in upgrades.get('peace', []):
        peace_html += f"<li class='font-semibold mt-2'>{branch['name']}</li>"
        peace_html += "".join([f"<li class='ml-8'>{up['name']} {up['level']}</li>" for up in branch.get('upgrades', [])])
    war_html = ""
    for branch in upgrades.get('war', []):
        war_html += f"<li class='font-semibold mt-2'>{branch['name']}</li>"
        war_html += "".join([f"<li class='ml-8'>{up['name']} {up['level']}</li>" for up in branch.get('upgrades', [])])

    return f"""
    <div class="card">
        <h3 class="text-xl font-semibold text-white mb-4 border-b border-gray-700 pb-2">Upgrades</h3>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div><h4 class="font-bold text-lg text-cyan-400">Core</h4><ul class="list-disc list-inside text-gray-300">{core_html}</ul></div>
            <div><h4 class="font-bold text-lg text-cyan-400">Peace</h4><ul class="list-disc list-inside text-gray-300">{peace_html}</ul></div>
            <div><h4 class="font-bold text-lg text-cyan-400">War</h4><ul class="list-disc list-inside text-gray-300">{war_html}</ul></div>
        </div>
    </div>
    """

# --- Main Execution ---

def main():
    """
    Main function to fetch all available faction data from v1 and v2,
    save it to a JSON file, and then generate an HTML report.
    """
    api_key = 'epyKCv5VsDV5tJuv'
    json_filename = "faction_full_report.json"

    # 1. Fetch user data to get the faction ID
    print("Fetching user data to find faction ID...")
    user_data = get_data_from_torn_api(api_key, 'user', selections='profile', api_version='v2')

    if not user_data or 'faction' not in user_data or 'faction_id' not in user_data['faction']:
        print("Could not retrieve faction ID.")
        return
    
    faction_id = user_data['faction']['faction_id']
    if faction_id == 0:
        print("This user is not currently in a faction.")
        return
    print(f"Faction ID found: {faction_id}")

    # 2. Define the refined list of faction selections to fetch
    selections_to_fetch = {
        'v2': ['basic', 'attacks', 'attacksfull', 'chain', 'crimes', 'reports', 'stats', 'temporary', 'territory', 'upgrades'],
        'v1': ['basic', 'donations', 'currency', 'mainnews', 'chainreport']
    }

    # 3. Fetch all data and store it
    full_report = {}
    print(f"\nFetching all faction data for faction ID {faction_id}...")
    for version, selections in selections_to_fetch.items():
        for selection in selections:
            print(f"Fetching '{selection}' data from {version.upper()}...")
            time.sleep(1)
            data = get_data_from_torn_api(api_key, 'faction', str(faction_id), selection, api_version=version)
            report_key = f"{version}_{selection}"
            if data:
                full_report[report_key] = data
                print(f" -> Success: Data for '{report_key}' captured.")
            else:
                full_report[report_key] = {"error": "Failed to fetch or no data returned."}
                print(f" -> Failed to fetch or no data returned for '{selection}'.")

    # 4. Save the consolidated report to a single JSON file
    try:
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(full_report, f, indent=4)
        print(f"\nDiagnostic data fetching complete. All data saved to {json_filename}")
    except IOError as e:
        print(f"\nError writing to file {json_filename}: {e}")

    # 5. Generate the HTML report from the saved JSON file
    print("\nGenerating HTML report...")
    generate_html_report(full_report)

if __name__ == '__main__':
    main()
