# Bitcoin Node Crawler and Heatmap

A Python-based Bitcoin network crawler that discovers Bitcoin **Mainnet** nodes, collects their information, and visualizes them on an interactive world map heatmap.

## Features

- **Bitcoin P2P Protocol Implementation**: Implements Bitcoin protocol messages from scratch
- **Async Crawling**: Uses asyncio for concurrent connections (500+ nodes simultaneously)
- **IP Geolocation**: Automatically geolocates IP addresses to show nodes on a world map
- **Interactive Heatmap**: Creates interactive heatmaps showing node distribution worldwide
- **Static Frontend**: Frontend can be deployed as a static website

## Usage - Command Sequence

Follow these commands **in order** to set up and run the Bitcoin node crawler:

```bash
# Step 1: Install dependencies
pip install -r requirements.txt

# Step 2: Crawl Bitcoin nodes, get geolocation, store in database, update JSON
python3 main.py --max-nodes 1000 --create-heatmap

# Step 3: Update JSON file with ALL nodes from database (not just new ones)
python3 -m backend.update_json

# Step 4: Start HTTP server on http://localhost:8000 (Ctrl+C to stop)
python3 start_live_map.py
```

Open this link in your browser: http://localhost:8002/index.html

## License

This project is for educational purposes. Use responsibly and respect Bitcoin network resources.
