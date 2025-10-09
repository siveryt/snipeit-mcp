"""Snipe-IT MCP Server

A Model Context Protocol (MCP) server for managing Snipe-IT inventory.
Provides tools for CRUD operations on Assets and Consumables.
"""

import os
import logging
from typing import Literal, Annotated, Any
from pydantic import BaseModel, Field

from fastmcp import FastMCP
from snipeit import SnipeIT
from snipeit.exceptions import (
    SnipeITException,
    SnipeITNotFoundError,
    SnipeITAuthenticationError,
    SnipeITValidationError
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP(
    name="Snipe-IT MCP Server"
)

# Get Snipe-IT configuration from environment variables
SNIPEIT_URL = os.getenv("SNIPEIT_URL")
SNIPEIT_TOKEN = os.getenv("SNIPEIT_TOKEN")

if not SNIPEIT_URL or not SNIPEIT_TOKEN:
    logger.warning(
        "SNIPEIT_URL and SNIPEIT_TOKEN environment variables must be set. "
        "Server will start but tools will fail until these are configured."
    )

# Initialize Snipe-IT client (will be used in tools)
def get_snipeit_client() -> SnipeIT:
    """Get or create a Snipe-IT client instance."""
    if not SNIPEIT_URL or not SNIPEIT_TOKEN:
        raise SnipeITException(
            "Snipe-IT credentials not configured. "
            "Please set SNIPEIT_URL and SNIPEIT_TOKEN environment variables."
        )
    return SnipeIT(url=SNIPEIT_URL, token=SNIPEIT_TOKEN)


# ============================================================================
# Pydantic Models for Tool Input/Output
# ============================================================================

class AssetData(BaseModel):
    """Model for asset data used in create/update operations."""
    status_id: int | None = Field(None, description="ID of the status label")
    model_id: int | None = Field(None, description="ID of the asset model")
    asset_tag: str | None = Field(None, description="Asset tag identifier")
    name: str | None = Field(None, description="Asset name")
    serial: str | None = Field(None, description="Serial number")
    purchase_date: str | None = Field(None, description="Purchase date (YYYY-MM-DD)")
    purchase_cost: float | None = Field(None, description="Purchase cost")
    order_number: str | None = Field(None, description="Order number")
    notes: str | None = Field(None, description="Additional notes")
    warranty_months: int | None = Field(None, description="Warranty period in months")
    location_id: int | None = Field(None, description="Location ID")
    rtd_location_id: int | None = Field(None, description="Default location ID")
    supplier_id: int | None = Field(None, description="Supplier ID")
    company_id: int | None = Field(None, description="Company ID")
    requestable: bool | None = Field(None, description="Whether asset is requestable")


class CheckoutData(BaseModel):
    """Model for asset checkout operations."""
    checkout_to_type: Literal["user", "asset", "location"] = Field(
        ..., 
        description="Type of entity to checkout to"
    )
    assigned_to_id: int = Field(..., description="ID of the user/asset/location")
    expected_checkin: str | None = Field(None, description="Expected checkin date (YYYY-MM-DD)")
    checkout_at: str | None = Field(None, description="Checkout date (YYYY-MM-DD)")
    note: str | None = Field(None, description="Checkout notes")
    name: str | None = Field(None, description="Name for the checkout")


class CheckinData(BaseModel):
    """Model for asset checkin operations."""
    note: str | None = Field(None, description="Checkin notes")
    location_id: int | None = Field(None, description="Location ID to checkin to")


class AuditData(BaseModel):
    """Model for asset audit operations."""
    location_id: int | None = Field(None, description="Location ID")
    note: str | None = Field(None, description="Audit notes")
    next_audit_date: str | None = Field(None, description="Next audit date (YYYY-MM-DD)")


class MaintenanceData(BaseModel):
    """Model for asset maintenance records."""
    asset_improvement: str = Field(..., description="Type of maintenance/improvement")
    supplier_id: int = Field(..., description="Supplier ID")
    title: str = Field(..., description="Maintenance title")
    cost: float | None = Field(None, description="Maintenance cost")
    start_date: str | None = Field(None, description="Start date (YYYY-MM-DD)")
    completion_date: str | None = Field(None, description="Completion date (YYYY-MM-DD)")
    notes: str | None = Field(None, description="Maintenance notes")


class ConsumableData(BaseModel):
    """Model for consumable data used in create/update operations."""
    name: str | None = Field(None, description="Consumable name")
    qty: int | None = Field(None, description="Quantity")
    category_id: int | None = Field(None, description="Category ID")
    company_id: int | None = Field(None, description="Company ID")
    location_id: int | None = Field(None, description="Location ID")
    manufacturer_id: int | None = Field(None, description="Manufacturer ID")
    model_number: str | None = Field(None, description="Model number")
    item_no: str | None = Field(None, description="Item number")
    order_number: str | None = Field(None, description="Order number")
    purchase_date: str | None = Field(None, description="Purchase date (YYYY-MM-DD)")
    purchase_cost: float | None = Field(None, description="Purchase cost")
    min_amt: int | None = Field(None, description="Minimum quantity threshold")
    notes: str | None = Field(None, description="Additional notes")


# ============================================================================
# Asset Tools
# ============================================================================

@mcp.tool(
    annotations={
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": False,
    }
)
def manage_assets(
    action: Annotated[
        Literal["create", "get", "list", "update", "delete"],
        "The action to perform on assets"
    ],
    asset_id: Annotated[int | None, "Asset ID (required for get, update, delete)"] = None,
    asset_tag: Annotated[str | None, "Asset tag (alternative to asset_id for get)"] = None,
    serial: Annotated[str | None, "Serial number (alternative to asset_id for get)"] = None,
    asset_data: Annotated[AssetData | None, "Asset data (required for create, optional for update)"] = None,
    limit: Annotated[int | None, "Number of results to return (for list action)"] = 50,
    offset: Annotated[int | None, "Number of results to skip (for list action)"] = 0,
    search: Annotated[str | None, "Search query (for list action)"] = None,
    sort: Annotated[str | None, "Field to sort by (for list action)"] = None,
    order: Annotated[Literal["asc", "desc"] | None, "Sort order (for list action)"] = None,
) -> dict[str, Any]:
    """Manage Snipe-IT assets with CRUD operations.
    
    This tool handles all basic asset operations:
    - create: Create a new asset (requires asset_data with at least status_id and model_id)
    - get: Retrieve a single asset by ID, asset_tag, or serial number
    - list: List assets with optional pagination and filtering
    - update: Update an existing asset (requires asset_id and asset_data)
    - delete: Delete an asset (requires asset_id)
    
    Returns:
        dict: Result of the operation including success status and data
    """
    try:
        client = get_snipeit_client()
        
        with client:
            if action == "create":
                if not asset_data:
                    return {"success": False, "error": "asset_data is required for create action"}
                
                if not asset_data.status_id or not asset_data.model_id:
                    return {
                        "success": False,
                        "error": "status_id and model_id are required to create an asset"
                    }
                
                # Build creation payload
                create_kwargs = {k: v for k, v in asset_data.model_dump().items() if v is not None}
                asset = client.assets.create(**create_kwargs)
                
                return {
                    "success": True,
                    "action": "create",
                    "asset": {
                        "id": asset.id,
                        "asset_tag": getattr(asset, "asset_tag", None),
                        "name": getattr(asset, "name", None),
                        "serial": getattr(asset, "serial", None),
                    }
                }
            
            elif action == "get":
                if asset_tag:
                    asset = client.assets.get_by_tag(asset_tag)
                elif serial:
                    asset = client.assets.get_by_serial(serial)
                elif asset_id:
                    asset = client.assets.get(asset_id)
                else:
                    return {
                        "success": False,
                        "error": "One of asset_id, asset_tag, or serial is required for get action"
                    }
                
                # Extract asset data
                asset_dict = {
                    "id": asset.id,
                    "asset_tag": getattr(asset, "asset_tag", None),
                    "name": getattr(asset, "name", None),
                    "serial": getattr(asset, "serial", None),
                    "model": getattr(asset, "model", None),
                    "status_label": getattr(asset, "status_label", None),
                    "category": getattr(asset, "category", None),
                    "manufacturer": getattr(asset, "manufacturer", None),
                    "supplier": getattr(asset, "supplier", None),
                    "notes": getattr(asset, "notes", None),
                    "location": getattr(asset, "location", None),
                    "assigned_to": getattr(asset, "assigned_to", None),
                    "purchase_date": getattr(asset, "purchase_date", None),
                    "purchase_cost": getattr(asset, "purchase_cost", None),
                }
                
                return {
                    "success": True,
                    "action": "get",
                    "asset": asset_dict
                }
            
            elif action == "list":
                params = {"limit": limit, "offset": offset}
                if search:
                    params["search"] = search
                if sort:
                    params["sort"] = sort
                if order:
                    params["order"] = order
                
                assets = client.assets.list(**params)
                
                assets_list = [
                    {
                        "id": asset.id,
                        "asset_tag": getattr(asset, "asset_tag", None),
                        "name": getattr(asset, "name", None),
                        "serial": getattr(asset, "serial", None),
                        "model": getattr(asset, "model", {}).get("name") if hasattr(asset, "model") and isinstance(getattr(asset, "model", None), dict) else None,
                    }
                    for asset in assets
                ]
                
                return {
                    "success": True,
                    "action": "list",
                    "count": len(assets_list),
                    "assets": assets_list
                }
            
            elif action == "update":
                if not asset_id:
                    return {"success": False, "error": "asset_id is required for update action"}
                if not asset_data:
                    return {"success": False, "error": "asset_data is required for update action"}
                
                # Build update payload (only include non-None values)
                update_kwargs = {k: v for k, v in asset_data.model_dump().items() if v is not None}
                
                asset = client.assets.patch(asset_id, **update_kwargs)
                
                return {
                    "success": True,
                    "action": "update",
                    "asset": {
                        "id": asset.id,
                        "asset_tag": getattr(asset, "asset_tag", None),
                        "name": getattr(asset, "name", None),
                    }
                }
            
            elif action == "delete":
                if not asset_id:
                    return {"success": False, "error": "asset_id is required for delete action"}
                
                client.assets.delete(asset_id)
                
                return {
                    "success": True,
                    "action": "delete",
                    "asset_id": asset_id,
                    "message": "Asset deleted successfully"
                }
            
    except SnipeITNotFoundError as e:
        logger.error(f"Asset not found: {e}")
        return {"success": False, "error": f"Asset not found: {str(e)}"}
    except SnipeITAuthenticationError as e:
        logger.error(f"Authentication error: {e}")
        return {"success": False, "error": f"Authentication failed: {str(e)}"}
    except SnipeITValidationError as e:
        logger.error(f"Validation error: {e}")
        return {"success": False, "error": f"Validation error: {str(e)}"}
    except SnipeITException as e:
        logger.error(f"Snipe-IT error: {e}")
        return {"success": False, "error": f"Snipe-IT error: {str(e)}"}
    except Exception as e:
        logger.error(f"Unexpected error in manage_assets: {e}", exc_info=True)
        return {"success": False, "error": f"Unexpected error: {str(e)}"}


@mcp.tool(
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
    }
)
def asset_operations(
    action: Annotated[
        Literal["checkout", "checkin", "audit", "restore"],
        "The operation to perform on the asset"
    ],
    asset_id: Annotated[int, "Asset ID"],
    checkout_data: Annotated[CheckoutData | None, "Checkout details (required for checkout action)"] = None,
    checkin_data: Annotated[CheckinData | None, "Checkin details (optional for checkin action)"] = None,
    audit_data: Annotated[AuditData | None, "Audit details (optional for audit action)"] = None,
) -> dict[str, Any]:
    """Perform state operations on assets (checkout, checkin, audit, restore).
    
    Operations:
    - checkout: Check out an asset to a user, location, or another asset
    - checkin: Check in an asset back to inventory
    - audit: Mark an asset as audited
    - restore: Restore a soft-deleted asset
    
    Returns:
        dict: Result of the operation including success status and data
    """
    try:
        client = get_snipeit_client()
        
        with client:
            asset = client.assets.get(asset_id)
            
            if action == "checkout":
                if not checkout_data:
                    return {"success": False, "error": "checkout_data is required for checkout action"}
                
                # Build checkout kwargs
                checkout_kwargs = {
                    "checkout_to_type": checkout_data.checkout_to_type,
                    "assigned_to_id": checkout_data.assigned_to_id,
                }
                
                if checkout_data.expected_checkin:
                    checkout_kwargs["expected_checkin"] = checkout_data.expected_checkin
                if checkout_data.checkout_at:
                    checkout_kwargs["checkout_at"] = checkout_data.checkout_at
                if checkout_data.note:
                    checkout_kwargs["note"] = checkout_data.note
                if checkout_data.name:
                    checkout_kwargs["name"] = checkout_data.name
                
                updated_asset = asset.checkout(**checkout_kwargs)
                
                return {
                    "success": True,
                    "action": "checkout",
                    "asset_id": asset_id,
                    "message": f"Asset checked out to {checkout_data.checkout_to_type} {checkout_data.assigned_to_id}",
                    "asset": {
                        "id": updated_asset.id,
                        "asset_tag": getattr(updated_asset, "asset_tag", None),
                        "assigned_to": getattr(updated_asset, "assigned_to", None),
                    }
                }
            
            elif action == "checkin":
                checkin_kwargs = {}
                if checkin_data:
                    if checkin_data.note:
                        checkin_kwargs["note"] = checkin_data.note
                    if checkin_data.location_id:
                        checkin_kwargs["location_id"] = checkin_data.location_id
                
                updated_asset = asset.checkin(**checkin_kwargs)
                
                return {
                    "success": True,
                    "action": "checkin",
                    "asset_id": asset_id,
                    "message": "Asset checked in successfully",
                    "asset": {
                        "id": updated_asset.id,
                        "asset_tag": getattr(updated_asset, "asset_tag", None),
                    }
                }
            
            elif action == "audit":
                audit_kwargs = {}
                if audit_data:
                    if audit_data.location_id:
                        audit_kwargs["location_id"] = audit_data.location_id
                    if audit_data.note:
                        audit_kwargs["note"] = audit_data.note
                    if audit_data.next_audit_date:
                        audit_kwargs["next_audit_date"] = audit_data.next_audit_date
                
                updated_asset = asset.audit(**audit_kwargs)
                
                return {
                    "success": True,
                    "action": "audit",
                    "asset_id": asset_id,
                    "message": "Asset audited successfully",
                    "asset": {
                        "id": updated_asset.id,
                        "asset_tag": getattr(updated_asset, "asset_tag", None),
                    }
                }
            
            elif action == "restore":
                updated_asset = asset.restore()
                
                return {
                    "success": True,
                    "action": "restore",
                    "asset_id": asset_id,
                    "message": "Asset restored successfully",
                    "asset": {
                        "id": updated_asset.id,
                        "asset_tag": getattr(updated_asset, "asset_tag", None),
                    }
                }
    
    except SnipeITNotFoundError as e:
        logger.error(f"Asset not found: {e}")
        return {"success": False, "error": f"Asset not found: {str(e)}"}
    except SnipeITException as e:
        logger.error(f"Snipe-IT error: {e}")
        return {"success": False, "error": f"Snipe-IT error: {str(e)}"}
    except Exception as e:
        logger.error(f"Unexpected error in asset_operations: {e}", exc_info=True)
        return {"success": False, "error": f"Unexpected error: {str(e)}"}


@mcp.tool(
    annotations={
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": False,
    }
)
def asset_files(
    action: Annotated[
        Literal["upload", "list", "download", "delete"],
        "The file operation to perform"
    ],
    asset_id: Annotated[int, "Asset ID"],
    file_paths: Annotated[list[str] | None, "List of file paths to upload (for upload action)"] = None,
    notes: Annotated[str | None, "Notes for uploaded files (for upload action)"] = None,
    file_id: Annotated[int | None, "File ID (required for download and delete actions)"] = None,
    save_path: Annotated[str | None, "Path to save downloaded file (for download action)"] = None,
) -> dict[str, Any]:
    """Manage file attachments for assets.
    
    Operations:
    - upload: Upload one or more files to an asset
    - list: List all files attached to an asset
    - download: Download a specific file from an asset
    - delete: Delete a specific file from an asset
    
    Returns:
        dict: Result of the operation including success status and data
    """
    try:
        client = get_snipeit_client()
        
        with client:
            if action == "upload":
                if not file_paths:
                    return {"success": False, "error": "file_paths is required for upload action"}
                
                result = client.assets.upload_files(asset_id, file_paths, notes)
                
                return {
                    "success": True,
                    "action": "upload",
                    "asset_id": asset_id,
                    "message": f"Uploaded {len(file_paths)} file(s) successfully",
                    "result": result
                }
            
            elif action == "list":
                result = client.assets.list_files(asset_id)
                
                return {
                    "success": True,
                    "action": "list",
                    "asset_id": asset_id,
                    "files": result
                }
            
            elif action == "download":
                if file_id is None:
                    return {"success": False, "error": "file_id is required for download action"}
                if not save_path:
                    return {"success": False, "error": "save_path is required for download action"}
                
                downloaded_path = client.assets.download_file(asset_id, file_id, save_path)
                
                return {
                    "success": True,
                    "action": "download",
                    "asset_id": asset_id,
                    "file_id": file_id,
                    "saved_to": downloaded_path,
                    "message": f"File downloaded to {downloaded_path}"
                }
            
            elif action == "delete":
                if file_id is None:
                    return {"success": False, "error": "file_id is required for delete action"}
                
                client.assets.delete_file(asset_id, file_id)
                
                return {
                    "success": True,
                    "action": "delete",
                    "asset_id": asset_id,
                    "file_id": file_id,
                    "message": "File deleted successfully"
                }
    
    except SnipeITNotFoundError as e:
        logger.error(f"Asset or file not found: {e}")
        return {"success": False, "error": f"Not found: {str(e)}"}
    except SnipeITException as e:
        logger.error(f"Snipe-IT error: {e}")
        return {"success": False, "error": f"Snipe-IT error: {str(e)}"}
    except Exception as e:
        logger.error(f"Unexpected error in asset_files: {e}", exc_info=True)
        return {"success": False, "error": f"Unexpected error: {str(e)}"}


@mcp.tool(
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
    }
)
def asset_labels(
    asset_ids: Annotated[list[int] | None, "List of asset IDs to generate labels for"] = None,
    asset_tags: Annotated[list[str] | None, "List of asset tags to generate labels for"] = None,
    save_path: Annotated[str, "Path where the PDF labels file should be saved"] = "/tmp/asset_labels.pdf",
) -> dict[str, Any]:
    """Generate printable labels for assets.
    
    Provide either asset_ids or asset_tags to generate labels for specific assets.
    The labels will be saved as a PDF file to the specified save_path.
    
    Returns:
        dict: Result with path to generated labels PDF
    """
    try:
        client = get_snipeit_client()
        
        if not asset_ids and not asset_tags:
            return {
                "success": False,
                "error": "Either asset_ids or asset_tags must be provided"
            }
        
        with client:
            # If asset_ids provided, get the Asset objects
            if asset_ids:
                assets = [client.assets.get(asset_id) for asset_id in asset_ids]
                saved_path = client.assets.labels(save_path, assets)
            else:
                # Use asset_tags directly
                saved_path = client.assets.labels(save_path, asset_tags)
            
            return {
                "success": True,
                "action": "generate_labels",
                "saved_to": saved_path,
                "message": f"Labels generated and saved to {saved_path}"
            }
    
    except SnipeITNotFoundError as e:
        logger.error(f"Asset not found: {e}")
        return {"success": False, "error": f"Asset not found: {str(e)}"}
    except SnipeITException as e:
        logger.error(f"Snipe-IT error: {e}")
        return {"success": False, "error": f"Snipe-IT error: {str(e)}"}
    except Exception as e:
        logger.error(f"Unexpected error in asset_labels: {e}", exc_info=True)
        return {"success": False, "error": f"Unexpected error: {str(e)}"}


@mcp.tool(
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
    }
)
def asset_maintenance(
    action: Annotated[
        Literal["create"],
        "The maintenance operation to perform (currently only create is supported)"
    ],
    asset_id: Annotated[int, "Asset ID"],
    maintenance_data: Annotated[MaintenanceData, "Maintenance record data (required for create action)"],
) -> dict[str, Any]:
    """Manage maintenance records for assets.
    
    Currently supports:
    - create: Create a new maintenance record for an asset
    
    Returns:
        dict: Result of the operation including success status and data
    """
    try:
        client = get_snipeit_client()
        
        with client:
            if action == "create":
                # Build maintenance payload
                maintenance_kwargs = {
                    "asset_id": asset_id,
                    "asset_improvement": maintenance_data.asset_improvement,
                    "supplier_id": maintenance_data.supplier_id,
                    "title": maintenance_data.title,
                }
                
                if maintenance_data.cost is not None:
                    maintenance_kwargs["cost"] = maintenance_data.cost
                if maintenance_data.start_date:
                    maintenance_kwargs["start_date"] = maintenance_data.start_date
                if maintenance_data.completion_date:
                    maintenance_kwargs["completion_date"] = maintenance_data.completion_date
                if maintenance_data.notes:
                    maintenance_kwargs["notes"] = maintenance_data.notes
                
                result = client.assets.create_maintenance(**maintenance_kwargs)
                
                return {
                    "success": True,
                    "action": "create",
                    "asset_id": asset_id,
                    "message": "Maintenance record created successfully",
                    "maintenance": result
                }
    
    except SnipeITNotFoundError as e:
        logger.error(f"Asset not found: {e}")
        return {"success": False, "error": f"Asset not found: {str(e)}"}
    except SnipeITException as e:
        logger.error(f"Snipe-IT error: {e}")
        return {"success": False, "error": f"Snipe-IT error: {str(e)}"}
    except Exception as e:
        logger.error(f"Unexpected error in asset_maintenance: {e}", exc_info=True)
        return {"success": False, "error": f"Unexpected error: {str(e)}"}


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
    }
)
def asset_licenses(
    asset_id: Annotated[int, "Asset ID"],
) -> dict[str, Any]:
    """Get all licenses checked out to an asset.
    
    Returns:
        dict: List of licenses associated with the asset
    """
    try:
        client = get_snipeit_client()
        
        with client:
            result = client.assets.get_licenses(asset_id)
            
            return {
                "success": True,
                "asset_id": asset_id,
                "licenses": result
            }
    
    except SnipeITNotFoundError as e:
        logger.error(f"Asset not found: {e}")
        return {"success": False, "error": f"Asset not found: {str(e)}"}
    except SnipeITException as e:
        logger.error(f"Snipe-IT error: {e}")
        return {"success": False, "error": f"Snipe-IT error: {str(e)}"}
    except Exception as e:
        logger.error(f"Unexpected error in asset_licenses: {e}", exc_info=True)
        return {"success": False, "error": f"Unexpected error: {str(e)}"}


# ============================================================================
# Consumable Tools
# ============================================================================

@mcp.tool(
    annotations={
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": False,
    }
)
def manage_consumables(
    action: Annotated[
        Literal["create", "get", "list", "update", "delete"],
        "The action to perform on consumables"
    ],
    consumable_id: Annotated[int | None, "Consumable ID (required for get, update, delete)"] = None,
    consumable_data: Annotated[ConsumableData | None, "Consumable data (required for create, optional for update)"] = None,
    limit: Annotated[int | None, "Number of results to return (for list action)"] = 50,
    offset: Annotated[int | None, "Number of results to skip (for list action)"] = 0,
    search: Annotated[str | None, "Search query (for list action)"] = None,
    sort: Annotated[str | None, "Field to sort by (for list action)"] = None,
    order: Annotated[Literal["asc", "desc"] | None, "Sort order (for list action)"] = None,
) -> dict[str, Any]:
    """Manage Snipe-IT consumables with CRUD operations.
    
    This tool handles all basic consumable operations:
    - create: Create a new consumable (requires consumable_data with name, qty, and category_id)
    - get: Retrieve a single consumable by ID
    - list: List consumables with optional pagination and filtering
    - update: Update an existing consumable (requires consumable_id and consumable_data)
    - delete: Delete a consumable (requires consumable_id)
    
    Returns:
        dict: Result of the operation including success status and data
    """
    try:
        client = get_snipeit_client()
        
        with client:
            if action == "create":
                if not consumable_data:
                    return {"success": False, "error": "consumable_data is required for create action"}
                
                if not consumable_data.name or consumable_data.qty is None or not consumable_data.category_id:
                    return {
                        "success": False,
                        "error": "name, qty, and category_id are required to create a consumable"
                    }
                
                # Build creation payload
                create_kwargs = {k: v for k, v in consumable_data.model_dump().items() if v is not None}
                consumable = client.consumables.create(**create_kwargs)
                
                return {
                    "success": True,
                    "action": "create",
                    "consumable": {
                        "id": consumable.id,
                        "name": getattr(consumable, "name", None),
                        "qty": getattr(consumable, "qty", None),
                    }
                }
            
            elif action == "get":
                if not consumable_id:
                    return {"success": False, "error": "consumable_id is required for get action"}
                
                consumable = client.consumables.get(consumable_id)
                
                # Extract consumable data
                consumable_dict = {
                    "id": consumable.id,
                    "name": getattr(consumable, "name", None),
                    "qty": getattr(consumable, "qty", None),
                    "category": getattr(consumable, "category", None),
                    "company": getattr(consumable, "company", None),
                    "location": getattr(consumable, "location", None),
                    "manufacturer": getattr(consumable, "manufacturer", None),
                    "model_number": getattr(consumable, "model_number", None),
                    "item_no": getattr(consumable, "item_no", None),
                    "order_number": getattr(consumable, "order_number", None),
                    "purchase_date": getattr(consumable, "purchase_date", None),
                    "purchase_cost": getattr(consumable, "purchase_cost", None),
                    "min_amt": getattr(consumable, "min_amt", None),
                    "remaining": getattr(consumable, "remaining", None),
                }
                
                return {
                    "success": True,
                    "action": "get",
                    "consumable": consumable_dict
                }
            
            elif action == "list":
                params = {"limit": limit, "offset": offset}
                if search:
                    params["search"] = search
                if sort:
                    params["sort"] = sort
                if order:
                    params["order"] = order
                
                consumables = client.consumables.list(**params)
                
                consumables_list = [
                    {
                        "id": consumable.id,
                        "name": getattr(consumable, "name", None),
                        "qty": getattr(consumable, "qty", None),
                        "remaining": getattr(consumable, "remaining", None),
                    }
                    for consumable in consumables
                ]
                
                return {
                    "success": True,
                    "action": "list",
                    "count": len(consumables_list),
                    "consumables": consumables_list
                }
            
            elif action == "update":
                if not consumable_id:
                    return {"success": False, "error": "consumable_id is required for update action"}
                if not consumable_data:
                    return {"success": False, "error": "consumable_data is required for update action"}
                
                # Build update payload (only include non-None values)
                update_kwargs = {k: v for k, v in consumable_data.model_dump().items() if v is not None}
                
                consumable = client.consumables.patch(consumable_id, **update_kwargs)
                
                return {
                    "success": True,
                    "action": "update",
                    "consumable": {
                        "id": consumable.id,
                        "name": getattr(consumable, "name", None),
                        "qty": getattr(consumable, "qty", None),
                    }
                }
            
            elif action == "delete":
                if not consumable_id:
                    return {"success": False, "error": "consumable_id is required for delete action"}
                
                client.consumables.delete(consumable_id)
                
                return {
                    "success": True,
                    "action": "delete",
                    "consumable_id": consumable_id,
                    "message": "Consumable deleted successfully"
                }
    
    except SnipeITNotFoundError as e:
        logger.error(f"Consumable not found: {e}")
        return {"success": False, "error": f"Consumable not found: {str(e)}"}
    except SnipeITAuthenticationError as e:
        logger.error(f"Authentication error: {e}")
        return {"success": False, "error": f"Authentication failed: {str(e)}"}
    except SnipeITValidationError as e:
        logger.error(f"Validation error: {e}")
        return {"success": False, "error": f"Validation error: {str(e)}"}
    except SnipeITException as e:
        logger.error(f"Snipe-IT error: {e}")
        return {"success": False, "error": f"Snipe-IT error: {str(e)}"}
    except Exception as e:
        logger.error(f"Unexpected error in manage_consumables: {e}", exc_info=True)
        return {"success": False, "error": f"Unexpected error: {str(e)}"}


# ============================================================================
# Server Entry Point
# ============================================================================

if __name__ == "__main__":
    # Run the server with stdio transport (default for MCP)
    mcp.run(transport="stdio")
