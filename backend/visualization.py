#!/usr/bin/env python3

import json
import logging
import time
from typing import Dict, List

logger = logging.getLogger(__name__)


def export_nodes_json(nodes_data: List[Dict], json_file: str = "frontend/bitcoin_nodes.json") -> str:
    with open(json_file, 'w') as f:
        json.dump(nodes_data, f, indent=2)
    logger.info(f"Exported {len(nodes_data)} nodes to {json_file}")
    return json_file


def create_heatmap(nodes_data: List[Dict], output_file: str = "frontend/index.html", json_file: str = "frontend/bitcoin_nodes.json", load_once: bool = False) -> str:
    valid_nodes = [
        node for node in nodes_data
        if node.get('latitude') is not None 
        and node.get('longitude') is not None
        and -90 <= node['latitude'] <= 90
        and -180 <= node['longitude'] <= 180
    ]
    
    if not valid_nodes:
        logger.warning("No nodes with valid coordinates found")
        return None
    
    logger.info(f"Creating heatmap with {len(valid_nodes)} nodes")
    
    avg_lat = sum(node['latitude'] for node in valid_nodes) / len(valid_nodes)
    avg_lon = sum(node['longitude'] for node in valid_nodes) / len(valid_nodes)
    
    export_nodes_json(valid_nodes, json_file)
    
    unique_countries = len(set(node.get('country', '') for node in valid_nodes if node.get('country')))
    
    update_text = "Data loaded" if load_once else "Nodes will be updated every 10 seconds"
    
    if load_once:
        update_js_code = ""
    else:
        update_js_code = """
        function tryUpdateFromFile() {
            const loader = document.getElementById('update-loader');
            const updateText = document.getElementById('update-text');
            if (loader) loader.classList.remove('hidden');
            if (updateText) updateText.textContent = 'Updating nodes...';
            
            fetch('bitcoin_nodes.json?t=' + new Date().getTime())
                .then(response => {
                    if (!response.ok) throw new Error('Network response was not ok');
                    return response.json();
                })
                        .then(data => {
                    console.log('✓ Updated from server:', data.length, 'nodes');
                    loadNodes(data);
                        })
                        .catch(error => {
                    console.log('Using embedded data (server fetch failed):', error.message);
                    if (loader) loader.classList.add('hidden');
                    if (updateText) updateText.textContent = 'Nodes will be updated every 10 seconds';
                        });
                }
                
        setInterval(tryUpdateFromFile, 10000);
        
        setTimeout(tryUpdateFromFile, 2000);"""
    
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bitcoin Network Map</title>
    
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.3/dist/leaflet.css" />
    
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        html, body {{
            width: 100%;
            height: 100%;
            overflow: hidden;
        }}
        
        #map {{
            width: 100%;
            height: 100vh;
            position: fixed;
            top: 0;
            left: 0;
            z-index: 1;
        }}
        
        .stats-panel {{
            position: fixed;
            top: 20px;
            right: 20px;
            width: 280px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    z-index: 9999; 
                    border-radius: 12px; 
                    padding: 20px;
                    color: white;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        }}
        
        .stats-panel h3 {{
            margin: 0 0 15px 0;
            font-size: 18px;
            font-weight: 600;
            text-align: center;
            border-bottom: 2px solid rgba(255,255,255,0.3);
            padding-bottom: 10px;
        }}
        
        .stats-content {{
            background: rgba(255,255,255,0.15);
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 10px;
        }}
        
        .stats-content p {{
            margin: 5px 0;
            font-size: 14px;
        }}
        
        .stats-content span {{
            float: right;
            font-weight: 700;
        }}
        
        .loading {{
            margin: 10px 0 0 0;
            font-size: 11px;
            text-align: center;
            opacity: 0.8;
            font-style: italic;
            min-height: 20px;
        }}
        
        .loader {{
            display: inline-block;
            width: 12px;
            height: 12px;
            border: 2px solid rgba(255, 255, 255, 0.3);
            border-radius: 50%;
            border-top-color: white;
            animation: spin 0.8s linear infinite;
            margin-right: 6px;
            vertical-align: middle;
        }}
        
        @keyframes spin {{
            to {{ transform: rotate(360deg); }}
        }}
        
        .loader.hidden {{
            display: none;
        }}
    </style>
    </head>
<body>
    <div class="stats-panel">
        <h3>🌍 Bitcoin Network Mainnet</h3>
        <div class="stats-content">
            <p><b>Total Nodes:</b> <span id="node-count">{len(valid_nodes)}</span></p>
            <p><b>Countries:</b> <span id="country-count">{unique_countries}</span></p>
        </div>
        <p class="loading">
            <span class="loader hidden" id="update-loader"></span>
            <span id="update-text">{update_text}</span>
        </p>
    </div>
    
    <div id="map"></div>
    
    <script src="https://unpkg.com/leaflet@1.9.3/dist/leaflet.js"></script>
    <script src="https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js"></script>
    
    <script>
        const map = L.map('map', {{
            center: [{avg_lat}, {avg_lon}],
            zoom: 2,
            maxBounds: [[-90, -180], [90, 180]],
            worldCopyJump: false
        }});
        
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxZoom: 19
        }}).addTo(map);
        
        let heatmapLayer = null;
        let markersLayer = L.layerGroup().addTo(map);
        
        const nodeData = {json.dumps(valid_nodes, ensure_ascii=False)};
        
        function loadNodes(dataToUse = null) {{
            const data = dataToUse || nodeData;
            
            try {{
                    console.log('Loaded', data.length, 'nodes');
                                
                    document.getElementById('node-count').textContent = data.length;
                                    const countries = new Set(data.filter(n => n.country).map(n => n.country));
                    document.getElementById('country-count').textContent = countries.size;
                                
                                const heatData = data.map(node => [node.latitude, node.longitude, 1]);
                                
                    if (heatmapLayer) {{
                        map.removeLayer(heatmapLayer);
                    }}
                    
                                if (typeof L.heatLayer !== 'undefined') {{
                                    heatmapLayer = L.heatLayer(heatData, {{
                                        radius: 20,
                                        blur: 20,
                                        maxZoom: 18,
                                        gradient: {{
                                            0.2: 'blue',
                                            0.4: 'cyan', 
                                            0.6: 'lime',
                                            0.8: 'yellow',
                                            1.0: 'red'
                                        }},
                                        minOpacity: 0.3
                        }}).addTo(map);
                                }}
                                
                                    markersLayer.clearLayers();
                                    
                                    const nodesToShow = data.length <= 1000 ? data : data.slice(0, 1000);
                                    nodesToShow.forEach(node => {{
                                        const popupText = `
                                            <div style="font-family: monospace; font-size: 12px;">
                                                <b>📍 Node Information</b><hr style="margin: 5px 0;">
                                                <b>IP:</b> ${{node.ip || 'N/A'}}<br>
                                                <b>Port:</b> ${{node.port || 'N/A'}}<br>
                                                <b>Version:</b> ${{node.version || 'N/A'}}<br>
                                                <b>Country:</b> ${{node.country || 'N/A'}}<br>
                                                <b>City:</b> ${{node.city || 'N/A'}}<br>
                                                <b>User Agent:</b><br>
                                                <small>${{(node.user_agent || 'N/A').substring(0, 60)}}...</small>
                                            </div>
                                        `;
                                        
                                        L.circleMarker([node.latitude, node.longitude], {{
                                            radius: 4,
                                            color: '#ff4444',
                                            fillColor: '#ff6666',
                                            fill: true,
                                            fillOpacity: 0.6,
                                            weight: 1
                                        }}).bindPopup(popupText).addTo(markersLayer);
                                    }});
                                    
                                    if (data.length > 1000) {{
                                        console.log('Showing first 1000 markers for performance');
                                    }}
                    
                    const loader = document.getElementById('update-loader');
                    const updateText = document.getElementById('update-text');
                    if (loader) loader.classList.add('hidden');
                    if (updateText) updateText.textContent = '{update_text}';
            }} catch(error) {{
                console.error('Error processing nodes:', error);
                const loader = document.getElementById('update-loader');
                const updateText = document.getElementById('update-text');
                if (loader) loader.classList.add('hidden');
                if (updateText) updateText.textContent = 'Error processing data';
            }}
        }}
        
        loadNodes();
        
        {update_js_code}
        
        setTimeout(function() {{
            map.invalidateSize();
        }}, 100);
    </script>
</body>
</html>
    """
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    logger.info(f"Heatmap saved to {output_file}")
    return output_file


def create_statistics_plot(nodes_data: List[Dict], output_file: str = "bitcoin_nodes_stats.html") -> str:
    logger.info("Statistics plot creation not implemented")
    return None
