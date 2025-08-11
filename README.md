# Surfboard - Windows Chrome Automation Bridge

A native Windows automation bridge that enables LLMs to control Google Chrome through intelligent protocol selection, providing secure, performant, and reliable browser automation specifically optimized for AI-driven interactions.

## Project Vision

Build a production-ready automation bridge that combines Windows UI Automation with Chrome DevTools Protocol, WebDriver, and Native Messaging to create the most flexible and secure browser automation platform for LLM interactions.

## Core Principles

- **Security First**: Every feature must pass security review before implementation
- **Protocol Agnostic**: Support multiple automation methods, selecting the best for each task
- **LLM Optimized**: Design APIs and responses specifically for LLM consumption
- **Production Ready**: Build for reliability, monitoring, and enterprise deployment
- **Extensible Architecture**: Enable plugin system for custom capabilities

## Architecture Overview

Surfboard implements a layered architecture:

- **Core Layer**: Win32 APIs for window discovery and management
- **Automation Layer**: Windows UI Automation for application interaction
- **Browser Layer**: Chrome DevTools Protocol, WebDriver, and Extensions API
- **Communication Layer**: WebSocket server optimized for LLM interaction
- **Security Layer**: Sandboxing, authentication, and audit logging

## Development Status

🚧 **Currently in Phase 0: Foundation & Planning**

See [Roadmap.md](Roadmap.md) for detailed development timeline and progress tracking.

## Requirements

### System Requirements
- Windows 10 version 1809 minimum (Windows 11 recommended)
- Google Chrome 64+ (Chrome 117+ recommended for full CDP support)
- .NET 6+ or Visual Studio 2022 with Windows development workload
- Windows SDK 10.0.26100

### Development Requirements
- Windows SDK for UI Automation APIs
- Chrome with `--remote-debugging-port` capability
- WebSocket library for real-time communication
- Code signing certificate (for UIAccess functionality in production)

## Quick Start

*Coming soon - currently in development*

## Documentation

- [Technical Specification](specs/Specification.md) - Comprehensive technical research and implementation guidance
- [Development Roadmap](Roadmap.md) - 24-week development plan with phase gates
- [Architecture Documentation](docs/architecture/) - *Coming in Phase 0*
- [Security Model](docs/security/) - *Coming in Phase 0*

## Contributing

This project is currently in early development. Contribution guidelines will be established during Phase 0.

## License

*License to be determined*

## Security

Security is our top priority. Please see our [Security Policy](SECURITY.md) for reporting vulnerabilities.

*Security documentation will be completed during Phase 0*
