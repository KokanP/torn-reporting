import requests
import json # Added for writing JSON files

def get_data_from_torn_api(api_key, endpoint, object_id='', selections=''):
    """
    Generic function to fetch data from the Torn API.

    Args:
        api_key (str): Your Torn API key.
        endpoint (str): The API endpoint to call (e.g., 'user', 'faction').
        object_id (str, optional): The ID of the user, faction, etc.
        selections (str, optional): A comma-separated string of selections to fetch.

    Returns:
        dict: The JSON response from the API, or None if an error occurs.
    """
    # Corrected base URL to use the v2 API endpoint
    base_url = f'https://api.torn.com/{endpoint}/'
    if endpoint in ['user', 'faction']: # v2 endpoints
        base_url = f'https://api.torn.com/v2/{endpoint}/'
        
    url = f"{base_url}{object_id}?selections={selections}&key={api_key}"

    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes
        data = response.json()
        if 'error' in data:
            print(f"API Error for selection '{selections}': {data['error']['error']}")
            return None
        return data
    except requests.exceptions.RequestException as e:
        print(f"An HTTP error occurred for selection '{selections}': {e}")
        return None
    except ValueError:
        print(f"Error decoding JSON from response for selection '{selections}'.")
        return None


def main():
    """
    Main function to fetch all available faction data selections and save each to a JSON file.
    """
    # Your provided API key
    api_key = 'epyKCv5VsDV5tJuv'

    # 1. Fetch user data to get the faction ID
    print("Fetching user data to find faction ID...")
    user_data = get_data_from_torn_api(api_key, 'user', selections='profile')

    if not user_data or 'faction' not in user_data or 'faction_id' not in user_data['faction']:
        print("Could not retrieve faction ID. Please ensure the API key is correct and has access.")
        return
    
    faction_id = user_data['faction']['faction_id']
    
    if faction_id == 0:
        print("This user is not currently in a faction.")
        return

    print(f"Faction ID found: {faction_id}")

    # 2. Define all faction selections to fetch and save
    # This list includes all known selections for the faction endpoint.
    selections_to_fetch = [
        'basic', 'members', 'donations', 'armory', 'attacks',
        'attacksfull', 'chain', 'chainreport', 'crimes', 'currency',
        'mainnews', 'mainnewsfull', 'reports', 'stats', 'temporary',
        'territory', 'upgrades'
    ]

    # 3. Loop through selections, fetch data, and save each to a file
    print(f"\nFetching all faction data for faction ID {faction_id} and saving to JSON files...")
    for selection in selections_to_fetch:
        print(f"Fetching '{selection}' data...")
        data = get_data_from_torn_api(api_key, 'faction', str(faction_id), selection)

        if data:
            # Create a filename based on the selection
            filename = f"faction_{selection}.json"
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4)
                print(f" -> Successfully saved to {filename}")
            except IOError as e:
                print(f" -> Error writing to file {filename}: {e}")
        else:
            print(f" -> Failed to fetch or no data returned for '{selection}'.")

    print("\nDiagnostic data fetching complete. Check the generated .json files.")


if __name__ == '__main__':
    main()
