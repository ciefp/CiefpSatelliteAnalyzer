
# CiefpSatelliteAnalyzer

![Enigma2](https://img.shields.io/badge/Enigma2-Plugin-blue)
![Python](https://img.shields.io/badge/Python-2.7%2B%20%7C%203.x-green)
![License](https://img.shields.io/badge/License-MIT-yellow)
![DVB-S/S2](https://img.shields.io/badge/DVB-S%2FS2-Supported-success)
![Astra-SM](https://img.shields.io/badge/Astra--SM-Scanner-orange)
![Abertis](https://img.shields.io/badge/Abertis-Scanner-red)

> **Advanced satellite signal analyzer with Astra-SM & Abertis scanning and automatic bouquet creation for Enigma2**

`CiefpSatelliteAnalyzer` is an all-in-one Enigma2 plugin for real-time signal analysis, precise antenna alignment, **scanning Astra-SM and Abertis frequencies**, and **automatically generating bouquets** with discovered channels.

---

## Features

- **Real-time signal analysis** (SNR, AGC, BER, Lock status)
- **Multi-tuner support** (auto-detection)
- **Graphical signal history** with live graph
- **Data logging** to file
- **USALS & DiSEqC support**
- **Manual frequency, polarization, and FEC tuning**
- **Fast satellite & transponder switching**

### Satellite Scanning
- **Astra-SM **: Full auto-scan of active SM transponders 5°W,9°E,16°E
- **Abertis (DTT Spain)**: Scan on 30°W
- **Blind scan support** for unknown frequencies
- **Provider filtering** (Canal+, Movistar+, etc.)

### Bouquet Creation
- **Auto-generated bouquets**:
  - `Astra-SM Favorites`
  - `Abertis DTT`
  - `Ciefp - Scanned [date]`
- **Enigma2-compatible `.tv` and `.radio` files**
- **Import into main bouquet menu** (with merge option)
- **Duplicate removal** and sorting by name/HD

---

## Requirements

| Requirement | Description |
|-----------|-------------|
| **Enigma2 image** | OpenPLi, OpenATV, VTi, BlackHole, etc. |
| **DVB-S/S2 tuner** | Physical tuner required |
| **Python** | 2.7 or 3.x (standard in Enigma2) |
| **Access rights** | `/usr/lib/enigma2/python/Plugins/Extensions/` |
| **Free space** | ~50 MB for logs and bouquets |

> No external dependencies!

---

## Installation

### 1. Download

```bash
wget https://github.com/ciefp/CiefpSatelliteAnalyzer/archive/refs/heads/main.zip
unzip main.zip
```

### 2. Copy to device

```bash
scp -r CiefpSatelliteAnalyzer-main/usr/lib/enigma2/python/Plugins/Extensions/CiefpSatelliteAnalyzer root@your-box-ip:/usr/lib/enigma2/python/Plugins/Extensions/
```

### 3. Restart Enigma2

```bash
init 4 && sleep 2 && init 3
```

> The plugin will appear in the **Extensions** menu.

---

## Usage

### 1. Signal Analysis
- **Menu → Extensions → CiefpSatelliteAnalyzer**
- Select tuner → satellite → transponder
- Monitor live graph while aligning dish

### 2. Scan Astra-SM
- **Yellow button → Scan Astra-SM**
- Select range: `10700–12750 MHz`, H/V
- Wait for completion (5–15 min)
- Bouquet created: `Astra-SM Favorites`

### 3. Scan Abertis
- **Blue button → Scan Abertis**
- Choose satellite: `30°W`
- Detects DTT multiplexes
- Bouquet created: `Abertis DTT [Spain]`

### 4. Import Bouquets
- After scan: **Green button → Save & Import**
- Bouquets appear in **Bouquet menu**
- Use **Bouquet Wizard** to organize

---

## Screenshots

![Analyzer](https://via.placeholder.com/800x450.png?text=CiefpSatelliteAnalyzer+-+Signal+Analysis)
![Astra-SM Scan](https://via.placeholder.com/800x450.png?text=Astra--SM+Scanning)
![Bouquet](https://via.placeholder.com/800x450.png?text=Generated+Bouquet)

> *Add real screenshots to `/docs/` folder!*

---

## Configuration

- **Config file**: `/etc/enigma2/ciefp_analyzer.conf` (if exists)
- **Bouquet path**: `/etc/enigma2/bouquets.tv`
- **Logs**: `/tmp/ciefp_scan_YYYYMMDD.log`

> Customize theme in `skin.xml` or add custom transponders in `transponders.xml`.

---

## Troubleshooting

| Issue | Solution |
|------|----------|
| Plugin not showing | Check path & restart GUI |
| No signal | Check LNB, cables, DiSEqC port |
| Empty bouquet | Ensure tuner is locked |
| Duplicates | Use **"Clean Bouquet"** option |
| No Abertis signal | Verify dish position (Spain/regions) |

---

## Contributing

Contributions welcome!

1. Fork the repo
2. Create branch: `git checkout -b feature/abertis-enhancement`
3. Commit: `git commit -m "Add new feature"`
4. Push & open **Pull Request**

> Looking for:
> - TivùSat (Italy) support
> - Fransat (5°W) integration
> - Auto-update transponder list

---

## Author

- **ciefp** – [GitHub Profile](https://github.com/ciefp)
- Issues? Open an [Issue](https://github.com/ciefp/CiefpSatelliteAnalyzer/issues)

---

## License

This project is licensed under the **MIT License** – free to use, modify, and distribute.

```plaintext
MIT License © 2025 ciefp
```

---

## Star the Project

Love the plugin? Give it a star!

[![GitHub stars](https://img.shields.io/github/stars/ciefp/CiefpSatelliteAnalyzer?style=social)](https://github.com/ciefp/CiefpSatelliteAnalyzer)

> **Thanks to all installers and users testing in the field!**

---

> **Note**: This plugin is not officially affiliated with Astra or Abertis. Use at your own risk.
```
