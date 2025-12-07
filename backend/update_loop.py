#!/usr/bin/env python3

import time
import logging
from update_json import update_json_from_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    logger.info("Starting JSON update loop (every 10 seconds)")
    logger.info("Press Ctrl+C to stop")
    
    try:
        while True:
            try:
                update_json_from_db()
                logger.info("✓ JSON updated")
            except Exception as e:
                logger.error(f"Error updating JSON: {e}")
            
            time.sleep(10)
    except KeyboardInterrupt:
        logger.info("\nUpdate loop stopped")


if __name__ == "__main__":
    main()

