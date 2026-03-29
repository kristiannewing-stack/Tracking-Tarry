# Security Policy

## Our Commitment to Security

The Windows 11 Transparency Monitor is designed to help users understand what their system is doing. As a security and privacy-focused tool, we take the security of this project seriously. This document outlines our security practices, how to report vulnerabilities, and what users can expect from us.

## Supported Versions

We provide security updates for the following versions:

| Version | Supported          | Status |
| ------- | ------------------ | ------ |
| 1.0.x   | :white_check_mark: | Active development |
| 0.9.x   | :white_check_mark: | Security fixes only |
| < 0.9   | :x:                | No longer supported |

**Note**: We recommend always using the latest stable release.

## Security Principles

### 1. **No Data Collection**
- This tool does **NOT** collect, transmit, or store any user data.
- All monitoring happens locally on your machine.
- No telemetry, analytics, or phone-home functionality.
- No network connections are made by this application.

### 2. **Minimal Permissions**
- The tool requests only the permissions necessary for monitoring.
- Administrator privileges are **optional** (required only for full service status checks).
- Registry access is read-only.
- No system modifications are made.

### 3. **Transparency**
- All source code is open and auditable.
- Detection methods are documented.
- No obfuscated or hidden functionality.
- Dependencies are minimal and well-known (Python, PyQt6).

### 4. **Local Operation**
- Everything runs on your local machine.
- No cloud services or external APIs.
- No dependencies on third-party servers.
- Fully functional offline.

## What This Tool Does NOT Do

To be absolutely clear about our security stance:

- ❌ **Does NOT modify** Windows registry.
- ❌ **Does NOT disable** any Windows services.
- ❌ **Does NOT collect** user data.
- ❌ **Does NOT connect** to the internet.
- ❌ **Does NOT require** administrator rights (though some features work better with them).
- ❌ **Does NOT install** drivers or kernel modules.
- ❌ **Does NOT execute** arbitrary code.
- ❌ **Does NOT access** personal files or documents.

## What This Tool DOES Do

- ✅ **Reads** Windows registry values (read-only).
- ✅ **Queries** Windows service status.
- ✅ **Checks** running processes.
- ✅ **Displays** status information in a GUI.
- ✅ **Runs** in the system tray.
- ✅ **Updates** status periodically (every 30 seconds by default).

## Reporting a Vulnerability

We take all security reports seriously. If you discover a security vulnerability.

### 1. **Do Not Open a Public Issue**
Please do not disclose security vulnerabilities publicly until we've had a chance to address them.

### 2. **Contact Us Privately**

**Email**: tracking.tarry@gmail.com 

**Subject**: `[SECURITY] Brief description of the issue`

### 3. **Include the Following Information**

```markdown
**Vulnerability Type**
[e.g., Code Injection, Privilege Escalation, Information Disclosure]

**Affected Component**
[e.g., Registry checker, Service monitor, UI component]

**Affected Versions**
[e.g., v1.0.0, all versions, etc.]

**Description**
A clear description of the vulnerability.

**Steps to Reproduce**
1. Step one
2. Step two
3. ...

**Proof of Concept**
Code, screenshots, or other evidence demonstrating the vulnerability.

**Impact Assessment**
What could an attacker do with this vulnerability?

**Suggested Fix** (optional)
If you have ideas on how to fix it.

**Your Contact Information**
So we can follow up with you.