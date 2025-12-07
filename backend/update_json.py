#!/usr/bin/env python3

import sys
import os

backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

from database import NodeDatabase
from visualization import export_nodes_json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def update_json_from_db(db_path: str = "backend/bitcoin_nodes.db", json_file: str = "frontend/bitcoin_nodes.json"):
    db = NodeDatabase(db_path)
    nodes = db.get_nodes_with_location()
    
    if nodes:
        export_nodes_json(nodes, json_file)
        logger.info(f"Updated {json_file} with {len(nodes)} nodes")
        return len(nodes)
    else:
        logger.warning("No nodes found in database")
        return 0


if __name__ == "__main__":
    update_json_from_db()

