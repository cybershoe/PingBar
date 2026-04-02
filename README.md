# PingBar

A macOS menu bar application for monitoring network connectivity through continuous ping monitoring. PingBar provides at-a-glance visibility into your connection quality with color-coded status indicators and customizable ping targets.

## Features

- **Background Network Monitoring**: Continuously checks multiple ping targets
- **Menu Bar Integration**: Lives in your macOS menu bar for always-visible network status
- **Color-coded Status Indicators**: Visual feedback with different colors based on latency and packet loss thresholds
  - Normal: Ping <80ms, 0% packet loss
  - Yellow: Ping 80-500 ms, 0.1-5% packet loss
  - Orange: Ping 500-1000 ms, 5-25% packet loss
  - Red: Ping > 1000 ms, > 25% packet loss  
- **Customizable Targets**: By default, PingBar checks 2 Google DNS and 2 Cloudflare DNS targets, but you can add or remove addresses as desired
- **Outlier Filtering**: Discards anomalous results for more accurate measurements; you care about your connection quality, not a brief outage of one of the ping targets.

## Usage

1. **Starting**: Launch PingBar and it will appear in your menu bar
2. **Monitoring**: The icon shows current network status with color coding
3. **Pausing**: Use the "Pause" menu item to temporarily stop monitoring
4. **Configuration**: Access "Ping targets" to modify which servers to monitor

### Customizing Targets

1. Click the PingBar icon in your menu bar
2. Select "Ping targets"
3. Enter comma-separated IP addresses in the dialog
4. Click "Save" to apply changes

**Note**: Only IPv4 addresses are currently supported.

## Build from source

### Requirements

- macOS 10.14 or later
- Python 3.8 or later

### Dependencies

Install the required Python packages:

```bash
pip install -r requirements.txt
```

Required packages:
- `rumps`: For macOS menu bar application framework
- `icmplib`: For network ping functionality
- `pyobjc`: For macOS system integration

### Building the Application

To create a standalone macOS application bundle:

```bash
python setup.py py2app
```

This will create a `dist/PingBar.app` bundle that can be moved to your Applications folder.

### Running from Source

For development or testing:

```bash
python main.py
```

### Debug Mode

Enable debug output by setting the `LOGLEVEL` environment variable to `INFO` or `DEBUG`

```bash
LOGLEVEL=DEBUG python main.py
```

---

For questions, issues, or feature requests, please use the GitHub issue tracker.
