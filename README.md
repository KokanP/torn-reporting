# **Torn War Reporting**

A Python script to generate detailed, interactive HTML reports for ranked wars in the online game Torn.com. It automatically fetches war data from the Torn API, calculates member participation based on respect earned, and determines prize money distribution.

The final output is a single, self-contained HTML file that can be shared and used to manage payouts easily.

## **Features**

* **Direct API Integration**: Fetches war details and attack logs directly from the Torn API.  
* **Automated Calculations**: Calculates each member's respect contribution during the war.  
* **Interactive HTML Reports**: Generates a sophisticated, single-file HTML report.  
  * Dynamically adjust the total prize money, the faction's cut, and the guaranteed share for participants.  
  * Toggle members on or off to instantly recalculate payouts for the remaining participants.  
  * Includes direct links that pre-fill the "give money" page in Torn for each member.  
  * Easily copy a member's name and ID to your clipboard.  
  * Take a screenshot of the report for easy sharing.  
  * Lock the configuration to prevent accidental changes.  
* **Caching**: Caches API results to speed up subsequent runs and reduce API calls.  
* **Flexible Execution**: Can be run in an interactive mode that prompts for inputs or directly with command-line arguments.

## **Installation**

To get the script up and running, follow these steps.

### **1\. Install Python**

If you don't have Python installed, you'll need to download it first.

* Go to the [official Python website](https://www.python.org/downloads/).  
* Download the latest version for your operating system (Windows, macOS, etc.).  
* Run the installer. **Important**: On the first screen of the installer, make sure to check the box that says **"Add Python to PATH"** or "Add python.exe to PATH".

### **2\. Get the Project Files**

You can either download the entire project or just the essential files.

#### **Option A: Download Everything (Recommended)**

Download the project files to your computer by clicking the "Code" button and then "Download ZIP" on the [project's GitHub page](https://github.com/KokanP/torn-reporting), or by using Git if you have it installed.

#### **Option B: Download Individual Files**

If you prefer to only get the necessary files, download the two files below. **Right-click** on each link and choose **"Save Link As..."**. Make sure you save them both into the **same folder**.

* **Download war\_report.py**  
* [**Download report\_template.html**](https://www.google.com/search?q=https://raw.githubusercontent.com/KokanP/torn-reporting/main/report_template.html)

### **3\. Install Required Libraries**

The script depends on a couple of Python libraries. You can install them easily using the requirements.txt file included in the project.

* Open a terminal or command prompt.  
  * **On Windows**, you can type cmd in your Start Menu.  
  * **On macOS**, you can open the "Terminal" app.  
* Navigate to the folder where you saved the project files. You can use the cd command (e.g., cd C:\\Users\\YourUser\\Downloads\\torn-reporting).  
* Once you are in the correct folder, run the following command:

pip install requests jinja2

This will automatically download and install the required libraries.

## **How to Use**

### **1\. Configuration**

Before you can run the script, you must set up your configuration file.

1. In the folder where you saved the script, create a new file named config.ini.  
2. Open this file with a text editor (like Notepad or VS Code) and add your Torn API key.  
3. Optionally, you can also set the default percentages for the FactionShare and GuaranteedShare.

Your config.ini should look like this:

\[TornAPI\]  
ApiKey \= YourActualApiKeyHere

\[Defaults\]  
FactionShare \= 30  
GuaranteedShare \= 10

### **2\. Running the Script**

You can run the script in two ways from your terminal or command prompt.

#### **Interactive Mode**

This is the easiest way to start. It will ask you for all the necessary information.

1. Make sure you are in the project directory in your terminal.  
2. Run the following command:  
   python war\_report.py

3. The script will then prompt you to enter the War ID, the total prize money, and the payout shares.

#### **Command-Line Mode**

If you already know the war details, you can provide them as arguments to run the script faster.

* To generate a basic report:  
  (This will use the default share percentages from your config.ini file.)  
  python war\_report.py 28997

* **To specify all payout details:**  
  python war\_report.py 28997 \--prize-total 1000000000 \--faction-share 25 \--guaranteed-share 5

* **To force the script to re-download attack data (ignoring the cache):**  
  python war\_report.py 28997 \--no-cache

### **3\. Viewing the Report**

After the script finishes, it will create an HTML file in a new **reports** directory. Just open this file in any web browser to view your interactive war report.

## **License**

This project is licensed under the MIT License. See the LICENSE file for full details.