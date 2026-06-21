# Project Overview

This project is a Python script that generates detailed, interactive HTML reports for "ranked wars" in the online game Torn.com. It fetches war data from the Torn API, calculates member participation based on respect earned, and determines prize money distribution.

The main script, `war_report.py` (specifically version `v4`), is written in Python and uses the `requests` library to fetch data from the Torn API and `jinja2` to render HTML reports.

The project now features:
*   An **advanced, modernized HTML report** (`v4`) with an interactive dashboard, live metric toggling, and bulletproof data filtering.
*   **Strict Attack Filtering**: The script ensures 100% accuracy by matching attacks against the war's time window and validating `ranked_war` modifiers. Off-target or non-war hits are completely ignored.
*   **Advanced Fairness Metrics**: Toggle between "Full Respect", "Fair Respect" (flattens large bonus hits), "True Base" (no chain multipliers), and "Hits" directly in the browser to instantly recalculate payouts.
*   An **interactive menu for selecting payout presets** directly from the terminal.

The final output is a single, self-contained HTML file that can be shared and used to manage payouts easily.

# Building and Running

## 1. Installation

First, install the required Python libraries using pip within the `v4` directory:

```bash
cd v4
pip install -r requirements.txt
```

## 2. Configuration

Create or modify a `config.ini` file in the `v4` directory with your Torn API key and define payout presets.

```ini
[TornAPI]
ApiKey = YourActualApiKeyHere

[Defaults]
FactionShare = 30
GuaranteedShare = 10

# Example Payout Preset
[Preset_Standard_With_Assists]
use_bonus_respect = true
assist_payment_type = flat
assist_payment_value = 1000000
penalty_per_hit_taken = 0
```

## 3. Running the Script

Navigate to the `v4` directory. You can run the script in two modes:

### Interactive Mode

The script will prompt you for the War ID, payout details, and includes an **interactive menu to select a payout preset**.

```bash
python war_report.py
```

### Command-Line Mode

You can provide the war details as command-line arguments. Use the `--preset` argument to specify a payout preset.

```bash
# Basic report with default shares
python war_report.py <WAR_ID>

# Report with Custom Payouts and a specific preset
python war_report.py <WAR_ID> --prize-total 1000000000 --faction-share 25 --guaranteed-share 5 --preset Preset_Standard_With_Assists

# Force a refresh of the cached data
python war_report.py <WAR_ID> --no-cache
```

## 4. Viewing the Report

After the script finishes, it will create HTML files in the `v4/reports` directory. Open these files in any web browser to view your interactive war reports.

# Development Conventions

*   **Code Style:** The Python code follows the PEP 8 style guide. It uses a strict filtering mechanism inside `process_war_data` to ensure accurate respect calculations.
*   **Dependencies:** The project uses a `requirements.txt` file to manage Python dependencies (`requests` and `jinja2`). The HTML templates use Tailwind CSS and `html2canvas.js` via CDNs.
*   **Configuration:** Configuration is handled via a `config.ini` file.
*   **Versioning:** The project is organized into versioned folders (`v2`, `v3`, `v4`, `big new version`). **`v4` is the current, most stable, and accurate iteration.**
*   **UI/UX:** The dashboard provides real-time calculations. Inactive members (0 hits/assists) are strictly excluded from the guaranteed pool. Screenshots dynamically hide inactive users for a cleaner export.
