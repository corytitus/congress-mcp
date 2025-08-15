"""
Token Management Configuration
Configuration management for the token system with environment variables and defaults
"""

import os
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from pathlib import Path
import json


@dataclass
class DatabaseConfig:
    """Database configuration."""
    path: str = "tokens.db"
    backup_enabled: bool = True
    backup_interval_hours: int = 24
    cleanup_days: int = 30


@dataclass
class SecurityConfig:
    """Security configuration."""
    secret_key: Optional[str] = None
    token_prefix: str = "enact_"
    token_length: int = 32
    hash_algorithm: str = "sha256"
    require_https: bool = False


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    default_rate_limit: int = 1000  # requests per hour
    window_hours: int = 1
    burst_allowance: int = 50  # additional requests allowed in short bursts


@dataclass
class LoggingConfig:
    """Logging configuration."""
    enabled: bool = True
    log_level: str = "INFO"
    log_file: Optional[str] = None
    max_log_size_mb: int = 100
    backup_count: int = 5


@dataclass
class AnalyticsConfig:
    """Analytics configuration."""
    enabled: bool = True
    retention_days: int = 90
    aggregation_interval_minutes: int = 15
    dashboard_enabled: bool = True
    dashboard_port: int = 8083


@dataclass
class AlertsConfig:
    """Alerts configuration."""
    enabled: bool = True
    high_usage_threshold: int = 1000  # requests per hour
    error_rate_threshold: float = 0.1  # 10% error rate
    unused_token_days: int = 30
    notification_email: Optional[str] = None


@dataclass
class TokenManagementConfig:
    """Complete token management configuration."""
    database: DatabaseConfig
    security: SecurityConfig
    rate_limiting: RateLimitConfig
    logging: LoggingConfig
    analytics: AnalyticsConfig
    alerts: AlertsConfig
    
    # Server configuration
    server_port: int = 8082
    server_host: str = "0.0.0.0"
    debug: bool = False
    
    # API configuration
    congress_api_key: str = ""
    govinfo_api_key: str = ""


class ConfigManager:
    """Configuration manager for the token system."""
    
    def __init__(self, config_file: Optional[str] = None):
        """Initialize configuration manager."""
        self.config_file = config_file or os.getenv("TOKEN_CONFIG_FILE", "token_config.json")
        self.config = self._load_config()
    
    def _load_config(self) -> TokenManagementConfig:
        """Load configuration from environment variables and config file."""
        # Start with defaults
        config_dict = self._get_default_config()
        
        # Override with config file if it exists
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    file_config = json.load(f)
                config_dict = self._merge_config(config_dict, file_config)
            except Exception as e:
                print(f"Warning: Could not load config file {self.config_file}: {e}")
        
        # Override with environment variables
        env_config = self._load_from_env()
        config_dict = self._merge_config(config_dict, env_config)
        
        # Convert to dataclass
        return TokenManagementConfig(
            database=DatabaseConfig(**config_dict["database"]),
            security=SecurityConfig(**config_dict["security"]),
            rate_limiting=RateLimitConfig(**config_dict["rate_limiting"]),
            logging=LoggingConfig(**config_dict["logging"]),
            analytics=AnalyticsConfig(**config_dict["analytics"]),
            alerts=AlertsConfig(**config_dict["alerts"]),
            server_port=config_dict["server_port"],
            server_host=config_dict["server_host"],
            debug=config_dict["debug"],
            congress_api_key=config_dict["congress_api_key"],
            govinfo_api_key=config_dict["govinfo_api_key"]
        )
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "database": {
                "path": "tokens.db",
                "backup_enabled": True,
                "backup_interval_hours": 24,
                "cleanup_days": 30
            },
            "security": {
                "secret_key": None,
                "token_prefix": "enact_",
                "token_length": 32,
                "hash_algorithm": "sha256",
                "require_https": False
            },
            "rate_limiting": {
                "default_rate_limit": 1000,
                "window_hours": 1,
                "burst_allowance": 50
            },
            "logging": {
                "enabled": True,
                "log_level": "INFO",
                "log_file": None,
                "max_log_size_mb": 100,
                "backup_count": 5
            },
            "analytics": {
                "enabled": True,
                "retention_days": 90,
                "aggregation_interval_minutes": 15,
                "dashboard_enabled": True,
                "dashboard_port": 8083
            },
            "alerts": {
                "enabled": True,
                "high_usage_threshold": 1000,
                "error_rate_threshold": 0.1,
                "unused_token_days": 30,
                "notification_email": None
            },
            "server_port": 8082,
            "server_host": "0.0.0.0",
            "debug": False,
            "congress_api_key": "",
            "govinfo_api_key": ""
        }
    
    def _load_from_env(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        env_config = {
            "database": {},
            "security": {},
            "rate_limiting": {},
            "logging": {},
            "analytics": {},
            "alerts": {}
        }
        
        # Database configuration
        if os.getenv("TOKEN_DB_PATH"):
            env_config["database"]["path"] = os.getenv("TOKEN_DB_PATH")
        if os.getenv("TOKEN_DB_BACKUP_ENABLED"):
            env_config["database"]["backup_enabled"] = os.getenv("TOKEN_DB_BACKUP_ENABLED").lower() == "true"
        if os.getenv("TOKEN_DB_CLEANUP_DAYS"):
            env_config["database"]["cleanup_days"] = int(os.getenv("TOKEN_DB_CLEANUP_DAYS"))
        
        # Security configuration
        if os.getenv("TOKEN_SECRET_KEY"):
            env_config["security"]["secret_key"] = os.getenv("TOKEN_SECRET_KEY")
        if os.getenv("TOKEN_PREFIX"):
            env_config["security"]["token_prefix"] = os.getenv("TOKEN_PREFIX")
        if os.getenv("TOKEN_LENGTH"):
            env_config["security"]["token_length"] = int(os.getenv("TOKEN_LENGTH"))
        if os.getenv("REQUIRE_HTTPS"):
            env_config["security"]["require_https"] = os.getenv("REQUIRE_HTTPS").lower() == "true"
        
        # Rate limiting configuration
        if os.getenv("DEFAULT_RATE_LIMIT"):
            env_config["rate_limiting"]["default_rate_limit"] = int(os.getenv("DEFAULT_RATE_LIMIT"))
        if os.getenv("RATE_LIMIT_WINDOW_HOURS"):
            env_config["rate_limiting"]["window_hours"] = int(os.getenv("RATE_LIMIT_WINDOW_HOURS"))
        
        # Analytics configuration
        if os.getenv("ANALYTICS_ENABLED"):
            env_config["analytics"]["enabled"] = os.getenv("ANALYTICS_ENABLED").lower() == "true"
        if os.getenv("ANALYTICS_RETENTION_DAYS"):
            env_config["analytics"]["retention_days"] = int(os.getenv("ANALYTICS_RETENTION_DAYS"))
        if os.getenv("DASHBOARD_PORT"):
            env_config["analytics"]["dashboard_port"] = int(os.getenv("DASHBOARD_PORT"))
        
        # Server configuration
        if os.getenv("PORT"):
            env_config["server_port"] = int(os.getenv("PORT"))
        if os.getenv("HOST"):
            env_config["server_host"] = os.getenv("HOST")
        if os.getenv("DEBUG"):
            env_config["debug"] = os.getenv("DEBUG").lower() == "true"
        
        # API keys
        if os.getenv("CONGRESS_GOV_API_KEY"):
            env_config["congress_api_key"] = os.getenv("CONGRESS_GOV_API_KEY")
        if os.getenv("GOVINFO_API_KEY"):
            env_config["govinfo_api_key"] = os.getenv("GOVINFO_API_KEY")
        
        return env_config
    
    def _merge_config(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Merge configuration dictionaries."""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def save_config(self, config_file: Optional[str] = None):
        """Save current configuration to file."""
        file_path = config_file or self.config_file
        
        config_dict = {
            "database": {
                "path": self.config.database.path,
                "backup_enabled": self.config.database.backup_enabled,
                "backup_interval_hours": self.config.database.backup_interval_hours,
                "cleanup_days": self.config.database.cleanup_days
            },
            "security": {
                "secret_key": self.config.security.secret_key,
                "token_prefix": self.config.security.token_prefix,
                "token_length": self.config.security.token_length,
                "hash_algorithm": self.config.security.hash_algorithm,
                "require_https": self.config.security.require_https
            },
            "rate_limiting": {
                "default_rate_limit": self.config.rate_limiting.default_rate_limit,
                "window_hours": self.config.rate_limiting.window_hours,
                "burst_allowance": self.config.rate_limiting.burst_allowance
            },
            "logging": {
                "enabled": self.config.logging.enabled,
                "log_level": self.config.logging.log_level,
                "log_file": self.config.logging.log_file,
                "max_log_size_mb": self.config.logging.max_log_size_mb,
                "backup_count": self.config.logging.backup_count
            },
            "analytics": {
                "enabled": self.config.analytics.enabled,
                "retention_days": self.config.analytics.retention_days,
                "aggregation_interval_minutes": self.config.analytics.aggregation_interval_minutes,
                "dashboard_enabled": self.config.analytics.dashboard_enabled,
                "dashboard_port": self.config.analytics.dashboard_port
            },
            "alerts": {
                "enabled": self.config.alerts.enabled,
                "high_usage_threshold": self.config.alerts.high_usage_threshold,
                "error_rate_threshold": self.config.alerts.error_rate_threshold,
                "unused_token_days": self.config.alerts.unused_token_days,
                "notification_email": self.config.alerts.notification_email
            },
            "server_port": self.config.server_port,
            "server_host": self.config.server_host,
            "debug": self.config.debug,
            "congress_api_key": self.config.congress_api_key,
            "govinfo_api_key": self.config.govinfo_api_key
        }
        
        try:
            # Create directory if it doesn't exist
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w') as f:
                json.dump(config_dict, f, indent=2)
            
            print(f"Configuration saved to {file_path}")
        except Exception as e:
            print(f"Error saving configuration: {e}")
    
    def validate_config(self) -> List[str]:
        """Validate configuration and return list of issues."""
        issues = []
        
        # Check required API keys
        if not self.config.congress_api_key:
            issues.append("CONGRESS_GOV_API_KEY is not set")
        
        # Check database path is writable
        db_dir = Path(self.config.database.path).parent
        if not db_dir.exists():
            try:
                db_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                issues.append(f"Cannot create database directory: {db_dir}")
        
        # Check port availability
        if not (1 <= self.config.server_port <= 65535):
            issues.append(f"Invalid server port: {self.config.server_port}")
        
        if not (1 <= self.config.analytics.dashboard_port <= 65535):
            issues.append(f"Invalid dashboard port: {self.config.analytics.dashboard_port}")
        
        # Check rate limiting values
        if self.config.rate_limiting.default_rate_limit < 1:
            issues.append("Default rate limit must be at least 1")
        
        # Check analytics retention
        if self.config.analytics.retention_days < 1:
            issues.append("Analytics retention days must be at least 1")
        
        return issues
    
    def print_config(self):
        """Print current configuration (masking sensitive values)."""
        print("Token Management Configuration:")
        print(f"  Database: {self.config.database.path}")
        print(f"  Server: {self.config.server_host}:{self.config.server_port}")
        print(f"  Dashboard: Port {self.config.analytics.dashboard_port}")
        print(f"  Rate Limit: {self.config.rate_limiting.default_rate_limit} req/hour")
        print(f"  Analytics: {'Enabled' if self.config.analytics.enabled else 'Disabled'}")
        print(f"  Debug: {'Enabled' if self.config.debug else 'Disabled'}")
        
        if self.config.congress_api_key:
            print(f"  Congress API Key: {self.config.congress_api_key[:10]}...")
        else:
            print("  Congress API Key: Not set")


# Global configuration instance
_config_manager = None

def get_config() -> TokenManagementConfig:
    """Get the global configuration instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager.config

def get_config_manager() -> ConfigManager:
    """Get the global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


# Configuration validation script
if __name__ == "__main__":
    import sys
    
    print("Token Management Configuration Validator")
    print("=" * 50)
    
    config_manager = ConfigManager()
    config_manager.print_config()
    
    print("\nValidating configuration...")
    issues = config_manager.validate_config()
    
    if issues:
        print("\nConfiguration Issues Found:")
        for issue in issues:
            print(f"  ⚠️  {issue}")
        sys.exit(1)
    else:
        print("\n✅ Configuration is valid!")
        sys.exit(0)