"""mlops-dev exceptions"""

class MLOpsError(Exception):
    """Base SDK exception."""

class AuthenticationError(MLOpsError):
    """Invalid or missing API key."""

class DeviceNotFoundError(MLOpsError):
    """Device not found in fleet."""

class ModelNotFoundError(MLOpsError):
    """Model or version not found."""

class DeploymentError(MLOpsError):
    """Deployment failed or was rejected."""

class RateLimitError(MLOpsError):
    """API rate limit exceeded."""

class NetworkError(MLOpsError):
    """Network/connectivity error."""
