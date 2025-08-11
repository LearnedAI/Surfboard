# Surfboard Coding Standards

## Python Code Style

### Formatting
- **Line Length**: 88 characters (Black default)
- **Indentation**: 4 spaces (no tabs)
- **String Quotes**: Double quotes preferred
- **Import Sorting**: isort with Black profile

### Type Hints
- **Required**: All public functions must have type hints
- **Optional Parameters**: Use `Optional[Type]` or `Type | None` (Python 3.10+)
- **Return Types**: Always specify return types
- **Generic Types**: Use proper generic typing from `typing` module

```python
from typing import Optional, List, Dict, Any
import asyncio

async def process_request(
    data: Dict[str, Any],
    timeout: Optional[float] = None
) -> List[str]:
    """Process request with optional timeout."""
    # Implementation here
    pass
```

### Docstrings
- **Format**: Google-style docstrings
- **Required**: All public classes, methods, and functions
- **Content**: Purpose, parameters, returns, raises

```python
async def connect_to_chrome(port: int = 9222) -> CDPClient:
    """Connect to Chrome DevTools Protocol.

    Args:
        port: Chrome debugging port (default: 9222)

    Returns:
        Connected CDP client instance

    Raises:
        ConnectionError: If unable to connect to Chrome
        ValueError: If port is invalid
    """
    pass
```

### Error Handling
- **Specific Exceptions**: Use specific exception types
- **Async Context**: Proper async exception handling
- **Logging**: Log errors before re-raising
- **Resource Cleanup**: Use async context managers

```python
import logging
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

@asynccontextmanager
async def chrome_session(port: int):
    client = None
    try:
        client = await CDPClient.connect(port)
        yield client
    except ConnectionError as e:
        logger.error(f"Failed to connect to Chrome on port {port}: {e}")
        raise
    finally:
        if client:
            await client.close()
```

### Async Programming
- **Always Use Async**: For I/O operations
- **Context Managers**: For resource management
- **Proper Awaiting**: Don't mix sync/async incorrectly
- **Cancellation**: Handle task cancellation properly

## Architecture Patterns

### Module Organization
```
src/surfboard/
├── __init__.py          # Public API
├── core.py              # Main client
├── protocols/           # Protocol implementations
│   ├── __init__.py
│   ├── cdp.py          # Chrome DevTools Protocol
│   ├── webdriver.py    # WebDriver implementation
│   └── native.py       # Native messaging
├── automation/          # Automation layers
│   ├── __init__.py
│   ├── browser.py      # Browser control
│   ├── windows.py      # Windows UI Automation
│   └── actions.py      # Action primitives
├── communication/       # LLM communication
│   ├── __init__.py
│   ├── websocket.py    # WebSocket server
│   ├── api.py          # REST API
│   └── protocol.py     # Message protocol
└── security/            # Security components
    ├── __init__.py
    ├── sandbox.py      # Sandboxing
    ├── auth.py         # Authentication
    └── audit.py        # Audit logging
```

### Dependency Injection
- Use abstract base classes for interfaces
- Inject dependencies through constructors
- Support configuration-driven component selection

```python
from abc import ABC, abstractmethod
from typing import Protocol

class BrowserAutomation(Protocol):
    async def click_element(self, selector: str) -> bool:
        ...

class CDPBrowserAutomation(BrowserAutomation):
    async def click_element(self, selector: str) -> bool:
        # CDP implementation
        pass

class SurfboardClient:
    def __init__(self, browser: BrowserAutomation):
        self._browser = browser
```

### Configuration
- Environment-based configuration
- Pydantic models for validation
- Hierarchical config (env -> file -> defaults)

```python
from pydantic import BaseSettings

class SurfboardConfig(BaseSettings):
    chrome_port: int = 9222
    websocket_port: int = 8765
    log_level: str = "INFO"

    class Config:
        env_prefix = "SURFBOARD_"
        case_sensitive = False
```

## Testing Standards

### Test Structure
```
tests/
├── unit/               # Unit tests
├── integration/        # Integration tests
├── e2e/               # End-to-end tests
├── fixtures/          # Test fixtures
└── conftest.py        # Pytest configuration
```

### Test Naming
- Descriptive names: `test_chrome_connection_with_invalid_port_raises_error`
- Arrange-Act-Assert pattern
- Use fixtures for setup

```python
import pytest
from surfboard.protocols.cdp import CDPClient

@pytest.mark.asyncio
async def test_cdp_client_connection_timeout():
    """Test CDP client handles connection timeout properly."""
    # Arrange
    invalid_port = 99999

    # Act & Assert
    with pytest.raises(ConnectionError):
        async with CDPClient(port=invalid_port, timeout=1.0) as client:
            await client.connect()
```

### Coverage Requirements
- Minimum 90% code coverage
- 100% coverage for security-critical components
- Test both success and failure paths

## Security Standards

### Input Validation
- Validate all external inputs
- Use Pydantic models for complex validation
- Sanitize data before processing

### Logging
- No sensitive data in logs
- Structured logging with correlation IDs
- Configurable log levels

```python
import structlog

logger = structlog.get_logger(__name__)

async def process_command(command: str, session_id: str):
    logger.info(
        "Processing command",
        command_type=command.split()[0],  # Don't log full command
        session_id=session_id
    )
```

### Authentication
- API keys for external access
- Session tokens for WebSocket connections
- Rate limiting per client

## Documentation Standards

### API Documentation
- OpenAPI/Swagger for REST APIs
- Comprehensive examples
- Error response documentation

### Architecture Documentation
- C4 model diagrams
- Sequence diagrams for complex flows
- Decision records for major choices

### User Documentation
- Quick start guide
- Integration examples
- Troubleshooting guide

## Git Workflow

### Branch Naming
- `feature/feature-name`
- `bugfix/bug-description`
- `hotfix/critical-fix`

### Commit Messages
```
type(scope): description

Longer description if needed

- Bullet points for details
- Reference issues: Fixes #123
```

### Pull Requests
- Feature branch to main
- Required: tests, documentation, security review
- Squash merge preferred

## Tools Configuration

### Pre-commit Hooks
- Black (formatting)
- isort (import sorting)
- flake8 (linting)
- mypy (type checking)
- pytest (run tests)

### IDE Configuration
- VS Code settings included
- PyCharm configuration available
- EditorConfig for consistency

This ensures consistent, secure, and maintainable code across the Surfboard project.
