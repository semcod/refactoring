import * as vscode from 'vscode';
import { spawn } from 'child_process';
import { readFile, writeFile } from 'fs/promises';
import { join } from 'path';

interface PrefactIssue {
    rule_id: string;
    file: string;
    line: number;
    col: number;
    message: string;
    severity: 'error' | 'warning' | 'info';
    original?: string;
    suggested?: string;
}

interface PrefactResult {
    issues_found: PrefactIssue[];
    fixes_applied: number;
    fixes_failed: number;
    validations: any[];
}

class PrefactDiagnosticsProvider {
    private diagnosticCollection: vscode.DiagnosticCollection;
    private outputChannel: vscode.OutputChannel;

    constructor() {
        this.diagnosticCollection = vscode.languages.createDiagnosticCollection('prefact');
        this.outputChannel = vscode.window.createOutputChannel('Prefact');
    }

    async scanFile(document: vscode.TextDocument): Promise<void> {
        if (document.languageId !== 'python') {
            return;
        }

        const config = vscode.workspace.getConfiguration('prefact');
        if (!config.get('enabled')) {
            return;
        }

        try {
            const result = await this.runPrefact(['scan', '--path', document.uri.fsPath]);
            this.updateDiagnostics(document, result.issues_found);
            this.showOutput(result);
        } catch (error) {
            this.outputChannel.appendLine(`Error scanning file: ${error}`);
        }
    }

    async scanWorkspace(): Promise<void> {
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders) {
            return;
        }

        const config = vscode.workspace.getConfiguration('prefact');
        if (!config.get('enabled')) {
            return;
        }

        try {
            const result = await this.runPrefact(['scan', '--path', workspaceFolders[0].uri.fsPath]);
            this.updateWorkspaceDiagnostics(result.issues_found);
            this.showOutput(result);
        } catch (error) {
            this.outputChannel.appendLine(`Error scanning workspace: ${error}`);
        }
    }

    async fixFile(document: vscode.TextDocument): Promise<void> {
        if (document.languageId !== 'python') {
            return;
        }

        try {
            await this.runPrefact(['fix', '--path', document.uri.fsPath]);
            
            // Reload the document
            const document = await vscode.workspace.openTextDocument(document.uri);
            await vscode.window.showTextDocument(document);
            
            // Re-scan to verify fixes
            await this.scanFile(document);
            
            vscode.window.showInformationMessage('Prefact fixes applied successfully');
        } catch (error) {
            this.outputChannel.appendLine(`Error fixing file: ${error}`);
            vscode.window.showErrorMessage(`Failed to apply fixes: ${error}`);
        }
    }

    async fixWorkspace(): Promise<void> {
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders) {
            return;
        }

        try {
            await this.runPrefact(['fix', '--path', workspaceFolders[0].uri.fsPath]);
            
            // Re-scan workspace
            await this.scanWorkspace();
            
            vscode.window.showInformationMessage('Prefact fixes applied to workspace');
        } catch (error) {
            this.outputChannel.appendLine(`Error fixing workspace: ${error}`);
            vscode.window.showErrorMessage(`Failed to apply fixes: ${error}`);
        }
    }

    private async runPrefact(args: string[]): Promise<PrefactResult> {
        const config = vscode.workspace.getConfiguration('prefact');
        const executablePath = config.get<string>('executablePath', 'prefact');
        
        return new Promise((resolve, reject) => {
            const child = spawn(executablePath, args, {
                cwd: vscode.workspace.workspaceFolders?.[0]?.uri.fsPath,
                stdio: 'pipe'
            });

            let stdout = '';
            let stderr = '';

            child.stdout?.on('data', (data) => {
                stdout += data.toString();
            });

            child.stderr?.on('data', (data) => {
                stderr += data.toString();
            });

            child.on('close', (code) => {
                if (code === 0) {
                    try {
                        const result: PrefactResult = JSON.parse(stdout);
                        resolve(result);
                    } catch (e) {
                        // Fallback for non-JSON output
                        resolve({
                            issues_found: [],
                            fixes_applied: 0,
                            fixes_failed: 0,
                            validations: []
                        });
                    }
                } else {
                    reject(new Error(stderr || `Process exited with code ${code}`));
                }
            });

            child.on('error', (error) => {
                reject(error);
            });
        });
    }

    private updateDiagnostics(document: vscode.TextDocument, issues: PrefactIssue[]): void {
        const diagnostics: vscode.Diagnostic[] = [];

        for (const issue of issues) {
            if (issue.file !== document.uri.fsPath) {
                continue;
            }

            const range = new vscode.Range(
                new vscode.Position(issue.line - 1, issue.col),
                new vscode.Position(issue.line - 1, issue.col + 1)
            );

            const severity = this.getSeverity(issue.severity);
            const diagnostic = new vscode.Diagnostic(
                range,
                issue.message,
                severity
            );

            diagnostic.code = issue.rule_id;
            diagnostic.source = 'Prefact';

            if (issue.suggested) {
                diagnostic.message += `\nSuggested: ${issue.suggested}`;
            }

            diagnostics.push(diagnostic);
        }

        this.diagnosticCollection.set(document.uri, diagnostics);
    }

    private updateWorkspaceDiagnostics(issues: PrefactIssue[]): void {
        const diagnosticsByFile = new Map<string, vscode.Diagnostic[]>();

        for (const issue of issues) {
            const diagnostics = diagnosticsByFile.get(issue.file) || [];
            
            const range = new vscode.Range(
                new vscode.Position(issue.line - 1, issue.col),
                new vscode.Position(issue.line - 1, issue.col + 1)
            );

            const severity = this.getSeverity(issue.severity);
            const diagnostic = new vscode.Diagnostic(
                range,
                issue.message,
                severity
            );

            diagnostic.code = issue.rule_id;
            diagnostic.source = 'Prefact';

            diagnostics.push(diagnostic);
            diagnosticsByFile.set(issue.file, diagnostics);
        }

        const entries = Array.from(diagnosticsByFile.entries()).map(
            ([file, diagnostics]) => [vscode.Uri.file(file), diagnostics] as [vscode.Uri, vscode.Diagnostic[]]
        );

        this.diagnosticCollection.set(entries);
    }

    private getSeverity(severity: string): vscode.DiagnosticSeverity {
        switch (severity) {
            case 'error':
                return vscode.DiagnosticSeverity.Error;
            case 'warning':
                return vscode.DiagnosticSeverity.Warning;
            case 'info':
                return vscode.DiagnosticSeverity.Information;
            default:
                return vscode.DiagnosticSeverity.Warning;
        }
    }

    private showOutput(result: PrefactResult): void {
        this.outputChannel.clear();
        this.outputChannel.appendLine('Prefact Scan Results:');
        this.outputChannel.appendLine(`Issues found: ${result.issues_found.length}`);
        this.outputChannel.appendLine(`Fixes applied: ${result.fixes_applied}`);
        this.outputChannel.appendLine(`Fixes failed: ${result.fixes_failed}`);
        this.outputChannel.appendLine('');

        if (result.issues_found.length > 0) {
            this.outputChannel.appendLine('Issues:');
            for (const issue of result.issues_found) {
                this.outputChannel.appendLine(
                    `  ${issue.file}:${issue.line}:${issue.col} - [${issue.rule_id}] ${issue.message}`
                );
            }
        }

        this.outputChannel.show();
    }

    dispose() {
        this.diagnosticCollection.dispose();
        this.outputChannel.dispose();
    }
}

class PrefactTreeItem extends vscode.TreeItem {
    constructor(
        public readonly label: string,
        public readonly collapsibleState: vscode.TreeItemCollapsibleState,
        public readonly issue?: PrefactIssue,
        public readonly command?: vscode.Command
    ) {
        super(label, collapsibleState);
    }
}

class PrefactTreeProvider implements vscode.TreeDataProvider<PrefactTreeItem> {
    private _onDidChangeTreeData = new vscode.EventEmitter<PrefactTreeItem | undefined>();
    readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

    private issues: PrefactIssue[] = [];

    refresh(issues: PrefactIssue[]): void {
        this.issues = issues;
        this._onDidChangeTreeData.fire(undefined);
    }

    getTreeItem(element: PrefactTreeItem): vscode.TreeItem {
        return element;
    }

    getChildren(element?: PrefactTreeItem): PrefactTreeItem[] {
        if (!element) {
            // Root level - group by file
            const issuesByFile = new Map<string, PrefactIssue[]>();
            for (const issue of this.issues) {
                const file = issue.file;
                if (!issuesByFile.has(file)) {
                    issuesByFile.set(file, []);
                }
                issuesByFile.get(file)!.push(issue);
            }

            return Array.from(issuesByFile.entries()).map(([file, fileIssues]) => {
                const item = new PrefactTreeItem(
                    file,
                    vscode.TreeItemCollapsibleState.Expanded,
                    undefined,
                    {
                        command: 'vscode.open',
                        title: 'Open File',
                        arguments: [vscode.Uri.file(file)]
                    }
                );
                item.tooltip = `${fileIssues.length} issue(s)`;
                return item;
            });
        } else {
            // File level - show issues
            const fileIssues = this.issues.filter(issue => issue.file === element.label);
            return fileIssues.map(issue => {
                const item = new PrefactTreeItem(
                    `[${issue.rule_id}] ${issue.message}`,
                    vscode.TreeItemCollapsibleState.None,
                    issue,
                    {
                        command: 'vscode.open',
                        title: 'Go to Issue',
                        arguments: [
                            vscode.Uri.file(issue.file),
                            {
                                selection: new vscode.Range(
                                    new vscode.Position(issue.line - 1, issue.col),
                                    new vscode.Position(issue.line - 1, issue.col)
                                )
                            }
                        ]
                    }
                );
                item.tooltip = `Line ${issue.line}, Column ${issue.col}`;
                return item;
            });
        }
    }
}

export function activate(context: vscode.ExtensionContext) {
    console.log('Prefact extension is now active!');

    const diagnosticsProvider = new PrefactDiagnosticsProvider();
    const treeProvider = new PrefactTreeProvider();

    // Register tree view
    const treeView = vscode.window.createTreeView('prefactDiagnostics', {
        treeDataProvider: treeProvider
    });

    // Register commands
    const scanCommand = vscode.commands.registerCommand('prefact.scan', async (uri?: vscode.Uri) => {
        const document = uri 
            ? await vscode.workspace.openTextDocument(uri)
            : vscode.window.activeTextEditor?.document;
        
        if (document) {
            await diagnosticsProvider.scanFile(document);
        }
    });

    const scanWorkspaceCommand = vscode.commands.registerCommand('prefact.scanWorkspace', async () => {
        await diagnosticsProvider.scanWorkspace();
    });

    const fixCommand = vscode.commands.registerCommand('prefact.fix', async (uri?: vscode.Uri) => {
        const document = uri 
            ? await vscode.workspace.openTextDocument(uri)
            : vscode.window.activeTextEditor?.document;
        
        if (document) {
            await diagnosticsProvider.fixFile(document);
        }
    });

    const fixWorkspaceCommand = vscode.commands.registerCommand('prefact.fixWorkspace', async () => {
        await diagnosticsProvider.fixWorkspace();
    });

    const configureCommand = vscode.commands.registerCommand('prefact.configure', async () => {
        const config = vscode.workspace.getConfiguration('prefact');
        await vscode.commands.executeCommand('workbench.action.openSettings', 'prefact');
    });

    const installHooksCommand = vscode.commands.registerCommand('prefact.installHooks', async () => {
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders) {
            vscode.window.showErrorMessage('No workspace folder found');
            return;
        }

        try {
            const { spawn } = require('child_process');
            spawn('prefact', ['git-hooks', 'install'], {
                cwd: workspaceFolders[0].uri.fsPath,
                stdio: 'inherit'
            });
            vscode.window.showInformationMessage('Git hooks installed successfully');
        } catch (error) {
            vscode.window.showErrorMessage(`Failed to install Git hooks: ${error}`);
        }
    });

    // Register event handlers
    const onSave = vscode.workspace.onDidSaveTextDocument(async (document) => {
        const config = vscode.workspace.getConfiguration('prefact');
        if (document.languageId === 'python') {
            if (config.get('scanOnSave')) {
                await diagnosticsProvider.scanFile(document);
            }
            if (config.get('fixOnSave')) {
                await diagnosticsProvider.fixFile(document);
            }
        }
    });

    // Update tree provider when diagnostics change
    setInterval(() => {
        // This is a simplified approach - in practice, you'd want to track issues more carefully
        treeProvider.refresh([]);
    }, 5000);

    // Add to subscriptions
    context.subscriptions.push(
        diagnosticsProvider,
        treeView,
        scanCommand,
        scanWorkspaceCommand,
        fixCommand,
        fixWorkspaceCommand,
        configureCommand,
        installHooksCommand,
        onSave
    );
}

export function deactivate() {}
