#!/usr/bin/env node

const fs = require("node:fs");
const fsp = require("node:fs/promises");
const http = require("node:http");
const os = require("node:os");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const { spawn, spawnSync } = require("node:child_process");

const DEFAULT_CHROME_PATHS = [
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  "/Applications/Chromium.app/Contents/MacOS/Chromium",
  "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
  "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
];

function parseArgs(argv) {
  const args = {
    width: 1280,
    height: 720,
    duration: 7.2,
    fps: 30,
    fragments: 0,
    startDelay: 0,
    crf: 20,
    keepFrames: false,
    showRevealUi: false,
    format: null,
  };

  for (let i = 2; i < argv.length; i += 1) {
    const arg = argv[i];
    const next = () => {
      i += 1;
      if (i >= argv.length) throw new Error(`Missing value for ${arg}`);
      return argv[i];
    };

    if (arg === "--html") args.html = next();
    else if (arg === "--out") args.out = next();
    else if (arg === "--hash") args.hash = next();
    else if (arg === "--selector") args.selector = next();
    else if (arg === "--clip-selector") args.clipSelector = next();
    else if (arg === "--duration") args.duration = Number(next());
    else if (arg === "--fps") args.fps = Number(next());
    else if (arg === "--width") args.width = Number(next());
    else if (arg === "--height") args.height = Number(next());
    else if (arg === "--fragments") args.fragments = Number(next());
    else if (arg === "--start-delay") args.startDelay = Number(next());
    else if (arg === "--crf") args.crf = Number(next());
    else if (arg === "--chrome") args.chrome = next();
    else if (arg === "--format") args.format = next();
    else if (arg === "--frames-dir") args.framesDir = next();
    else if (arg === "--keep-frames") args.keepFrames = true;
    else if (arg === "--show-reveal-ui") args.showRevealUi = true;
    else if (arg === "--help" || arg === "-h") {
      printHelp();
      process.exit(0);
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }

  if (!args.html) throw new Error("Missing --html");
  if (!args.out) throw new Error("Missing --out");
  if (!Number.isFinite(args.duration) || args.duration <= 0) throw new Error("--duration must be positive");
  if (!Number.isFinite(args.fps) || args.fps <= 0) throw new Error("--fps must be positive");
  if (!Number.isFinite(args.width) || args.width <= 0) throw new Error("--width must be positive");
  if (!Number.isFinite(args.height) || args.height <= 0) throw new Error("--height must be positive");
  if (!Number.isFinite(args.fragments) || args.fragments < 0) throw new Error("--fragments must be >= 0");

  args.width = Math.round(args.width);
  args.height = Math.round(args.height);
  args.fps = Math.round(args.fps);
  args.fragments = Math.round(args.fragments);

  if (!args.format) {
    const ext = path.extname(args.out).toLowerCase();
    args.format = ext === ".gif" ? "gif" : "mp4";
  }
  if (!["mp4", "gif"].includes(args.format)) throw new Error("--format must be mp4 or gif");

  return args;
}

function printHelp() {
  console.log(`Usage:
  node scripts/export_reveal_animation.js --html SLIDES.html --hash '#/slide-id' --out movie.mp4 [options]

Options:
  --duration SECONDS       Capture duration, default 7.2
  --fps FPS                Output frame rate, default 30
  --width PX               Browser viewport width, default 1280
  --height PX              Browser viewport height, default 720
  --fragments N            Reveal N fragments before capture
  --start-delay SECONDS    Wait after navigation/fragments before capture
  --selector CSS           Wait until selector exists before capture
  --clip-selector CSS      Crop capture to an element
  --show-reveal-ui         Keep Reveal controls/progress/slide number visible
  --chrome PATH            Chrome/Chromium executable
  --format mp4|gif         Defaults from output extension
  --frames-dir DIR         Use this directory for PNG frames
  --keep-frames            Do not delete captured PNG frames
`);
}

function findExecutable(command) {
  const result = spawnSync("which", [command], { encoding: "utf8" });
  return result.status === 0 ? result.stdout.trim() : null;
}

function findChrome(explicitPath) {
  if (explicitPath) return explicitPath;
  if (process.env.CHROME_PATH) return process.env.CHROME_PATH;

  const fromPath = findExecutable("google-chrome") || findExecutable("chromium") || findExecutable("chrome");
  if (fromPath) return fromPath;

  for (const candidate of DEFAULT_CHROME_PATHS) {
    if (fs.existsSync(candidate)) return candidate;
  }

  throw new Error("Chrome/Chromium executable not found. Pass --chrome or set CHROME_PATH.");
}

function htmlToUrl(html, hash) {
  let url;
  if (/^https?:\/\//.test(html) || /^file:\/\//.test(html)) {
    url = html;
  } else {
    url = pathToFileURL(path.resolve(html)).href;
  }

  if (hash) {
    const cleanHash = hash.startsWith("#") ? hash : `#${hash}`;
    url = `${url.split("#")[0]}${cleanHash}`;
  }

  return url;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function waitForDevtools(chrome, timeoutMs = 10000) {
  return new Promise((resolve, reject) => {
    let stderr = "";
    const timeout = setTimeout(() => {
      reject(new Error(`Timed out waiting for Chrome DevTools endpoint. stderr:\n${stderr}`));
    }, timeoutMs);

    chrome.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
      const match = stderr.match(/DevTools listening on (ws:\/\/[^\s]+)/);
      if (match) {
        clearTimeout(timeout);
        resolve(match[1]);
      }
    });

    chrome.once("exit", (code) => {
      clearTimeout(timeout);
      reject(new Error(`Chrome exited before DevTools endpoint was ready, code ${code}. stderr:\n${stderr}`));
    });
  });
}

class CdpConnection {
  constructor(url) {
    this.url = url;
    this.socket = null;
    this.nextId = 1;
    this.pending = new Map();
    this.waiters = [];
  }

  async connect() {
    this.socket = new WebSocket(this.url);
    await new Promise((resolve, reject) => {
      this.socket.addEventListener("open", resolve, { once: true });
      this.socket.addEventListener("error", reject, { once: true });
    });

    this.socket.addEventListener("message", async (event) => {
      const text = typeof event.data === "string" ? event.data : await event.data.text();
      const message = JSON.parse(text);

      if (message.id && this.pending.has(message.id)) {
        const { resolve, reject } = this.pending.get(message.id);
        this.pending.delete(message.id);
        if (message.error) reject(new Error(`${message.error.message || "CDP error"}: ${JSON.stringify(message.error)}`));
        else resolve(message.result || {});
        return;
      }

      for (const waiter of [...this.waiters]) {
        if (waiter.method !== message.method) continue;
        if (waiter.sessionId && waiter.sessionId !== message.sessionId) continue;
        if (waiter.predicate && !waiter.predicate(message.params || {})) continue;
        clearTimeout(waiter.timeout);
        this.waiters = this.waiters.filter((item) => item !== waiter);
        waiter.resolve(message.params || {});
      }
    });
  }

  send(method, params = {}, sessionId = undefined) {
    const id = this.nextId;
    this.nextId += 1;
    const payload = sessionId ? { id, method, params, sessionId } : { id, method, params };

    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.socket.send(JSON.stringify(payload));
    });
  }

  waitFor(method, sessionId = undefined, timeoutMs = 15000, predicate = null) {
    return new Promise((resolve, reject) => {
      const waiter = {
        method,
        sessionId,
        predicate,
        resolve,
        timeout: setTimeout(() => {
          this.waiters = this.waiters.filter((item) => item !== waiter);
          reject(new Error(`Timed out waiting for ${method}`));
        }, timeoutMs),
      };
      this.waiters.push(waiter);
    });
  }

  close() {
    if (this.socket) this.socket.close();
  }
}

async function evaluate(cdp, sessionId, expression, awaitPromise = true) {
  const result = await cdp.send("Runtime.evaluate", {
    expression,
    awaitPromise,
    returnByValue: true,
  }, sessionId);

  if (result.exceptionDetails) {
    throw new Error(`Evaluation failed: ${JSON.stringify(result.exceptionDetails)}`);
  }
  return result.result ? result.result.value : undefined;
}

async function setupReveal(cdp, sessionId, args) {
  await evaluate(cdp, sessionId, `
    (async () => {
      if (document.readyState !== "complete") {
        await new Promise((resolve) => window.addEventListener("load", resolve, { once: true }));
      }
      if (window.Reveal) {
        if (typeof Reveal.isReady === "function" && !Reveal.isReady()) {
          await new Promise((resolve) => Reveal.on("ready", resolve));
        }
        if (typeof Reveal.layout === "function") Reveal.layout();
      }
    })()
  `);

  if (!args.showRevealUi) {
    await evaluate(cdp, sessionId, `
      (() => {
        const style = document.createElement("style");
        style.dataset.exportRevealAnimation = "true";
        style.textContent = [
          ".reveal .controls{display:none!important}",
          ".reveal .progress{display:none!important}",
          ".reveal .slide-number{display:none!important}",
          ".slide-menu-button{display:none!important}",
          ".chalkboard-button{display:none!important}",
          ".reveal-menu-button{display:none!important}",
          ".nh-slide-footer{display:none!important}"
        ].join("\\n");
        document.head.appendChild(style);
      })()
    `, false);
  }

  if (args.fragments > 0) {
    await evaluate(cdp, sessionId, `
      (async () => {
        for (let i = 0; i < ${args.fragments}; i += 1) {
          if (window.Reveal && typeof Reveal.nextFragment === "function") {
            Reveal.nextFragment();
          }
          await new Promise((resolve) => setTimeout(resolve, 130));
        }
      })()
    `);
  }

  if (args.selector) {
    await evaluate(cdp, sessionId, `
      (async () => {
        const selector = ${JSON.stringify(args.selector)};
        const deadline = performance.now() + 10000;
        while (!document.querySelector(selector)) {
          if (performance.now() > deadline) throw new Error("Selector not found: " + selector);
          await new Promise((resolve) => setTimeout(resolve, 100));
        }
      })()
    `);
  }

  if (args.startDelay > 0) {
    await sleep(args.startDelay * 1000);
  }
}

async function clipForSelector(cdp, sessionId, selector) {
  if (!selector) return null;

  const rect = await evaluate(cdp, sessionId, `
    (() => {
      const element = document.querySelector(${JSON.stringify(selector)});
      if (!element) throw new Error("Clip selector not found: " + ${JSON.stringify(selector)});
      const rect = element.getBoundingClientRect();
      return {
        x: Math.max(0, rect.x),
        y: Math.max(0, rect.y),
        width: Math.max(1, rect.width),
        height: Math.max(1, rect.height),
        scale: 1
      };
    })()
  `);

  return rect;
}

async function captureFrames(cdp, sessionId, args, framesDir) {
  const frameCount = Math.ceil(args.duration * args.fps);
  const pad = String(frameCount).length < 5 ? 5 : String(frameCount).length;
  const clip = await clipForSelector(cdp, sessionId, args.clipSelector);
  const start = Date.now();

  for (let i = 0; i < frameCount; i += 1) {
    const targetTime = start + (i * 1000) / args.fps;
    const wait = targetTime - Date.now();
    if (wait > 0) await sleep(wait);

    const screenshot = await cdp.send("Page.captureScreenshot", {
      format: "png",
      fromSurface: true,
      captureBeyondViewport: false,
      ...(clip ? { clip } : {}),
    }, sessionId);
    const name = `frame_${String(i + 1).padStart(pad, "0")}.png`;
    await fsp.writeFile(path.join(framesDir, name), Buffer.from(screenshot.data, "base64"));

    if ((i + 1) % Math.max(1, Math.round(args.fps)) === 0 || i + 1 === frameCount) {
      process.stderr.write(`Captured ${i + 1}/${frameCount} frames\r`);
    }
  }
  process.stderr.write("\n");
  return { frameCount, pad };
}

function runCommand(command, args, cwd = process.cwd()) {
  const result = spawnSync(command, args, { cwd, stdio: "inherit" });
  if (result.status !== 0) {
    throw new Error(`${command} failed with status ${result.status}`);
  }
}

async function terminateProcess(child) {
  if (!child || child.exitCode !== null || child.signalCode !== null) return;

  const exited = new Promise((resolve) => {
    child.once("exit", resolve);
  });

  child.kill("SIGTERM");
  await Promise.race([exited, sleep(2000)]);

  if (child.exitCode === null && child.signalCode === null) {
    child.kill("SIGKILL");
    await Promise.race([exited, sleep(1000)]);
  }
}

async function encodeVideo(args, framesDir, pad) {
  await fsp.mkdir(path.dirname(path.resolve(args.out)), { recursive: true });
  const input = path.join(framesDir, `frame_%0${pad}d.png`);

  if (args.format === "gif") {
    const palette = path.join(framesDir, "palette.png");
    runCommand("ffmpeg", [
      "-y",
      "-framerate", String(args.fps),
      "-i", input,
      "-vf", `fps=${args.fps},scale=${args.width}:-1:flags=lanczos,palettegen`,
      palette,
    ]);
    runCommand("ffmpeg", [
      "-y",
      "-framerate", String(args.fps),
      "-i", input,
      "-i", palette,
      "-lavfi", `fps=${args.fps},scale=${args.width}:-1:flags=lanczos[x];[x][1:v]paletteuse`,
      args.out,
    ]);
    return;
  }

  runCommand("ffmpeg", [
    "-y",
    "-framerate", String(args.fps),
    "-i", input,
    "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
    "-c:v", "libx264",
    "-pix_fmt", "yuv420p",
    "-crf", String(args.crf),
    "-movflags", "+faststart",
    args.out,
  ]);
}

async function main() {
  const args = parseArgs(process.argv);
  const ffmpeg = findExecutable("ffmpeg");
  if (!ffmpeg) throw new Error("ffmpeg not found in PATH");

  const chromePath = findChrome(args.chrome);
  const url = htmlToUrl(args.html, args.hash);
  const userDataDir = await fsp.mkdtemp(path.join(os.tmpdir(), "reveal-export-chrome-"));
  const framesDir = args.framesDir
    ? path.resolve(args.framesDir)
    : await fsp.mkdtemp(path.join(os.tmpdir(), "reveal-export-frames-"));

  await fsp.mkdir(framesDir, { recursive: true });

  const chrome = spawn(chromePath, [
    "--headless=new",
    "--remote-debugging-port=0",
    `--user-data-dir=${userDataDir}`,
    `--window-size=${args.width},${args.height}`,
    "--allow-file-access-from-files",
    "--autoplay-policy=no-user-gesture-required",
    "--disable-background-timer-throttling",
    "--disable-backgrounding-occluded-windows",
    "--disable-renderer-backgrounding",
    "--disable-dev-shm-usage",
    "--hide-scrollbars",
    "--mute-audio",
    "--no-first-run",
    "--no-default-browser-check",
    "about:blank",
  ], { stdio: ["ignore", "ignore", "pipe"] });

  let cdp;
  try {
    const wsUrl = await waitForDevtools(chrome);
    cdp = new CdpConnection(wsUrl);
    await cdp.connect();

    const { targetId } = await cdp.send("Target.createTarget", {
      url: "about:blank",
    });
    const { sessionId } = await cdp.send("Target.attachToTarget", {
      targetId,
      flatten: true,
    });

    await cdp.send("Page.enable", {}, sessionId);
    await cdp.send("Runtime.enable", {}, sessionId);
    await cdp.send("Emulation.setDeviceMetricsOverride", {
      width: args.width,
      height: args.height,
      deviceScaleFactor: 1,
      mobile: false,
      screenWidth: args.width,
      screenHeight: args.height,
    }, sessionId);

    const loadEvent = cdp.waitFor("Page.loadEventFired", sessionId, 30000);
    await cdp.send("Page.navigate", { url }, sessionId);
    await loadEvent;

    await setupReveal(cdp, sessionId, args);
    const { pad } = await captureFrames(cdp, sessionId, args, framesDir);
    await encodeVideo(args, framesDir, pad);

    console.log(`Created ${args.out}`);
    if (args.keepFrames || args.framesDir) console.log(`Frames: ${framesDir}`);
  } finally {
    if (cdp) cdp.close();
    await terminateProcess(chrome);
    if (!args.keepFrames && !args.framesDir) await fsp.rm(framesDir, { recursive: true, force: true }).catch(() => {});
    await fsp.rm(userDataDir, { recursive: true, force: true }).catch(() => {});
  }
}

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
