#!/usr/bin/env python3
"""
ClawChat File System API - Example Usage
=========================================
Demonstrates various ways to use the File System API.
"""

import asyncio
import json
from datetime import datetime

# Import the File API modules
from file_api import create_file_api, FileSystemAPI
from security import PermissionLevel, initialize_security
from path_validator import PathValidator, initialize_validator


async def example_direct_usage():
    """Example: Using the API directly (without WebSocket)."""
    print("=" * 60)
    print("Example 1: Direct API Usage")
    print("=" * 60)
    
    # Create API instance
    api = create_file_api(
        root_directory="/root/.openclaw/workspace/projects/",
        allow_hidden=False,
        require_auth=False
    )
    
    # Get the service
    service = api.get_service()
    security = api.get_security()
    
    # Create a security context
    context = security.create_context(
        user_id="demo_user",
        ip_address="127.0.0.1",
        permissions=[PermissionLevel.READ, PermissionLevel.LIST, PermissionLevel.DOWNLOAD]
    )
    
    # 1. List root directory
    print("\n1. Listing root directory:")
    response = await service.list_directory("/", context)
    
    if response.success:
        listing = response.data
        print(f"   Path: {listing.path}")
        print(f"   Total items: {listing.total_count}")
        print(f"   Files: {listing.file_count}, Directories: {listing.directory_count}")
        print("   Contents:")
        for item in listing.items[:5]:  # Show first 5
            icon = "📁" if item.type == "directory" else "📄"
            size = f"({item.size} bytes)" if item.type == "file" else ""
            print(f"     {icon} {item.name} {size}")
        if len(listing.items) > 5:
            print(f"     ... and {len(listing.items) - 5} more")
    else:
        print(f"   Error: {response.error}")
    
    # 2. Get metadata for a specific item
    if response.success and listing.items:
        first_item = listing.items[0]
        print(f"\n2. Getting metadata for '{first_item.name}':")
        meta_response = await service.get_file_metadata(first_item.path, context)
        
        if meta_response.success:
            meta = meta_response.data
            print(f"   Name: {meta.name}")
            print(f"   Type: {meta.type}")
            print(f"   Size: {meta.size} bytes")
            print(f"   Modified: {datetime.fromtimestamp(meta.modified_time)}")
            print(f"   Permissions: {meta.permissions}")
            print(f"   MIME Type: {meta.mime_type or 'N/A'}")
        else:
            print(f"   Error: {meta_response.error}")
    
    # 3. List a subdirectory (clawchat project)
    print("\n3. Listing 'clawchat' project directory:")
    subdir_response = await service.list_directory("clawchat", context)
    
    if subdir_response.success:
        subdir = subdir_response.data
        print(f"   Contents of clawchat/:")
        for item in subdir.items[:10]:
            icon = "📁" if item.type == "directory" else "📄"
            print(f"     {icon} {item.name}")
    else:
        print(f"   Error: {subdir_response.error}")
    
    print("\n" + "=" * 60)


async def example_websocket_simulation():
    """Example: Simulating WebSocket messages."""
    print("\nExample 2: Simulated WebSocket Usage")
    print("=" * 60)
    
    # Create API
    api = create_file_api(
        root_directory="/root/.openclaw/workspace/projects/",
        allow_hidden=False,
        require_auth=False
    )
    
    # Store responses
    responses = []
    
    async def mock_send(data):
        """Mock WebSocket send function."""
        responses.append(data)
        # Pretty print the response
        print(f"\n   Response:")
        print(f"   {json.dumps(data, indent=2, default=str)[:500]}...")
    
    client_info = {
        'ip_address': '127.0.0.1',
        'user_id': 'demo_user'
    }
    
    # Simulate different WebSocket messages
    
    # 1. Ping
    print("\n1. Sending ping:")
    await api.handle_websocket_message(
        message={'action': 'ping'},
        client_info=client_info,
        send_callback=mock_send
    )
    
    # 2. List directory
    print("\n2. Requesting directory listing:")
    await api.handle_websocket_message(
        message={
            'action': 'list_directory',
            'path': '/'
        },
        client_info=client_info,
        send_callback=mock_send
    )
    
    # 3. Get metadata
    print("\n3. Requesting file metadata:")
    await api.handle_websocket_message(
        message={
            'action': 'get_metadata',
            'path': 'clawchat'
        },
        client_info=client_info,
        send_callback=mock_send
    )
    
    # 4. Download request
    print("\n4. Requesting file download info:")
    # First, let's check what files exist in clawchat
    responses.clear()
    await api.handle_websocket_message(
        message={
            'action': 'list_directory',
            'path': 'clawchat'
        },
        client_info=client_info,
        send_callback=mock_send
    )
    
    # Try to download a file if one exists
    if responses and responses[-1].get('success'):
        items = responses[-1].get('data', {}).get('items', [])
        files = [i for i in items if i.get('type') == 'file']
        if files:
            target_file = files[0]['path']
            print(f"\n   Attempting to download: {target_file}")
            responses.clear()
            await api.handle_websocket_message(
                message={
                    'action': 'download_file',
                    'path': target_file
                },
                client_info=client_info,
                send_callback=mock_send
            )
    
    # 5. Test security - attempt directory traversal
    print("\n5. Testing security (directory traversal attempt):")
    responses.clear()
    await api.handle_websocket_message(
        message={
            'action': 'list_directory',
            'path': '../../../etc/passwd'
        },
        client_info=client_info,
        send_callback=mock_send
    )
    
    # 6. Invalid action
    print("\n6. Testing unknown action:")
    responses.clear()
    await api.handle_websocket_message(
        message={
            'action': 'delete_everything'
        },
        client_info=client_info,
        send_callback=mock_send
    )
    
    print("\n" + "=" * 60)


async def example_security_features():
    """Example: Security and permission features."""
    print("\nExample 3: Security Features")
    print("=" * 60)
    
    from path_validator import PathValidator, DirectoryTraversalError
    from security import SecurityManager, PermissionLevel
    
    # 1. Path Validation
    print("\n1. Path Validation:")
    validator = PathValidator(
        root_directory="/tmp",
        allow_hidden=False
    )
    
    # Valid path
    try:
        result = validator.validate("documents/file.txt")
        print(f"   ✓ Valid path: {result}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Directory traversal attempt
    try:
        result = validator.validate("../../../etc/passwd")
        print(f"   ✗ Should have been blocked!")
    except DirectoryTraversalError:
        print("   ✓ Directory traversal attack blocked!")
    
    # Hidden file blocked
    try:
        result = validator.validate(".hidden_file")
        print(f"   ✗ Should have been blocked!")
    except Exception as e:
        print(f"   ✓ Hidden file blocked: {e}")
    
    # 2. Permissions
    print("\n2. Permission System:")
    security = SecurityManager(require_auth=False)
    
    # Read-only user
    read_only = security.create_context(
        user_id="readonly_user",
        permissions=[PermissionLevel.READ, PermissionLevel.LIST]
    )
    print(f"   Read-only user can read: {read_only.can_read()}")
    print(f"   Read-only user can write: {read_only.can_write()}")
    print(f"   Read-only user can download: {read_only.can_download()}")
    
    # Admin user
    admin = security.create_context(
        user_id="admin_user",
        permissions=[PermissionLevel.ADMIN]
    )
    print(f"   Admin user has full access: {admin.has_permission(PermissionLevel.DELETE)}")
    
    # 3. Rate Limiting
    print("\n3. Rate Limiting:")
    limiter = security.list_rate_limiter
    
    key = "test_client"
    allowed_count = 0
    for i in range(15):
        allowed = await limiter.is_allowed(key)
        if allowed:
            allowed_count += 1
    
    remaining = await limiter.get_remaining(key)
    print(f"   Requests allowed: {allowed_count}")
    print(f"   Remaining: {remaining}")
    
    print("\n" + "=" * 60)


async def example_configuration():
    """Example: Configuration options."""
    print("\nExample 4: Configuration")
    print("=" * 60)
    
    from file_api_config import FileAPIConfig
    
    # Development configuration
    print("\n1. Development Config:")
    dev_config = FileAPIConfig.for_development()
    print(f"   Allow hidden: {dev_config.ALLOW_HIDDEN_FILES}")
    print(f"   Require auth: {dev_config.REQUIRE_AUTHENTICATION}")
    print(f"   Log level: {dev_config.LOG_LEVEL}")
    
    # Production configuration
    print("\n2. Production Config:")
    prod_config = FileAPIConfig.for_production(secret_key="secret123")
    print(f"   Allow hidden: {prod_config.ALLOW_HIDDEN_FILES}")
    print(f"   Require auth: {prod_config.REQUIRE_AUTHENTICATION}")
    print(f"   Secret key set: {prod_config.SECRET_KEY is not None}")
    
    # Environment-based configuration
    print("\n3. Environment Config:")
    import os
    os.environ['FILE_API_LOG_LEVEL'] = 'DEBUG'
    os.environ['FILE_API_ALLOW_HIDDEN'] = 'true'
    
    env_config = FileAPIConfig.from_environment()
    print(f"   Log level from env: {env_config.LOG_LEVEL}")
    print(f"   Allow hidden from env: {env_config.ALLOW_HIDDEN_FILES}")
    
    print("\n" + "=" * 60)


async def main():
    """Run all examples."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "ClawChat File System API" + " " * 19 + "║")
    print("║" + " " * 12 + "Usage Examples & Demonstration" + " " * 16 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    try:
        await example_direct_usage()
        await example_websocket_simulation()
        await example_security_features()
        await example_configuration()
        
        print("\n")
        print("╔" + "=" * 58 + "╗")
        print("║" + " " * 18 + "All examples completed!" + " " * 17 + "║")
        print("╚" + "=" * 58 + "╝")
        print()
        
    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
