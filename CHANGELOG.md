# Changelog

All notable changes to the Snipe-IT MCP Server will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-10-09

### Added
- Initial implementation of Snipe-IT MCP Server
- `manage_assets` tool for comprehensive asset CRUD operations
  - Create, get, list, update, and delete assets
  - Support for searching by ID, asset tag, or serial number
  - Pagination and filtering for list operations
- `asset_operations` tool for asset state management
  - Checkout assets to users, locations, or other assets
  - Checkin assets back to inventory
  - Audit assets with optional audit date
  - Restore soft-deleted assets
- `asset_files` tool for file attachment management
  - Upload multiple files to assets
  - List all files attached to an asset
  - Download specific files from assets
  - Delete file attachments
- `asset_labels` tool for generating printable PDF labels
  - Support for generating labels by asset IDs or asset tags
  - Customizable save path for PDF output
- `asset_maintenance` tool for maintenance record management
  - Create maintenance records with cost, dates, and notes
- `asset_licenses` tool for viewing licenses associated with assets
- `manage_consumables` tool for comprehensive consumable CRUD operations
  - Create, get, list, update, and delete consumables
  - Pagination and filtering support
- Comprehensive error handling with structured responses
- Logging configuration for debugging and monitoring
- Environment variable configuration for Snipe-IT credentials
- Type-safe Pydantic models for all tool inputs
- Comprehensive README documentation with examples
- MCP client integration guides for Claude Desktop and Cursor

### Technical Details
- Built with FastMCP 2.x
- Uses snipeit-python-api for backend API communication
- Python 3.11+ required
- UV package manager support
- Stdio transport for MCP communication

[0.1.0]: https://github.com/yourusername/snipeit-mcp/releases/tag/v0.1.0
