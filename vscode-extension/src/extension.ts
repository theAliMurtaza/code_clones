import * as vscode from "vscode";

const SECRET_KEY = "clonescope.accessToken";
const EXTENSIONS = new Set([".py", ".java", ".c", ".h"]);
const IGNORED_GLOB = "**/{.git,node_modules,dist,build,.venv,venv,__pycache__}/**";

type ClonePair = {
  file_a: string;
  file_b: string;
  lines_a: [number, number];
  lines_b: [number, number];
  clone_type: string;
  similarity: number;
  description?: string;
};
type Job = { status: "queued" | "running" | "done" | "failed"; error?: string; clone_pairs?: ClonePair[]; };

class CloneResultItem extends vscode.TreeItem {
  constructor(readonly pair: ClonePair) {
    super(`${pair.clone_type} · ${Math.round(pair.similarity * 100)}%`, vscode.TreeItemCollapsibleState.None);
    this.description = `${pair.file_a}:${pair.lines_a[0]} ↔ ${pair.file_b}:${pair.lines_b[0]}`;
    this.tooltip = pair.description ?? this.description;
    this.command = { command: "clonescope.openPair", title: "Open clone", arguments: [pair] };
    this.iconPath = new vscode.ThemeIcon("references");
  }
}

class ResultsProvider implements vscode.TreeDataProvider<CloneResultItem> {
  private readonly emitter = new vscode.EventEmitter<CloneResultItem | undefined>();
  readonly onDidChangeTreeData = this.emitter.event;
  private pairs: ClonePair[] = [];
  setResults(pairs: ClonePair[]): void { this.pairs = pairs; this.emitter.fire(undefined); }
  getChildren(): CloneResultItem[] { return this.pairs.map(pair => new CloneResultItem(pair)); }
  getTreeItem(element: CloneResultItem): vscode.TreeItem { return element; }
}

function config<T>(name: string): T { return vscode.workspace.getConfiguration("clonescope").get<T>(name)!; }
function baseUrl(): string { return config<string>("apiBaseUrl").replace(/\/$/, ""); }
function isSupported(uri: vscode.Uri): boolean {
  return uri.scheme === "file" && EXTENSIONS.has(uri.path.slice(uri.path.lastIndexOf(".")).toLowerCase());
}

async function api(context: vscode.ExtensionContext, path: string, init: RequestInit = {}): Promise<Response> {
  const token = await context.secrets.get(SECRET_KEY);
  if (!token) { throw new Error("Sign in to CloneScope first."); }
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${token}`);
  let response: Response;
  try { response = await fetch(`${baseUrl()}${path}`, { ...init, headers }); }
  catch { throw new Error("CloneScope API cannot be reached. Check clonescope.apiBaseUrl."); }
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try { detail = (await response.json() as { detail?: string }).detail ?? detail; } catch { /* generic error only */ }
    if (response.status === 401) { await context.secrets.delete(SECRET_KEY); }
    throw new Error(detail);
  }
  return response;
}

async function signIn(context: vscode.ExtensionContext): Promise<void> {
  const email = await vscode.window.showInputBox({ prompt: "CloneScope email", ignoreFocusOut: true });
  if (!email) { return; }
  const password = await vscode.window.showInputBox({ prompt: "CloneScope password", password: true, ignoreFocusOut: true });
  if (!password) { return; }
  const response = await fetch(`${baseUrl()}/api/auth/login`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, password })
  });
  if (!response.ok) { throw new Error("Sign-in failed. Check your email, password, and API URL."); }
  const body = await response.json() as { access_token?: string };
  if (!body.access_token) { throw new Error("CloneScope sign-in returned no access token."); }
  await context.secrets.store(SECRET_KEY, body.access_token);
  vscode.window.showInformationMessage("Signed in to CloneScope.");
}

async function submit(context: vscode.ExtensionContext, uris: vscode.Uri[]): Promise<string> {
  if (uris.length < 1) { throw new Error("Select at least one supported source file to compare."); }
  const form = new FormData();
  const paths: string[] = [];
  for (const uri of uris) {
    const content = await vscode.workspace.fs.readFile(uri);
    const relative = vscode.workspace.asRelativePath(uri, false).replace(/\\/g, "/");
    paths.push(relative);
    form.append("files", new Blob([content.buffer as ArrayBuffer]), relative);
  }
  form.set("paths_json", JSON.stringify(paths));
  form.set("threshold", String(config<number>("similarityThreshold")));
  const response = await api(context, "/api/detect", { method: "POST", body: form });
  return (await response.json() as { job_id: string }).job_id;
}

async function waitForJob(context: vscode.ExtensionContext, jobId: string): Promise<Job> {
  const deadline = Date.now() + 10 * 60 * 1000;
  while (Date.now() < deadline) {
    const job = await (await api(context, `/api/jobs/${encodeURIComponent(jobId)}`)).json() as Job;
    if (job.status === "done") { return job; }
    if (job.status === "failed") { throw new Error(job.error || "Clone analysis failed."); }
    await new Promise(resolve => setTimeout(resolve, 1500));
  }
  throw new Error("Clone analysis timed out. Open CloneScope in the web app to check this job.");
}

async function uriForRelativePath(path: string): Promise<vscode.Uri | undefined> {
  for (const root of vscode.workspace.workspaceFolders ?? []) {
    const candidate = vscode.Uri.joinPath(root.uri, ...path.split("/"));
    try { await vscode.workspace.fs.stat(candidate); return candidate; } catch { /* try next workspace folder */ }
  }
  return undefined;
}

async function showPair(pair: ClonePair): Promise<void> {
  const uri = await uriForRelativePath(pair.file_a);
  if (!uri) { vscode.window.showWarningMessage(`Could not locate ${pair.file_a} in this workspace.`); return; }
  const document = await vscode.workspace.openTextDocument(uri);
  const editor = await vscode.window.showTextDocument(document);
  const range = new vscode.Range(Math.max(0, pair.lines_a[0] - 1), 0, Math.max(0, pair.lines_a[1] - 1), Number.MAX_SAFE_INTEGER);
  editor.selection = new vscode.Selection(range.start, range.end);
  editor.revealRange(range, vscode.TextEditorRevealType.InCenter);
}

async function publishResults(job: Job, provider: ResultsProvider, diagnostics: vscode.DiagnosticCollection): Promise<void> {
  const pairs = job.clone_pairs ?? [];
  provider.setResults(pairs);
  diagnostics.clear();
  const grouped = new Map<string, vscode.Diagnostic[]>();
  for (const pair of pairs) {
    for (const [file, lines] of [[pair.file_a, pair.lines_a], [pair.file_b, pair.lines_b]] as const) {
      const uri = await uriForRelativePath(file);
      if (!uri) { continue; }
      const range = new vscode.Range(Math.max(0, lines[0] - 1), 0, Math.max(0, lines[1] - 1), Number.MAX_SAFE_INTEGER);
      const diagnostic = new vscode.Diagnostic(range, `${pair.clone_type}: ${Math.round(pair.similarity * 100)}% similar code`, vscode.DiagnosticSeverity.Information);
      diagnostic.source = "CloneScope";
      const entries = grouped.get(uri.toString()) ?? [];
      entries.push(diagnostic); grouped.set(uri.toString(), entries);
    }
  }
  for (const [key, entries] of grouped) { diagnostics.set(vscode.Uri.parse(key), entries); }
  vscode.window.showInformationMessage(`CloneScope found ${pairs.length} clone pair${pairs.length === 1 ? "" : "s"}.`);
}

async function analyze(context: vscode.ExtensionContext, provider: ResultsProvider, diagnostics: vscode.DiagnosticCollection, uris: vscode.Uri[]): Promise<void> {
  await vscode.window.withProgress({ location: vscode.ProgressLocation.Notification, title: "CloneScope: analyzing code", cancellable: false }, async progress => {
    progress.report({ message: "Uploading supported source files…" });
    const jobId = await submit(context, uris);
    progress.report({ message: "Comparing code…" });
    await publishResults(await waitForJob(context, jobId), provider, diagnostics);
  });
}

export function activate(context: vscode.ExtensionContext): void {
  const provider = new ResultsProvider();
  const diagnostics = vscode.languages.createDiagnosticCollection("clonescope");
  context.subscriptions.push(diagnostics, vscode.window.createTreeView("clonescope.results", { treeDataProvider: provider }));
  const run = (action: () => Promise<void>) => () => action().catch(error => vscode.window.showErrorMessage(error instanceof Error ? error.message : "CloneScope failed."));

  context.subscriptions.push(
    vscode.commands.registerCommand("clonescope.signIn", run(() => signIn(context))),
    vscode.commands.registerCommand("clonescope.signOut", run(async () => { await context.secrets.delete(SECRET_KEY); vscode.window.showInformationMessage("Signed out of CloneScope."); })),
    vscode.commands.registerCommand("clonescope.openPair", (pair: ClonePair) => showPair(pair)),
    vscode.commands.registerCommand("clonescope.analyzeActiveFile", run(async () => {
      const active = vscode.window.activeTextEditor?.document.uri;
      if (!active || !isSupported(active)) { throw new Error("Open a supported .py, .java, .c, or .h file first."); }
      await analyze(context, provider, diagnostics, [active]);
    })),
    vscode.commands.registerCommand("clonescope.analyzeWorkspace", run(async () => {
      const maximum = config<number>("maxFiles");
      const files = await vscode.workspace.findFiles("**/*.{py,java,c,h}", IGNORED_GLOB, maximum + 1);
      if (files.length > maximum) { throw new Error("Workspace has more supported files than clonescope.maxFiles. Narrow the workspace or raise that setting."); }
      await analyze(context, provider, diagnostics, files);
    })),
    vscode.commands.registerCommand("clonescope.showResults", run(async () => { await vscode.commands.executeCommand("workbench.view.explorer"); }))
  );
}

export function deactivate(): void { /* VS Code disposes subscriptions. */ }
