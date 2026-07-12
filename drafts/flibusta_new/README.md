# Flibusta new books reader

Skript dlya chteniya novinok s Flibusta cherez Tor.

## Trebovaniya

- Python 3.10+
- `requests`, `beautifulsoup4`, `lxml`, `PySocks`
- Zapushchennyy Tor Browser (port 9150) ili sluzhba tor (port 9050)

Ustanovka zavisimostey:

```powershell
pip install requests beautifulsoup4 lxml PySocks
```

## Zapusk

```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
chcp 65001

python flibusta_new.py --url "/new/655427?page=2"
python flibusta_new.py --url "/new/655427" --pages 1-3
python flibusta_new.py --url "/new/655427?page=2" --html-report reports/page2.html
python flibusta_new.py --url "/new/655427" --pages 1-5 --save-state data/seen.json --only-new
```

## Parametry

| Parametr | Opisanie |
|---|---|
| `--url` | Otnositelnyy ili polnyy URL spiska novinok |
| `--pages` | Diapazon stranits: `1-3`, `2,4,5` |
| `--proxy-port` | Port SOCKS5 (avto: 9150, potom 9050) |
| `--html-report` | Sozdat HTML-otchet |
| `--save-state` | JSON s uzhe prosmotrennymi knigami |
| `--only-new` | Pokazat tolko novye otnositelno state |

## Primery URL

- `/new/655427` - poslednie postupleniya (filtr/polka)
- `/new/655427?page=2` - vtoraya stranitsa
