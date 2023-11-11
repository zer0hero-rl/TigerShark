# Standard library imports
import os                                              # Operating system interfaces
import json                                            # JSON encoder and decoder
import subprocess                                      # Process creation and management
from collections import Counter                        # Container for counting hashable objects

# Type hinting imports
from typing import Optional, Dict, List, Tuple, Union, Any

# Custom module imports
from dcerpc_method_abuse_notes import get_dcerpc_info  # DCERPC service opnums and method names helper
from make_colorful import Color                        # Terminal color output utility
from make_helpers import (
    input_prompt,                                      # Standardized user input prompt
    is_valid_interval,                                 # Interval validation
    is_valid_digit,                                    # Digit validation
    is_valid_ipv4_address,                             # IPv4 address validation
    set_tshark_path,                                   # Set the path to the tshark application
    get_input_opnum,                                   # Validate user input for opnum
    process_output,                                    # Takes input, processes it, cleans it, and returns it
)

# The make_helpers module contains custom utility functions that are used throughout the script.

# After locating the paths to tshark and capinfo, set_tshark_path() returns these paths, which is then interpreted as
# a tuple. The returned tuple is then unpacked into the variables tshark and capinfo by utilizing a feature called
# tuple unpacking
tshark, capinfo = set_tshark_path()


class TShark:
    """
    A class to interface with the TShark utility, allowing parsing and analysis of pcap files.

    Attributes
    ----------
    pcap_file : str
        The file path to the pcap file to be analyzed.
    proc : Optional[subprocess.Popen]
        A subprocess.Popen object for running the TShark commands. This is initialized as None and
        may be set later if needed.
    """

    def __init__(self, pcap_file: str) -> None:
        """
        Initializes the TShark class with the specified pcap file.

        Parameters
        ----------
            pcap_file : str
                the file path to the pcap file
        """
        self.pcap_file: str = pcap_file
        self.proc: Optional[subprocess.CompletedProcess] = None
        if not os.path.isfile(tshark):
            raise FileNotFoundError('Cannot find tshark in ' + tshark)

    def _run_tshark_command(self, options: List[str], display_filter: Optional[str] = None,
                            custom_fields: Optional[str] = None) -> str:
        """
        Executes a tshark command with the given options, display filter, and custom fields.

        Parameters
        ----------
        options : List[str]
            List of command-line options for tshark.
        display_filter : str, optional
            A string representing the display filter for tshark.
        custom_fields : str, optional
            A string representing custom fields to include in the tshark output.

        Returns
        -------
        str
            The decoded stdout from the executed command.
        """
        cmd = [tshark, '-r', self.pcap_file] + options
        if display_filter:
            cmd.extend(['-Y', display_filter])
        if custom_fields:
            fields_options = ['-e' + field.strip() for field in custom_fields.split(',')]
            cmd.extend(['-T', 'fields'] + fields_options)

        # Directly use subprocess.run here instead of calling _run_command
        completed_process: subprocess.CompletedProcess = subprocess.run(cmd, stdout=subprocess.PIPE, check=False)
        return completed_process.stdout.decode()

    def _run_command(self, cmd: List[str]) -> str:
        """
        Executes a command in a subprocess and returns its output.

        Parameters
        ----------
        cmd : List[str]
            The command to run, specified as a list of strings.

        Returns
        -------
        str
            The decoded stdout from the executed command.
        """
        completed_process: subprocess.CompletedProcess = subprocess.run(cmd, stdout=subprocess.PIPE, check=False)
        return completed_process.stdout.decode()

    def _process_protocol(self, display_filter: str, fields: List[str]) -> str:
        """
        Constructs and executes a tshark command to extract specific fields from packets
        that match a given display filter.

        Args:
            display_filter (str): A tshark display filter string used to filter packets
                                  based on matching criteria.
            fields (List[str]): A list of field names to extract data from each filtered packet.

        Returns:
            str: The stdout from tshark containing the extracted data from the specified fields.
        """
        # Construct the tshark command options for extracting fields
        options = ['-T', 'fields'] + ['-e' + field for field in fields]

        # Run the tshark command and capture the output
        output = self._run_tshark_command(options, display_filter=display_filter)
        return output

    def pcap_info(self) -> str:
        """
        Retrieves and returns information about the pcap file using capinfo.

        Returns
        -------
        str
            Information about the pcap file as a decoded string.
        """
        return self._run_command([capinfo, self.pcap_file])

    def iophs(self) -> str:
        """
        Returns I/O phase statistics of the pcap file by executing the appropriate tshark command.

        Returns
        -------
        str
            I/O phase statistics as a decoded string.
        """
        return self._run_tshark_command(['-qz', 'io,phs'])

    def whois_ip(self) -> None:
        """
        Executes a tshark command to retrieve IP addresses and prints whois information for each unique IP address.
        """
        # Use tshark to extract destination IP addresses from the pcap file
        check_tshark_output = self._run_tshark_command(['-T', 'fields', '-e', 'ip.dst'])

        # Split the tshark output into a list of IP addresses
        tshark_dest_ips = check_tshark_output.strip().splitlines()

        # Create a set of unique IP addresses, filtering out empty strings
        unique_ips = set(filter(None, tshark_dest_ips))

        # Perform a WHOIS lookup for each unique IP address and print the results
        for ip in unique_ips:
            # If this hangs, try running this command: `sudo vim /etc/resolv.conf`.  Comment out the current
            # nameserver line.  Add two lines: `nameserver 8.8.8.8`\n`nameserver 8.8.4.4`. Save and exit.
            whois_info = self._run_command(['whois', '-h', 'whois.cymru.com', ip])
            print(whois_info)

    def find_beacons(self, ip_address: Optional[str] = None, interval_frequency: Optional[str] = None) -> Any:
        """
        Analyzes the pcap for beacon-like traffic patterns based on the specified IP address and interval frequency.

        If `ip_address` or `interval_frequency` is not provided, the method will prompt the user for input.

        Parameters
        ----------
        ip_address : str, optional
            The IPv4 address to look for beacon patterns. If None, prompts the user.
        interval_frequency : str, optional
            The frequency interval (in seconds) to analyze for beacon patterns. If None, prompts the user.

        Returns
        -------
        Any
            The output from the TShark command, which includes statistics related to beacon-like traffic patterns.
        """
        if ip_address is None:
            ip_address = input_prompt(
                "Enter the IPv4 address you wish to look for patterns to determine beacons (Example valid input: "
                "10.10.14.19): ", is_valid_ipv4_address)
        if interval_frequency is None:
            interval_frequency = input_prompt(
                "Enter the interval frequency (Example: for 120 secs intervals, enter 120): ",
                is_valid_interval)
        return self._run_tshark_command(['-qz',
                                         f'io,stat,{interval_frequency},MAX(frame.time_relative)frame.time_relative,ip.addr=={ip_address},MIN(frame.time_relative)frame.time_relative'])

    def expert_chat(self) -> str:
        """
        Returns expert chat messages and analysis results from the pcap file.

        Returns
        -------
        str
            Expert chat messages as a decoded string.
        """
        return self._run_tshark_command(['-qz', 'expert,chat'])

    def display_filter(self) -> str:
        """
        Prompts the user for a display filter and additional options, then executes a tshark command and
        returns the filtered and formatted output.

        Returns
        -------
        str
            The formatted output after applying the display filter.
        """
        get_input = input("Enter a valid display filter: ")
        view_verbose = input("Expand the packet layers? (Y/N): ")
        view_all_pkts = input("View all packets? (Y/N): ")
        custom_fields = input("Specify custom fields? (Y/N): ")

        options = ['-Y', get_input]

        if view_verbose.lower() == "y":
            options.append('-V')
        if view_all_pkts.lower() == "n":
            how_many_pkts = input("How many packets do you want to see? ")
            options.extend(['-c', how_many_pkts])
        elif view_all_pkts.lower() == "y":
            # If there is a need to add additional options when viewing all packets
            pass

        # Call _run_tshark_command with or without custom fields
        if custom_fields.lower() == "y":
            custom_field_options = input("Enter one or more custom field options (comma-separated): ")
            output = self._run_tshark_command(options, custom_fields=custom_field_options)

            # Process the output if custom fields were specified
            non_blank_lines = [line for line in output.splitlines() if line.strip()]
            sorted_output = sorted(non_blank_lines, key=lambda x: x.split()[0])
            counts = Counter(sorted_output)
            sorted_by_count_output = '\n'.join(f'{count} {line}' for line, count in counts.most_common())
            return sorted_by_count_output
        else:
            output = self._run_tshark_command(options)
            return output

    def get_dcerpc_abuse_info(self) -> None:
        """
        Prompts the user for a service and operation number, then prints detailed information about potential
        DCERPC method abuse.
        """

        service_name_input = input("Enter the service (e.g., samr, drsuapi, netlogon, lsarpc, srvsvc): ")
        opnum_input = get_input_opnum()

        method, note, attack_ttp, attack_type = get_dcerpc_info(service_name_input, opnum_input)

        if method:
            print("")
            print(f"{Color.AQUA}Info for {service_name_input} opnum {opnum_input}:{Color.END}")
            print(f"{Color.UNDERLINE}Function{Color.END}: {method}")
            print("")
            print(f"{Color.UNDERLINE}Note{Color.END}: {note}")
            print("")
            print(f"{Color.UNDERLINE}ATT&CK TTP{Color.END}: {attack_ttp}")
            print("")
            print(f"{Color.UNDERLINE}Attack Type{Color.END}: {attack_type}")
            print("")

        else:
            print(note)

    def failed_connections(self) -> str:
        """
        Analyzes the pcap file for failed TCP connections by executing the appropriate tshark command.

        Returns
        -------
        str
            Formatted string with information about failed TCP connections.
        """
        return self._run_tshark_command(['-Y', 'tcp.analysis.retransmission and tcp.flags eq 0x0002'])

    def arp_thunt(self) -> Tuple[str, str]:
        """
        Returns information about ARP threats such as duplicate address detection and packet storms.

        Returns
        -------
        Tuple[str, str]
            A tuple containing information about ARP duplicate address detection and packet storms.
        """
        return self._run_tshark_command(['-Y', 'arp.duplicate-address-detected', '-T', 'fields', '-e',
                                         'arp.duplicate-address-detected']), \
            self._run_tshark_command(['-Y', 'arp.packet-storm-detected', '-T', 'fields', '-e',
                                      'arp.packet-storm-detected'])

    def dns_hunt(self) -> str:
        """
        Prompts the user for a domain to search for, then returns DNS queries that match the given domain name.

        Returns
        -------
        str
            Formatted string with DNS queries matching the domain.
        """
        ask_dns = input("Enter the domain you want to search for here in double quotes: ")
        return self._run_tshark_command(['-Y', 'dns matches ' + f"{ask_dns}"])

    def user_agent(self) -> str:
        """
        Returns a list of user agent strings found in the pcap file, along with their occurrence counts.

        Returns
        -------
        str
            JSON formatted string containing user agent strings and their counts.
        """

        # Extract User Agent strings using tshark
        cmd = ['-T', 'fields', '-e', 'http.user_agent']
        output = self._run_tshark_command(cmd)

        # Clean, split, and filter out blank User Agent strings
        user_agents = [ua for ua in output.strip().split('\n') if ua.strip()]
        user_agent_counts = Counter(user_agents).most_common()
        print("User Agent (by count):")
        return json.dumps(user_agent_counts, indent=2)

    def viewframe_getstream(self) -> str:
        """
        Prompts the user for a frame number and returns the TCP stream index associated with that frame.

        Returns
        -------
        str
            TCP stream index associated with the provided frame number.
        """
        ask_frame = input("Enter the frame number you'd like to get the tcp stream index for: ")
        return self._run_tshark_command(['-Y', f"frame.number == {ask_frame}", '-T', 'fields', '-e', 'tcp.stream'])

    def web_basic(self) -> str:
        """
        Returns basic web traffic information from the pcap file, focusing on HTTP and TLS handshakes.

        Returns
        -------
        str
            Formatted string with basic web traffic information.
        """
        print('')
        print(f"{Color.GREEN}Web Traffic:{Color.END}")
        print('')
        return self._run_tshark_command(['-Y', '(http.request or http.response or tls.handshake.type eq 1) and !(ssdp)'])

    def tcp_stream(self) -> str:
        """
        Prompts the user for a TCP stream index and returns the ASCII representation of that TCP stream.

        Returns
        -------
        str
            ASCII representation of the selected TCP stream.
        """
        get_tcp_stream_number = input_prompt("Which TCP stream index would you like to see? ", is_valid_digit)
        return self._run_tshark_command(['-qz', f'follow,tcp,ascii,{get_tcp_stream_number}'])

    def http_stream(self) -> str:
        """
        Prompts the user for an HTTP stream index and returns the ASCII representation of that HTTP stream.

        Returns
        -------
        str
            ASCII representation of the selected HTTP stream.
        """
        get_http_stream_number = input_prompt("Which HTTP stream index would you like to see? ", is_valid_digit)
        return self._run_tshark_command(['-qz', f'follow,http,ascii,{get_http_stream_number}'])

    def enum_streams(self) -> str:
        """
        Prompts the user for a protocol filter, then enumerates and returns streams that match the filter.

        Returns
        -------
        str
            Formatted string with enumerated streams matching the protocol filter.
        """
        ask = input("Which protocol would you like to search for? Examples: "
                    "x509sat.printableString, http.request.full_uri, dns.qry.name: ")
        print(' ')
        return self._run_tshark_command(
            ['-Y', f"{ask}", '-T', 'fields', '-e', 'frame.number', '-e', 'tcp.stream',
             '-e', 'ip.src', '-e', 'ip.dst', '-e', 'tcp.dstport', '-e', f"{ask}", '-E', 'header=yes'])

    def show_packets(self) -> str:
        """
        Depending on user input, displays all packets or all packets for a selected protocol from the pcap file.

        Returns
        -------
        str
            Formatted string with all packets or all packets for a specified protocol.
        """
        get_proto = input("Show all packets? (yes or no) ")
        print('')
        # If the user doesn't want to show all packets
        if get_proto == "no":
            which_proto = input("Which protocol would you like to see all packets for? ")
            print('')
            # Extract packets for the specified protocol
            return 'All ' + which_proto + ' packets:\n\n' + self._run_tshark_command(['-Y', which_proto])

        # If the user wants to show all packets
        elif get_proto == "yes":
            return 'All packets:' + self._run_tshark_command([])

    def statistics(self) -> Optional[str]:
        """
        Prompts the user to choose a type of statistics to view from a pcap file.
        Depending on the choice, it calls a corresponding nested function to handle
        the specific statistics functionality.

        Returns:
            Optional[str]: A string indicating an unsupported protocol if a user's choice
            does not match any of the provided options. Otherwise, it prints the statistics
            and returns None.
        """
        which_stats = input(
            f"{Color.LIGHTYELLOW}What type of statistics do you want to view? (conv/hosts/srt/tree): {Color.END}: ")

        def conversations() -> None:
            """
            Asks the user for a specific protocol and prints the conversation statistics
            for that protocol using TShark. It accesses a predefined dictionary of commands
            to generate the appropriate statistics.
            """
            ask_protocol = input(
                f"{Color.CYAN}Which protocol would you like to view conversations for? "
                f"(bluetooth/eth/ip/tcp/usb/wlan){Color.END}: ")
            # Define a dictionary mapping protocol names to TShark commands
            protocol_commands: Dict[str, List[str]] = {
                'bluetooth': ['conv,bluetooth'],
                'eth': ['conv,eth'],
                'ip': ['conv,ip'],
                'tcp': ['conv,tcp'],
                'usb': ['conv,usb'],
                'wlan': ['conv,wlan']
            }
            if ask_protocol in protocol_commands:
                tshark_command = ['-qz'] + protocol_commands[ask_protocol]
                print(self._run_tshark_command(tshark_command))
            else:
                print("Unsupported protocol")

        def server_resp_times() -> None:
            """
            Asks the user for a specific protocol and prints the server response time
            statistics for that protocol using TShark. It accesses a predefined dictionary
            of commands to generate the appropriate statistics.
            """
            ask_protocol = input(
                f"{Color.GOLD}Which protocol would you like to see server response times for? "
                f"(icmp/ldap/smb/smb2/srvsvc/drsuapi/lsarpc/netlogon/samr){Color.END}: ")
            protocol_commands: Dict[str, List[str]] = {
                'icmp': ['icmp,srt'],
                'ldap': ['ldap,srt'],
                'smb': ['smb,srt'],
                'smb2': ['smb2,srt'],
                'drsuapi': ['dcerpc,srt,e3514235-4b06-11d1-ab04-00c04fc2dcd2,4.0'],
                'lsarpc': ['dcerpc,srt,12345778-1234-abcd-ef00-0123456789ab,0.0'],
                'netlogon': ['dcerpc,srt,12345678-1234-abcd-ef00-01234567cffb,1.0'],
                'samr': ['dcerpc,srt,12345778-1234-ABCD-EF00-0123456789AC,1.0'],
                'srvsvc': ['dcerpc,srt,4b324fc8-1670-01d3-1278-5a47bf6ee188,3.0']
            }
            if ask_protocol in protocol_commands:
                tshark_command = ['-qz'] + protocol_commands[ask_protocol]
                print(self._run_tshark_command(tshark_command))
            else:
                print("Unsupported protocol")

        def tree() -> None:
            """
            Asks the user for a specific protocol and prints the protocol tree statistics
            for that protocol using TShark. It accesses a predefined dictionary of commands
            to generate the appropriate statistics.
            """
            ask_protocol = input(
                f"{Color.LIGHTGREEN}Which protocol would you like to see tree statistics for? "
                f"(dns/ip_hosts/http/http_req/http_srv/plen/ptype){Color.END}: ")
            protocol_commands: Dict[str, List[str]] = {
                'dns': ['dns,tree'],
                'http_req': ['http_req,tree'],
                'http_srv': ['http_srv,tree'],
                'http': ['http,tree'],
                'ip_hosts': ['ip_hosts,tree'],
                'ip_srcdst': ['ip_srcdst,tree'],
                'plen': ['plen,tree'],
                'ptype': ['ptype,tree']
            }
            if ask_protocol in protocol_commands:
                tshark_command = ['-qz'] + protocol_commands[ask_protocol]
                print(self._run_tshark_command(tshark_command))
            else:
                print("Unsupported protocol")

        def hosts() -> None:
            """
            Prints the host statistics from the PCAP file using TShark.
            """
            tshark_command = ['-qz', 'hosts,ip']
            print(self._run_tshark_command(tshark_command))

        # Mapping of statistics types to the corresponding function calls
        stats_functions: Dict[str, Any] = {
            'conv': conversations,
            'srt': server_resp_times,
            'tree': tree,
            'hosts': hosts
        }

        # Call the selected function or print an error if the choice is invalid
        return stats_functions.get(which_stats, lambda: "Unsupported protocol")()

    def read_verbose(self) -> Union[List[Tuple[str, int]], Any]:
        """
        Prompts the user to choose a protocol and processes the pcap file to extract and
        count occurrences of fields related to that protocol. The counts are returned as a sorted list of tuples,
        where each tuple contains a field value and its occurrence count.

        If the protocol requires processing multiple fields, each field is processed separately and
        the results are combined into a single output.

        Returns:
            Union[List[Tuple[str, int]], Any]: Depending on the protocol, this method returns either
            a list of tuples with the field values and their counts, or a JSON string representation
            of such lists for protocols that require double processing.
        """
        # Prompt the user to select a protocol to search within the pcap file.
        ask_protocol = input(f"{Color.CYAN}Choose a protocol to search{Color.END}: ")

        # Dictionary mapping protocol names to their corresponding field names and display filters.
        # This is used to construct the appropriate tshark command for each protocol.
        protocol_args = {
            'eth': (['eth.addr.oui_resolved'], 'eth'),          # Ethernet protocol, filter on OUI resolved addresses
            'samr': (['samr.samr_LookupNames.names'], 'samr'),  # SAMR protocol, filter on LookupNames
            'smb2': (['smb2.filename'], 'smb2.filename'),       # SMB2 protocol, filter on filenames
            'dns': (['dns.qry.name'], 'dns'),                   # DNS protocol, filter on query names
            'dhcp': (['dhcp.option.hostname'], 'dhcp'),         # DHCP protocol, filter on option hostnames
        }

        # Check if the selected protocol is one of the common ones with predefined args.
        # Common tshark command processing
        if ask_protocol in protocol_args:
            # Extract the fields and display filter for the chosen protocol.
            fields, display_filter = protocol_args[ask_protocol]
            # Run the tshark command with the fields and display filter, process the output,
            # and return the results as a JSON string.
            output = self._process_protocol(display_filter, fields)
            return process_output(output)

        # 'http' Protocol
        elif ask_protocol == 'http':
            return self._run_tshark_command(['-Y', 'http.request || http.response', '-Tfields', '-e', 'frame.number',
                                             '-e', 'frame.time', '-e', 'ip.src', '-e', 'http.request.full_uri', '-e',
                                             'http.response_for.uri', '-E', 'header=y'])

        # 'smb' Protocol
        elif ask_protocol == 'smb':
            # NTLMSSP Auth Hostname
            out_smb_ntlmssp = self._run_tshark_command(['-T', 'fields', '-e', 'ntlmssp.auth.hostname'])
            hostnames = [hostname for hostname in out_smb_ntlmssp.strip().split('\n') if hostname]
            count_hostnames = Counter(sorted(hostnames)).most_common()

            # NTLMSSP Auth Username
            out_smb_ntlmssp_uname = self._run_tshark_command(['-T', 'fields', '-e', 'ntlmssp.auth.username'])
            usernames = [username for username in out_smb_ntlmssp_uname.strip().split('\n') if username]
            count_usernames = Counter(sorted(usernames)).most_common()

            return (
                f"{Color.YELLOW}NTLMSSP Auth Hostname (by count): {Color.END}\n{count_hostnames}\n\n"
                f"{Color.RED}NTLMSSP Auth Username (by count): {Color.END}\n{count_usernames}\n\n"
            )

        # 'data-text-lines' Protocol
        elif ask_protocol == 'data-text-lines':
            return self._run_tshark_command(['-Y', 'data-text-lines', '-V', '-O', 'data-text-lines'])

        # 'mime_multipart' Protocol
        elif ask_protocol == 'mime_multipart':
            return self._run_tshark_command(['-Y', 'mime_multipart', '-V', '-O', 'mime_multipart'])

        # 'kerberos' Protocol
        elif ask_protocol == 'kerberos':
            # Analyzes Kerberos protocol traffic within the PCAP file to extract user and hostnames
            # from Kerberos tickets. It distinguishes between regular usernames and machine accounts
            # (which contain a '$'), counts the occurrences, and returns a formatted string containing
            # the results.

            tshark_args = ['-Tfields', '-e', 'kerberos.CNameString']

            cname_string = self._run_tshark_command(
                tshark_args + ['-Y', 'kerberos.CNameString and !(kerberos.CNameString contains "$")']
            )
            cname_string_with_dollar = self._run_tshark_command(
                tshark_args + ['-Y', 'kerberos.CNameString and (kerberos.CNameString contains "$")']
            )

            kerb_users = [name for name in set(cname_string.strip().split('\n')) if name]
            kerb_hosts = [name for name in set(cname_string_with_dollar.strip().split('\n')) if name]

            return (f'Windows Account Username\n{Counter(kerb_users).most_common()}\n\nHostname\n'
                    f'{Counter(kerb_hosts).most_common()}\n')

        # 'ldap' Protocol
        elif ask_protocol == "ldap":
            return self._run_tshark_command(['-Y', 'ldap.AttributeDescription == "givenName"'])

        # 'epm' Protocol
        elif ask_protocol == "epm":
            return self._run_tshark_command(['-Y', 'epm', '-V', '-O', 'epm'])

        # 'tls' Protocol
        elif ask_protocol == "tls":
            # Get TLS extension server name
            tls_server_names = self._run_tshark_command(['-Y', 'tls', '-T', 'fields', '-e',
                                                         'tls.handshake.extensions_server_name']).strip().split('\n')
            # List comprehension to remove blank lines
            tls_server_names = [name for name in tls_server_names if name]

            # Get counts for server names
            counts = Counter(tls_server_names).most_common(20)

            return f"{Color.BOLD}TLS Handshake Extensions Server Name (Top 10):{Color.END}" + json.dumps(counts)

        # 'icmp' Protocol
        elif ask_protocol == "icmp":
            # Common tshark arguments shared by all commands
            tshark_args = ['-t', 'ad']

            # Capture ICMP Echo Requests data
            icmp_req = self._run_tshark_command([*tshark_args, '-Y', '(icmp.type == 8) && (icmp.code == 0)'])

            # Capture ICMP Echo Replies data
            icmp_resp = self._run_tshark_command([*tshark_args, '-Y', '(icmp[0] == 0) && (icmp[1] == 0)'])

            # Return formatted ICMP data
            return (f"{Color.LIGHTBLUE}ECHO Requests (frame #, time, src ip, dst ip, info):{Color.END}\n{icmp_req}\n"
                    f"{Color.LIGHTGREEN}ECHO replies (frame #, time, src ip, dst ip, info):{Color.END}\n{icmp_resp}")

        else:
            raise ValueError(f"Unknown protocol: {ask_protocol}")


# The following block will only be executed if this module is run as the main script.
if __name__ == '__main__':
    # This code will not run when the module is imported.
    pass
