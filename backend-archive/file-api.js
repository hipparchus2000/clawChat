/**
 * ClawChat File System API - Node.js Version
 * 
 * Provides directory listing, file metadata, and download capabilities.
 */

const fs = require('fs').promises;
const path = require('path');
const crypto = require('crypto');

class FileAPI {
    constructor(basePath = '/home/openclaw/.openclaw/workspace/projects') {
        this.basePath = path.resolve(basePath);
        this.ensureBasePath();
    }
    
    async ensureBasePath() {
        try {
            await fs.access(this.basePath);
        } catch (error) {
            console.warn(`Base path ${this.basePath} doesn't exist, creating...`);
            await fs.mkdir(this.basePath, { recursive: true });
        }
    }
    
    async listDirectory(dirPath = '.') {
        try {
            const absolutePath = this.resolvePath(dirPath);
            const stats = await fs.stat(absolutePath);
            
            if (!stats.isDirectory()) {
                throw new Error('Path is not a directory');
            }
            
            const items = await fs.readdir(absolutePath, { withFileTypes: true });
            const fileItems = [];
            
            for (const item of items) {
                try {
                    const itemPath = path.join(absolutePath, item.name);
                    const itemStats = await fs.stat(itemPath);
                    const isHidden = item.name.startsWith('.');
                    
                    const fileItem = {
                        name: item.name,
                        path: this.getRelativePath(itemPath),
                        type: item.isDirectory() ? 'directory' : 'file',
                        size: itemStats.size,
                        modifiedTime: itemStats.mtime.getTime(),
                        createdTime: itemStats.birthtime.getTime(),
                        permissions: this.getPermissions(itemStats),
                        isHidden: isHidden,
                        extension: item.isDirectory() ? null : path.extname(item.name).toLowerCase(),
                        mimeType: this.getMimeType(item.name)
                    };
                    
                    fileItems.push(fileItem);
                } catch (error) {
                    console.warn(`Error reading item ${item.name}: ${error.message}`);
                }
            }
            
            // Sort: directories first, then files, alphabetically
            fileItems.sort((a, b) => {
                if (a.type === 'directory' && b.type !== 'directory') return -1;
                if (a.type !== 'directory' && b.type === 'directory') return 1;
                return a.name.localeCompare(b.name);
            });
            
            const directoryCount = fileItems.filter(item => item.type === 'directory').length;
            const fileCount = fileItems.filter(item => item.type === 'file').length;
            const hiddenCount = fileItems.filter(item => item.isHidden).length;
            
            return {
                success: true,
                data: {
                    path: this.getRelativePath(absolutePath),
                    items: fileItems,
                    totalCount: fileItems.length,
                    fileCount: fileCount,
                    directoryCount: directoryCount,
                    hiddenCount: hiddenCount,
                    parentPath: this.getParentPath(absolutePath)
                },
                timestamp: Date.now()
            };
            
        } catch (error) {
            console.error(`Error listing directory ${dirPath}: ${error.message}`);
            return {
                success: false,
                error: error.message,
                errorCode: 'DIRECTORY_LIST_ERROR',
                timestamp: Date.now()
            };
        }
    }
    
    async getFileContent(filePath) {
        try {
            const absolutePath = this.resolvePath(filePath);
            const stats = await fs.stat(absolutePath);
            
            if (stats.isDirectory()) {
                throw new Error('Path is a directory, not a file');
            }
            
            // Check file size (limit to 10MB for now)
            if (stats.size > 10 * 1024 * 1024) {
                throw new Error('File too large (max 10MB)');
            }
            
            const content = await fs.readFile(absolutePath, 'utf8');
            const extension = path.extname(filePath).toLowerCase();
            
            return {
                success: true,
                data: {
                    path: this.getRelativePath(absolutePath),
                    name: path.basename(filePath),
                    content: content,
                    size: stats.size,
                    modifiedTime: stats.mtime.getTime(),
                    createdTime: stats.birthtime.getTime(),
                    extension: extension,
                    mimeType: this.getMimeType(filePath),
                    encoding: 'utf8'
                },
                timestamp: Date.now()
            };
            
        } catch (error) {
            console.error(`Error reading file ${filePath}: ${error.message}`);
            return {
                success: false,
                error: error.message,
                errorCode: 'FILE_READ_ERROR',
                timestamp: Date.now()
            };
        }
    }
    
    async saveFile(filePath, content) {
        try {
            const absolutePath = this.resolvePath(filePath);
            const dirPath = path.dirname(absolutePath);
            
            // Ensure directory exists
            await fs.mkdir(dirPath, { recursive: true });
            
            // Write file
            await fs.writeFile(absolutePath, content, 'utf8');
            
            // Get updated stats
            const stats = await fs.stat(absolutePath);
            
            return {
                success: true,
                data: {
                    path: this.getRelativePath(absolutePath),
                    name: path.basename(filePath),
                    size: stats.size,
                    modifiedTime: stats.mtime.getTime(),
                    createdTime: stats.birthtime.getTime()
                },
                timestamp: Date.now()
            };
            
        } catch (error) {
            console.error(`Error saving file ${filePath}: ${error.message}`);
            return {
                success: false,
                error: error.message,
                errorCode: 'FILE_WRITE_ERROR',
                timestamp: Date.now()
            };
        }
    }
    
    async createDirectory(dirPath) {
        try {
            const absolutePath = this.resolvePath(dirPath);
            
            // Check if already exists
            try {
                const stats = await fs.stat(absolutePath);
                if (stats.isDirectory()) {
                    return {
                        success: true,
                        data: {
                            path: this.getRelativePath(absolutePath),
                            message: 'Directory already exists'
                        },
                        timestamp: Date.now()
                    };
                } else {
                    throw new Error('Path exists but is not a directory');
                }
            } catch {
                // Directory doesn't exist, create it
                await fs.mkdir(absolutePath, { recursive: true });
                
                const stats = await fs.stat(absolutePath);
                
                return {
                    success: true,
                    data: {
                        path: this.getRelativePath(absolutePath),
                        name: path.basename(dirPath),
                        createdTime: stats.birthtime.getTime(),
                        modifiedTime: stats.mtime.getTime()
                    },
                    timestamp: Date.now()
                };
            }
            
        } catch (error) {
            console.error(`Error creating directory ${dirPath}: ${error.message}`);
            return {
                success: false,
                error: error.message,
                errorCode: 'DIRECTORY_CREATE_ERROR',
                timestamp: Date.now()
            };
        }
    }
    
    async deletePath(targetPath) {
        try {
            const absolutePath = this.resolvePath(targetPath);
            const stats = await fs.stat(absolutePath);
            
            if (stats.isDirectory()) {
                // Check if directory is empty
                const items = await fs.readdir(absolutePath);
                if (items.length > 0) {
                    throw new Error('Directory is not empty');
                }
                await fs.rmdir(absolutePath);
            } else {
                await fs.unlink(absolutePath);
            }
            
            return {
                success: true,
                data: {
                    path: this.getRelativePath(absolutePath),
                    type: stats.isDirectory() ? 'directory' : 'file',
                    deleted: true
                },
                timestamp: Date.now()
            };
            
        } catch (error) {
            console.error(`Error deleting ${targetPath}: ${error.message}`);
            return {
                success: false,
                error: error.message,
                errorCode: 'DELETE_ERROR',
                timestamp: Date.now()
            };
        }
    }
    
    async renamePath(oldPath, newName) {
        try {
            const absoluteOldPath = this.resolvePath(oldPath);
            const dirPath = path.dirname(absoluteOldPath);
            const absoluteNewPath = path.join(dirPath, newName);
            
            // Check if new name already exists
            try {
                await fs.access(absoluteNewPath);
                throw new Error('Target name already exists');
            } catch {
                // Target doesn't exist, proceed
            }
            
            await fs.rename(absoluteOldPath, absoluteNewPath);
            
            const stats = await fs.stat(absoluteNewPath);
            
            return {
                success: true,
                data: {
                    oldPath: this.getRelativePath(absoluteOldPath),
                    newPath: this.getRelativePath(absoluteNewPath),
                    name: newName,
                    type: stats.isDirectory() ? 'directory' : 'file',
                    modifiedTime: stats.mtime.getTime()
                },
                timestamp: Date.now()
            };
            
        } catch (error) {
            console.error(`Error renaming ${oldPath} to ${newName}: ${error.message}`);
            return {
                success: false,
                error: error.message,
                errorCode: 'RENAME_ERROR',
                timestamp: Date.now()
            };
        }
    }
    
    resolvePath(requestedPath) {
        let resolvedPath;
        
        if (path.isAbsolute(requestedPath)) {
            resolvedPath = path.resolve(requestedPath);
        } else {
            resolvedPath = path.resolve(this.basePath, requestedPath);
        }
        
        // Security check: ensure path is within basePath
        if (!resolvedPath.startsWith(this.basePath)) {
            throw new Error('Path traversal attempt detected');
        }
        
        return resolvedPath;
    }
    
    getRelativePath(absolutePath) {
        return path.relative(this.basePath, absolutePath) || '.';
    }
    
    getParentPath(absolutePath) {
        if (absolutePath === this.basePath) {
            return null;
        }
        const parent = path.dirname(absolutePath);
        return this.getRelativePath(parent);
    }
    
    getPermissions(stats) {
        const mode = stats.mode;
        const perms = [];
        
        perms.push(stats.isDirectory() ? 'd' : '-');
        perms.push(mode & 0o400 ? 'r' : '-');
        perms.push(mode & 0o200 ? 'w' : '-');
        perms.push(mode & 0o100 ? 'x' : '-');
        perms.push(mode & 0o040 ? 'r' : '-');
        perms.push(mode & 0o020 ? 'w' : '-');
        perms.push(mode & 0o010 ? 'x' : '-');
        perms.push(mode & 0o004 ? 'r' : '-');
        perms.push(mode & 0o002 ? 'w' : '-');
        perms.push(mode & 0o001 ? 'x' : '-');
        
        return perms.join('');
    }
    
    getMimeType(filename) {
        const ext = path.extname(filename).toLowerCase();
        const mimeTypes = {
            '.txt': 'text/plain',
            '.html': 'text/html',
            '.htm': 'text/html',
            '.css': 'text/css',
            '.js': 'application/javascript',
            '.json': 'application/json',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.svg': 'image/svg+xml',
            '.pdf': 'application/pdf',
            '.md': 'text/markdown',
            '.py': 'text/x-python',
            '.java': 'text/x-java',
            '.c': 'text/x-c',
            '.cpp': 'text/x-c++',
            '.h': 'text/x-c',
            '.cs': 'text/x-csharp',
            '.php': 'application/x-php',
            '.xml': 'application/xml',
            '.csv': 'text/csv',
            '.yml': 'application/x-yaml',
            '.yaml': 'application/x-yaml'
        };
        
        return mimeTypes[ext] || 'application/octet-stream';
    }
    
    async getStats() {
        try {
            const stats = await fs.stat(this.basePath);
            
            // Get total file count recursively (simplified)
            async function countFiles(dir) {
                let total = 0;
                const items = await fs.readdir(dir, { withFileTypes: true });
                
                for (const item of items) {
                    if (item.isDirectory()) {
                        total += await countFiles(path.join(dir, item.name));
                    } else {
                        total++;
                    }
                }
                
                return total;
            }
            
            const totalFiles = await countFiles(this.basePath);
            
            return {
                success: true,
                data: {
                    basePath: this.basePath,
                    totalFiles: totalFiles,
                    totalSize: stats.size,
                    createdTime: stats.birthtime.getTime(),
                    modifiedTime: stats.mtime.getTime()
                },
                timestamp: Date.now()
            };
            
        } catch (error) {
            console.error(`Error getting stats: ${error.message}`);
            return {
                success: false,
                error: error.message,
                errorCode: 'STATS_ERROR',
                timestamp: Date.now()
            };
        }
    }
}

module.exports = FileAPI;