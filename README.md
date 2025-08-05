# 🌍 National Library of Israel Search MCP

Welcome to the **National Library of Israel Model Context Protocol (NLI MCP)** - a modern AI-powered bridge for exploring millions of cultural, historical, and literary assets held by the **National Library of Israel (NLI)**.

This MCP server allows **natural language search** using **Claude**, making it easier than ever to search the NLI digital archive through conversational queries in Hebrew or English.

## 🤔 Why Use This?

The NLI API is powerful but complex. It requires structured metadata-based queries that are hard to construct without technical or library-specific knowledge. This MCP bridges that gap by converting simple questions like:

> "medieval Hebrew manuscripts"

into rich API calls that return accurate and media-rich results with thumbnails, manifests, or streaming content when available.

## 📚 What You Can Discover

The National Library of Israel houses an extraordinary collection including:

- **Historical Documents**: Ancient manuscripts, government records, and personal archives
- **Literary Works**: Books, poetry, and writings in multiple languages
- **Visual Materials**: Photographs, maps, illustrations, and artwork
- **Audio Collections**: Music recordings, speeches, and oral histories
- **Cultural Artifacts**: Items representing Jewish heritage and Israeli culture
- **Academic Resources**: Research materials and scholarly publications

## ⚡ Getting Started

### 1. Install Claude Desktop

First, you need to install Claude Desktop if you haven't already:

- **Windows & Mac**: Download from [https://claude.ai/download](https://claude.ai/download)
- **Linux**: Use the AppImage or follow the installation instructions on the official website

Make sure you have Claude Desktop version ≥ 2.0 for MCP support.

### 2. Download or Clone

#### Option A: Download the packaged release
Download it from [here](https://github.com/mula2812/NLI_AI_Search/releases/tag/v1.0.0).

- Available for **Windows** (with .zip) and **Linux** (with .tar.gz).
- Unzip the downloaded file.
- Double-click to install:
  - `install_mcp_server.bat` (for Windows)
  - `install_mcp_server.bash` (for Linux)

➡ This will install and register the server with **Claude Desktop**.

#### Option B: Clone manually

```bash
git clone https://github.com/mula2812/NLI_AI_Search.git
```

```bash
cd nli_mcp
```

### 3. Make sure Python ≥ 3.10 is installed

#### Windows:

```powershell
winget install Python.Python.3
```

#### Ubuntu/Debian:

```bash
sudo apt update
sudo apt install python3.10 python3.10-venv python3.10-distutils -y
```

To optionally set Python 3.10 as the default:

```bash
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1
sudo update-alternatives --config python3
```

### 4. Install Requirements

```bash
pip install -r requirements.txt
```

### 5. Run the Installer

#### Windows

```cmd
.\install_mcp_server.bat
```

#### Linux

```bash
chmod +x install_mcp_server.bash
./install_mcp_server.bash
```

### 6. Launch Claude Desktop

- Restart Claude Desktop.
- After clicking the **"Search and Tools"** button that is near the + button in the search bar, you should now see a tool named: `nli_mcp`

> If visible, you're ready to go!

## 🔍 What It Does

This server provides:

- 🤖 **Natural Language Query Processing**:

  - Converts everyday language into structured API calls.
  - Handles advanced disambiguation, topic inference, and multiple query generation.

- 📸 **Image Extraction**:

  - Automatically detects relevant thumbnails.
  - Falls back to IIIF manifests if no thumbnails are available.

- 🎧 **Streaming Support**:

  - Supports playback of media via MP4, HLS, or audio endpoints.

- 🌐 **Multilingual Responses**:

  - Answers can be returned in **Hebrew** or **English** based on the user's input.

## ⚙ Tools Available

| Tool Name               | Purpose                                                             |
| ----------------------- | ------------------------------------------------------------------- |
| `process_natural_query` | Converts a natural language query into structured API parameters    |
| `generate_response`     | Fetches results, extracts images, and builds a user-facing response |
| `stream_batches`        | Streams large result sets for long or segmented queries             |
| `get_image`             | Retrieves IIIF image by identifier                                  |
| `get_manifest`          | Retrieves IIIF manifest JSON for a given record                     |
| `get_stream`            | Retrieves MP4/HLS/audio streams associated with a library record    |

## 🎉 Now You Can Enjoy Using It 👨‍💻

Once installed:

- Open **Claude Desktop**.
- Ask any question involving books, authors, subjects, images, or topics.
- For example:
  > Books by Bialik published after 1920.

You'll get:

- Search results
- Metadata
- Links to items
- Images or thumbnails
- In some cases, streaming content or IIIF resources

## 🛠️ Troubleshooting & FAQ

**🔧 Plugin not appearing?**

- Ensure Claude Desktop is ≥ v2.0 and you restarted after install.
- Ensure that the installation package or project is located **only in a path that contains English characters**.

**💬 MCP isn't responding. What should I do?**

- Make sure you installed it correctly. You should see in search and tools the "nli_mcp" addition.

- Ensure you enable all the "nli_mcp" inside options (from the search and tools options).

- Check your internet connection and firewall settings.

- Review the logs for any error messages.

**🔑 "Invalid API key" error**

As a default visitor key is installed to your computer using the bat or bash file, which allows basic access to the library data.

1. Double-check the NLI_API_KEY environment variable, to ensure it installed correctly.
2. Another option is to create your own free KEY:
   Obtaining a personal API key is not essential for the project's initial function, as mentioned. However, if you want to get full access to all the data and capabilities the National Library offers, it is highly recommended to register and get your own API key.

- Visit the National Library of Israel's Open Library API documentation Open Library API ([click](https://api2.nli.org.il/signup/)).
- Follow the instructions to register and get your API key. You may need to contact the National Library for access.

## 🤝 Contributing

I warmly welcome contributions to improve this project. To contribute, please follow these steps:

1. Fork this repository to create your own copy.

2. Make your changes in a new branch.

3. Submit a pull request with a clear description of your changes.

I look forward to seeing your inventions and updates!

## 📬 Contact & Support

Issues & Bugs: GitHub Issues

Discussions & Q&A: GitHub Discussions

## License

This project is open-source and available under the MIT License. Users must retain the copyright notice and license text in all copies or substantial portions of the software.

## 🚨 Disclaimer

This project is not officially affiliated with the National Library of Israel, but it uses their free public OpenLibrary APIs.
