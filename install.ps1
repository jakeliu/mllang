# MLLANG one-shot installer for Windows (PowerShell).
#
# Usage (from PowerShell):
#   iwr -useb https://raw.githubusercontent.com/jakeliu/mllang/main/install.ps1 | iex
#   iwr -useb https://raw.githubusercontent.com/jakeliu/mllang/main/install.ps1 | iex; mllang-install -MyBox alice
#
# Or, if executing this script directly:
#   .\install.ps1 -MyBox alice
#   .\install.ps1 -MyBox alice -Only claude
#   .\install.ps1 -MyBox alice -Only codex
#
# Does in one command:
#   1. Installs pipx (via pip or winget) + mllang-protocol[mcp]
#   2. Detects Claude Code (%USERPROFILE%\.claude*) and/or Codex (%USERPROFILE%\.codex)
#   3. Drops /mllang slash command + hook scripts + bootstrap into Claude Code
#   4. Adds [mcp_servers.mllang] + [[hooks.UserPromptSubmit]] to Codex config.toml
#   5. Appends AGENTS.md natural-language snippet for Codex
#   6. Sets MLLANG_MY_BOX env (user scope)
#   7. Re-runnable, backs up modified files as <file>.bak-<ts>

param(
    [string]$MyBox = "",
    [ValidateSet("", "claude", "codex", "both")]
    [string]$Only = "",
    [switch]$DryRun
)

$ErrorActionPreference = "Continue"
$RepoRaw = "https://raw.githubusercontent.com/jakeliu/mllang/main"
$Ts = Get-Date -Format "yyyyMMdd_HHmmss"

function Log($m)  { Write-Host "[mllang] $m" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "[ok] $m"     -ForegroundColor Green }
function Warn($m) { Write-Host "[warn] $m"   -ForegroundColor Yellow }
function Err($m)  { Write-Host "[err] $m"    -ForegroundColor Red }

function Backup-File($path) {
    if (Test-Path $path) {
        Copy-Item $path "$path.bak-$Ts"
        Log "backed up $path -> $path.bak-$Ts"
    }
}

function Fetch-Text($url) {
    try { (Invoke-WebRequest -UseBasicParsing -Uri $url).Content }
    catch { Err "failed to fetch $url"; "" }
}

# ── 1. Install mllang-protocol via pipx ──────────────────────────────────

if (-not (Get-Command pipx -ErrorAction SilentlyContinue)) {
    Log "pipx not found, installing"
    if ($DryRun) { Log "would: python -m pip install --user pipx" }
    else {
        python -m pip install --user pipx 2>&1 | Out-Null
        python -m pipx ensurepath 2>&1 | Out-Null
        # Refresh PATH so pipx is available in this session
        $env:PATH = [Environment]::GetEnvironmentVariable("PATH","User") + ";" + [Environment]::GetEnvironmentVariable("PATH","Machine")
    }
}

$pipxList = (pipx list 2>$null) -join "`n"
if ($pipxList -match "mllang-protocol") {
    Log "mllang-protocol already installed -- upgrading"
    if (-not $DryRun) { pipx upgrade mllang-protocol 2>&1 | Out-Null }
} else {
    Log "installing mllang-protocol[mcp]"
    if (-not $DryRun) { pipx install 'mllang-protocol[mcp]' 2>&1 | Out-Null }
}

$MllangBin = (Get-Command mllang-mailbox -ErrorAction SilentlyContinue).Source
$McpBin    = (Get-Command mllang-mcp-server -ErrorAction SilentlyContinue).Source

if (-not $MllangBin) {
    Err "mllang-mailbox not on PATH after install. Open a new PowerShell window or check pipx output."
    exit 1
}
Ok "mllang-mailbox at $MllangBin"
Ok "mllang-mcp-server at $McpBin"

# ── 2. Detect clients ───────────────────────────────────────────────────

$HomeDir = $env:USERPROFILE
$HasClaude = $false
$HasCodex  = $false
$ClaudeDir = ""

foreach ($candidate in @("$HomeDir\.claude-$env:USERNAME", "$HomeDir\.claude")) {
    if ((Test-Path $candidate) -and ((Test-Path "$candidate\settings.json") -or (Test-Path "$candidate\commands"))) {
        $ClaudeDir = $candidate
        $HasClaude = $true
        break
    }
}

if (Test-Path "$HomeDir\.codex") { $HasCodex = $true }

if ($Only -eq "claude") { $HasCodex  = $false }
if ($Only -eq "codex")  { $HasClaude = $false }

if ($HasClaude) { Log "found Claude Code at $ClaudeDir" }
if ($HasCodex)  { Log "found Codex CLI at $HomeDir\.codex" }

if (-not $HasClaude -and -not $HasCodex) {
    Warn "Neither Claude Code nor Codex CLI detected. CLI installed; skipping client wiring."
    exit 0
}

# Mailbox dir
New-Item -ItemType Directory -Force -Path "$HomeDir\.mllang-mailbox" | Out-Null

# ── 3. Claude Code wiring ───────────────────────────────────────────────

if ($HasClaude) {
    Log "wiring Claude Code at $ClaudeDir"

    # 3a. Slash command
    New-Item -ItemType Directory -Force -Path "$ClaudeDir\commands" | Out-Null
    if (-not $DryRun) {
        $body = Fetch-Text "$RepoRaw/claude-code-skill/commands/mllang.md"
        Set-Content -Path "$ClaudeDir\commands\mllang.md" -Value $body -Encoding UTF8
    }

    # 3b. Skill dir + hooks + bootstrap + roles
    $skillDir = "$ClaudeDir\skills\mllang"
    New-Item -ItemType Directory -Force -Path "$skillDir\scripts","$skillDir\roles" | Out-Null

    foreach ($f in @("SKILL.md","bootstrap.md","spec-summary.md")) {
        if (-not $DryRun) {
            $body = Fetch-Text "$RepoRaw/claude-code-skill/$f"
            if ($body) { Set-Content -Path "$skillDir\$f" -Value $body -Encoding UTF8 }
        }
    }
    foreach ($f in @("hook_preprompt.py","hook_postagent.py")) {
        if (-not $DryRun) {
            $body = Fetch-Text "$RepoRaw/claude-code-skill/scripts/$f"
            Set-Content -Path "$skillDir\scripts\$f" -Value $body -Encoding UTF8
        }
    }
    foreach ($role in @("orchestrator","critic","implementer","synthesizer")) {
        if (-not $DryRun) {
            $body = Fetch-Text "$RepoRaw/claude-code-skill/roles/$role.md"
            Set-Content -Path "$skillDir\roles\$role.md" -Value $body -Encoding UTF8
        }
    }

    # 3c. settings.json hook wiring (idempotent)
    $settings = "$ClaudeDir\settings.json"
    if (Test-Path $settings) {
        Backup-File $settings
        $raw = Get-Content $settings -Raw
        # ConvertFrom-Json -AsHashtable requires PS 7+; fall back for PS 5.1
        if ($PSVersionTable.PSVersion.Major -ge 7) {
            $cfg = $raw | ConvertFrom-Json -AsHashtable
        } else {
            # Parse as PSObject then convert to nested hashtable
            function ConvertTo-Hashtable($obj) {
                if ($obj -is [System.Management.Automation.PSCustomObject]) {
                    $ht = @{}
                    foreach ($p in $obj.PSObject.Properties) {
                        $ht[$p.Name] = ConvertTo-Hashtable $p.Value
                    }
                    return $ht
                } elseif ($obj -is [System.Collections.IEnumerable] -and $obj -isnot [string]) {
                    return @($obj | ForEach-Object { ConvertTo-Hashtable $_ })
                } else {
                    return $obj
                }
            }
            $cfg = ConvertTo-Hashtable ($raw | ConvertFrom-Json)
        }
        if (-not $cfg.hooks) { $cfg.hooks = @{} }
        $hookScript    = "$skillDir\scripts\hook_preprompt.py".Replace('\','/')
        $postagentCmd  = "$skillDir\scripts\hook_postagent.py".Replace('\','/')

        function Add-Hook($evt, $cmd, $matcher) {
            if (-not $cfg.hooks[$evt]) { $cfg.hooks[$evt] = @() }
            foreach ($e in $cfg.hooks[$evt]) {
                foreach ($h in $e.hooks) {
                    if ($h.command -eq $cmd -and $e.matcher -eq $matcher) { return }
                }
            }
            $block = @{ hooks = @(@{ type = "command"; command = $cmd }) }
            if ($matcher) { $block.matcher = $matcher }
            $cfg.hooks[$evt] += $block
        }
        Add-Hook "UserPromptSubmit" "python `"$hookScript`""    $null
        Add-Hook "PreToolUse"       "python `"$hookScript`""    $null
        Add-Hook "PostToolUse"      "python `"$postagentCmd`""  "Agent"

        if (-not $DryRun) {
            $cfg | ConvertTo-Json -Depth 20 | Set-Content $settings -Encoding UTF8
        }
        Ok "settings.json wired"
    }
    Ok "Claude Code wired"
}

# ── 4. Codex CLI wiring ─────────────────────────────────────────────────

if ($HasCodex) {
    Log "wiring Codex CLI at $HomeDir\.codex"
    $codexCfg = "$HomeDir\.codex\config.toml"
    $codexAgents = "$HomeDir\.codex\AGENTS.md"
    $codexInt = "$HomeDir\.codex\mllang-integration\scripts"
    New-Item -ItemType Directory -Force -Path $codexInt | Out-Null

    # 4a. Hook scripts
    if (-not $DryRun) {
        $body = Fetch-Text "$RepoRaw/codex-cli-integration/scripts/hook_preprompt_codex_wrapper.py"
        Set-Content -Path "$codexInt\hook_preprompt_codex_wrapper.py" -Value $body -Encoding UTF8
        $body = Fetch-Text "$RepoRaw/claude-code-skill/scripts/hook_preprompt.py"
        Set-Content -Path "$codexInt\hook_preprompt.py" -Value $body -Encoding UTF8
    }

    # 4b. MCP server entry + UserPromptSubmit hook in config.toml
    if (Test-Path $codexCfg) {
        $text = Get-Content $codexCfg -Raw
        $needMcp  = ($text -notmatch "mcp_servers\.mllang")
        $needHook = ($text -notmatch "hook_preprompt_codex_wrapper")
        if ($needMcp -or $needHook) {
            Backup-File $codexCfg
            $boxName = if ($MyBox) { $MyBox } else { "codex" }
            $addLines = ""
            if ($needMcp) {
                $mcpPath = $McpBin.Replace('\','/')
                $addLines += "`n[mcp_servers.mllang]`ncommand = `"$mcpPath`"`n"
            }
            if ($needHook) {
                $wrapper = "$codexInt\hook_preprompt_codex_wrapper.py".Replace('\','/')
                # Use TOML single-quoted string to avoid nested double-quote issues
                $sq = "'"
                $addLines += "`n[[hooks.UserPromptSubmit]]`nmatcher = `"`"`n`n[[hooks.UserPromptSubmit.hooks]]`ntype = `"command`"`ncommand = ${sq}MLLANG_MY_BOX=$boxName python `"$wrapper`"${sq}`n"
            }
            if (-not $DryRun) {
                Add-Content -Path $codexCfg -Value $addLines -Encoding UTF8
            }
        }
    }

    # 4c. AGENTS.md natural-language snippet
    if (-not (Test-Path $codexAgents) -or -not ((Get-Content $codexAgents -Raw -ErrorAction SilentlyContinue) -match "MLLANG mailbox shortcuts")) {
        if (-not $DryRun) {
            $snippet = Fetch-Text "$RepoRaw/codex-cli-integration/AGENTS_mllang_snippet.md"
            Add-Content -Path $codexAgents -Value $snippet -Encoding UTF8
        }
    }

    Ok "Codex CLI wired"
}

# ── 5. MLLANG_MY_BOX env var (user scope) ───────────────────────────────

if ($MyBox) {
    if (-not $DryRun) {
        [Environment]::SetEnvironmentVariable("MLLANG_MY_BOX", $MyBox, "User")
    }
    Ok "MLLANG_MY_BOX=$MyBox set at user scope"
}

# ── 6. Done ─────────────────────────────────────────────────────────────

Write-Host @"

──────────────────────────────────────────────────────────────────────
mllang installed.

Next steps:
  1. Open a NEW PowerShell window (so MLLANG_MY_BOX is picked up).
  2. Restart Claude Code and/or Codex CLI for hooks to load.
  3. From any PowerShell:
       mllang-mailbox send <box> "hi"
       mllang-mailbox check
  4. In Claude Code:
       /mllang send <box> hi
       /mllang receive
  5. In Codex (natural language):
       send hi to <box>
       check my mailbox

PyPI:   https://pypi.org/project/mllang-protocol/
Source: https://github.com/jakeliu/mllang
──────────────────────────────────────────────────────────────────────
"@
