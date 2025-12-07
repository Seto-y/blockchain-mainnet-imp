#!/usr/bin/env python3

import asyncio
import argparse
import logging
import sys
from typing import List, Tuple

from crawler import BitcoinNodeCrawler
from database import NodeDatabase
from geolocation import IPGeolocator
from visualization import create_heatmap, create_statistics_plot

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


BITCOIN_SEED_NODES = [
    ("seed.bitcoin.sipa.be", 8333),
    ("dnsseed.bluematt.me", 8333),
    ("dnsseed.bitcoin.dashjr.org", 8333),
    ("seed.bitcoinstats.com", 8333),
    ("seed.bitcoin.jonasschnelli.ch", 8333),
    ("seed.btc.petertodd.org", 8333),
    ("seed.bitcoin.sprovoost.nl", 8333),
    ("dnsseed.emzy.de", 8333),
    ("seed.bitcoin.wiz.biz", 8333),
]


async def fetch_bitnodes_seeds(max_nodes: int = 10000) -> List[Tuple[str, int]]:
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            try:
                logger.info("Fetching nodes from bitnodes.io API...")
                async with session.get('https://bitnodes.io/api/v1/snapshots/latest/', timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        nodes = []
                        if 'nodes' in data:
                            node_list = list(data['nodes'].keys())
                            logger.info(f"Found {len(node_list)} total nodes in bitnodes.io")
                            
                            for node_info in node_list[:max_nodes]:
                                try:
                                    ip, port = node_info.split(':')
                                    if ip and port:
                                        nodes.append((ip, int(port)))
                                except:
                                    continue
                        logger.info(f"Fetched {len(nodes)} nodes from bitnodes.io")
                        return nodes
            except Exception as e:
                logger.warning(f"Error fetching from bitnodes.io: {e}")
    except Exception as e:
        logger.debug(f"Could not fetch from bitnodes: {e}")
    return []


def resolve_dns_seeds() -> List[Tuple[str, int]]:
    import socket
    
    resolved_nodes = []
    for hostname, port in BITCOIN_SEED_NODES:
        try:
            try:
                addrinfo = socket.getaddrinfo(hostname, port, socket.AF_INET)
                for info in addrinfo:
                    ip = info[4][0]
                    resolved_nodes.append((ip, port))
                    logger.info(f"Resolved {hostname} -> {ip}:{port}")
            except:
                ip = socket.gethostbyname(hostname)
                resolved_nodes.append((ip, port))
                logger.info(f"Resolved {hostname} -> {ip}:{port}")
        except socket.gaierror as e:
            logger.warning(f"Could not resolve {hostname}: {e}")
    
    known_nodes = [
        ("104.248.9.1", 8333),
        ("159.89.232.238", 8333),
        ("178.128.221.177", 8333),
        ("188.166.162.1", 8333),
        ("46.101.99.250", 8333),
        ("51.15.79.92", 8333),
        ("52.9.214.54", 8333),
        ("54.36.126.36", 8333),
        ("88.198.62.148", 8333),
        ("95.179.135.131", 8333),
        ("138.68.60.56", 8333),
        ("167.99.83.20", 8333),
        ("167.172.42.94", 8333),
        ("178.62.193.19", 8333),
        ("206.189.58.82", 8333),
    ]
    
    resolved_nodes.extend(known_nodes)
    logger.info(f"Added {len(known_nodes)} known node IPs as seeds")
    
    return resolved_nodes


async def main():
    parser = argparse.ArgumentParser(
        description='Bitcoin Node Crawler and Heatmap Generator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --max-nodes 500 --create-heatmap
  python main.py --max-nodes 1000 --no-geolocation
  python main.py --heatmap-only
        """
    )
    
    parser.add_argument(
        '--max-nodes',
        type=int,
        default=1000,
        help='Maximum number of nodes to crawl (default: 1000)'
    )
    
    parser.add_argument(
        '--max-concurrent',
        type=int,
        default=500,
        help='Maximum concurrent connections (default: 500)'
    )
    
    parser.add_argument(
        '--timeout',
        type=float,
        default=10.0,
        help='Connection timeout in seconds (default: 10.0)'
    )
    
    parser.add_argument(
        '--no-geolocation',
        action='store_true',
        help='Skip IP geolocation step'
    )
    
    parser.add_argument(
        '--geolocation-rate-limit',
        type=float,
        default=0.15,
        help='Rate limit for geolocation API (seconds between requests, default: 0.15)'
    )
    
    parser.add_argument(
        '--create-heatmap',
        action='store_true',
        help='Create heatmap visualization after crawling'
    )
    
    parser.add_argument(
        '--heatmap-only',
        action='store_true',
        help='Only create heatmap from existing database (skip crawling)'
    )
    
    parser.add_argument(
        '--db-path',
        type=str,
        default='backend/bitcoin_nodes.db',
        help='Path to SQLite database (default: backend/bitcoin_nodes.db)'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default='frontend',
        help='Output directory for visualizations (default: frontend)'
    )
    
    args = parser.parse_args()
    
    db = NodeDatabase(args.db_path)
    
    if args.heatmap_only:
        logger.info("Heatmap-only mode: loading nodes from database")
        nodes = db.get_nodes_with_location()
        
        if not nodes:
            logger.error("No nodes with location data found in database")
            logger.info("Run the crawler first with --create-heatmap to collect data")
            return
        
        logger.info(f"Found {len(nodes)} nodes with location data")
        create_heatmap(nodes, f"{args.output_dir}/index.html", f"{args.output_dir}/bitcoin_nodes.json", load_once=True)
        logger.info("Heatmap created successfully!")
        return
    
    logger.info("=" * 60)
    logger.info("Step 1: Crawling Bitcoin Network")
    logger.info("=" * 60)
    
    seed_nodes = resolve_dns_seeds()
    
    try:
        bitnodes_seeds = await fetch_bitnodes_seeds(max_nodes=10000)
        if bitnodes_seeds:
            seed_nodes.extend(bitnodes_seeds)
            logger.info(f"Added {len(bitnodes_seeds)} nodes from bitnodes.io")
    except Exception as e:
        logger.debug(f"Could not fetch from bitnodes: {e}")
    
    if not seed_nodes:
        logger.error("Could not resolve any seed nodes. Using hardcoded IPs.")
        seed_nodes = [
            ("104.248.9.1", 8333),
            ("159.89.232.238", 8333),
            ("178.128.221.177", 8333),
        ]
    
    logger.info(f"Total seed nodes: {len(seed_nodes)}")
    
    crawler = BitcoinNodeCrawler(
        max_concurrent=args.max_concurrent,
        timeout=args.timeout
    )
    
    nodes_data = await crawler.crawl(seed_nodes, max_nodes=args.max_nodes, update_viz_callback=None)
    
    if not nodes_data:
        logger.error("No nodes were crawled. Exiting.")
        return
    
    logger.info(f"Crawled {len(nodes_data)} nodes")
    
    if not args.no_geolocation:
        logger.info("=" * 60)
        logger.info("Step 2: Getting Geolocation Data")
        logger.info("=" * 60)
        
        unique_ips = list(set(node['ip'] for node in nodes_data))
        logger.info(f"Getting geolocation for {len(unique_ips)} unique IPs")
        
        async with IPGeolocator(rate_limit=args.geolocation_rate_limit) as geolocator:
            location_data = await geolocator.get_locations_batch(unique_ips, max_concurrent=10)
        
        for node in nodes_data:
            ip = node['ip']
            location = location_data.get(ip)
            if location:
                node.update(location)
        
        nodes_with_location = sum(1 for node in nodes_data if node.get('latitude'))
        logger.info(f"Got geolocation for {nodes_with_location} nodes")
    else:
        logger.info("Skipping geolocation step")
    
    logger.info("=" * 60)
    logger.info("Step 3: Storing Data in Database")
    logger.info("=" * 60)
    
    db.insert_nodes_batch(nodes_data)
    
    stats = db.get_statistics()
    logger.info("Database Statistics:")
    logger.info(f"  Total nodes: {stats['total_nodes']}")
    logger.info(f"  Nodes with location: {stats['nodes_with_location']}")
    logger.info(f"  Unique countries: {stats['unique_countries']}")
    logger.info(f"  Average version: {stats['average_version']:.2f}")
    
    if args.create_heatmap:
        logger.info("=" * 60)
        logger.info("Step 4: Updating JSON File")
        logger.info("=" * 60)
        
        all_nodes = db.get_nodes_with_location()
        
        if all_nodes:
            from visualization import export_nodes_json
            json_file = f"{args.output_dir}/bitcoin_nodes.json"
            export_nodes_json(all_nodes, json_file)
            logger.info(f"Updated {json_file} with {len(all_nodes)} nodes (all nodes from database)")
            logger.info("Note: index.html was not modified - it reads from bitcoin_nodes.json")
        else:
            logger.warning("No nodes with location data in database")
    
    logger.info("=" * 60)
    logger.info("Done!")
    logger.info("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)

