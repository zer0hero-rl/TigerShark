# TigerShark - A Python Wrapper for TShark
TigerShark is a Python script that provides a user-friendly interface for interacting with TShark, a network protocol analyzer. It allows you to perform various network analysis tasks, view statistics, and extract information from packet capture (PCAP) files. TigerShark simplifies the use of TShark's command-line capabilities and provides an easy-to-use menu-driven interface.

## Usage
1. Run `tiger_shark.py` and provide the path to a PCAP file when prompted.
2. Choose from a variety of options in the interactive menu to perform specific tasks or analyses on the PCAP file.

## Requirements
- Python 3.9+
    - see `requirements.txt`
- Mac or Linux.  Support for Windows is coming soon.
- WireShark (Required tshark location on Mac: /Applications/Wireshark.app/Contents/MacOS/tshark)

## Installation

1. Clone the TigerShark repository to your local machine:
   ```
   git clone https://github.com/z0her0/TigerShark.git
   ```

2. Navigate to the TigerShark root directory:
   ```
   cd TigerShark
   ```

3. Create a virtual environment:
   ```
   python3 -m venv venv_tigershark
   ```

4. Activate the virtual environment:
   ```
   source venv_tigershark/bin/activate
   ```

5. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

6. Run the main program `tiger_shark.py`:
   ```
   python3 src/tiger_shark.py
   ```

7. When prompted, provide path to PCAP file (point this to where your PCAP file exists):
   ```
   ../pcaps/name_of_pcap.pcap
   ```

8. Press ENTER to display the main menu.
