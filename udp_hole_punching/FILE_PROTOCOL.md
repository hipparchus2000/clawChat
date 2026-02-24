# ClawChat File Protocol

Complete file manager protocol for secure file operations over encrypted UDP.

## Overview

The file protocol provides secure file operations between ClawChat client and server:
- **List** directory contents
- **Download** files (chunked for large files)
- **Upload** files (chunked for large files)
- **Delete** files and empty directories
- **Rename** files and directories
- **Mkdir** create new directories

## Message Types

| Message Type | Value | Description |
|-------------|-------|-------------|
| `FILE_LIST` | 0x50 | Request/response directory listing |
| `FILE_DOWNLOAD` | 0x51 | Request file download chunk |
| `FILE_UPLOAD` | 0x52 | Upload file chunk |
| `FILE_DELETE` | 0x53 | Delete file/directory |
| `FILE_RENAME` | 0x54 | Rename file/directory |
| `FILE_MKDIR` | 0x55 | Create directory |
| `FILE_STAT` | 0x56 | Get file info |

## Protocol Flow

### List Directory
```
Client -> Server: FILE_LIST {path: "."}
Server -> Client: FILE_LIST {success: true, items: [...]}
```

**Request:**
```json
{
  "path": "."  // Relative path from base directory
}
```

**Response:**
```json
{
  "success": true,
  "path": ".",
  "items": [
    {
      "name": "document.txt",
      "path": "document.txt",
      "size": 1024,
      "modified": 1705312800.0,
      "is_dir": false,
      "permissions": "-rw-r--r--"
    }
  ],
  "count": 1
}
```

### Download File
```
Client -> Server: FILE_DOWNLOAD {path: "file.txt", offset: 0}
Server -> Client: FILE_DOWNLOAD {success: true, data: "base64...", eof: false}
...
Client -> Server: FILE_DOWNLOAD {path: "file.txt", offset: 8192}
Server -> Client: FILE_DOWNLOAD {success: true, data: "base64...", eof: true}
```

**Request:**
```json
{
  "path": "file.txt",
  "offset": 0  // Byte offset for resuming
}
```

**Response:**
```json
{
  "success": true,
  "path": "file.txt",
  "data": "SGVsbG8gV29ybGQh...",  // Base64 encoded chunk
  "offset": 0,
  "size": 8192,
  "total_size": 16384,
  "eof": false,
  "hash": "a1b2c3d4..."  // SHA256 hash of chunk (first 16 chars)
}
```

### Upload File
```
Client -> Server: FILE_UPLOAD {path: "file.txt", data: "base64...", offset: 0}
Server -> Client: FILE_UPLOAD {success: true, bytes_written: 4096}
...
```

**Request:**
```json
{
  "path": "file.txt",
  "data": "SGVsbG8gV29ybGQh...",  // Base64 encoded chunk
  "offset": 0,
  "append": false  // true to append to existing file
}
```

**Response:**
```json
{
  "success": true,
  "path": "file.txt",
  "bytes_written": 4096,
  "offset": 0
}
```

### Delete
```json
// Request
{"path": "file.txt"}

// Response
{"success": true, "path": "file.txt", "message": "Deleted successfully"}
```

### Rename
```json
// Request
{"path": "old.txt", "new_name": "new.txt"}

// Response
{
  "success": true,
  "old_path": "old.txt",
  "new_path": "new.txt",
  "message": "Renamed successfully"
}
```

### Mkdir
```json
// Request
{"path": "new_folder"}

// Response
{"success": true, "path": "new_folder", "message": "Directory created"}
```

## Security

### Path Validation
- All paths are resolved relative to `CLAWCHAT_BASE_PATH`
- Directory traversal attempts (e.g., `../etc/passwd`) are rejected
- Absolute paths are rejected

### Write Protection
- `allow_write` parameter in `FileProtocolHandler` controls write operations
- When disabled, UPLOAD, DELETE, RENAME, MKDIR return `WRITE_DISABLED` error

### Base Path Configuration
```python
# Environment variable
CLAWCHAT_BASE_PATH=/path/to/allowed/directory

# Default: ./clawchat_data
```

## GUI Implementation

### File Tab Features
- **Tree View**: Name, Size, Modified, Type columns
- **Toolbar**: Up, Refresh, Download, Upload, Delete, Rename, New Folder
- **Navigation**: Double-click directories to enter
- **Status Bar**: Shows current operation status

### Operations
- **Refresh**: Sends `FILE_LIST` and populates tree
- **Download**: Chunked download with progress
- **Upload**: Chunked upload with progress
- **Delete**: Confirmation dialog before deleting
- **Rename**: Simple dialog for new name
- **New Folder**: Creates new directory

## Error Codes

| Code | Description |
|------|-------------|
| `INVALID_PATH` | Path contains traversal or is invalid |
| `NOT_FOUND` | Path does not exist |
| `NOT_DIRECTORY` | Path is not a directory (for LIST) |
| `IS_DIRECTORY` | Path is a directory (for DOWNLOAD) |
| `NOT_EMPTY` | Directory not empty (for DELETE) |
| `WRITE_DISABLED` | Write operations disabled |
| `LIST_ERROR` | Failed to list directory |
| `DOWNLOAD_ERROR` | Failed to download file |
| `UPLOAD_ERROR` | Failed to upload file |
| `DELETE_ERROR` | Failed to delete file |
| `RENAME_ERROR` | Failed to rename file |
| `MKDIR_ERROR` | Failed to create directory |
| `ALREADY_EXISTS` | Path already exists |
| `INVALID_NAME` | Invalid new name for rename |

## Implementation Files

| File | Description |
|------|-------------|
| `src/server/file_protocol_handler.py` | Server-side file protocol handler |
| `src/server/llm_server.py` | Server integration |
| `src/gui_client.py` | GUI client implementation |
| `src/protocol/messages.py` | Message type definitions |

## Testing

Run the file protocol handler standalone:
```bash
python src/server/file_protocol_handler.py
```

This runs built-in tests using a temporary directory.
