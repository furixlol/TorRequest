# Tor Request Handler

A high-performance Python tool for sending HTTP requests through the Tor network, providing robust privacy, IP rotation, and advanced session management for secure web scraping and data collection.

<div align="center">
  <img src="https://github.com/TheTorProject/tor-media/raw/master/Tor%20Logo/Purple.png" alt="Tor Logo" width="120"/>
</div>

---

## Features

- 🚀 Fast, concurrent HTTP requests via the Tor network  
- 🔄 Automatic IP rotation and session management  
- 💾 Built-in caching of Tor exit nodes for efficiency  
- 🔒 Thread-safe, multi-session architecture  
- 🛠️ Simple CLI for batch requests  
- 🧩 Easy integration into your own Python projects  

---

## Visual Overview

<div align="center">
  <img src="https://files.catbox.moe/7ku84v.png" alt="Tor Request Process" width="600"/>
</div>

---

## Quickstart

### Prerequisites

- Python 3.8 or higher
- [Tor service](https://www.torproject.org/download/) running locally (default port 9050)
- `pip` for installing dependencies

### Installation

```bash
git clone https://github.com/yourusername/tor-request-handler.git
cd tor-request-handler
pip install -r requirements.txt
```

### Usage

1. **Start the Tor service** on your machine (ensure it's running on port 9050).
2. **Run the script:**

```bash
python tor_request.py
```

3. **Follow the prompts:**
   - Enter the number of requests to send
   - Enter the target domain (e.g., `example.com`)

The tool will automatically manage Tor sessions, rotate IPs, and display the status of each request.

---

## Example

```text
Enter the number of requests to send: 5
Enter the target domain (e.g., example.com): example.com

Starting 5 requests to https://example.com using 5 threads...
Thread 1 - Using IP: 185.220.101.1 with Port: 12345
Thread 1 - Status Code: 200
Thread 1 - Response Length: 1256 bytes
...
```

---

## Integrate in Your Project

You can import and use the `TorSessionManager` class in your own Python scripts:

```python
from tor_request import TorSessionManager

manager = TorSessionManager()
manager.prepare_sessions(3)
session, ip, port = manager.get_next_session()
response = session.get("https://example.com")
print(response.text)
```

---

## Requirements

- Python 3.8+
- [stem](https://stem.torproject.org/)
- [requests](https://docs.python-requests.org/)
- [PySocks](https://pypi.org/project/PySocks/)
- Tor service running locally

All dependencies are listed in `requirements.txt`.

---

## Security

All requests are routed through the Tor network for maximum privacy and anonymity. The tool supports automatic IP rotation and session isolation.

---

## License

MIT License. See [LICENSE](LICENSE) for details.
