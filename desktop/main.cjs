const { app, BrowserWindow, dialog, Menu, shell } = require("electron");
const { execFile } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");
const { promisify } = require("node:util");

const runFile = promisify(execFile);
const projectRoot = path.resolve(
  process.env.STUDIO_ROOT ||
    (app.isPackaged ? path.join(path.dirname(process.execPath), "../../..") : path.join(__dirname, ".."))
);
const python = process.env.STUDIO_PYTHON ||
  path.join(projectRoot, "runtime/official/code/venv/Scripts/python.exe");
const clientScript = path.join(projectRoot, "scripts/studio_cli.py");
const smokeArgument = process.argv.find((argument) => argument.startsWith("--smoke-output="));
const smokeOutput = smokeArgument ? path.resolve(smokeArgument.slice("--smoke-output=".length)) : null;

let window = null;
let runtime = null;
let lease = null;
let heartbeat = null;
let closing = false;
let starting = false;
const loadedModels = [];

fs.mkdirSync(path.join(projectRoot, "local_data/desktop"), { recursive: true });
fs.mkdirSync(path.join(projectRoot, "logs"), { recursive: true });
app.setPath("userData", path.join(projectRoot, "local_data/desktop"));
app.setName("Phanes Studio");
app.setAppUserModelId("local.phanes.studio");

function log(message) {
  fs.appendFileSync(
    path.join(projectRoot, "logs/studio-desktop.log"),
    `${new Date().toISOString()} ${message}\n`,
    "utf8"
  );
}

async function request(method, route, body) {
  const response = await fetch(runtime.url + route, {
    method,
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
    signal: AbortSignal.timeout(15000)
  });
  const result = await response.json();
  if (!response.ok) {
    throw new Error(result.detail || `Studio respondeu com erro ${response.status}`);
  }
  return result;
}

async function registerWindow() {
  lease = await request("POST", "/api/runtime/clients", { kind: "desktop", pid: process.pid });
  heartbeat = setInterval(async () => {
    try {
      await request("PUT", `/api/runtime/clients/${lease.client_id}`);
    } catch (error) {
      log(`Heartbeat: ${error.message}`);
      if (!closing && !starting) {
        clearInterval(heartbeat);
        lease = null;
        await startStudio();
      }
    }
  }, 10000);
}

async function releaseWindow() {
  clearInterval(heartbeat);
  if (runtime && lease) {
    try {
      await request("DELETE", `/api/runtime/clients/${lease.client_id}`);
    } catch (error) {
      log(`Release: ${error.message}`);
    }
    lease = null;
  }
}

function allowedNavigation(url) {
  if (!runtime) {
    return false;
  }
  try {
    return new URL(url).origin === runtime.url;
  } catch {
    return false;
  }
}

async function startStudio() {
  if (starting || closing) {
    return;
  }
  starting = true;
  try {
    await window.loadFile(path.join(__dirname, "loading.html"));
    const result = await runFile(python, [clientScript, "--root", projectRoot, "start", "--ui"], {
      cwd: projectRoot,
      windowsHide: true,
      timeout: 180000,
      maxBuffer: 1024 * 1024,
      env: { ...process.env, PYTHONUTF8: "1" }
    });
    runtime = JSON.parse(result.stdout.trim());
    await registerWindow();
    await window.loadURL(runtime.url);
    log(`Connected to ${runtime.instance_id} at ${runtime.url}`);
    if (smokeOutput) {
      await validateDesktop();
    }
  } catch (error) {
    if (closing) {
      return;
    }
    log(`Startup: ${error.stack || error.message}`);
    await releaseWindow();
    if (smokeOutput) {
      fs.writeFileSync(smokeOutput, JSON.stringify({ ok: false, error: error.message }, null, 2));
      closing = true;
      app.exit(1);
      return;
    }
    starting = false;
    while (!closing) {
      const answer = await dialog.showMessageBox(window, {
        type: "error",
        title: "Não foi possível iniciar o Phanes Studio",
        message: "O Phanes Studio não conseguiu abrir.",
        detail: error.stderr || error.message,
        buttons: ["Tentar novamente", "Abrir registros", "Fechar"],
        defaultId: 0,
        cancelId: 2
      });
      if (answer.response === 0) {
        await startStudio();
        break;
      }
      if (answer.response === 1) {
        await shell.openPath(path.join(projectRoot, "logs"));
      } else {
        closing = true;
        window.close();
      }
    }
  } finally {
    starting = false;
  }
}

async function closeStudio(event) {
  if (closing) {
    return;
  }
  event.preventDefault();
  if (starting) {
    closing = true;
    await releaseWindow();
    window.destroy();
    app.quit();
    return;
  }
  try {
    if (runtime && !smokeOutput) {
      const status = await request("GET", "/api/runtime");
      if (status.work.running || (status.work.pending && !status.work.paused)) {
        const answer = await dialog.showMessageBox(window, {
          type: "info",
          title: "Processamento em andamento",
          message: "O processamento continuará com a janela fechada.",
          detail: "Você pode acompanhar os pedidos pelo Studio ou pelo cliente para agentes.",
          buttons: ["Fechar e continuar", "Voltar ao Studio"],
          defaultId: 0,
          cancelId: 1
        });
        if (answer.response === 1) {
          return;
        }
      }
    }
  } catch (error) {
    log(`Close: ${error.message}`);
  }
  closing = true;
  await releaseWindow();
  window.destroy();
  app.quit();
}

async function validateDesktop() {
  const deadline = Date.now() + 45000;
  let state;
  while (Date.now() < deadline) {
    state = await window.webContents.executeJavaScript(`(() => {
      const text = document.body.innerText;
      const canvas = document.createElement("canvas");
      const webgl = Boolean(canvas.getContext("webgl2") || canvas.getContext("webgl"));
      return {
        title: document.title,
        branded: document.title === "Phanes Studio" && text.includes("Phanes Studio"),
        modelHistory: text.includes("Histórico · high e low-poly"),
        imageHistory: text.includes("Histórico de imagens utilizadas"),
        queue: text.includes("Adicionar imagens à fila"),
        populated: Array.from(document.querySelectorAll("button")).some(
          (button) => /(?:HIGH|LOW|Rejeitado) ·/.test(button.innerText)
        ),
        webgl
      };
    })()`);
    if (state.modelHistory && state.imageHistory && state.queue && state.populated) {
      break;
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  if (state.populated) {
    await window.webContents.executeJavaScript(`(() => {
      const button = Array.from(document.querySelectorAll("button")).find(
        (item) => /(?:HIGH|LOW) ·/.test(item.innerText)
      );
      if (button) button.click();
    })()`);
    const viewerDeadline = Date.now() + 60000;
    while (Date.now() < viewerDeadline) {
      const viewer = await window.webContents.executeJavaScript(`(() => {
        const canvas = document.querySelector("canvas");
        if (!canvas) return null;
        const bounds = canvas.getBoundingClientRect();
        return { x: Math.ceil(bounds.x), y: Math.ceil(bounds.y),
          width: Math.floor(bounds.width), height: Math.floor(bounds.height) };
      })()`);
      if (viewer && viewer.width > 0 && viewer.height > 0 && loadedModels.length > 0) {
        const frame = await window.webContents.capturePage(viewer);
        const pixels = frame.toBitmap();
        const colors = new Set();
        for (let index = 0; index < pixels.length; index += 64) {
          colors.add(`${pixels[index]},${pixels[index + 1]},${pixels[index + 2]}`);
        }
        state.viewerColors = colors.size;
        state.glbLoaded = true;
        state.modelOpened = colors.size > 100;
        if (state.modelOpened) {
          break;
        }
      }
      await new Promise((resolve) => setTimeout(resolve, 500));
    }
    await new Promise((resolve) => setTimeout(resolve, 2000));
  }
  const screenshot = smokeOutput.replace(/\.json$/i, ".png");
  const image = await window.webContents.capturePage();
  fs.writeFileSync(screenshot, image.toPNG());
  const ok = Boolean(state.branded && state.modelHistory && state.imageHistory && state.queue && state.webgl && state.populated && state.modelOpened);
  fs.writeFileSync(smokeOutput, JSON.stringify({
    ok,
    ...state,
    applicationName: app.getName(),
    windowTitle: window.getTitle(),
    executable: process.execPath,
    runtime,
    screenshot
  }, null, 2));
  if (!ok) {
    throw new Error("A interface desktop não passou na verificação visual");
  }
  closing = true;
  await releaseWindow();
  app.exit(0);
}

function createWindow() {
  window = new BrowserWindow({
    title: "Phanes Studio",
    icon: path.join(__dirname, "assets/phanes-studio-minimal.ico"),
    width: 1600,
    height: 1000,
    minWidth: 1050,
    minHeight: 720,
    show: !smokeOutput,
    backgroundColor: "#19191e",
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      backgroundThrottling: !smokeOutput
    }
  });
  window.on("close", closeStudio);
  window.on("page-title-updated", (event) => {
    event.preventDefault();
    window.setTitle("Phanes Studio");
  });
  window.webContents.on("will-navigate", (event, url) => {
    if (!allowedNavigation(url)) {
      event.preventDefault();
    }
  });
  window.webContents.setWindowOpenHandler(() => ({ action: "deny" }));
  const session = window.webContents.session;
  if (smokeOutput) {
    session.webRequest.onCompleted((details) => {
      if (details.url.includes(".glb") && details.statusCode === 200) {
        loadedModels.push(details.url);
      }
    });
  }
  session.setPermissionRequestHandler((_contents, _permission, callback) => callback(false));
  session.setPermissionCheckHandler(() => false);
  session.on("will-download", (_event, item) => {
    item.setSaveDialogOptions({
      title: "Salvar arquivo do Phanes Studio",
      defaultPath: path.join(app.getPath("downloads"), item.getFilename())
    });
  });
  Menu.setApplicationMenu(Menu.buildFromTemplate([
    { label: "Phanes Studio", submenu: [
      { label: "Abrir pasta de resultados", click: () => shell.openPath(path.join(projectRoot, "outputs")) },
      { label: "Abrir registros", click: () => shell.openPath(path.join(projectRoot, "logs")) },
      { type: "separator" },
      { label: "Fechar", accelerator: "Alt+F4", click: () => window.close() }
    ] },
    { label: "Editar", submenu: [
      { role: "undo", label: "Desfazer" }, { role: "redo", label: "Refazer" },
      { type: "separator" }, { role: "cut", label: "Recortar" },
      { role: "copy", label: "Copiar" }, { role: "paste", label: "Colar" },
      { role: "selectAll", label: "Selecionar tudo" }
    ] },
    { label: "Exibir", submenu: [
      { role: "reload", label: "Recarregar" }, { role: "resetZoom", label: "Zoom padrão" },
      { role: "zoomIn", label: "Aumentar" }, { role: "zoomOut", label: "Diminuir" },
      { role: "togglefullscreen", label: "Tela cheia" }
    ] }
  ]));
  startStudio();
}

if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (window) {
      if (window.isMinimized()) {
        window.restore();
      }
      window.show();
      window.focus();
    }
  });
  app.on("window-all-closed", () => app.quit());
  app.whenReady().then(createWindow);
}
