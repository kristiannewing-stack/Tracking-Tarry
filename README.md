# Tarry v1.1

**Tarry** is a lightweight, data-driven Windows Telemetry Monitor designed to help users maintain a "debloated" system state. It sits in your system tray and periodically checks if unwanted Windows services, processes, or registry keys have been re-enabled by system updates.

### 🚀 Key Features
- **Real-time Monitoring:** Checks system services, active processes, registry keys, and DISM features.
- **Data-Driven Design:** Add or remove monitored items by simply editing a JSON file—no coding required.
- **Smart Navigation:** 3-page interface (Monitor, Settings, About) with a modern dark theme.
- **Windows Integration:** 
  - Fixed-size, bottom-right aligned window for a "widget" feel.
  - Native System Tray integration with "Start on Boot" options.
  - Single-instance protection (prevents multiple copies from running).

---

<img width="382" height="570" alt="image" src="https://github.com/user-attachments/assets/5fab384c-b56b-4ba3-b289-b8abecaad623" />


### 📂 Folder Structure
To run the executable or the script, ensure your folder looks like this:
```text
Tarry/
├── Tarry_v1_1.exe          # The main application
├── settings.json           # Auto-generated user preferences
├── about/
│   └── about.json          # Content for the "About" page
└── services/
    └── services.json       # Definitions for telemetry checks


Please check the Releases section for the executable.
