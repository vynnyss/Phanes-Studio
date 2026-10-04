const fs = require("node:fs");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const electronDirectory = path.join(__dirname, "node_modules/electron/dist");
const destination = path.join(__dirname, "dist/3DStudio");
const applicationName = "Phanes Studio";
const executable = path.join(destination, `${applicationName}.exe`);
const icon = path.join(__dirname, "assets/phanes-studio-minimal.ico");
if (!fs.existsSync(path.join(electronDirectory, "electron.exe"))) {
  throw new Error("Install the local Electron dependency before packaging");
}
if (!fs.existsSync(icon)) {
  throw new Error("The Phanes Studio icon is missing");
}
fs.mkdirSync(destination, { recursive: true });
const permissions = spawnSync("powershell.exe", ["-NoProfile", "-Command", `
  $taskRules = (Get-Acl -LiteralPath $env:STUDIO_PACKAGE_DIRECTORY).GetAccessRules(
    $true, $true, [System.Security.Principal.SecurityIdentifier]
  );
  $taskAllowed = $taskRules | Where-Object {
    $_.IdentityReference.Value -eq 'S-1-15-2-1'
  };
  if ($taskAllowed) { exit 0 }
  & icacls.exe $env:STUDIO_PACKAGE_DIRECTORY /grant '*S-1-15-2-1:(OI)(CI)(RX)';
  exit $LASTEXITCODE
`], {
  windowsHide: true,
  env: { ...process.env, STUDIO_PACKAGE_DIRECTORY: destination },
  encoding: "utf8"
});
if (permissions.status !== 0) {
  throw new Error(`Cannot prepare Electron sandbox permissions: ${permissions.stderr || permissions.stdout}`);
}
fs.cpSync(electronDirectory, destination, { recursive: true });
const appDirectory = path.join(destination, "resources/app");
fs.mkdirSync(appDirectory, { recursive: true });
for (const filename of ["main.cjs", "loading.html", "package.json"]) {
  fs.copyFileSync(path.join(__dirname, filename), path.join(appDirectory, filename));
}
fs.cpSync(path.join(__dirname, "assets"), path.join(appDirectory, "assets"), {
  recursive: true
});
fs.renameSync(path.join(destination, "electron.exe"), executable);

async function applyBranding() {
  const { rcedit } = await import("rcedit");
  const metadata = JSON.parse(fs.readFileSync(path.join(__dirname, "package.json"), "utf8"));
  await rcedit(executable, {
    icon,
    "file-version": metadata.version,
    "product-version": metadata.version,
    "version-string": {
      ProductName: applicationName,
      FileDescription: applicationName,
      InternalName: applicationName,
      OriginalFilename: `${applicationName}.exe`,
      CompanyName: applicationName,
      LegalCopyright: ""
    }
  });
  const previousExecutable = path.join(destination, "3D Studio.exe");
  if (fs.existsSync(previousExecutable)) {
    fs.unlinkSync(previousExecutable);
  }
  console.log(executable);
}

applyBranding().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
