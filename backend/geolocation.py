import asyncio
import aiohttp
import logging
from typing import Dict, Optional, List
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IPGeolocator:
    def __init__(self, rate_limit: float = 0.1):
        self.rate_limit = rate_limit
        self.last_request_time = 0
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _rate_limit(self):
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit:
            await asyncio.sleep(self.rate_limit - elapsed)
        self.last_request_time = time.time()
    
    async def get_location(self, ip: str) -> Optional[Dict]:
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        await self._rate_limit()
        
        try:
            url = f"http://ip-api.com/json/{ip}?fields=status,message,country,countryCode,city,lat,lon,timezone,isp"
            
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get('status') == 'success':
                        return {
                            'latitude': data.get('lat'),
                            'longitude': data.get('lon'),
                            'country': data.get('country'),
                            'country_code': data.get('countryCode'),
                            'city': data.get('city'),
                            'timezone': data.get('timezone'),
                            'isp': data.get('isp')
                        }
                    else:
                        logger.debug(f"API returned error for {ip}: {data.get('message')}")
                        return None
                else:
                    logger.debug(f"HTTP {response.status} for {ip}")
                    return None
                    
        except asyncio.TimeoutError:
            logger.debug(f"Timeout getting location for {ip}")
            return None
        except Exception as e:
            logger.debug(f"Error getting location for {ip}: {e}")
            return None
    
    async def get_locations_batch(self, ips: List[str], max_concurrent: int = 10) -> Dict[str, Optional[Dict]]:
        semaphore = asyncio.Semaphore(max_concurrent)
        results = {}
        
        async def get_with_semaphore(ip: str):
            async with semaphore:
                location = await self.get_location(ip)
                results[ip] = location
        
        tasks = [get_with_semaphore(ip) for ip in ips]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        return results


class IPInfoGeolocator:
    def __init__(self, api_key: Optional[str] = None, rate_limit: float = 0.1):
        self.api_key = api_key
        self.rate_limit = rate_limit
        self.last_request_time = 0
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _rate_limit(self):
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit:
            await asyncio.sleep(self.rate_limit - elapsed)
        self.last_request_time = time.time()
    
    async def get_location(self, ip: str) -> Optional[Dict]:
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        await self._rate_limit()
        
        try:
            url = f"https://ipinfo.io/{ip}/json"
            headers = {}
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'
            
            async with self.session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    lat, lon = None, None
                    if 'loc' in data:
                        try:
                            lat, lon = map(float, data['loc'].split(','))
                        except:
                            pass
                    
                    return {
                        'latitude': lat,
                        'longitude': lon,
                        'country': data.get('country'),
                        'country_code': data.get('country'),
                        'city': data.get('city'),
                        'region': data.get('region'),
                        'timezone': data.get('timezone'),
                        'isp': data.get('org')
                    }
                else:
                    logger.debug(f"HTTP {response.status} for {ip}")
                    return None
                    
        except Exception as e:
            logger.debug(f"Error getting location for {ip}: {e}")
            return None

