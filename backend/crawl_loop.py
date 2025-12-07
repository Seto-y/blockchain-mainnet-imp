#!/usr/bin/env python3

import asyncio
import time
import logging
import sys
import os
import socket

backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

from crawler import BitcoinNodeCrawler
from database import NodeDatabase
from geolocation import IPGeolocator

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


def resolve_dns_seeds():
    resolved_nodes = []
    for hostname, port in BITCOIN_SEED_NODES:
        try:
            try:
                addrinfo = socket.getaddrinfo(hostname, port, socket.AF_INET)
                for info in addrinfo:
                    ip = info[4][0]
                    resolved_nodes.append((ip, port))
            except:
                ip = socket.gethostbyname(hostname)
                resolved_nodes.append((ip, port))
        except socket.gaierror:
            pass
    return resolved_nodes


async def fetch_bitnodes_seeds(max_nodes: int = 200):
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get('https://bitnodes.io/api/v1/snapshots/latest/', timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        nodes = []
                        for node_info in list(data.get('nodes', {}).keys())[:max_nodes]:
                            if ':' in node_info:
                                ip, port = node_info.split(':')
                                if ip and port:
                                    nodes.append((ip, int(port)))
                        return nodes
            except:
                pass
    except:
        pass
    return []

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def crawl_batch(max_nodes: int = 50, max_concurrent: int = 50):
    try:
        seed_nodes = resolve_dns_seeds()
        
        try:
            bitnodes_seeds = await fetch_bitnodes_seeds(max_nodes=200)
            if bitnodes_seeds:
                seed_nodes.extend(bitnodes_seeds)
                logger.info(f"Added {len(bitnodes_seeds)} nodes from bitnodes.io")
        except Exception as e:
            logger.debug(f"Could not fetch from bitnodes: {e}")
        
        if not seed_nodes:
            logger.warning("No seed nodes available")
            return 0
        
        crawler = BitcoinNodeCrawler(
            max_concurrent=max_concurrent,
            timeout=8.0
        )
        
        logger.info(f"Crawling up to {max_nodes} nodes...")
        nodes_data = await crawler.crawl(seed_nodes, max_nodes=max_nodes)
        
        if not nodes_data:
            logger.warning("No nodes were crawled")
            return 0
        
        logger.info(f"Crawled {len(nodes_data)} nodes")
        
        unique_ips = list(set(node['ip'] for node in nodes_data))
        logger.info(f"Getting geolocation for {len(unique_ips)} unique IPs")
        
        async with IPGeolocator(rate_limit=0.1) as geolocator:
            location_data = await geolocator.get_locations_batch(unique_ips, max_concurrent=5)
        
        for node in nodes_data:
            ip = node['ip']
            location = location_data.get(ip)
            if location:
                node.update(location)
        
        nodes_with_location = sum(1 for node in nodes_data if node.get('latitude'))
        logger.info(f"Got geolocation for {nodes_with_location} nodes")
        
        db_path = os.path.join(backend_dir, 'bitcoin_nodes.db')
        db = NodeDatabase(db_path)
        db.insert_nodes_batch(nodes_data)
        
        stats = db.get_statistics()
        logger.info(f"✓ Database now has {stats['total_nodes']} total nodes ({stats['nodes_with_location']} with location)")
        
        return len(nodes_data)
        
    except Exception as e:
        logger.error(f"Error during crawl: {e}", exc_info=True)
        return 0


async def main():
    logger.info("=" * 60)
    logger.info("Starting Bitcoin Node Crawler Loop")
    logger.info("=" * 60)
    logger.info("Will crawl nodes every 10 seconds")
    logger.info("Press Ctrl+C to stop")
    logger.info("=" * 60)
    
    iteration = 0
    try:
        while True:
            iteration += 1
            logger.info(f"\n--- Crawl iteration #{iteration} ---")
            
            start_time = time.time()
            nodes_crawled = await crawl_batch(max_nodes=50, max_concurrent=50)
            elapsed = time.time() - start_time
            
            logger.info(f"Crawled {nodes_crawled} nodes in {elapsed:.1f} seconds")
            
            wait_time = max(0, 10 - elapsed)
            if wait_time > 0:
                logger.info(f"Waiting {wait_time:.1f} seconds until next crawl...")
                await asyncio.sleep(wait_time)
            else:
                logger.warning("Crawl took longer than 10 seconds, starting next immediately")
                
    except KeyboardInterrupt:
        logger.info("\n\nCrawler loop stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

