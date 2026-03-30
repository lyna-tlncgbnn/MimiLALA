import { spawn } from "node:child_process";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

import electron from "electron";

const { app, BrowserWindow } = electron;

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, "..", "..");
const preloadPath = path.resolve(__dirname, "preload.js");
const rendererUrl = process.env.AGENTBOT_UI_URL ?? "http://127.0.0.1:5173";

let backendProcess = null;

function startBackend() {
  const pythonExecutable = path.join(repoRoot, ".venv", "Scripts", "python.exe");
  backendProcess = spawn(
    pythonExecutable,
    ["-m", "uvicorn", "agentbot.api.app:app", "--host", "127.0.0.1", "--port", "8000"],
    {
      cwd: repoRoot,
      stdio: "inherit",
      windowsHide: true,
    },
  );
}

async function createWindow() {
  const window = new BrowserWindow({
    width: 1480,
    height: 960,
    minWidth: 1180,
    minHeight: 760,
    backgroundColor: "#f7f7f5",
    title: "AgentBot Desktop",
    webPreferences: {
      preload: preloadPath,
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  await window.loadURL(rendererUrl);
}

app.whenReady().then(async () => {
  startBackend();
  await createWindow();

  app.on("activate", async () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      await createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("before-quit", () => {
  if (backendProcess) {
    backendProcess.kill();
    backendProcess = null;
  }
});
