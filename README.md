# Loggamera Integration for Home Assistant
[![HACS](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=flat-square)](https://github.com/hacs/integration)
[![GitHub license](https://img.shields.io/github/license/delize/home-assistant-loggamera-integration.svg?style=flat-square)](https://github.com/delize/home-assistant-loggamera-integration/blob/main/LICENSE)


[![Release Date](https://img.shields.io/github/release-date/delize/home-assistant-loggamera-integration?label=Latest%20Release&color=green)](https://github.com/delize/home-assistant-loggamera-integration/releases/latest) [![Latest Stable](https://img.shields.io/github/v/release/delize/home-assistant-loggamera-integration?label=Stable&color=blue)](https://github.com/delize/home-assistant-loggamera-integration/releases/latest) [![Pre-Release Date](https://img.shields.io/github/release-date-pre/delize/home-assistant-loggamera-integration?label=Latest%20Pre-Release&color=orange)](https://github.com/delize/home-assistant-loggamera-integration/releases) [![Latest Pre-Release](https://img.shields.io/github/v/release/delize/home-assistant-loggamera-integration?include_prereleases&label=Pre-Release&color=orange)](https://github.com/delize/home-assistant-loggamera-integration/releases)


[![Validate with hassfest](https://github.com/delize/home-assistant-loggamera-integration/actions/workflows/hacs-hassfest.yaml/badge.svg?branch=main)](https://github.com/delize/home-assistant-loggamera-integration/actions/workflows/hassfest.yaml)
[![HACS Action](https://github.com/delize/home-assistant-loggamera-integration/actions/workflows/hacs-validation.yaml/badge.svg?branch=main)](https://github.com/delize/home-assistant-loggamera-integration/actions/workflows/hacs.yaml)
[![Code Quality](https://github.com/delize/home-assistant-loggamera-integration/actions/workflows/lint.yaml/badge.svg?branch=main)](https://github.com/delize/home-assistant-loggamera-integration/actions/workflows/lint.yaml)

Integrate your Loggamera devices with Home Assistant for comprehensive energy monitoring, environmental tracking, and device control.

## 📚 **[Complete Documentation & Wiki →](https://github.com/delize/home-assistant-loggamera-integration/wiki)**

**For installation, device support, troubleshooting, and all documentation, visit the [comprehensive wiki](https://github.com/delize/home-assistant-loggamera-integration/wiki).**

## 🚀 Quick Start

### Installation
1. **HACS** → **Integrations** → Search **"Loggamera"** → **Install**
2. **Settings** → **Devices & Services** → **Add Integration** → **Loggamera**
3. Enter your **Loggamera API key** (for a key limited to one device, also enter its Device ID and type)

### Supported Devices
- ⚡ **PowerMeter** - Energy monitoring with HA Energy dashboard integration
- 🌡️ **RoomSensor** - Temperature and humidity tracking
- 💧 **WaterMeter** - Water consumption monitoring
- 🔥 **HeatMeter** - Comprehensive heating system monitoring
- 🔌 **ChargingStation** - EV charging tracking
- 🌡️ **HeatPump** - Heat pump system monitoring
- 🏢 **Organization** - Multi-organization management

## 📊 Features

- **25+ Diagnostic Tools** for troubleshooting and setup
- **Automatic Device Discovery** across organizations
- **Energy Dashboard Integration** for PowerMeter devices
- **Smart Sensor Management** (standard + detailed RawData sensors)
- **Retry Logic & Circuit Breaker** for robust API connectivity
- **Multi-Organization Support** with hierarchy tracking

## 📸 Screenshots

| Device Type | Example |
|-------------|---------|
| **PowerMeter** | ![PowerMeter](https://github.com/delize/home-assistant-loggamera-integration/wiki/assets/demo-screenshot-powermeter.png) |
| **RoomSensor** | ![RoomSensor](https://github.com/delize/home-assistant-loggamera-integration/wiki/assets/demo-screenshot-roomsensor.png) |
| **WaterMeter** | ![WaterMeter](https://github.com/delize/home-assistant-loggamera-integration/wiki/assets/demo-screenshot-watermeter.png) |
| **HeatMeter** | ![HeatMeter](https://github.com/delize/home-assistant-loggamera-integration/wiki/assets/demo-screenshot-heatmeter.png) |

**[View All Screenshots →](https://github.com/delize/home-assistant-loggamera-integration/wiki/Screenshots)**

## 🆘 Need Help?

| Issue Type | Solution |
|------------|----------|
| **Installation problems** | **[Installation Guide](https://github.com/delize/home-assistant-loggamera-integration/wiki/Installation-and-Setup)** |
| **Device not working** | **[Device Help](https://github.com/delize/home-assistant-loggamera-integration/wiki/Device-Help)** |
| **Integration issues** | **[Troubleshooting](https://github.com/delize/home-assistant-loggamera-integration/wiki/Troubleshooting-Guide)** |
| **Check device support** | **[Supported Devices](https://github.com/delize/home-assistant-loggamera-integration/wiki/Supported-Devices)** |

## 🤝 Contributing

- **Developers**: See **[Development Setup](https://github.com/delize/home-assistant-loggamera-integration/wiki/Development-Setup)**
- **New Device Support**: **[Adding Device Support](https://github.com/delize/home-assistant-loggamera-integration/wiki/Adding-Device-Support)**
- **Report Issues**: [GitHub Issues](https://github.com/delize/home-assistant-loggamera-integration/issues)

## 📖 Documentation

**Complete documentation is available in the [Integration Wiki](https://github.com/delize/home-assistant-loggamera-integration/wiki):**

- 📦 [Installation and Setup](https://github.com/delize/home-assistant-loggamera-integration/wiki/Installation-and-Setup)
- 📱 [Supported Devices](https://github.com/delize/home-assistant-loggamera-integration/wiki/Supported-Devices)
- 📸 [Screenshots](https://github.com/delize/home-assistant-loggamera-integration/wiki/Screenshots)
- 🆘 [Device Help](https://github.com/delize/home-assistant-loggamera-integration/wiki/Device-Help)
- 🔧 [Troubleshooting](https://github.com/delize/home-assistant-loggamera-integration/wiki/Troubleshooting-Guide)
- 🛠️ [Diagnostic Tools](https://github.com/delize/home-assistant-loggamera-integration/wiki/Diagnostic-Tools-Reference)
- 👨‍💻 [Development Guide](https://github.com/delize/home-assistant-loggamera-integration/wiki/Development-Setup)

## 🎯 Latest Updates

- **HeatMeter Support** - Complete heating system monitoring with 7 sensors
- **Retry Logic** - Exponential backoff with circuit breaker pattern
- **Organization Hierarchy** - Parent/child organization management
- **Enhanced Sensor Mapping** - Intelligent detection of new device types
- **25+ Diagnostic Tools** - Comprehensive troubleshooting and setup tools
- **Energy Dashboard** - Full integration with Home Assistant Energy

---

**Integration Version**: Latest | **API Version**: Loggamera Platform API v2 | **License**: AGPL-3.0
