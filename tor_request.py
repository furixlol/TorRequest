from rich.console import Console
from rich.prompt import Prompt
from rich.text import Text
from rich.progress import Progress
from rich.panel import Panel
from rich.align import Align
from rich.style import Style
from rich import box
import requests
import time
import os
import socket
import threading
import random
import json
from concurrent.futures import ThreadPoolExecutor
from stem import Signal
from stem.control import Controller
from queue import Queue

console = Console()

ascii_art = r'''
 /$$$$$$$$ /$$$$$$  /$$$$$$$        /$$$$$$$  /$$$$$$$$  /$$$$$$  /$$   /$$ /$$$$$$$$  /$$$$$$  /$$$$$$$$
|__  $$__//$$__  $$| $$__  $$      | $$__  $$| $$_____/ /$$__  $$| $$  | $$| $$_____/ /$$__  $$|__  $$__/
   | $$  | $$  \ $$| $$  \ $$      | $$  \ $$| $$      | $$  \ $$| $$  | $$| $$      | $$  \__/   | $$   
   | $$  | $$  | $$| $$$$$$$/      | $$$$$$$/| $$$$$   | $$  | $$| $$  | $$| $$$$$   |  $$$$$$    | $$   
   | $$  | $$  | $$| $$__  $$      | $$__  $$| $$__/   | $$  | $$| $$  | $$| $$__/    \____  $$   | $$   
   | $$  | $$  | $$| $$  \ $$      | $$  \ $$| $$      | $$/$$ $$| $$  | $$| $$       /$$  \ $$   | $$   
   | $$  |  $$$$$$/| $$  | $$      | $$  | $$| $$$$$$$$|  $$$$$$/|  $$$$$$/| $$$$$$$$|  $$$$$$/   | $$   
   |__/   \______/ |__/  |__/      |__/  |__/|________/ \____ $$$ \______/ |________/ \______/    |__/   
                                                             \__/                                        
                                                                                                         
                                                                                                         
'''

def print_ascii_gradient():
    gradient_colors = [
        "#ff0000", "#ff1919", "#ff3232", "#ff4b4b", "#ff6464", "#ff7d7d", "#ff9696", "#ffafaf", "#ffc8c8", "#ffe0e0"
    ]
    lines = ascii_art.splitlines()
    for i, line in enumerate(lines):
        color = gradient_colors[min(i, len(gradient_colors)-1)]
        console.print(Align.center(Text(line, style=Style(color=color, bold=True))))

class TorSessionManager:
    def __init__(self):
        self.used_ips = set()
        self.valid_sessions = {}
        self.ip_lock = threading.Lock()
        self.session_lock = threading.Lock()
        self.session_queue = Queue()
        self.cache_file = "tor_ip_cache.json"
        self.cached_sessions = {}
        self.load_cached_ips()
        self.initialize_cached_sessions()

    def load_cached_ips(self):
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    cached_data = json.load(f)
                    self.used_ips = set(cached_data.get('ips', []))
                    for ip_data in cached_data.get('sessions', []):
                        ip = ip_data.get('ip')
                        port = ip_data.get('port')
                        if ip and port:
                            self.cached_sessions[ip] = (port, None)
                console.print(Panel(f"Loaded {len(self.cached_sessions)} cached sessions from [bold]{self.cache_file}[/]", style="bold green", box=box.ROUNDED))
        except Exception as e:
            console.print(Panel(f"Error loading cached IPs: {str(e)}", style="bold red", box=box.ROUNDED))

    def initialize_cached_sessions(self):
        console.print(Panel("Initializing cached sessions...", style="bold magenta", box=box.ROUNDED))
        valid_sessions = {}
        for ip, (port, _) in list(self.cached_sessions.items()):
            session = self.create_fresh_session()
            if session and self.validate_session(session):
                valid_sessions[ip] = (port, session)
                console.print(f"[green]Initialized cached session - IP: [bold]{ip}[/], Port: [bold]{port}[/]")
            else:
                if session:
                    session.close()
                del self.cached_sessions[ip]
                console.print(f"[yellow]Removed invalid cached session - IP: [bold]{ip}[/]")
        self.cached_sessions = valid_sessions
        self.save_cached_ips()
        console.print(Panel(f"Successfully initialized {len(self.cached_sessions)} valid sessions", style="bold green", box=box.ROUNDED))

    def save_cached_ips(self):
        try:
            with open(self.cache_file, 'w') as f:
                sessions_data = []
                for ip, (port, _) in self.cached_sessions.items():
                    sessions_data.append({'ip': ip, 'port': port})
                json.dump({
                    'ips': list(self.used_ips),
                    'sessions': sessions_data
                }, f, indent=2)
        except Exception as e:
            console.print(Panel(f"Error saving cached IPs: {str(e)}", style="bold red", box=box.ROUNDED))

    def force_new_identity(self):
        try:
            with Controller.from_port(port=9051) as controller:
                controller.authenticate()
                controller.signal(Signal.NEWNYM)
                time.sleep(5)
                return True
        except Exception as e:
            console.print(Panel(f"Error forcing new identity: {str(e)}", style="bold red", box=box.ROUNDED))
            return False

    def create_fresh_session(self):
        try:
            session = requests.Session()
            session.proxies = {
                'http': 'socks5h://127.0.0.1:9050',
                'https': 'socks5h://127.0.0.1:9050'
            }
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
            }
            session.headers.update(headers)
            return session
        except Exception as e:
            console.print(Panel(f"Error creating fresh session: {str(e)}", style="bold red", box=box.ROUNDED))
            return None

    def get_ip_and_port(self, session):
        try:
            response = session.get('https://api.ipify.org?format=json', timeout=10)
            ip = response.json()['ip']
            port = random.randint(1024, 65535)
            return ip, port
        except:
            return "Could not get IP", None

    def validate_session(self, session):
        try:
            response = session.get('https://api.ipify.org?format=json', timeout=10)
            return response.status_code == 200
        except:
            return False

    def get_unique_valid_session(self):
        max_attempts = 10
        attempts = 0
        for ip, (port, session) in list(self.cached_sessions.items()):
            if ip not in [s[1] for s in self.session_queue.queue]:
                if session is None:
                    session = self.create_fresh_session()
                if session and self.validate_session(session):
                    self.used_ips.add(ip)
                    self.cached_sessions[ip] = (port, session)
                    return session, ip, port
                else:
                    if session:
                        session.close()
                    del self.cached_sessions[ip]
        while attempts < max_attempts:
            if not self.force_new_identity():
                continue
            session = self.create_fresh_session()
            if not session:
                continue
            ip, port = self.get_ip_and_port(session)
            if not ip or ip == "Could not get IP":
                session.close()
                continue
            with self.ip_lock:
                if ip not in self.used_ips and ip not in [s[1] for s in self.session_queue.queue]:
                    if self.validate_session(session):
                        self.used_ips.add(ip)
                        self.cached_sessions[ip] = (port, session)
                        self.save_cached_ips()
                        return session, ip, port
                    else:
                        session.close()
            console.print(f"[yellow]IP {ip} invalid or in use, getting new identity...")
            attempts += 1
            time.sleep(2)
        return None, None, None

    def prepare_sessions(self, num_sessions):
        console.print(Panel("Preparing Tor sessions...", style="bold magenta", box=box.ROUNDED))
        sessions_needed = num_sessions - len(self.cached_sessions)
        if sessions_needed <= 0:
            console.print(Panel(f"Using {num_sessions} existing cached sessions", style="green", box=box.ROUNDED))
            for i, (ip, (port, session)) in enumerate(list(self.cached_sessions.items())[:num_sessions]):
                self.session_queue.put((session, ip, port))
                console.print(f"[green]Using cached session {i+1}/{num_sessions} - IP: [bold]{ip}[/], Port: [bold]{port}[/]")
            return True
        console.print(Panel(f"Need {sessions_needed} new sessions in addition to {len(self.cached_sessions)} cached ones", style="yellow", box=box.ROUNDED))
        for ip, (port, session) in self.cached_sessions.items():
            self.session_queue.put((session, ip, port))
            console.print(f"[green]Using cached session - IP: [bold]{ip}[/], Port: [bold]{port}[/]")
        new_sessions_created = 0
        max_attempts = sessions_needed * 3
        attempts = 0
        while new_sessions_created < sessions_needed and attempts < max_attempts:
            session, ip, port = self.get_unique_valid_session()
            if session and ip:
                if ip not in [s[1] for s in self.session_queue.queue]:
                    self.session_queue.put((session, ip, port))
                    console.print(f"[bold green]Prepared new session {new_sessions_created + 1}/{sessions_needed} - IP: [bold]{ip}[/], Port: [bold]{port}[/]")
                    new_sessions_created += 1
                else:
                    console.print(f"[yellow]IP {ip} already in use, getting new identity...")
                    session.close()
                    if ip in self.cached_sessions:
                        del self.cached_sessions[ip]
            attempts += 1
        if new_sessions_created < sessions_needed:
            console.print(Panel(f"Warning: Only got {new_sessions_created} new sessions out of {sessions_needed} needed. Will try to get more sessions as needed during execution.", style="yellow", box=box.ROUNDED))
        return True

    def get_next_session(self):
        if not self.session_queue.empty():
            session, ip, port = self.session_queue.get()
            with self.ip_lock:
                self.cached_sessions[ip] = (port, session)
                self.save_cached_ips()
            return session, ip, port
        console.print(Panel("Session queue empty, getting new sessions...", style="yellow", box=box.ROUNDED))
        new_session, new_ip, new_port = self.get_unique_valid_session()
        if new_session and new_ip:
            with self.ip_lock:
                self.cached_sessions[new_ip] = (new_port, new_session)
                self.save_cached_ips()
            return new_session, new_ip, new_port
        return None, None, None

    def make_single_request(self, url, thread_id):
        max_retries = 3
        retry_count = 0
        while retry_count < max_retries:
            try:
                session, ip, port = self.get_next_session()
                if not session or not ip:
                    console.print(f"[red]Thread {thread_id} - No valid session available, getting new identity...")
                    session, ip, port = self.get_unique_valid_session()
                    if not session or not ip:
                        console.print(f"[red]Thread {thread_id} - Failed to get new identity")
                        return
                console.print(f"[bold blue]Thread {thread_id} - Using IP: [bold]{ip}[/] with Port: [bold]{port}[/]")
                response = session.get(url, timeout=30)
                if response.status_code == 429 or response.status_code >= 500:
                    console.print(f"[yellow]Thread {thread_id} - Rate limited or server error. Getting new identity...")
                    session.close()
                    with self.ip_lock:
                        self.used_ips.remove(ip)
                        if ip in self.cached_sessions:
                            del self.cached_sessions[ip]
                        self.save_cached_ips()
                    new_session, new_ip, new_port = self.get_unique_valid_session()
                    if new_session and new_ip:
                        session = new_session
                        ip = new_ip
                        port = new_port
                        retry_count += 1
                        continue
                    else:
                        console.print(f"[red]Thread {thread_id} - Failed to get new identity")
                        return
                console.print(f"[green]Thread {thread_id} - Status Code: [bold]{response.status_code}[/]")
                console.print(f"[cyan]Thread {thread_id} - Response Length: [bold]{len(response.text)}[/] bytes")
                with self.ip_lock:
                    self.cached_sessions[ip] = (port, session)
                    self.save_cached_ips()
                return
            except Exception as e:
                console.print(f"[red]Thread {thread_id} - Error occurred: {str(e)}")
                if session:
                    session.close()
                if ip:
                    with self.ip_lock:
                        self.used_ips.discard(ip)
                        if ip in self.cached_sessions:
                            del self.cached_sessions[ip]
                        self.save_cached_ips()
                console.print(f"[yellow]Thread {thread_id} - Getting new identity after error...")
                new_session, new_ip, new_port = self.get_unique_valid_session()
                if new_session and new_ip:
                    session = new_session
                    ip = new_ip
                    port = new_port
                    retry_count += 1
                    continue
                else:
                    console.print(f"[red]Thread {thread_id} - Failed to get new identity after error")
                    return
            finally:
                if session and ('response' in locals() and (response.status_code == 429 or response.status_code >= 500)):
                    session.close()
                if ip and ('response' in locals() and (response.status_code == 429 or response.status_code >= 500)):
                    with self.ip_lock:
                        self.used_ips.discard(ip)
                        if ip in self.cached_sessions:
                            del self.cached_sessions[ip]
                        self.save_cached_ips()

def check_tor_connection():
    try:
        sock = socket.socket()
        sock.settimeout(5)
        sock.connect(('127.0.0.1', 9050))
        sock.close()
        return True
    except:
        return False

def make_requests_with_tor():
    print_ascii_gradient()
    console.print(Align.center(Text("Tor Request Handler", style="bold white on red")))
    console.print(Align.center(Text("(Dev: github.com/furixlol)", style="bold white on dark_red")))
    console.print()
    if not check_tor_connection():
        console.print(Panel("Tor is not running. Please start Tor first.", style="bold red", box=box.ROUNDED))
        return
    try:
        num_requests = int(Prompt.ask("[bold cyan]Enter the number of requests to send", default="1"))
        if num_requests <= 0:
            console.print(Panel("Please enter a positive number of requests.", style="bold red", box=box.ROUNDED))
            return
    except ValueError:
        console.print(Panel("Please enter a valid number.", style="bold red", box=box.ROUNDED))
        return
    try:
        target_domain = Prompt.ask("[bold cyan]Enter the target domain (e.g., example.com)").strip()
        if not target_domain:
            console.print(Panel("Please enter a valid domain.", style="bold red", box=box.ROUNDED))
            return
        if not target_domain.startswith(('http://', 'https://')):
            target_domain = 'https://' + target_domain
        if not any(c in target_domain for c in ['.com', '.org', '.net', '.io', '.co', '.edu', '.gov']):
            console.print(Panel("Please enter a valid domain with proper TLD.", style="bold red", box=box.ROUNDED))
            return
    except Exception as e:
        console.print(Panel(f"Error processing domain: {str(e)}", style="bold red", box=box.ROUNDED))
        return
    session_manager = TorSessionManager()
    num_sessions = num_requests
    if not session_manager.prepare_sessions(num_sessions):
        console.print(Panel("Failed to prepare all sessions. Exiting...", style="bold red", box=box.ROUNDED))
        return
    urls = [target_domain] * num_requests
    num_threads = min(5, num_requests)
    console.print(Panel(f"Starting {num_requests} requests to [bold]{target_domain}[/] using {num_threads} threads...", style="bold magenta", box=box.ROUNDED))
    with Progress() as progress:
        task = progress.add_task("[green]Sending requests...", total=num_requests)
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = []
            for i, url in enumerate(urls, 1):
                future = executor.submit(session_manager.make_single_request, url, i)
                futures.append(future)
                progress.update(task, advance=1)
            for future in futures:
                future.result()

if __name__ == "__main__":
    make_requests_with_tor() 