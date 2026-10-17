/**
 * Electron Preload Script for AI Remote PC Desktop Viewer.
 * Securely exposes limited system context and environment settings
 * to the renderer process via contextBridge.
 */

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
    platform: process.platform,
    version: process.versions.electron,
    getHostArg: () => {
        // Look for --host=<host> command line argument
        const hostArg = process.argv.find(arg => arg.startsWith('--host='));
        if (hostArg) {
            return hostArg.split('=')[1];
        }
        return null;
    }
});
