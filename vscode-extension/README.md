# CloneScope for VS Code

Scan the active Python, Java, C, or header file, or scan a workspace, with the
same authenticated CloneScope API used by the web app. No source is read or
uploaded until you run one of the **CloneScope** commands.

## Install locally

```powershell
cd D:\code_clone_detector\vscode-extension
npm install
npm run package
code --install-extension .\clonescope-0.1.0.vsix
```

Alternatively use VS Code's **Extensions: Install from VSIX...** command and
select the generated `.vsix` file.

## Use

1. Set `clonescope.apiBaseUrl` if your deployed API URL differs from the default.
2. Run **CloneScope: Sign In** once and enter the same email/password used in
   CloneScope. The JWT is stored by VS Code Secret Storage, not in settings.
3. Run **CloneScope: Analyze Active File** or **CloneScope: Analyze Workspace**.
4. Select a result under the Explorer's **CloneScope** view to open its source
   region. Informational diagnostics also mark both regions.

Workspace scans automatically include `.py`, `.java`, `.c`, and `.h` files and
ignore common generated/dependency folders. Linux C/header support needs no
separate extension setting.

## Publishing later

The generated VSIX is suitable for private/local installation. Publishing to
the Visual Studio Marketplace requires a publisher account and personal access
token; it is intentionally not performed by this project command.
