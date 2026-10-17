/**
 * AI Remote PC Desktop Viewer - Electron Main Process.
 * Manages native application windows, lifecycle events, and menu integration.
 */

const { app, BrowserWindow, Menu } = require('electron');
const path = require('path');

let mainWindow = null;

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1280,
        height: 850,
        minWidth: 800,
        minHeight: 600,
        title: 'AI Remote PC - Desktop Viewer',
        backgroundColor: '#0b0f19',
        autoHideMenuBar: true,
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            contextIsolation: true,
            nodeIntegration: false,
            sandbox: false // Allowed for preload argument parsing
        }
    });

    // Check for --host argument
    let initialHost = '';
    const hostArg = process.argv.find(arg => arg.startsWith('--host='));
    if (hostArg) {
        initialHost = hostArg.split('=')[1];
    } else if (process.env.REMOTE_HOST) {
        initialHost = process.env.REMOTE_HOST;
    }

    const htmlPath = path.join(__dirname, 'index.html');
    if (initialHost) {
        mainWindow.loadFile(htmlPath, { query: { host: initialHost } });
    } else {
        mainWindow.loadFile(htmlPath);
    }

    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}

// Ensure single instance lock
const gotTheLock = app.requestSingleInstanceLock();
if (!gotTheLock) {
    app.quit();
} else {
    app.on('second-instance', () => {
        if (mainWindow) {
            if (mainWindow.isMinimized()) mainWindow.restore();
            mainWindow.focus();
        }
    });

    app.whenReady().then(() => {
        createWindow();

        app.on('activate', () => {
            if (BrowserWindow.getAllWindows().length === 0) {
                createWindow();
            }
        });
    });
}

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});
