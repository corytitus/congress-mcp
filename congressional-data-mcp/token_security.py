"""
Token Security Utilities
Provides secure token generation, hashing, and validation functionality
"""

import hashlib
import secrets
import string
import hmac
from datetime import datetime, timedelta
from typing import Optional, Tuple
import base64
import os


class TokenSecurity:
    """Secure token management utilities."""
    
    # Token format: prefix_randompart (e.g., enact_abc123def456...)
    TOKEN_PREFIX = "enact_"
    TOKEN_LENGTH = 32  # Length of random part
    HASH_ALGORITHM = "sha256"
    
    def __init__(self, secret_key: Optional[str] = None):
        """Initialize token security with optional secret key."""
        self.secret_key = secret_key or os.getenv("TOKEN_SECRET_KEY", self._generate_secret_key())
    
    @staticmethod
    def _generate_secret_key() -> str:
        """Generate a secure random secret key."""
        return secrets.token_urlsafe(32)
    
    def generate_token(self) -> str:
        """Generate a new secure token."""
        # Use a mix of letters and numbers for the random part
        alphabet = string.ascii_letters + string.digits
        random_part = ''.join(secrets.choice(alphabet) for _ in range(self.TOKEN_LENGTH))
        return f"{self.TOKEN_PREFIX}{random_part}"
    
    def hash_token(self, token: str) -> str:
        """Hash a token using HMAC-SHA256."""
        return hmac.new(
            self.secret_key.encode(),
            token.encode(),
            hashlib.sha256
        ).hexdigest()
    
    def verify_token_format(self, token: str) -> bool:
        """Verify that a token has the correct format."""
        if not token.startswith(self.TOKEN_PREFIX):
            return False
        
        # Check length
        expected_length = len(self.TOKEN_PREFIX) + self.TOKEN_LENGTH
        if len(token) != expected_length:
            return False
        
        # Check that the random part contains only valid characters
        random_part = token[len(self.TOKEN_PREFIX):]
        valid_chars = set(string.ascii_letters + string.digits)
        return all(c in valid_chars for c in random_part)
    
    def compare_tokens(self, token1: str, token2: str) -> bool:
        """Safely compare two tokens using constant-time comparison."""
        hash1 = self.hash_token(token1)
        hash2 = self.hash_token(token2)
        return hmac.compare_digest(hash1, hash2)
    
    def verify_token_hash(self, token: str, hashed_token: str) -> bool:
        """Verify a token against its hash."""
        computed_hash = self.hash_token(token)
        return hmac.compare_digest(computed_hash, hashed_token)
    
    def generate_token_id(self) -> str:
        """Generate a unique token ID."""
        return secrets.token_urlsafe(16)
    
    def generate_usage_id(self) -> str:
        """Generate a unique usage record ID."""
        return secrets.token_urlsafe(12)
    
    def create_token_with_metadata(self, name: str, **kwargs) -> Tuple[str, str, str]:
        """
        Create a new token with metadata.
        Returns: (token_id, raw_token, hashed_token)
        """
        token_id = self.generate_token_id()
        raw_token = self.generate_token()
        hashed_token = self.hash_token(raw_token)
        
        return token_id, raw_token, hashed_token
    
    def is_token_expired(self, expires_at: Optional[datetime]) -> bool:
        """Check if a token has expired."""
        if expires_at is None:
            return False
        return datetime.now() > expires_at
    
    def generate_recovery_code(self) -> str:
        """Generate a recovery code for emergency access."""
        return secrets.token_urlsafe(24)
    
    def hash_recovery_code(self, code: str) -> str:
        """Hash a recovery code."""
        return hashlib.sha256(f"{self.secret_key}{code}".encode()).hexdigest()


class RateLimiter:
    """Simple rate limiter for token usage."""
    
    def __init__(self):
        """Initialize the rate limiter."""
        self.usage_windows = {}  # token_id -> list of timestamps
    
    def is_rate_limited(self, token_id: str, rate_limit: int, window_hours: int = 1) -> bool:
        """
        Check if a token has exceeded its rate limit.
        
        Args:
            token_id: The token identifier
            rate_limit: Maximum requests per window
            window_hours: Time window in hours
        
        Returns:
            True if rate limited, False otherwise
        """
        now = datetime.now()
        window_start = now - timedelta(hours=window_hours)
        
        # Clean up old entries
        if token_id in self.usage_windows:
            self.usage_windows[token_id] = [
                timestamp for timestamp in self.usage_windows[token_id]
                if timestamp > window_start
            ]
        else:
            self.usage_windows[token_id] = []
        
        # Check if rate limit exceeded
        if len(self.usage_windows[token_id]) >= rate_limit:
            return True
        
        # Record this usage
        self.usage_windows[token_id].append(now)
        return False
    
    def get_usage_count(self, token_id: str, window_hours: int = 1) -> int:
        """Get current usage count for a token in the time window."""
        now = datetime.now()
        window_start = now - timedelta(hours=window_hours)
        
        if token_id not in self.usage_windows:
            return 0
        
        return len([
            timestamp for timestamp in self.usage_windows[token_id]
            if timestamp > window_start
        ])
    
    def reset_usage(self, token_id: str):
        """Reset usage tracking for a token."""
        if token_id in self.usage_windows:
            del self.usage_windows[token_id]


class IPValidator:
    """IP address validation and whitelist checking."""
    
    @staticmethod
    def is_valid_ip(ip_address: str) -> bool:
        """Check if an IP address is valid."""
        try:
            import ipaddress
            ipaddress.ip_address(ip_address)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def is_ip_in_whitelist(ip_address: str, whitelist: list) -> bool:
        """Check if an IP address is in the whitelist."""
        if not whitelist:
            return True  # No whitelist means all IPs allowed
        
        try:
            import ipaddress
            ip = ipaddress.ip_address(ip_address)
            
            for allowed in whitelist:
                # Handle CIDR notation
                if '/' in allowed:
                    network = ipaddress.ip_network(allowed, strict=False)
                    if ip in network:
                        return True
                else:
                    # Exact IP match
                    if str(ip) == allowed:
                        return True
            
            return False
        except Exception:
            return False


class TokenValidator:
    """Complete token validation system."""
    
    def __init__(self, security: TokenSecurity, rate_limiter: RateLimiter):
        """Initialize the token validator."""
        self.security = security
        self.rate_limiter = rate_limiter
    
    def validate_token_request(self, 
                             token: str, 
                             token_data: dict,
                             tool_name: str,
                             ip_address: Optional[str] = None) -> Tuple[bool, str]:
        """
        Comprehensive token validation.
        
        Returns:
            (is_valid, error_message)
        """
        # Basic format validation
        if not self.security.verify_token_format(token):
            return False, "Invalid token format"
        
        # Check if token exists and is active
        if not token_data.get('is_active', False):
            return False, "Token is inactive or revoked"
        
        # Check expiration
        expires_at = token_data.get('expires_at')
        if expires_at and self.security.is_token_expired(expires_at):
            return False, "Token has expired"
        
        # Check tool permissions
        allowed_tools = token_data.get('allowed_tools')
        if allowed_tools is not None and tool_name not in allowed_tools:
            return False, f"Token does not have permission for tool: {tool_name}"
        
        # Check IP whitelist
        ip_whitelist = token_data.get('ip_whitelist')
        if ip_address and not IPValidator.is_ip_in_whitelist(ip_address, ip_whitelist):
            return False, "IP address not in whitelist"
        
        # Check rate limiting
        token_id = token_data.get('id')
        rate_limit = token_data.get('rate_limit', 1000)
        if self.rate_limiter.is_rate_limited(token_id, rate_limit):
            return False, "Rate limit exceeded"
        
        return True, "Token validated successfully"


# Utility functions for integration
def setup_token_security() -> Tuple[TokenSecurity, RateLimiter, TokenValidator]:
    """Set up the complete token security system."""
    security = TokenSecurity()
    rate_limiter = RateLimiter()
    validator = TokenValidator(security, rate_limiter)
    
    return security, rate_limiter, validator


def extract_token_from_header(authorization_header: str) -> Optional[str]:
    """Extract token from Authorization header."""
    if not authorization_header:
        return None
    
    if not authorization_header.startswith("Bearer "):
        return None
    
    return authorization_header[7:]  # Remove "Bearer " prefix


def mask_token_for_display(token: str) -> str:
    """Mask a token for safe display (show only first and last few characters)."""
    if len(token) <= 8:
        return "****"
    
    return f"{token[:4]}...{token[-4:]}"


def generate_api_key_display_name(name: str) -> str:
    """Generate a display name for API keys."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    return f"{name}_{timestamp}"