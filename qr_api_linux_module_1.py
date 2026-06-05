import ctypes

# Windows-only import for admin elevation
try:
    import pyuac
except ImportError:
    pyuac = None  # Not available on macOS/Linux

####Insert your PySimpleGUI distribution key at the top
PySimpleGUI_License ="""elyIJgMoaqWzNll5bHnuNAlhVaHhlKwCZhSlIj6KI6kpRep6cU3SRPyNafW3JZ1PdsGclzv8bAiLIBsZI7kVxEp5Y42cVRuQc822VnJARuCeIO6RMaTUcWzKNbzlIdz8NojQchxsNoSdwtivTJGQlljeZvWq56z0ZhUGRalYceGsx8vYerWN1hlQbZn2RxWkZMXNJZzOa1WH9BuVIFjLoGipNuSi4XwpIgimwkirTYmaFitOZaUcZ4pdc8n1N602Iljyoai5ScmVFnntYWWZ50uZYeXWROosIXikwrirTEmOFBtHZNUNxHhlch3uQRi5O8iXJ9C8Z2WHhLlScjmdEei1LRCkJ8DYbm2R1mwfYpWq5g5iIXjuoNiIS4mFFdnDYDW65zukYSXxR5oZIEEOJqlEavGZVeyxYiS8IHs8I0kwN71qcY3lRPvIbPWIVByOSKUnQGiQOpihIhy8M6DIUK1bM8i3ImsYITkvRHhPdnG8VoJfc63LNu1KZVWsQ3iTOgiGIJybM1D7Iy1bLeTdAux4LgTREe5pIwipwoiXRiG6FM0QZWUoVg4EcNGHlFyGZUXMMLi0OniBIZyqMIDVIs1jLdTBAu1uLeTVEo0lIFiFwXiVRuW61EhXaLWBxFB7Z1GYRly0ZFXFNkzvI6jqoqiHaFmTFon7YMWT5buOYsXNRiozYlmZVgo2Z0X3J5hYMZzFMOzeMQ09BfnvbxWNFtpxbuCR52jZbv2X05ikL1CzJkJWUwEFF9kxZyHWJ4lTc03CMbiXOkicID0PNxSo4C5yMHCn4gymMMj7ITuAMhT0Q83WIQnX0d=J517c7d5fae65077acdc2471d2e926436011f50cc3bff5e606996187bbc87cb0a4796f69a65646f4f2401c26398c4df3c2e20ac1bdeb726222b3535af30177dbcda327d862b8ef3d121801906e44ce44ce74e02331e3f88e13586c3337e7d4b113f826187ea2a355b3075917c78aa05926b289cf8738a54267aa4915a7f14840a36d4d4abc646871adbb8d9bf078f67f1e8461fde9cf36a2a5def3e81ce135a48eeb90c5d39a04e85af461d99f296a8677f30403585d5bb3eb9bec197839c48f1e4365fa61bd8b798a73e11b4c5de4285f3bfcb92434865cc97c01064fa2da9241ae20be5d353e47db24a67d0458bf8b95b51226ad2e3cefacb628e38d343183a672022e4bec60007d2004e040f64d7f5dc4cfdc95e1676717fb7ac0cfdff6f5ce5426003db19b59a1407e89b7d3aff88592a0d6d26b7dc3c2dc5903fa3bf2ffa6a3ffb6991ae1a89e4a24e215401673b9fad941e4b142a751654c7028d616835a554764579e316a98f22eabad4f98395c807633d28f9372488dcc39702c95545a413b990146c6d9b9030e18709d2c10fbe7d8510a81e9088349ea5a870a51e5d3cda58754b22e686394e3ecc5a43e47a6d4e374fc1972f7e95be48c7863a51de076112dd2415591c2c2851ddbf12c91de33d4e2aa28c8418c59c70a5dcd523cbc7df76ca12fd4e50be0cde747ebe6b43f21821190ed58faf2a6e416850145b10"""


import os
import sys
import signal
import re  # Added explicit import for regular expressions
import threading
import time
from datetime import datetime
import PySimpleGUI as sg
import pyqrcode
import json
import socket
import subprocess
import platform
import io
from waitress import serve
import shutil

###Old import types
#from urllib import request
#from flask import jsonify, Flask
###New Import type due to conflict of name
from urllib import request as urllib_request
from flask import jsonify, Flask, request

###Import for platform utilities
import platform_utils

###New Cross platform code START####
# Get correct path to resources whether running as script or packaged app
def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Use the directory where this script is located
        base_path = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_path, relative_path)


# Define nginx directory location
NGINX_DIR = get_resource_path("nginx")
print(f"Using Nginx directory: {NGINX_DIR}")


# Platform detection function
def get_platform():
    """
    Detects the current operating system and returns detailed information for debugging.
    """
    system = platform.system()
    print(f"Detected platform: {system}")
    print(f"Platform details: {platform.platform()}")
    print(f"Python version: {platform.python_version()}")

    if system == "Linux":
        # Get more detailed Linux information
        try:
            distro_info = subprocess.check_output("lsb_release -a", shell=True, text=True)
            print(f"Linux distribution info:\n{distro_info}")
        except Exception as e:
            print(f"Could not get Linux distribution info: {e}")

    return system


# Cross-platform replacement for STARTUPINFO functions FIXED
def start_nginx_silently():
    """Start Nginx server without opening folders or showing console windows."""
    try:
        system = get_platform()

        if system == "Windows":
            # Windows-specific implementation (unchanged)
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0  # SW_HIDE

            batch_file = os.path.join(os.getcwd(), "silent_start_nginx.bat")
            with open(batch_file, "w") as f:
                f.write("@echo off\n")
                f.write(f"cd {NGINX_DIR}\n")
                f.write("start /b nginx.exe\n")
                f.write("exit\n")

            subprocess.Popen(
                batch_file,
                shell=True,
                startupinfo=startupinfo
            )
        else:
            # Linux/Mac implementation - Use system nginx
            try:
                # Create a temporary nginx directory structure
                tmp_base_dir = "/tmp/qr_api_nginx"
                tmp_conf_dir = os.path.join(tmp_base_dir, "conf")
                tmp_logs_dir = os.path.join(tmp_base_dir, "logs")

                # Clean up any existing temp directories
                if os.path.exists(tmp_base_dir):
                    subprocess.run(f"rm -rf {tmp_base_dir}", shell=True)

                # Create the directory structure
                os.makedirs(tmp_conf_dir, exist_ok=True)
                os.makedirs(tmp_logs_dir, exist_ok=True)
                os.makedirs(os.path.join(tmp_conf_dir, "ssl"), exist_ok=True)

                # Copy the configuration files
                src_conf_dir = os.path.join(NGINX_DIR, "conf")
                subprocess.run(f"cp -r {src_conf_dir}/* {tmp_conf_dir}/", shell=True)

                # Create placeholder log files
                open(os.path.join(tmp_logs_dir, "error.log"), 'a').close()
                open(os.path.join(tmp_logs_dir, "access.log"), 'a').close()

                # Update the paths in nginx.conf file
                config_file = os.path.join(tmp_conf_dir, "nginx.conf")
                backup_file = f"{config_file}.bak"
                shutil.copy2(config_file, backup_file)

                # Read the file line by line to make precise replacements
                with open(backup_file, 'r') as infile, open(config_file, 'w') as outfile:
                    for line in infile:
                        if "error_log" in line and "logs/error.log" in line:
                            outfile.write(f"error_log {tmp_logs_dir}/error.log;\n")
                        elif "pid" in line and "logs/nginx.pid" in line:
                            outfile.write(f"pid {tmp_logs_dir}/nginx.pid;\n")
                        else:
                            outfile.write(line)

                # Set proper permissions
                subprocess.run(f"chmod -R 755 {tmp_base_dir}", shell=True)
                subprocess.run(f"find {tmp_conf_dir} -type f -exec chmod 644 {{}} \\;", shell=True)
                subprocess.run(f"chmod 644 {tmp_logs_dir}/error.log", shell=True)
                subprocess.run(f"chmod 644 {tmp_logs_dir}/access.log", shell=True)

                # Test the configuration (needs sudo for port 443)
                test_result = subprocess.run(
                    f"sudo -n nginx -c {config_file} -t",
                    shell=True,
                    capture_output=True,
                    text=True,
                    stdin=subprocess.DEVNULL
                )

                if test_result.returncode != 0:
                    return False, f"Nginx configuration test failed: {test_result.stderr}"

                # Start nginx with our configuration
                # On macOS/Linux, privileged ports (<1024) require sudo
                # Check if we need sudo by reading the nginx port from config
                nginx_cmd = f"sudo -n nginx -c {config_file}"  # Use sudo for port 443

                print(f"Starting nginx with command: {nginx_cmd}")
                result = subprocess.run(
                    nginx_cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    stdin=subprocess.DEVNULL
                )

                # Check if nginx started properly
                if result.returncode != 0:
                    error_msg = result.stderr if result.stderr else result.stdout
                    print(f"Nginx failed to start: {error_msg}")
                    return False, f"Nginx failed to start: {error_msg}"

                # Give nginx a moment to start
                time.sleep(1)

                # Verify nginx is actually running
                check_result = subprocess.run("pgrep nginx", shell=True, capture_output=True)
                if check_result.returncode == 0:
                    print("Nginx started successfully and is running")
                    return True, "Nginx started successfully using system binary"
                else:
                    print("Nginx command succeeded but process not found")
                    return False, "Nginx started but process not detected"

            except Exception as inner_e:
                print(f"Error starting system nginx: {str(inner_e)}")
                return False, f"Error starting system nginx: {str(inner_e)}"

        return True, "Nginx started successfully"
    except Exception as e:
        return False, f"Error starting Nginx: {str(e)}"


def stop_nginx_silently():
    """Stop Nginx server without opening folders or showing console windows."""
    try:
        system = get_platform()

        if system == "Windows":
            # Windows implementation remains the same
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0  # SW_HIDE

            batch_file = os.path.join(os.getcwd(), "silent_stop_nginx.bat")
            with open(batch_file, "w") as f:
                f.write("@echo off\n")
                f.write(f"cd {NGINX_DIR}\n")
                f.write("nginx.exe -s stop\n")
                f.write("exit\n")

            subprocess.run(
                batch_file,
                shell=True,
                startupinfo=startupinfo
            )
        else:
            # Linux/Mac implementation — stop ONLY this project's nginx
            # IMPORTANT: Other projects (e.g. API_Server_Training) run their own nginx
            # on different ports. We must NEVER use bare 'pkill nginx' or 'nginx -s stop'
            # as that would kill other projects' nginx instances.
            tmp_base_dir = "/tmp/qr_api_nginx"
            config_file = os.path.join(tmp_base_dir, "conf", "nginx.conf")
            pid_file = os.path.join(tmp_base_dir, "logs", "nginx.pid")

            # Method 1: Use PID file to kill only THIS project's nginx
            pid_killed = False
            if os.path.exists(pid_file):
                try:
                    with open(pid_file, 'r') as f:
                        pid = int(f.read().strip())
                    # Send SIGQUIT for graceful shutdown (nginx master process)
                    os.kill(pid, signal.SIGQUIT)
                    print(f"Sent SIGQUIT to nginx master (PID {pid})")
                    time.sleep(2)
                    # Check if it's still alive
                    try:
                        os.kill(pid, 0)
                        # Still alive — force kill
                        os.kill(pid, signal.SIGKILL)
                        print(f"Force-killed nginx master (PID {pid})")
                        time.sleep(1)
                    except OSError:
                        pass  # Already dead — good
                    pid_killed = True
                except (ValueError, OSError) as e:
                    print(f"PID file kill attempt: {e}")

            # Method 2: Fallback — use -c config flag to stop only this config's nginx
            if not pid_killed and os.path.exists(config_file):
                try:
                    subprocess.run(
                        f"sudo -n nginx -c {config_file} -s stop",
                        shell=True, capture_output=True, stdin=subprocess.DEVNULL
                    )
                    time.sleep(1)
                except Exception:
                    pass

            # Clean up temporary files
            if os.path.exists(tmp_base_dir):
                subprocess.run(f"rm -rf {tmp_base_dir}", shell=True)

        return True, "Nginx stopped successfully"
    except Exception as e:
        return False, f"Error stopping Nginx: {str(e)}"




def check_nginx_status():
    """Check if Nginx is running by checking for its process."""
    try:
        system = get_platform()

        if system == "Windows":
            # Windows implementation
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq nginx.exe"],
                startupinfo=startupinfo,
                capture_output=True,
                text=True
            )

            return "nginx.exe" in result.stdout
        else:
            # Linux/Mac implementation
            try:
                # Check if nginx process is running using ps
                result = subprocess.run(
                    ["ps", "aux"],
                    capture_output=True,
                    text=True
                )

                # Look for nginx process
                return "nginx" in result.stdout
            except Exception as e:
                print(f"Error checking nginx status on Linux: {e}")
                return False
    except Exception:
        return False


def update_nginx_config(nginx_port, api_port):
    """
    Updates the nginx.conf file with the specified ports and corrects certificate paths.
    """
    try:
        nginx_conf_path = os.path.join(NGINX_DIR, "conf", "nginx.conf")

        # First check if the file exists
        if not os.path.exists(nginx_conf_path):
            print(f"Nginx config file not found at {nginx_conf_path}")
            return False

        # Read the original config file
        with open(nginx_conf_path, 'r') as f:
            config_content = f.read()

        # Make a backup of the original file
        backup_path = os.path.join(NGINX_DIR, "conf", "nginx.conf.bak")
        with open(backup_path, 'w') as f:
            f.write(config_content)

        # Define the correct certificate paths - use relative paths that work on both platforms
        ssl_dir = "ssl"  # Relative to nginx/conf directory
        cert_path = os.path.join(ssl_dir, "cert.pem").replace("\\", "/")
        key_path = os.path.join(ssl_dir, "key.pem").replace("\\", "/")

        # Update the certificate paths using regex
        cert_pattern = r'ssl_certificate\s+"[^"]+";'
        config_content = re.sub(cert_pattern, f'ssl_certificate "{cert_path}";', config_content)

        key_pattern = r'ssl_certificate_key\s+"[^"]+";'
        config_content = re.sub(key_pattern, f'ssl_certificate_key "{key_path}";', config_content)

        # Update the ports using regex to ensure we only change the correct lines
        # Update HTTP redirect port (typically 80 or 8080)
        http_pattern = r'listen\s+\d+;'
        config_content = re.sub(http_pattern, f'listen       8080;', config_content)

        # Update HTTPS port (nginx_port)
        https_pattern = r'listen\s+\d+\s+ssl;'
        config_content = re.sub(https_pattern, f'listen {nginx_port} ssl;', config_content)

        # Update proxy_pass port (api_port) - Force IPv4 to avoid macOS IPv6 issues
        # Match both formats: with and without path after port
        # Format 1: proxy_pass http://127.0.0.1:8081;
        # Format 2: proxy_pass http://127.0.0.1:8081/chat/stream;
        proxy_pattern = r'proxy_pass\s+http://(?:localhost|127\.0\.0\.1):\d+(/[^;]*)?;'
        config_content = re.sub(proxy_pattern, lambda m: f'proxy_pass http://127.0.0.1:{api_port}{m.group(1) if m.group(1) else ""};', config_content)

        # Write the updated config back to the file
        with open(nginx_conf_path, 'w') as f:
            f.write(config_content)

        print(f"Updated nginx config with paths: cert={cert_path}, key={key_path}")
        print(f"Updated ports: nginx={nginx_port}, api={api_port}")

        return True
    except Exception as e:
        print(f"Error updating nginx config: {str(e)}")
        return False

###New Cross platform code END####


# Rest of your original code here, with Windows-specific sections wrapped in if is_windows() checks
####Modified Layout and code matching to main project START#####
def create_api_layout():
    """Creates the API server configuration and control UI layout."""

    server_controls = [
        [sg.Text("API Server Login", font=('Helvetica', 11, 'bold'))],

        # Server control buttons - unified
        [sg.Button('Start Servers', key='-START_SERVERS-', size=(12, 1)),
         sg.Button('Stop Servers', key='-STOP_SERVERS-', size=(12, 1))],

        # Status indicators for both servers
        [sg.Text("Nginx Status:", pad=(10, 0)),
         sg.Text("Stopped", key='-NGINX_STATUS-', text_color='red'),
         sg.Text("API Status:", pad=(10, 0)),
         sg.Text("Stopped", key='-SERVER-', text_color='red')],

        # API server configuration fields - same as main project
        [sg.Text("VPS Public IP:", size=(15, 1), tooltip="Your VPS public IP for Android connection (not API binding)"),
         sg.InputText(get_public_ip(), key="-API_HOST-", size=(40, 1)),
         sg.Button("Refresh IP", key="-REFRESH_IP-")],

        [sg.Text("Nginx Port:", size=(15, 1)),
         sg.InputText("443", key="-NGINX_PORT-", size=(10, 1)),
         sg.Button("Add to Firewall", key="-ADD_NGINX_FW-")],

        [sg.Text("API Server Port:", size=(15, 1)),
         sg.InputText("8081", key="-API_PORT-", size=(10, 1)),
         sg.Button("Add to Firewall", key="-ADD_API_FW-")],

        # Save and connect buttons
        [sg.Button("Save API Settings", key="-SAVE_API-"),
         sg.Button("Connect to Mobile(API)", key="-CONNECT_MOBILE-", button_color="green")],

        [sg.Text('', key='-STATUS-', size=(60, 4), text_color='blue')],

        [sg.HorizontalSeparator()]
    ]

    return server_controls

def create_main_layout():
    """Creates the main window layout with the API server controls."""
    return [create_api_layout()]

def create_window():
    """Creates and returns the main window with proper configuration."""
    window = sg.Window(
        'API Server Setup',
        create_main_layout(),
        resizable=True,
        finalize=True
    )
    return window




def save_api_settings(host, nginx_port, api_port, config_file):
    """
    Saves API connection settings to a config file and updates nginx configuration.

    Args:
        host: VPS public IP address (for Android QR code, not for API binding)
        nginx_port: Port for Nginx to listen on
        api_port: Port for the API server to listen on
        config_file: Path to save the configuration

    Returns:
        bool: True if successful, False otherwise

    Note:
        - 'vps_host' stores the VPS public IP for QR code generation
        - 'host' is always '127.0.0.1' (API server binds to localhost only)
        - nginx proxy_pass always uses 127.0.0.1 (internal forwarding)
    """
    try:
        # Create config directory if it doesn't exist
        config_dir = os.path.dirname(config_file)
        os.makedirs(config_dir, exist_ok=True)

        # Save settings to config file
        # IMPORTANT: Separate VPS IP (external) from API binding IP (internal)
        config = {
            'vps_host': host,           # VPS public IP for Android QR code
            'host': '127.0.0.1',        # API server always binds to localhost
            'nginx_port': nginx_port,
            'api_port': api_port,
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        with open(config_file, 'w') as f:
            json.dump(config, f, indent=4)

        print(f"Saved VPS IP: {host}, API binding: 127.0.0.1")

        # Update nginx configuration file (always uses 127.0.0.1 internally)
        success = update_nginx_config(nginx_port, api_port)
        if not success:
            print(f"Failed to update nginx config")
            return False

        print(f"Successfully updated nginx config with ports: nginx={nginx_port}, api={api_port}")
        return True
    except Exception as e:
        print(f"Error saving API settings: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def load_api_settings(config_file):
    """
    Loads API settings from the config file.

    Args:
        config_file: Path to the configuration file

    Returns:
        dict: Configuration settings with 'vps_host' for GUI display

    Note:
        - Returns 'vps_host' for VPS public IP (used in GUI and QR code)
        - 'host' is always '127.0.0.1' (internal API binding)
    """
    try:
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = json.load(f)
                # Backward compatibility: if old format, migrate it
                if 'vps_host' not in config and 'host' in config:
                    # If host is localhost, user needs to set VPS IP manually
                    # Otherwise, it was the VPS IP (migrate it)
                    if config['host'] in ['127.0.0.1', 'localhost', '0.0.0.0']:
                        config['vps_host'] = get_public_ip()  # Default to detected public IP
                    else:
                        config['vps_host'] = config['host']  # Migrate old VPS IP
                    config['host'] = '127.0.0.1'  # API always binds to localhost
                return config
        return {}
    except Exception as e:
        print(f"Error loading API settings: {str(e)}")
        return {}



def is_port_listening(port):
    """
    Checks if a port is open and listening on localhost.

    Args:
        port: Port number to check

    Returns:
        bool: True if port is listening, False otherwise
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('127.0.0.1', int(port)))
        sock.close()
        return result == 0  # If result is 0, port is open
    except Exception:
        return False


def is_admin():
    """
    Check if the script is running with administrative privileges.
    Works across Windows, Linux, and macOS.

    Returns:
        bool: True if running with admin privileges, False otherwise
    """
    system = get_platform()

    if system == "Windows":
        try:
            print("Checking Windows admin rights")
            return ctypes.windll.shell32.IsUserAnAdmin()
        except Exception as e:
            print(f"Error checking Windows admin rights: {e}")
            return False

    elif system == "Linux":
        try:
            print("Checking Linux admin rights")
            # Check if effective user ID is 0 (root)
            is_root = os.geteuid() == 0
            print(f"User is running as root: {is_root}")

            # Also check if running through sudo
            is_sudo = 'SUDO_UID' in os.environ
            print(f"Script is running through sudo: {is_sudo}")

            return is_root or is_sudo
        except Exception as e:
            print(f"Error checking Linux admin rights: {e}")
            return False

    elif system == "Darwin":  # macOS
        try:
            print("Checking macOS admin rights")
            # Check if effective user ID is 0 (root)
            is_root = os.geteuid() == 0
            print(f"User is running as root: {is_root}")

            # Also check if running through sudo
            is_sudo = 'SUDO_UID' in os.environ
            print(f"Script is running through sudo: {is_sudo}")

            return is_root or is_sudo
        except Exception as e:
            print(f"Error checking macOS admin rights: {e}")
            return False

    # Unknown platform
    print(f"Unknown platform: {system}, cannot determine admin rights")
    return False

def request_admin_privileges():
    """
    Request administrator privileges if not already running with them.
    Implements different methods based on the platform.

    Returns:
        bool: True if successfully elevated or already admin, False otherwise
    """
    system = get_platform()

    # If already admin, no need to elevate
    if is_admin():
        print("Already running with admin privileges")
        return True

    print("Requesting admin privileges...")

    if system == "Windows":
        try:
            print("Using pyuac to request Windows admin rights")
            pyuac.runAsAdmin()
            return True  # if we get here on Windows, we're either admin or the script restarted
        except Exception as e:
            print(f"Error requesting Windows admin privileges: {e}")
            return False

    elif system == "Linux":
        try:
            print("Preparing to request Linux admin rights")
            # Prepare the command to run this script with sudo
            script_path = os.path.abspath(sys.argv[0])
            args = [arg for arg in sys.argv[1:]]

            # Build the sudo command
            sudo_command = ['sudo', sys.executable, script_path] + args

            print(f"Executing with sudo: {' '.join(sudo_command)}")

            # Execute the sudo command
            subprocess.call(sudo_command)

            # Exit the current non-privileged process
            sys.exit(0)
        except Exception as e:
            print(f"Error requesting Linux admin privileges: {e}")
            return False

    elif system == "Darwin":  # macOS
        try:
            print("Preparing to request macOS admin rights")
            # Same approach as Linux for macOS
            script_path = os.path.abspath(sys.argv[0])
            args = [arg for arg in sys.argv[1:]]

            # Build the sudo command
            sudo_command = ['sudo', sys.executable, script_path] + args

            print(f"Executing with sudo: {' '.join(sudo_command)}")

            # Execute the sudo command
            subprocess.call(sudo_command)

            # Exit the current non-privileged process
            sys.exit(0)
        except Exception as e:
            print(f"Error requesting macOS admin privileges: {e}")
            return False

    # Unknown platform
    print(f"Unknown platform: {system}, cannot request admin privileges")
    return False

def check_firewall_rule_exists(rule_name):
    """
    Cross-platform function to check if a firewall rule with the given name exists.

    Args:
        rule_name (str): The name of the rule to check

    Returns:
        bool: True if the rule exists, False otherwise
    """
    system = get_platform()
    print(f"Checking if firewall rule '{rule_name}' exists on {system}")

    if system == "Windows":
        # Original Windows implementation
        command = [
            "netsh", "advfirewall", "firewall", "show", "rule",
            f"name={rule_name}"
        ]

        try:
            # Run the command silently
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            # Check the command output
            if process.returncode == 0 and "No rules match the specified criteria" not in process.stdout:
                print(f"Rule '{rule_name}' already exists on Windows!")
                return True
            else:
                print(f"Rule '{rule_name}' does not exist yet on Windows.")
                return False
        except Exception as e:
            print(f"Error checking if rule exists on Windows: {str(e)}")
            # If there's an error, assume the rule doesn't exist to be safe
            return False

    elif system == "Linux":
        try:
            # For Linux, we'll check iptables rules
            # Extract port and protocol from rule_name (assuming format like "AIAgent_Inbound_TCP_22")
            parts = rule_name.split('_')
            if len(parts) >= 4:
                direction = parts[1].lower()  # "Inbound" or "Outbound"
                protocol = parts[2].lower()  # "TCP" or "UDP"
                port = parts[3]  # Port number

                # Check iptables for a matching rule
                command = ["sudo", "iptables", "-L", "-n"]

                process = subprocess.run(
                    command,
                    capture_output=True,
                    text=True
                )

                if process.returncode == 0:
                    # Look for rules matching our port and protocol
                    chain = "INPUT" if direction == "inbound" else "OUTPUT"
                    rule_pattern = f"{protocol.upper()}.*dpt:{port}"

                    for line in process.stdout.splitlines():
                        if chain in line:
                            # We're in the right chain section
                            if re.search(rule_pattern, line, re.IGNORECASE):
                                print(f"Found matching rule for {protocol} port {port} in {chain} chain")
                                return True

                    print(f"No matching rule found for {protocol} port {port} in {chain} chain")
                    return False
                else:
                    print(f"Error executing iptables command: {process.stderr}")
                    return False
            else:
                print(f"Invalid rule name format: {rule_name}")
                return False

        except Exception as e:
            print(f"Error checking if rule exists on Linux: {str(e)}")
            return False

    elif system == "Darwin":  # macOS
        try:
            # For macOS, we'll check using pfctl
            # Extract port and protocol from rule_name (assuming format like "AIAgent_Inbound_TCP_22")
            parts = rule_name.split('_')
            if len(parts) >= 4:
                direction = parts[1].lower()  # "Inbound" or "Outbound"
                protocol = parts[2].lower()  # "TCP" or "UDP"
                port = parts[3]  # Port number

                # Check pfctl for a matching rule
                command = ["sudo", "pfctl", "-s", "rules"]

                process = subprocess.run(
                    command,
                    capture_output=True,
                    text=True
                )

                if process.returncode == 0:
                    # Look for rules matching our port and protocol
                    rule_pattern = f"{protocol} port {port}"
                    direction_word = "in" if direction == "inbound" else "out"

                    for line in process.stdout.splitlines():
                        if direction_word in line and rule_pattern in line and "pass" in line:
                            print(f"Found matching rule for {protocol} port {port} in {direction} direction")
                            return True

                    print(f"No matching rule found for {protocol} port {port} in {direction} direction")
                    return False
                else:
                    print(f"Error executing pfctl command: {process.stderr}")
                    return False
            else:
                print(f"Invalid rule name format: {rule_name}")
                return False

        except Exception as e:
            print(f"Error checking if rule exists on macOS: {str(e)}")
            return False

    else:
        print(f"Unknown platform: {system}, cannot check firewall rules")
        return False

def add_firewall_rule(port, protocol="TCP", direction="in", name=None, application=None):
    """
    Cross-platform function to add a firewall rule for the specified port and direction.

    Args:
        port (int): The port number to allow
        protocol (str): The protocol (TCP or UDP)
        direction (str): The direction of the rule ('in' or 'out')
        name (str, optional): Custom name for the rule
        application (str, optional): Path to application to restrict the rule to

    Returns:
        tuple: (success, message)
    """
    system = get_platform()
    print(f"Adding firewall rule for port {port} ({protocol}) in {direction} direction on {system}")

    if system == "Windows":
        # Original Windows implementation
        if direction not in ["in", "out"]:
            return False, "Direction must be 'in' or 'out'"

        # Generate rule name if not provided
        if name is None:
            direction_text = "Inbound" if direction == "in" else "Outbound"
            name = f"AIAgent_{direction_text}_{protocol}_{port}"

        # First check if the rule already exists
        if check_firewall_rule_exists(name):
            return True, f"Firewall rule '{name}' already exists. No changes made."

        # Build the command
        command = [
            "netsh", "advfirewall", "firewall", "add", "rule",
            f"name={name}",
            f"dir={direction}",
            "action=allow",
            f"protocol={protocol}",
            f"localport={port}"
        ]

        # Add application path if specified
        if application:
            command.append(f"program={application}")

        print(f"Adding {direction}bound rule for port {port} ({name})...")

        try:
            # Execute the command
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            if process.returncode == 0:
                print(f"SUCCESS: {direction}bound rule for port {port} ({name}) added on Windows")
                return True, f"{direction}bound rule for port {port} added successfully."
            else:
                print(f"ERROR: Failed to add {direction}bound rule on Windows: {process.stderr}")
                return False, f"Failed to add {direction}bound rule: {process.stderr}"

        except Exception as e:
            print(f"EXCEPTION: Error adding firewall rule on Windows: {str(e)}")
            return False, f"Error adding firewall rule: {str(e)}"

    elif system == "Linux":
        try:
            # Generate rule identifier for Linux
            direction_text = "Inbound" if direction == "in" else "Outbound"
            rule_id = f"AIAgent_{direction_text}_{protocol}_{port}"

            print(f"Adding {direction_text} rule for {protocol} port {port} on Linux...")

            # First check if the rule already exists
            if check_firewall_rule_exists(rule_id):
                print(f"Rule already exists for {protocol} port {port}")
                return True, f"Firewall rule for {protocol} port {port} already exists. No changes made."

            # Check which firewall is in use (ufw, iptables, or firewalld)
            # First, try ufw (Uncomplicated Firewall) - common on Ubuntu
            try:
                # Check if ufw is installed and enabled
                ufw_status = subprocess.run(
                    ["sudo", "ufw", "status"],
                    capture_output=True,
                    text=True
                )

                if "Status: active" in ufw_status.stdout:
                    print("Using UFW firewall")

                    # UFW command to add the rule
                    if direction == "in":
                        ufw_cmd = ["sudo", "ufw", "allow", f"{port}/{protocol.lower()}"]
                    else:
                        # UFW doesn't directly support outbound rules in simple syntax
                        # Using the more detailed syntax
                        ufw_cmd = ["sudo", "ufw", "allow", "out", f"to", "any", "port", f"{port}", "proto",
                                   f"{protocol.lower()}"]

                    ufw_result = subprocess.run(
                        ufw_cmd,
                        capture_output=True,
                        text=True
                    )

                    if ufw_result.returncode == 0:
                        print(f"Successfully added {direction_text} rule for {protocol} port {port} using UFW")
                        return True, f"{direction_text} rule for {protocol} port {port} added successfully using UFW."
                    else:
                        print(f"Failed to add rule using UFW: {ufw_result.stderr}")
                        # Fall back to iptables if UFW fails
                else:
                    print("UFW not active, trying iptables")
            except Exception as e:
                print(f"UFW not available: {e}")

            # Try iptables as fallback
            print("Using iptables firewall")

            # Chain depends on direction
            chain = "INPUT" if direction == "in" else "OUTPUT"
            protocol_lower = protocol.lower()

            # iptables command to add the rule
            iptables_cmd = [
                "sudo", "iptables", "-A", chain,
                "-p", protocol_lower,
                "--dport" if direction == "in" else "--sport", str(port),
                "-j", "ACCEPT"
            ]

            iptables_result = subprocess.run(
                iptables_cmd,
                capture_output=True,
                text=True
            )

            if iptables_result.returncode == 0:
                print(f"Successfully added {direction_text} rule for {protocol} port {port} using iptables")

                # Try to make the rule persistent (varies by distribution)
                try:
                    # For Debian/Ubuntu
                    save_cmd = ["sudo", "sh", "-c", "iptables-save > /etc/iptables/rules.v4"]
                    save_result = subprocess.run(save_cmd, capture_output=True, text=True, shell=True)

                    if save_result.returncode == 0:
                        print("Successfully saved iptables rules")
                    else:
                        print(f"Could not save iptables rules: {save_result.stderr}")
                        # Try alternative method
                        alt_save_cmd = ["sudo", "sh", "-c", "iptables-save > /etc/iptables.rules"]
                        alt_save_result = subprocess.run(alt_save_cmd, capture_output=True, text=True, shell=True)

                        if alt_save_result.returncode == 0:
                            print("Successfully saved iptables rules (alternative method)")
                        else:
                            print("Could not save iptables rules persistently. Rules will be lost on reboot.")
                except Exception as e:
                    print(f"Could not make iptables rules persistent: {e}")

                return True, f"{direction_text} rule for {protocol} port {port} added successfully using iptables."
            else:
                print(f"Failed to add rule using iptables: {iptables_result.stderr}")
                return False, f"Failed to add firewall rule using iptables: {iptables_result.stderr}"

        except Exception as e:
            print(f"Error adding firewall rule on Linux: {str(e)}")
            return False, f"Error adding firewall rule: {str(e)}"

    else:
        print(f"Unknown platform: {system}, cannot add firewall rules")
        return False, f"Firewall configuration not supported on {system}"

def generate_qr_code(host, nginx_port, api_port, authentication_key):
    """
    Generates a QR code containing connection information.
    Returns the QR code as bytes for a PySimpleGUI Image element.
    """
    # Create a dictionary with the connection information
    connection_data = {
        "host": host,
        "nginx_port": nginx_port,
        "api_port": api_port,
        "authentication_key": authentication_key   ### Add this new Authentication key to pass to Android app for Authentication
    }

    # Convert to JSON
    json_data = json.dumps(connection_data)

    # Generate the QR code
    qr = pyqrcode.create(json_data)

    # Create an in-memory binary stream
    buffer = io.BytesIO()
    # Save the QR code as PNG to the buffer
    qr.png(buffer, scale=10)
    # Move buffer position to start
    buffer.seek(0)

    # Return the buffer content
    return buffer.getvalue()


def show_qr_popup(qr_data, connection_info):
    """
    Shows a popup window with a larger QR code and connection information.
    Makes scanning easier for users.
    """
    # Create layout for popup with a larger QR code display
    popup_layout = [
        [sg.Text("Mobile Connection QR Code", font=("Helvetica", 16, "bold"), justification="center")],
        [sg.Text("Scan this QR code with your Android app to connect", justification="center")],
        [sg.Image(data=qr_data)],
        [sg.Text(f"Connection Details: {connection_info}", justification="center")],
        [sg.Button("Copy to Clipboard", key="-COPY-"), sg.Button("Close", key="-CLOSE-")]
    ]

    # Create popup window
    popup = sg.Window("Connect to Mobile", popup_layout, modal=True, finalize=True, element_justification='center')

    # Simple event loop for popup
    while True:
        event, _ = popup.read()
        if event == "-COPY-":
            try:
                # Copy connection info to clipboard
                sg.clipboard_set(connection_info)
                sg.popup_quick_message("Connection details copied to clipboard!", background_color="green",
                                       text_color="white")
            except Exception as e:
                sg.popup_error(f"Failed to copy to clipboard: {str(e)}")
        elif event in (sg.WINDOW_CLOSED, "-CLOSE-"):
            break

    popup.close()


def test_connection(host, port):
    """
    Tests if the API server is reachable at the given host and port.
    """
    try:
        # Create a socket object
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Set a timeout of 2 seconds
        s.settimeout(2)
        # Attempt to connect
        s.connect((host, int(port)))
        # Close the connection
        s.close()
        return True, "Connection successful! API server is reachable."
    except Exception as e:
        return False, f"Connection failed: {str(e)}"



# Global variables for server state
api_server_running = False
server_thread = None

####NOTE::This is the real API server which the Android app uses for Chat and Action modes etc.
def start_api_server(port, window=None, system_instance=None):
    """Start the API server on the specified port."""
    global api_server_running, server_thread

    # Check if server is already running (like original)
    if api_server_running:
        print("Server is already running")
        return False

    def run_server():
        if system_instance is None:
            print("ERROR: No AI system provided - server will return error messages")
            app = Flask(__name__)

            @app.route('/chat', methods=['POST'])
            def chat():
                return jsonify({
                    'response': "ERROR: Server started without AI system. Please restart the application.",
                    'mode': "CHAT_MODE"
                })
        else:
            app = system_instance.app
            print("Using real AI server")

        try:
            print(f"Starting API server on port {port}")
            serve(app, host='0.0.0.0', port=port, channel_timeout=600)
        except Exception as e:
            print(f"Server error: {str(e)}")
            global api_server_running
            api_server_running = False

    # Start server in a new thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    api_server_running = True
    print("Server started successfully")

    return True


def start_both_servers(window, values, system_instance=None):
    """
    Starts both Nginx and API servers with the current settings.

    Args:
        window: The PySimpleGUI window
        values: The current values from the window

    Returns:
        tuple: (nginx_running, api_running) indicating whether each server started successfully
    """
    global api_server_running
    nginx_running = False

    try:
        # Validate nginx port
        nginx_port_str = values['-NGINX_PORT-'].strip()
        try:
            nginx_port = int(nginx_port_str) if nginx_port_str else 443
            if not nginx_port_str:
                window['-NGINX_PORT-'].update("443")
        except ValueError:
            nginx_port = 443
            window['-NGINX_PORT-'].update("443")

        # Validate API port
        api_port_str = values['-API_PORT-'].strip()
        try:
            api_port = int(api_port_str) if api_port_str else 8081
            if not api_port_str:
                window['-API_PORT-'].update("8081")
        except ValueError:
            api_port = 8081
            window['-API_PORT-'].update("8081")

        # Update nginx config with the current ports
        update_nginx_config(nginx_port, api_port)

        # Start Nginx
        window['-STATUS-'].update("Starting Nginx server...", text_color='blue')
        window.refresh()

        success, msg = start_nginx_silently()
        if success:
            # Wait a moment for nginx to start up
            time.sleep(2)
            # Verify nginx is actually listening
            if is_port_listening(nginx_port):
                nginx_running = True
                window['-NGINX_STATUS-'].update('Running', text_color='green')
                window['-STATUS-'].update("Nginx server started successfully", text_color='green')
            else:
                window['-STATUS-'].update(f"Nginx failed to bind to port {nginx_port}", text_color='red')
                stop_nginx_silently()  # Cleanup
        else:
            window['-STATUS-'].update(f"Failed to start Nginx: {msg}", text_color='red')

        # Start API server if Nginx started successfully
        if nginx_running:
            window['-STATUS-'].update("Starting API server...", text_color='blue')
            window.refresh()

            try:
                # Start the API server
                start_api_server(api_port, window, system_instance)  # Pass system_instance

                # Wait a moment for server to start up
                time.sleep(2)

                # Verify API server is actually listening
                if is_port_listening(api_port):
                    window['-SERVER-'].update('Running', text_color='green')
                    window['-STATUS-'].update("Both servers started successfully", text_color='green')
                else:
                    window['-STATUS-'].update(f"API server failed to bind to port {api_port}", text_color='red')
                    api_server_running = False
            except Exception as e:
                window['-STATUS-'].update(f"Failed to start API server: {str(e)}", text_color='red')
                api_server_running = False

        return nginx_running, api_server_running

    except Exception as e:
        window['-STATUS-'].update(f"Error starting servers: {str(e)}", text_color='red')
        return nginx_running, api_server_running

####Modified Layout and code matching to main project END#####

def get_local_ip():
    """Attempts to determine the machine's local IP address."""
    try:
        # This creates a socket that doesn't actually connect anywhere
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # This triggers the OS to determine which interface would be used
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"  # Fallback to localhost


def get_public_ip():
    """
    Attempts to determine the machine's public IP address by querying external services.
    This requires internet connectivity to work properly.
    """
    # Try multiple services in case some are down
    ip_services = [
        "https://api.ipify.org",
        "https://ipinfo.io/ip",
        "https://ifconfig.me/ip",
        "https://icanhazip.com"
    ]

    # Import here to avoid adding a dependency if not needed
    try:
        import urllib_request
        import urllib.error
    except ImportError:
        return "Error: urllib module not available"

    # Try each service until we get a valid response
    for service in ip_services:
        try:
            response = urllib_request.urlopen(service, timeout=3)
            public_ip = response.read().decode('utf-8').strip()

            # Basic validation that we got an IP address-like response
            if public_ip and len(public_ip) > 7 and "." in public_ip:
                return public_ip
        except (urllib.error.URLError, urllib.error.HTTPError, ConnectionError, TimeoutError) as e:
            continue
        except Exception as e:
            continue

    # If all services failed
    return "Could not determine public IP"




