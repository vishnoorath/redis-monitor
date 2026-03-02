"""
Authentication module for Redis Monitor.
Generates JWT tokens for API authentication.
"""

import jwt
import datetime
from src.config import Config


def generate_token(farm_id):
    """
    Generate JWT token for farm metadata API authentication.

    Args:
        farm_id (str): The farm ID to include in the token payload.

    Returns:
        str: JWT token string.

    Raises:
        Exception: If token generation fails.
    """
    try:
        # Create payload with all required fields
        payload = {
            "userId": Config.JWT_USER_ID,
            "deviceId": Config.JWT_DEVICE_ID,
            "farmId": farm_id,
            "language": Config.JWT_LANGUAGE,
            "role": Config.JWT_ROLE,
            "verificationStatus": Config.JWT_VERIFICATION_STATUS,
            "ModulesAccess": Config.JWT_MODULES_ACCESS,
            "FullName": Config.JWT_FULL_NAME,
            "OrganizationId": Config.JWT_ORGANIZATION_ID,
            "SwitchUserId": "",
            "SessionCorrelationId": Config.JWT_SESSION_CORRELATION_ID,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=Config.TOKEN_EXPIRY_MINUTES),
            "iat": datetime.datetime.utcnow()
        }

        # Encode token using HS256 algorithm
        token = jwt.encode(
            payload,
            Config.JWT_SECRET,
            algorithm="HS256"
        )

        if Config.VERBOSE:
            print(f"✓ Token generated successfully for farm: {farm_id}")

        return token

    except Exception as e:
        print(f"✗ Error generating token for farm {farm_id}: {str(e)}")
        raise


if __name__ == '__main__':
    # For testing token generation
    test_farm_id = '13f9ef67-19b0-4e3d-bec5-6dd15247492c'
    token = generate_token(test_farm_id)
    print(f"Generated token: {token[:50]}...")
