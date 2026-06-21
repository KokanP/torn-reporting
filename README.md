# **Torn War Reporting**

A Python script to generate detailed, interactive HTML reports for ranked wars in the online game Torn.com. It automatically fetches war data from the Torn API, calculates member participation based on respect earned, and determines prize money distribution.

The project has evolved through several iterations. The latest and recommended version is **`v4`**, which features highly strict data filtering, advanced metrics like "Fair Respect" and "True Base", and a powerful, interactive dashboard.

## **Features (v4)**

* **Strict Attack Filtering**: Guaranteed 100% accuracy. The script strictly checks timestamps and specific `ranked_war` modifiers directly from the Torn API. If an attack is not part of the official Ranked War score, it is not counted.
* **Advanced Respect Metrics**:
  * **Full Respect**: Total respect gained, including all chain modifiers and bonus hits.
  * **Fair Respect**: Respect gained keeping normal chain progression but flattening massive bonus multipliers (e.g. 10x, 25x bonuses).
  * **True Base (Fairness)**: Pure base respect without any multipliers. The most "communist" approach.
  * **Hits**: Distribution based purely on the number of attacks.
* **Interactive Dashboard**:
  * Dynamically adjust the total prize money, the faction's cut, and the guaranteed share.
  * Live-toggle between metrics (Full, Fair, Base, Hits) and watch the final payouts recalculate instantly in your browser.
  * Inactive members (0 hits and 0 assists) are automatically excluded from the guaranteed pool to prevent dilution.
  * Toggle specific members on or off to adjust payouts.
  * One-click "Export Image" (screenshot) button that automatically hides inactive participants for a clean, shareable image.
  * Detailed attack type breakdown (Hospitalizations, Mugs, Leaves, Assists).
* **Caching**: Caches API results to speed up subsequent runs and reduce API calls.

## **Installation**

### **1. Install Python**
Download and install Python from the [official website](https://www.python.org/downloads/). Ensure you check "Add Python to PATH" during installation.

### **2. Get the Project**
Download the project files from the [GitHub page](https://github.com/KokanP/torn-reporting) or clone the repository via Git.

### **3. Install Required Libraries**
Open a terminal in the `v4` directory and run:
```bash
pip install -r requirements.txt
```
*(Dependencies: `requests`, `jinja2`)*

## **Configuration**

Navigate to the `v4` folder and edit (or create) a file named `config.ini` with your Torn API key and payout presets.

```ini
[TornAPI]
ApiKey = YourActualApiKeyHere

[Defaults]
FactionShare = 30
GuaranteedShare = 10

# Example Payout Preset
[Preset_NoBonus_Respect_Only]
use_bonus_respect = false
use_fair_respect = true
assist_payment_type = none
```

## **Running the Script**

Navigate to the `v4` folder in your terminal and run the script:

### **Interactive Mode**
```bash
cd v4
python war_report.py
```
The script will prompt you for the War ID, Total Prize Pool, Faction Share, Guaranteed Share, and your chosen preset.

### **Command-Line Mode**
Provide the War ID as an argument:
```bash
python war_report.py <WAR_ID>
```
You can also supply optional arguments to skip prompts:
```bash
python war_report.py 38640 --prize-total 1.2b --preset Preset_NoBonus_Respect_Only
```

## **Viewing the Report**

Once execution is complete, a new HTML file will be generated in the `v4/reports/` folder. Open this file in your browser to view the interactive dashboard.

## **License**

This project is licensed under the MIT License. See the LICENSE file for full details.