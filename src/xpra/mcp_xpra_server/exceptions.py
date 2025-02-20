class XpraError(Exception):
    """Base exception for Xpra-related errors."""
    pass

class SessionError(XpraError):
    """Session-specific errors."""
    pass

class ConfigurationError(XpraError):
    """Configuration-related errors."""
    pass

class SystemDependencyError(XpraError):
    """System dependency related errors."""
    pass 