# RduPF (CFE)

Extension for IMDEV-8641: plan filtering for RDU-related scheduled operations in WIM_FIN.

## Target information base (development)

`Srvr="localhost";Ref="WIM_FIN";`

Match `Ref` with your 1C database list name. Main configuration XML sources: `bases/WIM_FIn/source-path.txt` -> `WORK/WIM_FIn`.

## Specification (repository, file names only)

- `imdev8641_brief_development_tz.html`
- `imdev8641_development_brief.md`

Folder: `bases/WIM_FIn/projects/IMDEV-8641 ... /Документация/`

## Current scope

- Extension scaffold: `cfe-init` from base `Configuration.xml` (compatibility Version8_3_27).
- Adopted **DataProcessor** `ГрупповоеВыполнениеЗакрытияПериодов` with **extended object module** (`xr:PropertyState` ObjectModule = Extended).
- **&ИзменениеИКонтроль** on `ВыполнитьМногопоточноеЗакрытиеПериодовПортфелей`: procedure `RduPF_ВыполнитьМногопоточноеЗакрытиеПериодовПортфелей` — full type body + `#Вставка` / `#КонецВставки` after `ПланРеглОпераций` and before `ПланРеглОперацийПоДням.Вставить` (filter to be wired when RS exists).

No extension-owned register/constant yet (`ПулРозницаДУ`, `ВидыОптимизируемыхРегламентныхОперацийДУ`).

## Next steps (per TZ)

1. Add RS and constant; implement filter in the `#Вставка` block (or call manager module of RS).
2. Reconcile body after типовые updates (compare with `WORK/WIM_FIn/.../ObjectModule.bsl`).

## Validate

From repo root:

```text
powershell.exe -NoProfile -File .cursor/skills/cfe-validate/scripts/cfe-validate.ps1 -ExtensionPath "<path>/RduPF"
```

Last run: 13 checks OK.

## Binary CFE and load into IB

**Canonical path in the repository:** `Расширения/RduPF.cfe` (same folder as the `RduPF/` XML tree, sibling of `RduPF/`).

After you load XML into the IB (or edit the extension in Designer and save to the database), **always dump** the extension back to this file so the committed `.cfe` matches what is in `WIM_FIN`:

```text
powershell.exe -NoProfile -File .cursor/skills/db-dump-cf/scripts/db-dump-cf.ps1 -V8Path "C:\Program Files\1cv8\8.3.27.1859\bin" -InfoBaseServer "localhost" -InfoBaseRef "WIM_FIN" -OutputFile "<project>\Расширения\RduPF.cfe" -Extension "RduPF"
```

Use the same `-V8Path` / credentials as for load.

Load XML into extension **RduPF** on server `localhost`, base `WIM_FIN` (platform 8.3.27 example):

```text
powershell.exe -NoProfile -File .cursor/skills/db-load-xml/scripts/db-load-xml.ps1 -V8Path "C:\Program Files\1cv8\8.3.27.1859\bin" -InfoBaseServer "localhost" -InfoBaseRef "WIM_FIN" -ConfigDir "<path>\RduPF" -Mode Full -Extension "RduPF"
```

Add `-UserName` / `-Password` if the IB requires authentication.

Dump extension back to CFE:

```text
powershell.exe -NoProfile -File .cursor/skills/db-dump-cf/scripts/db-dump-cf.ps1 -V8Path "C:\Program Files\1cv8\8.3.27.1859\bin" -InfoBaseServer "localhost" -InfoBaseRef "WIM_FIN" -OutputFile "<path>\RduPF.cfe" -Extension "RduPF"
```

Adopted `DataProcessors/...xml` must contain empty `<ChildObjects/>` so `LoadConfigFromFiles` accepts the file (see repo `cfe-borrow` for new borrows).

In Configurator: enable extension **RduPF** for the database if it is not active after load.
