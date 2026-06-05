####Insert your distribution key at the top
import re

PySimpleGUI_License ="""elyIJgMoaqWzNll5bHnuNAlhVaHhlKwCZhSlIj6KI6kpRep6cU3SRPyNafW3JZ1PdsGclzv8bAiLIBsZI7kVxEp5Y42cVRuQc822VnJARuCeIO6RMaTUcWzKNbzlIdz8NojQchxsNoSdwtivTJGQlljeZvWq56z0ZhUGRalYceGsx8vYerWN1hlQbZn2RxWkZMXNJZzOa1WH9BuVIFjLoGipNuSi4XwpIgimwkirTYmaFitOZaUcZ4pdc8n1N602Iljyoai5ScmVFnntYWWZ50uZYeXWROosIXikwrirTEmOFBtHZNUNxHhlch3uQRi5O8iXJ9C8Z2WHhLlScjmdEei1LRCkJ8DYbm2R1mwfYpWq5g5iIXjuoNiIS4mFFdnDYDW65zukYSXxR5oZIEEOJqlEavGZVeyxYiS8IHs8I0kwN71qcY3lRPvIbPWIVByOSKUnQGiQOpihIhy8M6DIUK1bM8i3ImsYITkvRHhPdnG8VoJfc63LNu1KZVWsQ3iTOgiGIJybM1D7Iy1bLeTdAux4LgTREe5pIwipwoiXRiG6FM0QZWUoVg4EcNGHlFyGZUXMMLi0OniBIZyqMIDVIs1jLdTBAu1uLeTVEo0lIFiFwXiVRuW61EhXaLWBxFB7Z1GYRly0ZFXFNkzvI6jqoqiHaFmTFon7YMWT5buOYsXNRiozYlmZVgo2Z0X3J5hYMZzFMOzeMQ09BfnvbxWNFtpxbuCR52jZbv2X05ikL1CzJkJWUwEFF9kxZyHWJ4lTc03CMbiXOkicID0PNxSo4C5yMHCn4gymMMj7ITuAMhT0Q83WIQnX0d=J517c7d5fae65077acdc2471d2e926436011f50cc3bff5e606996187bbc87cb0a4796f69a65646f4f2401c26398c4df3c2e20ac1bdeb726222b3535af30177dbcda327d862b8ef3d121801906e44ce44ce74e02331e3f88e13586c3337e7d4b113f826187ea2a355b3075917c78aa05926b289cf8738a54267aa4915a7f14840a36d4d4abc646871adbb8d9bf078f67f1e8461fde9cf36a2a5def3e81ce135a48eeb90c5d39a04e85af461d99f296a8677f30403585d5bb3eb9bec197839c48f1e4365fa61bd8b798a73e11b4c5de4285f3bfcb92434865cc97c01064fa2da9241ae20be5d353e47db24a67d0458bf8b95b51226ad2e3cefacb628e38d343183a672022e4bec60007d2004e040f64d7f5dc4cfdc95e1676717fb7ac0cfdff6f5ce5426003db19b59a1407e89b7d3aff88592a0d6d26b7dc3c2dc5903fa3bf2ffa6a3ffb6991ae1a89e4a24e215401673b9fad941e4b142a751654c7028d616835a554764579e316a98f22eabad4f98395c807633d28f9372488dcc39702c95545a413b990146c6d9b9030e18709d2c10fbe7d8510a81e9088349ea5a870a51e5d3cda58754b22e686394e3ecc5a43e47a6d4e374fc1972f7e95be48c7863a51de076112dd2415591c2c2851ddbf12c91de33d4e2aa28c8418c59c70a5dcd523cbc7df76ca12fd4e50be0cde747ebe6b43f21821190ed58faf2a6e416850145b10"""

import ctypes
import sys
import PySimpleGUI as sg
import pyqrcode
import json
import socket
import subprocess
import os
import platform
import io
import pyuac
###Extra imports for OpenSSH
import requests
import zipfile
import tempfile
import shutil
###Linux specific imports
import platform
import logging
import sys
import os
import subprocess

###START:: Cross platform Specific code for Windows, Linux and MAC compatible

# Set up logging for better debugging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("sftp_qr_debug.log")
    ]
)
logger = logging.getLogger("SFTP_QR_GENERATOR")


# Platform detection function
def get_platform():
    """
    Detects the current operating system and returns detailed information for debugging.

    Returns:
        str: 'Windows', 'Linux', 'Darwin' (macOS), or 'Unknown'
    """
    system = platform.system()
    logger.info(f"Detected platform: {system}")
    logger.info(f"Platform details: {platform.platform()}")
    logger.info(f"Python version: {platform.python_version()}")

    if system == "Linux":
        # Get more detailed Linux information
        try:
            distro_info = subprocess.check_output("lsb_release -a", shell=True, text=True)
            logger.info(f"Linux distribution info:\n{distro_info}")
        except Exception as e:
            logger.warning(f"Could not get Linux distribution info: {e}")

    return system


# Admin privileges checking function (cross-platform)
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
            logger.debug("Checking Windows admin rights")
            return ctypes.windll.shell32.IsUserAnAdmin()
        except Exception as e:
            logger.error(f"Error checking Windows admin rights: {e}")
            return False

    elif system == "Linux":
        try:
            logger.debug("Checking Linux admin rights")
            # Check if effective user ID is 0 (root)
            is_root = os.geteuid() == 0
            logger.info(f"User is running as root: {is_root}")

            # Also check if running through sudo
            is_sudo = 'SUDO_UID' in os.environ
            logger.info(f"Script is running through sudo: {is_sudo}")

            return is_root or is_sudo
        except Exception as e:
            logger.error(f"Error checking Linux admin rights: {e}")
            return False

    elif system == "Darwin":  # macOS
        try:
            logger.debug("Checking macOS admin rights")
            # Check if effective user ID is 0 (root)
            is_root = os.geteuid() == 0
            logger.info(f"User is running as root: {is_root}")

            # Also check if running through sudo
            is_sudo = 'SUDO_UID' in os.environ
            logger.info(f"Script is running through sudo: {is_sudo}")

            return is_root or is_sudo
        except Exception as e:
            logger.error(f"Error checking macOS admin rights: {e}")
            return False

    # Unknown platform
    logger.warning(f"Unknown platform: {system}, cannot determine admin rights")
    return False


# Function to request admin privileges when needed
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
        logger.info("Already running with admin privileges")
        return True

    logger.info("Requesting admin privileges...")

    if system == "Windows":
        try:
            logger.debug("Using pyuac to request Windows admin rights")
            pyuac.runAsAdmin()
            return True  # if we get here on Windows, we're either admin or the script restarted
        except Exception as e:
            logger.error(f"Error requesting Windows admin privileges: {e}")
            return False

    elif system == "Linux":
        try:
            logger.debug("Preparing to request Linux admin rights")
            # Prepare the command to run this script with sudo
            script_path = os.path.abspath(sys.argv[0])
            args = [arg for arg in sys.argv[1:]]

            # Build the sudo command
            sudo_command = ['sudo', sys.executable, script_path] + args

            logger.info(f"Executing with sudo: {' '.join(sudo_command)}")

            # Execute the sudo command
            subprocess.call(sudo_command)

            # Exit the current non-privileged process
            sys.exit(0)
        except Exception as e:
            logger.error(f"Error requesting Linux admin privileges: {e}")
            return False

    elif system == "Darwin":  # macOS
        try:
            logger.debug("Preparing to request macOS admin rights")
            # Same approach as Linux for macOS
            script_path = os.path.abspath(sys.argv[0])
            args = [arg for arg in sys.argv[1:]]

            # Build the sudo command
            sudo_command = ['sudo', sys.executable, script_path] + args

            logger.info(f"Executing with sudo: {' '.join(sudo_command)}")

            # Execute the sudo command
            subprocess.call(sudo_command)

            # Exit the current non-privileged process
            sys.exit(0)
        except Exception as e:
            logger.error(f"Error requesting macOS admin privileges: {e}")
            return False

    # Unknown platform
    logger.warning(f"Unknown platform: {system}, cannot request admin privileges")
    return False


# ===== START PATH MANAGEMENT MODIFICATIONS =====
def get_app_directories():
    """
    Creates and returns platform-specific directory paths

    Returns:
        dict: Dictionary containing paths for different purposes
    """
    system = get_platform()
    username = get_current_username()
    logger.info(f"Current username detected: {username}")

    # Get current script directory
    app_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    logger.info(f"Application directory: {app_dir}")

    # Common paths for all platforms
    common_paths = {
        "app_dir": app_dir,
        "logs_dir": os.path.join(app_dir, "logs"),
    }

    # Create platform-specific defaults for memory directories
    if system == "Windows":
        remote_memory_dir = os.path.join(app_dir, "Central AI Memory")
        local_memory_dir = os.path.join(app_dir, "Central AI Memory Local")
    elif system == "Linux":
        # For Linux, create in user's home by default
        home_dir = os.path.expanduser("~")
        remote_memory_dir = os.path.join(home_dir, "Central AI Memory")
        local_memory_dir = os.path.join(home_dir, "Central AI Memory Local")
    elif system == "Darwin":  # macOS
        # For macOS, create in user's Documents folder by default
        home_dir = os.path.expanduser("~")
        remote_memory_dir = os.path.join(home_dir, "Documents", "Central AI Memory")
        local_memory_dir = os.path.join(home_dir, "Documents", "Central AI Memory Local")
    else:
        # Fallback for unknown platforms
        remote_memory_dir = os.path.join(app_dir, "Central AI Memory")
        local_memory_dir = os.path.join(app_dir, "Central AI Memory Local")

    # Add memory paths to result
    common_paths.update({
        "remote_memory_dir": remote_memory_dir,
        "local_memory_dir": local_memory_dir,
    })

    # Create directories if they don't exist
    for path_name, path in common_paths.items():
        if not os.path.exists(path) and "dir" in path_name:
            try:
                os.makedirs(path, exist_ok=True)
                logger.info(f"Created directory: {path}")
            except Exception as e:
                logger.error(f"Failed to create directory {path}: {e}")

    return common_paths


# ===== END PATH MANAGEMENT MODIFICATIONS =====

###END: Cross platform Specific code for Windows, Linux and MAC compatible

def get_latest_openssh_download_url():
    """
    Queries the GitHub API to retrieve the latest OpenSSH release download URL.
    Adjust the asset selection logic if needed.
    """
    api_url = "https://api.github.com/repos/PowerShell/Win32-OpenSSH/releases/latest"
    response = requests.get(api_url)
    if response.status_code == 200:
        data = response.json()
        # Look for the asset containing "OpenSSH-Win64.zip" in its name
        for asset in data.get("assets", []):
            if "OpenSSH-Win64.zip" in asset.get("name", ""):
                return asset.get("browser_download_url")
    return None


# ===== START OPENSSH MANAGEMENT MODIFICATIONS =====
def ensure_openssh_installed():
    """
    Cross-platform function to ensure OpenSSH is installed and running.

    Returns:
        bool: True if OpenSSH is successfully installed and running, False otherwise
    """
    system = get_platform()
    logger.info(f"Checking OpenSSH installation on {system}")

    if system == "Windows":
        # Original Windows implementation remains unchanged
        try:
            # Check if the sshd service exists by running 'sc query sshd'
            result = subprocess.run(["sc", "query", "sshd"], capture_output=True, text=True)
            if result.returncode == 0:
                logger.info("OpenSSH is already installed on Windows.")
                return True
            else:
                logger.info("sshd service not found on Windows, proceeding with installation.")
        except Exception as e:
            logger.error(f"Error checking sshd service on Windows: {e}")
            # Proceed with installation if any error occurs

        # Try to get the latest download URL from GitHub dynamically
        download_url = get_latest_openssh_download_url()
        if not download_url:
            # Fallback URL if dynamic retrieval fails
            download_url = "https://github.com/PowerShell/Win32-OpenSSH/releases/download/v8.6.0.0/OpenSSH-Win64.zip"
        logger.info(f"Downloading OpenSSH package from: {download_url}")

        try:
            # Download the OpenSSH package
            response = requests.get(download_url, stream=True)
            if response.status_code != 200:
                print("Failed to download OpenSSH package.")
                return False

            # Save the downloaded file to a temporary directory
            tmp_dir = tempfile.mkdtemp()
            zip_path = os.path.join(tmp_dir, "OpenSSH-Win64.zip")
            with open(zip_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"Downloaded OpenSSH package to {zip_path}")

            # Define the base installation directory
            base_install_dir = r"C:\Program Files\OpenSSH"
            if not os.path.exists(base_install_dir):
                os.makedirs(base_install_dir)

            # Extract the downloaded ZIP file into the installation directory
            print("Extracting package...")
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(base_install_dir)
            print(f"Extracted package to {base_install_dir}")

            # Check if there's an extra subfolder (e.g., "OpenSSH-Win64") and update install_dir accordingly
            potential_subdir = os.path.join(base_install_dir, "OpenSSH-Win64")
            install_dir = potential_subdir if os.path.isdir(potential_subdir) else base_install_dir

            # Locate and run the installation script (install-sshd.ps1)
            install_script = os.path.join(install_dir, "install-sshd.ps1")
            if not os.path.exists(install_script):
                print("Installation script not found in", install_dir)
                return False

            print(f"Running installation script from {install_dir}...")
            cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", install_script]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"install-sshd.ps1 failed: {result.stderr}")
                return False
            else:
                print("install-sshd.ps1 executed successfully.")

            # Set the sshd service to start automatically
            print("Setting sshd service to start automatically...")
            cmd_set = ["powershell", "-Command", "Set-Service -Name sshd -StartupType 'Automatic'"]
            subprocess.run(cmd_set, capture_output=True, text=True)

            # Start the sshd service
            print("Starting sshd service...")
            cmd_start = ["powershell", "-Command", "Start-Service sshd"]
            subprocess.run(cmd_start, capture_output=True, text=True)

            # Verify that the service is running
            result = subprocess.run(["sc", "query", "sshd"], capture_output=True, text=True)
            if "RUNNING" in result.stdout:
                print("OpenSSH installed and running successfully.")
                return True
            else:
                print("Failed to start sshd service. Output:", result.stdout)
                return False

        except Exception as e:
            print(f"An error occurred during OpenSSH installation: {e}")
            return False
        finally:
            # Clean up the temporary directory
            if 'tmp_dir' in locals() and os.path.exists(tmp_dir):
                shutil.rmtree(tmp_dir)

    elif system == "Linux":
        try:
            logger.info("Checking OpenSSH installation on Linux")

            # First check if sshd service exists
            service_check = subprocess.run(
                ["systemctl", "status", "sshd"],
                capture_output=True,
                text=True
            )

            # If service doesn't exist, try ssh service instead (some Linux distros use different name)
            if service_check.returncode != 0:
                service_check = subprocess.run(
                    ["systemctl", "status", "ssh"],
                    capture_output=True,
                    text=True
                )

            if "running" in service_check.stdout:
                logger.info("SSH server is already running on Linux")
                return True

            logger.info("SSH server not running, checking if installed...")

            # Check if package is installed
            pkg_check = subprocess.run(
                ["dpkg", "-s", "openssh-server"],
                capture_output=True,
                text=True
            )

            if "Status: install ok installed" in pkg_check.stdout:
                logger.info("OpenSSH server is installed but not running, attempting to start...")
                # Try to start the service
                try:
                    start_result = subprocess.run(
                        ["sudo", "systemctl", "start", "ssh"],
                        capture_output=True,
                        text=True
                    )
                    if start_result.returncode == 0:
                        logger.info("Successfully started SSH server")
                        return True
                    else:
                        logger.error(f"Failed to start SSH server: {start_result.stderr}")
                        return False
                except Exception as e:
                    logger.error(f"Error starting SSH server: {e}")
                    return False
            else:
                logger.info("OpenSSH server not installed, attempting to install...")
                # Install the package
                try:
                    # Update package index first
                    update_result = subprocess.run(
                        ["sudo", "apt-get", "update"],
                        capture_output=True,
                        text=True
                    )

                    if update_result.returncode != 0:
                        logger.warning(f"Warning: apt-get update failed: {update_result.stderr}")

                    # Install openssh-server
                    install_result = subprocess.run(
                        ["sudo", "apt-get", "install", "-y", "openssh-server"],
                        capture_output=True,
                        text=True
                    )

                    if install_result.returncode == 0:
                        logger.info("Successfully installed OpenSSH server")

                        # Start the service
                        start_result = subprocess.run(
                            ["sudo", "systemctl", "start", "ssh"],
                            capture_output=True,
                            text=True
                        )

                        if start_result.returncode == 0:
                            logger.info("Successfully started SSH server")
                            return True
                        else:
                            logger.error(f"Failed to start SSH server: {start_result.stderr}")
                            return False
                    else:
                        logger.error(f"Failed to install OpenSSH server: {install_result.stderr}")
                        return False
                except Exception as e:
                    logger.error(f"Error installing OpenSSH server: {e}")
                    return False

        except Exception as e:
            logger.error(f"Error checking OpenSSH on Linux: {e}")
            return False

    elif system == "Darwin":  # macOS
        try:
            logger.info("Checking OpenSSH installation on macOS")

            # On macOS, check if the SSH service is running
            service_check = subprocess.run(
                ["sudo", "launchctl", "list", "com.openssh.sshd"],
                capture_output=True,
                text=True
            )

            if service_check.returncode == 0:
                logger.info("SSH server is already running on macOS")
                return True

            logger.info("SSH server not running, attempting to start...")

            # Try to start the service (OpenSSH is pre-installed on macOS)
            try:
                start_result = subprocess.run(
                    ["sudo", "launchctl", "load", "-w", "/System/Library/LaunchDaemons/ssh.plist"],
                    capture_output=True,
                    text=True
                )

                if start_result.returncode == 0:
                    logger.info("Successfully started SSH server on macOS")
                    return True
                else:
                    logger.error(f"Failed to start SSH server on macOS: {start_result.stderr}")
                    return False
            except Exception as e:
                logger.error(f"Error starting SSH server on macOS: {e}")
                return False

        except Exception as e:
            logger.error(f"Error checking OpenSSH on macOS: {e}")
            return False

    else:
        logger.warning(f"Unknown platform: {system}, cannot verify OpenSSH installation")
        return False


def ensure_sshd_running():
    """
    Cross-platform function to ensure the sshd service is running.

    Returns:
        bool: True if sshd is running, False otherwise
    """
    system = get_platform()
    logger.info(f"Ensuring SSH server is running on {system}")

    if system == "Windows":
        # Original Windows implementation
        try:
            # Check the current status of the sshd service
            result = subprocess.run(["sc", "query", "sshd"], capture_output=True, text=True)
            if "RUNNING" in result.stdout:
                logger.info("sshd is already running on Windows.")
                return True
            else:
                logger.info("sshd is not running on Windows. Attempting to start it...")
                # Attempt to start sshd using PowerShell
                start_cmd = ["powershell", "-Command", "Start-Service sshd"]
                subprocess.run(start_cmd, capture_output=True, text=True)
                # Re-check the service status
                result = subprocess.run(["sc", "query", "sshd"], capture_output=True, text=True)
                if "RUNNING" in result.stdout:
                    logger.info("sshd started successfully on Windows.")
                    return True
                else:
                    logger.error("Failed to start sshd on Windows. Service output:", result.stdout)
                    return False
        except Exception as e:
            logger.error(f"Exception while ensuring sshd is running on Windows: {e}")
            return False

    elif system == "Linux":
        try:
            # First try the 'sshd' service name
            service_check = subprocess.run(
                ["systemctl", "is-active", "sshd"],
                capture_output=True,
                text=True
            )

            # If that fails, try the 'ssh' service name (used by Debian/Ubuntu)
            if service_check.returncode != 0:
                service_check = subprocess.run(
                    ["systemctl", "is-active", "ssh"],
                    capture_output=True,
                    text=True
                )

            if "active" in service_check.stdout:
                logger.info("SSH server is already running on Linux")
                return True

            logger.info("SSH server not running on Linux. Attempting to start it...")

            # Try both service names
            start_result = subprocess.run(
                ["sudo", "systemctl", "start", "ssh"],
                capture_output=True,
                text=True
            )

            if start_result.returncode != 0:
                # Try alternative service name
                start_result = subprocess.run(
                    ["sudo", "systemctl", "start", "sshd"],
                    capture_output=True,
                    text=True
                )

            if start_result.returncode == 0:
                logger.info("Successfully started SSH server on Linux")
                return True
            else:
                logger.error(f"Failed to start SSH server on Linux: {start_result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Exception while ensuring sshd is running on Linux: {e}")
            return False

    elif system == "Darwin":  # macOS
        try:
            # Check if the SSH service is running
            service_check = subprocess.run(
                ["launchctl", "list", "com.openssh.sshd"],
                capture_output=True,
                text=True
            )

            if service_check.returncode == 0:
                logger.info("SSH server is already running on macOS")
                return True

            logger.info("SSH server not running on macOS. Attempting to start it...")

            # Start the service
            start_result = subprocess.run(
                ["sudo", "launchctl", "load", "-w", "/System/Library/LaunchDaemons/ssh.plist"],
                capture_output=True,
                text=True
            )

            if start_result.returncode == 0:
                logger.info("Successfully started SSH server on macOS")
                return True
            else:
                logger.error(f"Failed to start SSH server on macOS: {start_result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Exception while ensuring sshd is running on macOS: {e}")
            return False

    else:
        logger.warning(f"Unknown platform: {system}, cannot ensure sshd is running")
        return False


# ===== END OPENSSH MANAGEMENT MODIFICATIONS =====


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


# ===== START FIREWALL MANAGEMENT MODIFICATIONS =====
def check_firewall_rule_exists(rule_name):
    """
    Cross-platform function to check if a firewall rule with the given name exists.

    Args:
        rule_name (str): The name of the rule to check

    Returns:
        bool: True if the rule exists, False otherwise
    """
    system = get_platform()
    logger.info(f"Checking if firewall rule '{rule_name}' exists on {system}")

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
                logger.info(f"Rule '{rule_name}' already exists on Windows!")
                return True
            else:
                logger.info(f"Rule '{rule_name}' does not exist yet on Windows.")
                return False
        except Exception as e:
            logger.error(f"Error checking if rule exists on Windows: {str(e)}")
            # If there's an error, assume the rule doesn't exist to be safe
            return False

    elif system == "Linux":
        try:
            # For Linux, we'll check iptables rules
            # In Linux, rule names aren't a standard concept, so we'll search based on port and protocol
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
                                logger.info(f"Found matching rule for {protocol} port {port} in {chain} chain")
                                return True

                    logger.info(f"No matching rule found for {protocol} port {port} in {chain} chain")
                    return False
                else:
                    logger.error(f"Error executing iptables command: {process.stderr}")
                    return False
            else:
                logger.error(f"Invalid rule name format: {rule_name}")
                return False

        except Exception as e:
            logger.error(f"Error checking if rule exists on Linux: {str(e)}")
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
                            logger.info(f"Found matching rule for {protocol} port {port} in {direction} direction")
                            return True

                    logger.info(f"No matching rule found for {protocol} port {port} in {direction} direction")
                    return False
                else:
                    logger.error(f"Error executing pfctl command: {process.stderr}")
                    return False
            else:
                logger.error(f"Invalid rule name format: {rule_name}")
                return False

        except Exception as e:
            logger.error(f"Error checking if rule exists on macOS: {str(e)}")
            return False

    else:
        logger.warning(f"Unknown platform: {system}, cannot check firewall rules")
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
    logger.info(f"Adding firewall rule for port {port} ({protocol}) in {direction} direction on {system}")

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

        logger.info(f"Adding {direction}bound rule for port {port} ({name})...")

        try:
            # Execute the command
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            if process.returncode == 0:
                logger.info(f"SUCCESS: {direction}bound rule for port {port} ({name}) added on Windows")
                return True, f"{direction}bound rule for port {port} added successfully."
            else:
                logger.error(f"ERROR: Failed to add {direction}bound rule on Windows: {process.stderr}")
                return False, f"Failed to add {direction}bound rule: {process.stderr}"

        except Exception as e:
            logger.error(f"EXCEPTION: Error adding firewall rule on Windows: {str(e)}")
            return False, f"Error adding firewall rule: {str(e)}"

    elif system == "Linux":
        try:
            # Generate rule identifier for Linux
            direction_text = "Inbound" if direction == "in" else "Outbound"
            rule_id = f"AIAgent_{direction_text}_{protocol}_{port}"

            logger.info(f"Adding {direction_text} rule for {protocol} port {port} on Linux...")

            # First check if the rule already exists
            if check_firewall_rule_exists(rule_id):
                logger.info(f"Rule already exists for {protocol} port {port}")
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
                    logger.info("Using UFW firewall")

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
                        logger.info(f"Successfully added {direction_text} rule for {protocol} port {port} using UFW")
                        return True, f"{direction_text} rule for {protocol} port {port} added successfully using UFW."
                    else:
                        logger.error(f"Failed to add rule using UFW: {ufw_result.stderr}")
                        # Fall back to iptables if UFW fails
                else:
                    logger.info("UFW not active, trying iptables")
            except Exception as e:
                logger.warning(f"UFW not available: {e}")

            # Try iptables as fallback
            logger.info("Using iptables firewall")

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
                logger.info(f"Successfully added {direction_text} rule for {protocol} port {port} using iptables")

                # Try to make the rule persistent (varies by distribution)
                try:
                    # For Debian/Ubuntu
                    save_cmd = ["sudo", "sh", "-c", "iptables-save > /etc/iptables/rules.v4"]
                    save_result = subprocess.run(save_cmd, capture_output=True, text=True, shell=True)

                    if save_result.returncode == 0:
                        logger.info("Successfully saved iptables rules")
                    else:
                        logger.warning(f"Could not save iptables rules: {save_result.stderr}")
                        # Try alternative method
                        alt_save_cmd = ["sudo", "sh", "-c", "iptables-save > /etc/iptables.rules"]
                        alt_save_result = subprocess.run(alt_save_cmd, capture_output=True, text=True, shell=True)

                        if alt_save_result.returncode == 0:
                            logger.info("Successfully saved iptables rules (alternative method)")
                        else:
                            logger.warning("Could not save iptables rules persistently. Rules will be lost on reboot.")
                except Exception as e:
                    logger.warning(f"Could not make iptables rules persistent: {e}")

                return True, f"{direction_text} rule for {protocol} port {port} added successfully using iptables."
            else:
                logger.error(f"Failed to add rule using iptables: {iptables_result.stderr}")
                return False, f"Failed to add firewall rule using iptables: {iptables_result.stderr}"

        except Exception as e:
            logger.error(f"Error adding firewall rule on Linux: {str(e)}")
            return False, f"Error adding firewall rule: {str(e)}"

    elif system == "Darwin":  # macOS
        try:
            # Generate rule identifier for macOS
            direction_text = "Inbound" if direction == "in" else "Outbound"
            rule_id = f"AIAgent_{direction_text}_{protocol}_{port}"

            logger.info(f"Adding {direction_text} rule for {protocol} port {port} on macOS...")

            # First check if the rule already exists
            if check_firewall_rule_exists(rule_id):
                logger.info(f"Rule already exists for {protocol} port {port}")
                return True, f"Firewall rule for {protocol} port {port} already exists. No changes made."

            # macOS uses pfctl, which requires updating the pf.conf file

            # First, check if pf is enabled
            pf_status = subprocess.run(
                ["sudo", "pfctl", "-s", "info"],
                capture_output=True,
                text=True
            )

            if "Status: Enabled" not in pf_status.stdout:
                # Try to enable pf
                logger.info("Packet filter (pf) not enabled, attempting to enable it")
                enable_result = subprocess.run(
                    ["sudo", "pfctl", "-e"],
                    capture_output=True,
                    text=True
                )

                if enable_result.returncode != 0:
                    logger.error(f"Failed to enable packet filter: {enable_result.stderr}")
                    return False, "Failed to enable firewall (packet filter)"

            # Create a temporary rule file
            rule_content = f"# AI Agent rule for {protocol} port {port}\n"
            if direction == "in":
                rule_content += f"pass in proto {protocol.lower()} from any to any port {port}\n"
            else:
                rule_content += f"pass out proto {protocol.lower()} from any to any port {port}\n"

            temp_rule_file = "/tmp/ai_agent_pf_rule.conf"
            with open(temp_rule_file, "w") as f:
                f.write(rule_content)

            # Load the rule
            load_result = subprocess.run(
                ["sudo", "pfctl", "-f", temp_rule_file, "-a", "com.ai.agent"],
                capture_output=True,
                text=True
            )

            if load_result.returncode == 0:
                logger.info(f"Successfully added {direction_text} rule for {protocol} port {port} using pfctl")
                return True, f"{direction_text} rule for {protocol} port {port} added successfully."
            else:
                logger.error(f"Failed to add rule using pfctl: {load_result.stderr}")
                return False, f"Failed to add firewall rule: {load_result.stderr}"

        except Exception as e:
            logger.error(f"Error adding firewall rule on macOS: {str(e)}")
            return False, f"Error adding firewall rule: {str(e)}"

    else:
        logger.warning(f"Unknown platform: {system}, cannot add firewall rules")
        return False, f"Firewall configuration not supported on {system}"


# ===== END FIREWALL MANAGEMENT MODIFICATIONS =====

'''
def add_firewall_rule(port, protocol="TCP", direction="in", name=None, application=None):
    """
    Adds a firewall rule for the specified port and direction.

    Args:
        port (int): The port number to allow
        protocol (str): The protocol (TCP or UDP)
        direction (str): The direction of the rule ('in' or 'out')
        name (str, optional): Custom name for the rule
        application (str, optional): Path to application to restrict the rule to

    Returns:
        tuple: (success, message)
    """
    if platform.system() != "Windows":
        return False, "Firewall configuration only supported on Windows."

    # Validate direction
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
            print(f"SUCCESS: {direction}bound rule for port {port} ({name}) added")
            return True, f"{direction}bound rule for port {port} added successfully."
        else:
            print(f"ERROR: Failed to add {direction}bound rule: {process.stderr}")
            return False, f"Failed to add {direction}bound rule: {process.stderr}"

    except Exception as e:
        print(f"EXCEPTION: Error adding firewall rule: {str(e)}")
        return False, f"Error adding firewall rule: {str(e)}"
'''

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
        import urllib.request
        import urllib.error
    except ImportError:
        return "Error: urllib module not available"

    # Try each service until we get a valid response
    for service in ip_services:
        try:
            response = urllib.request.urlopen(service, timeout=3)
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


def get_current_username():
    """
    Retrieves the username of the currently logged-in user.
    Works across Windows, macOS, and Linux.
    Handles sudo elevation by returning the original user instead of root.
    """
    try:
        import os
        import getpass
        import platform

        system = platform.system()

        # Handle sudo case on Linux/macOS
        if system in ["Linux", "Darwin"]:
            # Check for sudo environment variables
            if 'SUDO_USER' in os.environ:
                return os.environ['SUDO_USER']  # Return the original user when running with sudo

            # Alternative sudo detection for some environments
            if os.geteuid() == 0:  # Running as root
                # Try to get the real user from environment
                for env_var in ['SUDO_USER', 'LOGNAME', 'USER', 'USERNAME']:
                    if env_var in os.environ and os.environ[env_var] != 'root':
                        return os.environ[env_var]

        # Standard username detection (works on all platforms)
        username = getpass.getuser()

        # If that doesn't work, try environment variables (backup method)
        if not username or username == 'root':
            # Windows typically uses USERNAME
            if system == "Windows":
                username = os.environ.get('USERNAME', '')
            # Unix/Linux/Mac typically use USER
            else:
                username = os.environ.get('USER', '')

                # One last check for root username
                if username == 'root' and 'SUDO_USER' in os.environ:
                    username = os.environ['SUDO_USER']

        return username
    except Exception as e:
        logger.error(f"Error getting username: {e}")
        return f"Error getting username: {str(e)}"


def generate_sftp_qr_code(host, port, username, password, remote_dir):
    """
    Generates a QR code containing SFTP connection information.
    Returns the QR code as bytes for a PySimpleGUI Image element.
    """
    # Process remote_dir to make it SFTP compatible
    if remote_dir and ":" in remote_dir:
        # For Windows paths like "C:\path" or "C:/path"
        # Split at colon and take the second part
        remote_dir = remote_dir.split(":", 1)[1]

        # Ensure path uses forward slashes and starts with /
        remote_dir = remote_dir.replace("\\", "/")
        if not remote_dir.startswith("/"):
            remote_dir = "/" + remote_dir

    # Create a dictionary with the connection information
    connection_data = {
        "host": host,
        "port": port,
        "username": username,
        "password": password,
        "remote_dir": remote_dir
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


def show_sftp_qr_popup(qr_data, connection_info):
    """
    Shows a popup window with a larger SFTP QR code and connection information.
    Makes scanning easier for users.
    """
    # Process connection_info to display proper SFTP paths
    if ":" in connection_info and (", Dir: C:" in connection_info or ", Dir: D:" in connection_info):
        parts = connection_info.split(", Dir: ")
        path_part = parts[1]
        if ":" in path_part:
            transformed_path = path_part.split(":", 1)[1].replace("\\", "/")
            if not transformed_path.startswith("/"):
                transformed_path = "/" + transformed_path
            connection_info = parts[0] + ", Dir: " + transformed_path

    # Create layout for popup with a larger QR code display
    popup_layout = [
        [sg.Text("SFTP Connection QR Code", font=("Helvetica", 16, "bold"), justification="center")],
        [sg.Text("Scan this QR code with your Android app to configure SFTP", justification="center")],
        [sg.Image(data=qr_data)],
        [sg.Text(f"Connection Details: {connection_info}", justification="center")],
        [sg.Button("Copy to Clipboard", key="-COPY-"), sg.Button("Close", key="-CLOSE-")]
    ]

    # Create popup window
    popup = sg.Window("SFTP Connection", popup_layout, modal=True, finalize=True, element_justification='center')

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
    Tests if the server is reachable at the given host and port.
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
        return True, "Connection successful! Port is reachable."
    except Exception as e:
        return False, f"Connection failed: {str(e)}"


def test_sftp_connection(host, port, username, password, timeout=5):
    """
    Tests an SFTP connection with the given credentials.
    Returns (success, message) tuple.
    """

    try:
        import paramiko

        # Set up client
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Try to connect with a timeout
        client.connect(
            hostname=host,
            port=int(port),
            username=username,
            password=password,
            timeout=timeout
        )

        # Try to open SFTP session
        sftp = client.open_sftp()

        # Try to list files to verify permissions
        sftp.listdir('.')

        # Close connections
        sftp.close()
        client.close()

        return True, "SFTP connection successful - credentials are valid!"

    except ImportError:
        return False, "Missing paramiko library. Install with: pip install paramiko"
    except paramiko.AuthenticationException:
        return False, "Authentication failed - check username and password"
    except paramiko.SSHException as e:
        return False, f"SSH error: {str(e)}"
    except Exception as e:
        return False, f"Connection error: {str(e)}"
    finally:
        try:
            if 'client' in locals():
                client.close()
        except:
            pass



