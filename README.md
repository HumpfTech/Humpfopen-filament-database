<img align="left" width="80" height="80" src="docs/img/logo.png">
<div style="display: flex; flex-wrap: wrap; gap: 4px; align-items: center;">
  <img src="https://github.com/OpenFilamentCollective/open-filament-database/actions/workflows/validate_data.yaml/badge.svg?v=1">
  <img src="docs/img/badges/brands.svg">
  <img src="docs/img/badges/filaments.svg">
  <img src="docs/img/badges/variants.svg">
  <img src="docs/img/badges/stores.svg">
</div>

# Open Filament Database
The Open Filament Database, hosted by the new "Open Filament Collective" group, currently facilitated by SimplyPrint.

## ✅ Contributing: how to add to the database
The beautiful thing about the database is that it's open source so anyone can contribute, whether you're a hobbyist, print farm or brand.

### The easiest way: use the hosted web editor

For most contributors there is **no setup required** — just open the hosted editor, sign in with GitHub, make your edits, and the editor opens a pull request for you:

👉 **<http://ofd-webui-vv73c.ondigitalocean.app/>**

The hosted editor runs in **cloud mode**: your changes are tracked in your browser and submitted as a GitHub pull request when you're ready (or anonymously, if enabled). See the [WebUI guide](docs/webui.md) for a full walkthrough.

> The URL above is the canonical hosted instance, also recorded under `[project.urls].WebUI` in [`pyproject.toml`](pyproject.toml).

### Or run it locally / edit by hand

If you'd rather work from a local clone — for offline editing, running the validator against your own data, or developing on the WebUI itself — follow the longer path below.

### So what are the steps (local route)?
1. **Create a GitHub account**
2. **Create a copy of the database** (called "forking" this repository)
3. **Install a few small applications** (Git, Python, Node.js)
4. **Download your copy of the database** (called "cloning" it).
5. **Use either our simple web editor or use the manual method**
6. **Check if your data has errors**
7. **Upload your data and make what's called a pull request**

## Let's do it!

### 1. Sign up for a GitHub Account
If you don’t have one already, [create a free GitHub account](https://github.com/join).

### 2. Fork the Project (Two-Click)
Click the **Fork** button in the top right of this page, a guide is [available here if needed](docs/forking.md)
![Fork button getting pressed](docs/img/forking01.png)
### 3. Install our requirements
If you don't have Git installed, [follow this guide](docs/installing-software.md#git). The OFD wrapper script will help you install Python and Node.js automatically (see step 5).

### 4. Download the database
Download the database using either [this guide](docs/cloning.md) or by just using the command below, with `YOUR_USERNAME` replaced ofc!
```bash
git clone https://github.com/YOUR_USERNAME/open-filament-database.git
cd open-filament-database
```
### 5. Make your changes!
You have three options, in order of how much setup they need:

**Option A — Hosted web editor (no setup, recommended):**

Just open <http://ofd-webui-vv73c.ondigitalocean.app/> and sign in with GitHub. Edits become a pull request automatically. See the [WebUI guide](docs/webui.md) for details.

**Option B — Local web editor (for offline work or WebUI development):**

Run the same editor against your local clone using the OFD wrapper (handles setup automatically):

Linux/macOS:
```bash
./ofd.sh webui
```

Windows:
```cmd
ofd.bat webui
```

On first run, the wrapper will:
- Check if Python 3.10+ and Node.js are installed (and help install them if not)
- Create a Python virtual environment
- Install all required dependencies
- Start the WebUI development server

Then access it in your browser at http://localhost:5173

The WebUI includes built-in validation and data sorting features to help ensure your changes are correct. [Full WebUI guide](docs/webui.md)

If you'd rather run things by hand, [install our requirements](docs/installing-software.md) and then:
```bash
cd webui
npm ci
npm run dev
```

**Option C — Edit JSON files directly:** [follow this guide](docs/manual.md)

### 6. Validate and sort your changes
The WebUI can validate and sort your data automatically:

1. Click the "Validate" button in the top-right corner to check for errors
2. Click the "Sort Data" button to organize your JSON files consistently
3. Fix any validation errors that appear (they'll be highlighted in red)

Alternatively, you can use the command-line validation scripts ([see guide](docs/validation.md)):

Linux/macOS:
```bash
./ofd.sh validate                 # Run all validations
./ofd.sh validate --folder-names  # Validate folder names
./ofd.sh validate --json-files    # Validate JSON files against schemas
./ofd.sh validate --logos         # Validate logo files (size, naming, format)
./ofd.sh validate --store-ids     # Validate store IDs in purchase links
./ofd.sh validate --gtin          # Validate GTIN/EAN fields
```

Windows:
```cmd
ofd.bat validate                  # Run all validations
ofd.bat validate --folder-names   # Validate folder names
ofd.bat validate --json-files     # Validate JSON files against schemas
ofd.bat validate --logos          # Validate logo files (size, naming, format)
ofd.bat validate --store-ids      # Validate store IDs in purchase links
ofd.bat validate --gtin           # Validate GTIN/EAN fields
```
### 7. Submit your changes
Before submitting, make sure your data is sorted consistently:
- **In the WebUI:** Click the "Sort Data" button in the top-right corner
- **Or via command line:** Run `./ofd.sh script style_data` (Linux/macOS) or `ofd.bat script style_data` (Windows)

Then add your changes:
```bash
git add .
```

Create a commit with a descriptive message (e.g., "Added Elegoo Red PLA variant"):
```bash
git commit -m "COMMIT_MESSAGE"
```

Upload your changes to GitHub:
```bash
git push -u origin YOUR_BRANCHNAME
```

Finally, make a pull request [using this guide](docs/pull-requesting.md)
