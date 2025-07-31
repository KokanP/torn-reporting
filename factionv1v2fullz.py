import requests
import json
import time

def get_data_from_torn_api(api_key, endpoint, object_id='', selections='', api_version='v2'):
    """
    Generic function to fetch data from the Torn API, supporting both v1 and v2.

    Args:
        api_key (str): Your Torn API key.
        endpoint (str): The API endpoint to call (e.g., 'user', 'faction').
        object_id (str, optional): The ID of the user, faction, etc.
        selections (str, optional): A comma-separated string of selections to fetch.
        api_version (str, optional): The API version to use ('v1' or 'v2'). Defaults to 'v2'.

    Returns:
        dict: The JSON response from the API, or None if an error occurs.
    """
    # Correctly construct the base URL based on the API version
    if api_version == 'v2':
        base_url = f'https://api.torn.com/v2/{endpoint}/'
    else: # v1
        base_url = f'https://api.torn.com/{endpoint}/'

    # Construct the final URL
    url = f"{base_url}{object_id}?selections={selections}&key={api_key}"

    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes
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


def main():
    """
    Main function to fetch all available faction data from v1 and v2,
    and save it into a single consolidated JSON file.
    """
    api_key = 'epyKCv5VsDV5tJuv'

    # 1. Fetch user data to get the faction ID (using v2 as it's more current for this)
    print("Fetching user data to find faction ID...")
    user_data = get_data_from_torn_api(api_key, 'user', selections='profile', api_version='v2')

    if not user_data or 'faction' not in user_data or 'faction_id' not in user_data['faction']:
        print("Could not retrieve faction ID. Please ensure the API key is correct and has access.")
        return
    
    faction_id = user_data['faction']['faction_id']
    
    if faction_id == 0:
        print("This user is not currently in a faction.")
        return

    print(f"Faction ID found: {faction_id}")

    # 2. Define the refined list of faction selections to fetch
    selections_to_fetch = {
        # V2 Selections - 'members' is removed as it's included in 'basic'
        'v2': [
            'basic', 'attacks', 'attacksfull', 'chain', 'crimes',
            'reports', 'stats', 'temporary', 'territory', 'upgrades'
        ],
        # V1 Selections - 'armory' and 'events' removed due to errors
        'v1': [
            'basic', 'donations', 'currency', 'mainnews', 'chainreport'
        ]
    }

    # 3. Loop through selections, fetch data, and store it in a dictionary
    full_report = {}
    print(f"\nFetching all faction data for faction ID {faction_id}...")
    
    for version, selections in selections_to_fetch.items():
        for selection in selections:
            print(f"Fetching '{selection}' data from {version.upper()}...")
            # Small delay to avoid hitting API rate limits
            time.sleep(1) 
            
            data = get_data_from_torn_api(
                api_key, 
                'faction', 
                str(faction_id), 
                selection, 
                api_version=version
            )

            # Add the data to our consolidated report dictionary
            report_key = f"{version}_{selection}"
            if data:
                full_report[report_key] = data
                print(f" -> Success: Data for '{report_key}' captured.")
            else:
                full_report[report_key] = {"error": "Failed to fetch or no data returned."}
                print(f" -> Failed to fetch or no data returned for '{selection}'.")


    # 4. Save the consolidated report to a single file
    output_filename = "faction_full_report.json"
    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(full_report, f, indent=4)
        print(f"\nDiagnostic data fetching complete. All data saved to {output_filename}")
    except IOError as e:
        print(f"\nError writing to file {output_filename}: {e}")


if __name__ == '__main__':
    main()
