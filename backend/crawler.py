import asyncio
import socket
import ipaddress
from typing import Set, List, Tuple, Optional
from datetime import datetime
import logging

from bitcoin_protocol import (
    create_version_message,
    create_verack_message,
    create_getaddr_message,
    parse_addr_message,
    parse_message,
    MAINNET_MAGIC
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def is_private_ip(ip: str) -> bool:
    try:
        ip_obj = ipaddress.ip_address(ip)
        return ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local
    except ValueError:
        return True


class BitcoinNodeCrawler:
    def __init__(self, max_concurrent: int = 500, timeout: float = 10.0):
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.discovered_nodes: Set[Tuple[str, int]] = set()
        self.crawled_nodes: Set[Tuple[str, int]] = set()
        self.node_data: List[dict] = []
        self.failed_nodes: Set[Tuple[str, int]] = set()
        
    async def connect_to_node(self, ip: str, port: int) -> Optional[dict]:
        async with self.semaphore:
            if (ip, port) in self.crawled_nodes:
                return None
            
            self.crawled_nodes.add((ip, port))
            
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(ip, port),
                    timeout=self.timeout
                )
                
                version_msg = create_version_message()
                writer.write(version_msg)
                await writer.drain()
                
                try:
                    response = await asyncio.wait_for(
                        reader.read(1024),
                        timeout=self.timeout
                    )
                    
                    if not response:
                        writer.close()
                        await writer.wait_closed()
                        return None
                    
                    msg = parse_message(response)
                    if not msg or msg[0] != b'version':
                        writer.close()
                        await writer.wait_closed()
                        return None
                    
                    verack_msg = create_verack_message()
                    writer.write(verack_msg)
                    await writer.drain()
                    
                    verack_response = await asyncio.wait_for(
                        reader.read(1024),
                        timeout=self.timeout
                    )
                    
                    if not verack_response:
                        writer.close()
                        await writer.wait_closed()
                        return None
                    
                    verack_msg_parsed = parse_message(verack_response)
                    if not verack_msg_parsed or verack_msg_parsed[0] != b'verack':
                        writer.close()
                        await writer.wait_closed()
                        return None
                    
                    getaddr_msg = create_getaddr_message()
                    writer.write(getaddr_msg)
                    await writer.drain()
                    
                    new_peers = []
                    addr_data = b''
                    attempts = 0
                    max_attempts = 8
                    
                    await asyncio.sleep(0.3)
                    
                    while attempts < max_attempts:
                        try:
                            chunk = await asyncio.wait_for(
                                reader.read(16384),
                                timeout=1.5
                            )
                            if not chunk:
                                attempts += 1
                                await asyncio.sleep(0.2)
                                continue
                            addr_data += chunk
                            
                            offset = 0
                            while offset < len(addr_data):
                                msg_parsed = parse_message(addr_data[offset:])
                                if msg_parsed:
                                    cmd, payload = msg_parsed
                                    if cmd == b'addr':
                                        peers = parse_addr_message(payload)
                                        if peers:
                                            new_peers.extend(peers)
                                            logger.debug(f"Parsed {len(peers)} peers from ADDR message")
                                        offset += 24 + len(payload)
                                    else:
                                        msg_len = 24 + len(payload)
                                        offset += msg_len
                                else:
                                    break
                            
                            if new_peers and attempts >= 2:
                                break
                                
                            attempts += 1
                            await asyncio.sleep(0.2)
                        except asyncio.TimeoutError:
                            attempts += 1
                            if attempts < max_attempts:
                                await asyncio.sleep(0.2)
                            continue
                        except Exception as e:
                            logger.debug(f"Error reading ADDR response from {ip}:{port}: {e}")
                            break
                    
                    if addr_data and not new_peers:
                        for start_offset in [0, 24, 48]:
                            if start_offset < len(addr_data):
                                addr_msg = parse_message(addr_data[start_offset:])
                                if addr_msg and addr_msg[0] == b'addr':
                                    peers = parse_addr_message(addr_msg[1])
                                    if peers:
                                        new_peers.extend(peers)
                                        break
                    
                    version_info = self._parse_version_payload(msg[1])
                    
                    writer.close()
                    await writer.wait_closed()
                    
                    node_info = {
                        'ip': ip,
                        'port': port,
                        'version': version_info.get('version', 0),
                        'services': version_info.get('services', 0),
                        'user_agent': version_info.get('user_agent', ''),
                        'timestamp': datetime.now().isoformat(),
                        'peers_discovered': len(new_peers)
                    }
                    
                    for peer_ip, peer_port, _ in new_peers:
                        if not is_private_ip(peer_ip):
                            if (peer_ip, peer_port) not in self.discovered_nodes and (peer_ip, peer_port) not in self.crawled_nodes:
                                self.discovered_nodes.add((peer_ip, peer_port))
                    
                    if new_peers:
                        logger.debug(f"Discovered {len(new_peers)} peers from {ip}:{port}")
                    
                    return node_info
                    
                except asyncio.TimeoutError:
                    writer.close()
                    await writer.wait_closed()
                    return None
                except Exception as e:
                    logger.debug(f"Error communicating with {ip}:{port}: {e}")
                    writer.close()
                    await writer.wait_closed()
                    return None
                    
            except (asyncio.TimeoutError, ConnectionRefusedError, OSError) as e:
                self.failed_nodes.add((ip, port))
                return None
            except Exception as e:
                logger.debug(f"Error connecting to {ip}:{port}: {e}")
                self.failed_nodes.add((ip, port))
                return None
    
    def _parse_version_payload(self, payload: bytes) -> dict:
        try:
            import struct
            from bitcoin_protocol import varint_decode
            
            offset = 0
            if len(payload) < 4:
                return {}
            
            version = struct.unpack('<I', payload[offset:offset + 4])[0]
            offset += 4
            
            if len(payload) < offset + 8:
                return {'version': version}
            
            services = struct.unpack('<Q', payload[offset:offset + 8])[0]
            offset += 8
            
            if len(payload) < offset + 8:
                return {'version': version, 'services': services}
            
            timestamp = struct.unpack('<Q', payload[offset:offset + 8])[0]
            offset += 8
            
            offset += 26
            offset += 26
            offset += 8
            
            user_agent = ''
            if offset < len(payload):
                try:
                    ua_len, offset = varint_decode(payload, offset)
                    if offset + ua_len <= len(payload):
                        user_agent = payload[offset:offset + ua_len].decode('utf-8', errors='ignore')
                except:
                    pass
            
            return {
                'version': version,
                'services': services,
                'timestamp': timestamp,
                'user_agent': user_agent
            }
        except Exception:
            return {}
    
    async def crawl(self, seed_nodes: List[Tuple[str, int]], max_nodes: int = 1000, update_viz_callback=None):
        logger.info(f"Starting crawl with {len(seed_nodes)} seed nodes, max {max_nodes} nodes")
        
        for ip, port in seed_nodes:
            if not is_private_ip(ip):
                self.discovered_nodes.add((ip, port))
        
        tasks = []
        iteration = 0
        last_viz_update = 0
        
        while len(self.crawled_nodes) < max_nodes and self.discovered_nodes:
            iteration += 1
            logger.info(f"Iteration {iteration}: {len(self.discovered_nodes)} discovered, {len(self.crawled_nodes)} crawled")
            
            to_crawl = list(self.discovered_nodes - self.crawled_nodes)[:self.max_concurrent]
            
            if not to_crawl:
                break
            
            batch_tasks = [self.connect_to_node(ip, port) for ip, port in to_crawl]
            results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            successful = 0
            for result in results:
                if isinstance(result, dict) and result:
                    self.node_data.append(result)
                    successful += 1
                    logger.info(f"Crawled {result['ip']}:{result['port']} - Version: {result['version']}, Peers discovered: {result['peers_discovered']}")
            
            logger.info(f"Batch complete: {successful}/{len(to_crawl)} successful, {len(self.discovered_nodes)} total discovered")
            
            if update_viz_callback and len(self.node_data) - last_viz_update >= 20:
                try:
                    update_viz_callback(self.node_data)
                    last_viz_update = len(self.node_data)
                except Exception as e:
                    logger.debug(f"Error updating visualization: {e}")
            
            if len(self.discovered_nodes) - len(self.crawled_nodes) < 10 and len(self.crawled_nodes) < max_nodes:
                logger.info("Low discovery rate, continuing with available nodes...")
            
            await asyncio.sleep(0.3)
        
        if update_viz_callback and len(self.node_data) > last_viz_update:
            try:
                update_viz_callback(self.node_data)
            except Exception as e:
                logger.debug(f"Error in final visualization update: {e}")
        
        logger.info(f"Crawl complete: {len(self.node_data)} nodes crawled, {len(self.discovered_nodes)} total discovered")
        return self.node_data

