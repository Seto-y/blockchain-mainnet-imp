import sqlite3
import logging
from typing import List, Dict, Optional
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NodeDatabase:
    def __init__(self, db_path: str = "backend/bitcoin_nodes.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip TEXT NOT NULL,
                port INTEGER NOT NULL,
                version INTEGER,
                services INTEGER,
                user_agent TEXT,
                timestamp TEXT,
                peers_discovered INTEGER,
                latitude REAL,
                longitude REAL,
                country TEXT,
                city TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(ip, port)
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_ip_port ON nodes(ip, port)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_country ON nodes(country)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON nodes(timestamp)')
        
        conn.commit()
        conn.close()
        logger.info(f"Database initialized at {self.db_path}")
    
    def insert_node(self, node_data: Dict) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO nodes 
                (ip, port, version, services, user_agent, timestamp, peers_discovered, latitude, longitude, country, city)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                node_data.get('ip'),
                node_data.get('port'),
                node_data.get('version'),
                node_data.get('services'),
                node_data.get('user_agent'),
                node_data.get('timestamp'),
                node_data.get('peers_discovered'),
                node_data.get('latitude'),
                node_data.get('longitude'),
                node_data.get('country'),
                node_data.get('city')
            ))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error inserting node: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def insert_nodes_batch(self, nodes_data: List[Dict]):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.executemany('''
                INSERT OR REPLACE INTO nodes 
                (ip, port, version, services, user_agent, timestamp, peers_discovered, latitude, longitude, country, city)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', [(
                node.get('ip'),
                node.get('port'),
                node.get('version'),
                node.get('services'),
                node.get('user_agent'),
                node.get('timestamp'),
                node.get('peers_discovered'),
                node.get('latitude'),
                node.get('longitude'),
                node.get('country'),
                node.get('city')
            ) for node in nodes_data])
            conn.commit()
            logger.info(f"Inserted {len(nodes_data)} nodes into database")
        except Exception as e:
            logger.error(f"Error inserting nodes batch: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def get_all_nodes(self) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM nodes')
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_nodes_with_location(self) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM nodes WHERE latitude IS NOT NULL AND longitude IS NOT NULL')
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_statistics(self) -> Dict:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM nodes')
        total_nodes = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM nodes WHERE latitude IS NOT NULL')
        nodes_with_location = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT country) FROM nodes WHERE country IS NOT NULL')
        unique_countries = cursor.fetchone()[0]
        
        cursor.execute('SELECT AVG(version) FROM nodes WHERE version IS NOT NULL')
        avg_version = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_nodes': total_nodes,
            'nodes_with_location': nodes_with_location,
            'unique_countries': unique_countries,
            'average_version': avg_version
        }

