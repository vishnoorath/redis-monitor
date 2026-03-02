"""
Configuration module for Redis Monitor.
Loads environment variables from .env file and provides configuration values.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)


class Config:
    """Configuration class for Redis Monitor."""

    # JWT Configuration
    JWT_SECRET = os.getenv('JWT_SECRET', '12345678123456781234567812345678')
    TOKEN_EXPIRY_MINUTES = int(os.getenv('TOKEN_EXPIRY_MINUTES', '1440'))

    # API Endpoints
    OLD_API_ENDPOINT = os.getenv(
        'OLD_API_ENDPOINT',
        'https://prodgateway.nitara.co.in/cm/GetFarmMetaDataNew'
    )
    NEW_API_ENDPOINT = os.getenv(
        'NEW_API_ENDPOINT',
        'https://prodgateway.nitara.co.in/meta-data-api/farm-meta-data'
    )

    # Request Configuration
    REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '30'))

    # Farm IDs to Monitor
    @staticmethod
    def get_farm_ids():
        """Get farm IDs from config, returns list of farm IDs."""
        farm_ids_str = os.getenv('FARM_IDS', '13f9ef67-19b0-4e3d-bec5-6dd15247492c')
        return [farm_id.strip() for farm_id in farm_ids_str.split(',')]

    # JWT Payload Configuration
    JWT_USER_ID = os.getenv('JWT_USER_ID', 'c512c47d-1237-49fc-9168-bab3a2bd8b57')
    JWT_DEVICE_ID = os.getenv('JWT_DEVICE_ID', '7e01d642-75d1-4831-b5a6-7466e64c5c32')
    JWT_LANGUAGE = os.getenv('JWT_LANGUAGE', 'EN')
    JWT_ROLE = os.getenv('JWT_ROLE', 'VETERINARIAN, FARMER, NITARA FIELD ADMIN')
    JWT_VERIFICATION_STATUS = os.getenv('JWT_VERIFICATION_STATUS', 'False')
    JWT_MODULES_ACCESS = os.getenv('JWT_MODULES_ACCESS', 'NOCKIST')
    JWT_FULL_NAME = os.getenv('JWT_FULL_NAME', 'Mukesht live environment')
    JWT_ORGANIZATION_ID = os.getenv('JWT_ORGANIZATION_ID', '066b564b-7b7c-47d6-bdd8-9d7a0ce83bbe')
    JWT_SESSION_CORRELATION_ID = os.getenv('JWT_SESSION_CORRELATION_ID', 'a1b3d6ed-0a24-438c-bf46-7242fe568ae8')

    # Output Configuration
    OUTPUT_DIR = os.getenv('OUTPUT_DIR', 'results')
    VERBOSE = os.getenv('VERBOSE', 'False').lower() == 'true'

    @staticmethod
    def ensure_output_dir():
        """Ensure output directory exists."""
        Path(Config.OUTPUT_DIR).mkdir(parents=True, exist_ok=True)


if __name__ == '__main__':
    # For testing config
    print("Configuration loaded:")
    print(f"  JWT_SECRET: {Config.JWT_SECRET[:10]}...")
    print(f"  OLD_API_ENDPOINT: {Config.OLD_API_ENDPOINT}")
    print(f"  NEW_API_ENDPOINT: {Config.NEW_API_ENDPOINT}")
    print(f"  Farm IDs: {Config.get_farm_ids()}")
