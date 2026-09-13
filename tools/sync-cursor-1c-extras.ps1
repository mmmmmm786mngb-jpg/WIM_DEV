# -*- coding: utf-8 -*-
# Обновляет слой B из https://github.com/Desko77/cursor-1c-skills
# Копирует только белый список. Каталог .cursor/skills не трогает.

[CmdletBinding()]
param(
    [string]$RepoUrl = "https://github.com/Desko77/cursor-1c-skills.git",
    [string]$Branch = "master"
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $Root ".cursor\skills"))) {
    $Root = $PSScriptRoot
    if (-not (Test-Path (Join-Path $Root ".cursor\skills"))) {
        throw "Cannot find repo root (expected .cursor/skills next to tools/)"
    }
}

$CacheDir = Join-Path $Root "tools\cursor-1c-skills"
$DstSkills = Join-Path $Root ".agents\skills"
$DstRules = Join-Path $Root ".cursor\rules"
$CursorSkills = Join-Path $Root ".cursor\skills"

$SkillNames = @(
    "composing-1c-queries",
    "1c-query-optimization",
    "v8unpack-cf"
)
$RuleNames = @(
    "1c-form-reserved-names.mdc"
)

function Write-Info([string]$Message) {
    Write-Host $Message
}

function Update-Cache {
    if (-not (Test-Path (Join-Path $CacheDir ".git"))) {
        Write-Info "Cloning sparse cache: $RepoUrl"
        New-Item -ItemType Directory -Force -Path (Split-Path $CacheDir) | Out-Null
        git clone --filter=blob:none --sparse --branch $Branch --depth 1 $RepoUrl $CacheDir
        if ($LASTEXITCODE -ne 0) { throw "git clone failed" }
    }
    else {
        Write-Info "Updating sparse cache"
        git -C $CacheDir fetch origin $Branch --depth 1
        if ($LASTEXITCODE -ne 0) { throw "git fetch failed" }
        git -C $CacheDir checkout --force "FETCH_HEAD"
        if ($LASTEXITCODE -ne 0) { throw "git checkout failed" }
    }

    git -C $CacheDir sparse-checkout set `
        skills/composing-1c-queries `
        skills/1c-query-optimization `
        skills/v8unpack-cf `
        rules
    if ($LASTEXITCODE -ne 0) { throw "git sparse-checkout failed" }
}

function Copy-Whitelist {
    if (-not (Test-Path $DstSkills)) {
        New-Item -ItemType Directory -Force -Path $DstSkills | Out-Null
    }

    foreach ($name in $SkillNames) {
        $from = Join-Path $CacheDir "skills\$name"
        $to = Join-Path $DstSkills $name
        if (-not (Test-Path $from)) {
            throw "Skill not found in cache: $name"
        }
        if (Test-Path $to) {
            Remove-Item $to -Recurse -Force
        }
        Copy-Item $from $to -Recurse -Force
        Write-Info "Copied skill $name -> .agents/skills/$name"
    }

    foreach ($name in $RuleNames) {
        $from = Join-Path $CacheDir "rules\$name"
        $to = Join-Path $DstRules $name
        if (-not (Test-Path $from)) {
            throw "Rule not found in cache: $name"
        }
        Copy-Item $from $to -Force
        Write-Info "Copied rule $name -> .cursor/rules/$name"
    }
}

function Assert-LayerAUntouched {
    if (-not (Test-Path $CursorSkills)) {
        throw "Layer A missing: .cursor/skills"
    }
    Write-Info "Layer A kept as is: .cursor/skills"
}

function Apply-LocalPatches {
    $querySkill = Join-Path $DstSkills "composing-1c-queries\SKILL.md"
    $optSkill = Join-Path $DstSkills "1c-query-optimization\SKILL.md"
    $localIntro = "Правила и шаблоны языка запросов 1С:Предприятие.`r`n`r`nВ этом репозитории метаданные брать скиллами слоя A (``cf-info``, ``meta-info``), а не угадывать имена. AI-EDT (``validate_query``, ``get_metadata``, ``execute_query``) подключать только если сервер реально есть; без него скилл все равно используется как справочник языка. Продвинутая оптимизация - скилл ``1c-query-optimization``."

    $queryText = Get-Content -Raw -Encoding UTF8 $querySkill
    if ($queryText -match '(?m)^description:\s*">"\s*$') {
        $queryText = $queryText -replace '(?m)^description:\s*">"\s*$',
            'description: "Язык запросов 1С: синтаксис, функции, временные таблицы, соединения, виртуальные таблицы регистров, типичные ошибки. Используй когда пишешь, правишь или ревьюишь запрос 1С или набор данных СКД"'
        Write-Info "Patched composing-1c-queries description (upstream was empty)"
    }
    if ($queryText -notmatch 'слоя A') {
        $queryText = $queryText -replace '(?m)^# Composing 1C Queries\r?\n\r?\nRules and patterns for writing correct 1C:Enterprise query language \(язык запросов 1С\)\.\r?\nQueries are executed via the `execute_query` tool/endpoint\.',
            ("# Composing 1C Queries`r`n`r`n" + $localIntro)
        Write-Info "Patched composing-1c-queries local intro"
    }
    Set-Content -Path $querySkill -Value $queryText -Encoding UTF8 -NoNewline

    $optText = Get-Content -Raw -Encoding UTF8 $optSkill
    if ($optText -match 'query-optimization-tips\.md') {
        $optText = $optText -replace [regex]::Escape('description: "Advanced query patterns for 1C: temporary tables, joins, DCS optimization. Use for complex queries beyond basic rules in query-optimization-tips.md."'),
            'description: "Продвинутая оптимизация запросов 1С: временные таблицы, соединения вместо подзапросов, агрегаты, СКД, большие выборки. Используй когда запрос медленный, многошаговый или читает большие регистры"'
        $optText = $optText -replace 'Продвинутые паттерны оптимизации запросов\. Базовые оптимизации \(ВЫРАЗИТЬ, ПРЕДСТАВЛЕНИЕ, ВТ вместо подзапросов, ОБЪЕДИНИТЬ ВСЕ, индексы, СКД\) - см\. правило `query-optimization-tips\.md`\. Анти-паттерны \(запрос в цикле, обращение через точку\) - см\. `anti_patterns\.md`\.',
            "Продвинутые паттерны оптимизации запросов. Синтаксис языка и типовые ловушки - скилл ``composing-1c-queries`` (в том числе ``references/optimization-and-pitfalls.md``). Правила ``query-optimization-tips.md`` и ``anti_patterns.md`` из набора Desko77 в этот репозиторий не ставились."
        Write-Info "Patched 1c-query-optimization cross-refs"
    }
    Set-Content -Path $optSkill -Value $optText -Encoding UTF8 -NoNewline
}

Assert-LayerAUntouched
Update-Cache
Copy-Whitelist
Apply-LocalPatches
Write-Info "Done. Extra skills: $($SkillNames -join ', '). Extra rule: $($RuleNames -join ', ')."
Write-Info "Did not write into .cursor/skills and did not delete other folders."
