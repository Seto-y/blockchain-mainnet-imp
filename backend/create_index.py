#!/usr/bin/env python3

from database import NodeDatabase
from visualization import create_heatmap, export_nodes_json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_index_html(db_path: str = "backend/bitcoin_nodes.db", output_file: str = "frontend/index.html"):
    db = NodeDatabase(db_path)
    nodes = db.get_nodes_with_location()
    
    if not nodes:
        logger.warning("No nodes with location data found in database")
        logger.info("Run the crawler first to collect data")
        return None
    
    logger.info(f"Found {len(nodes)} TOTAL nodes with location data (ALL nodes: old + new)")
    
    json_file = "frontend/bitcoin_nodes.json"
    export_nodes_json(nodes, json_file)
    
    heatmap_file = create_heatmap(nodes, output_file, json_file, load_once=True)
    
    logger.info(f"Index page created: {output_file}")
    logger.info(f"  - Total nodes displayed: {len(nodes)} (ALL nodes from database, not just new ones)")
    logger.info(f"  - Countries: {len(set(node.get('country', '') for node in nodes if node.get('country')))}")
    
    return output_file


if __name__ == "__main__":
    create_index_html()

