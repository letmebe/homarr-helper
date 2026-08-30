# Homarr Helper

A browser extension that adds the current page to your [Homarr](https://github.com/homarr-labs/homarr) dashboard with a single click.

## Features

- Click the extension icon to open a popup editor with the page title, URL, and icon auto-filled
- All fields are editable — review and confirm before adding
- Automatically remembers the last-used board, with manual override
- Supports Chrome / Edge / Brave and other Chromium-based browsers
- Internationalized UI with Chinese and English (auto-detected from browser language)

## Installation

### Option 1: Load from Release (Recommended)

1. Download the latest `homarr-helper-x.x.x.zip` from the [Releases](../../releases) page
2. Extract it to any folder
3. Open `chrome://extensions/` and enable "Developer mode" in the top-right corner
4. Click "Load unpacked" and select the extracted folder

### Option 2: Load from Source

```bash
git clone https://github.com/letmebe/homarr-helper.git
```

Then load the project directory from `chrome://extensions/`.

## Configuration

After the first install, the options page opens automatically. You need to fill in:

- **Homarr Server URL** — e.g. `http://192.168.18.18:7575`
- **API Key** — create one in Homarr Admin Panel → Tools → API

Click "Test Connection" to verify, then save.

## Usage

1. Browse any webpage
2. Click the Homarr Helper icon in the browser toolbar
3. Confirm or edit the app name, URL, and icon in the popup
4. Select a target board and click "Add"

## Development

This is a plain Manifest V3 extension with no build step. Edit the source files and reload the extension on the extensions management page.

```
├── manifest.json              # Extension manifest
├── background.js              # Service Worker (API calls)
├── popup.html / popup.js      # Popup editor
├── options.html / options.js  # Options page
├── i18n.js                    # HTML i18n attribute processor
├── _locales/
│   ├── zh_CN/messages.json    # Chinese (Simplified) strings
│   └── en/messages.json       # English strings
└── icon48.png / icon128.png   # Icons
```

## License

MIT
