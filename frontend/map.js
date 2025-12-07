    const map = L.map('map', {
        center: [38.251518118932005, -18.133633932038858],
        zoom: 2,
        maxBounds: [[-90, -180], [90, 180]],
        worldCopyJump: false
    });
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19
    }).addTo(map);
    let heatmapLayer = null;
    let markersLayer = L.layerGroup().addTo(map);
    function loadNodes(dataToUse) {
        if (!dataToUse || !Array.isArray(dataToUse)) {
            console.error('Invalid or missing data provided to loadNodes');
            return;
        }
        const data = dataToUse;
        try {
                console.log('Loaded', data.length, 'nodes');
                const nodeCountEl = document.getElementById('node-count');
                if (nodeCountEl) {
                    nodeCountEl.textContent = data.length;
                }
                const countries = new Set(data.filter(n => n.country && n.country.trim()).map(n => n.country));
                const countryCountEl = document.getElementById('country-count');
                if (countryCountEl) {
                    countryCountEl.textContent = countries.size;
                }
                            const heatData = data.map(node => [node.latitude, node.longitude, 1]);
                if (heatmapLayer) {
                    map.removeLayer(heatmapLayer);
                }
                            if (typeof L.heatLayer !== 'undefined') {
                                heatmapLayer = L.heatLayer(heatData, {
                                    radius: 20,
                                    blur: 20,
                                    maxZoom: 18,
                                    gradient: {
                                        0.2: 'blue',
                                        0.4: 'cyan',
                                        0.6: 'lime',
                                        0.8: 'yellow',
                                        1.0: 'red'
                                    },
                                    minOpacity: 0.3
                    }).addTo(map);
                            }
                                markersLayer.clearLayers();
                                const nodesToShow = data.length <= 1000 ? data : data.slice(0, 1000);
                                nodesToShow.forEach(node => {
                                    const popupText = `
                                        <div style="font-family: monospace; font-size: 12px;">
                                            <b>📍 Node Information</b><hr style="margin: 5px 0;">
                                            <b>IP:</b> ${node.ip || 'N/A'}<br>
                                            <b>Port:</b> ${node.port || 'N/A'}<br>
                                            <b>Version:</b> ${node.version || 'N/A'}<br>
                                            <b>Country:</b> ${node.country || 'N/A'}<br>
                                            <b>City:</b> ${node.city || 'N/A'}<br>
                                            <b>User Agent:</b><br>
                                            <small>${(node.user_agent || 'N/A').substring(0, 60)}...</small>
                                        </div>
                                    `;
                                    L.circleMarker([node.latitude, node.longitude], {
                                        radius: 4,
                                        color: '#ff4444',
                                        fillColor: '#ff6666',
                                        fill: true,
                                        fillOpacity: 0.6,
                                        weight: 1
                                    }).bindPopup(popupText).addTo(markersLayer);
                                });
                                if (data.length > 1000) {
                                    console.log('Showing first 1000 markers for performance');
                                }
                const loader = document.getElementById('update-loader');
                const updateText = document.getElementById('update-text');
                if (loader) loader.classList.add('hidden');
                if (updateText) updateText.textContent = 'Data loaded';
        } catch(error) {
            console.error('Error processing nodes:', error);
            const loader = document.getElementById('update-loader');
            const updateText = document.getElementById('update-text');
            if (loader) loader.classList.add('hidden');
            if (updateText) updateText.textContent = 'Error loading data';
        }
    }
    fetch('bitcoin_nodes.json')
        .then(response => {
            if (!response.ok) throw new Error('Network response was not ok');
            return response.json();
        })
        .then(data => {
            console.log('✓ Loaded', data.length, 'nodes from file');
            loadNodes(data);
        })
        .catch(error => {
            console.error('Error loading data:', error.message);
            console.error('Failed to load bitcoin_nodes.json. Please ensure the file exists.');
            const nodeCountEl = document.getElementById('node-count');
            if (nodeCountEl) {
                nodeCountEl.textContent = 'Error loading data';
            }
        });
    setTimeout(function() {
        map.invalidateSize();
    }, 100);
