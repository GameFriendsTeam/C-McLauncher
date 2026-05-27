# 🚀 C-McLauncher

A lightweight Minecraft launcher built with Python 3.12.

> **Note** 🎯: This is a fun/non-serious project. Use at your own discretion!

## ✨ Features
- 🔐 Microsoft account authentication (working implementation)
- ⚙️ Customizable launch parameters
- 💻 Simple CLI interface
- 🐍 Python 3.12+ compatibility
- 📣 Next steps:
    - [x] Support for Loguru
    - [ ] Add optional download of fabric and forge
        - [ ] Fabric
        - [x] Forge (Can't choose)
    - [x] Improve authentication
        - [x] Fix opening browser on Android
        - [x] Remember Microsoft account
    - [ ] Refactoring
    - [x] Add selection version(s) to download

## 📋 Requirements
- Python 3.12+
- Pip package manager

## 🔧 Installation
1. Clone this repository:
```bash
git clone https://github.com/GameFriendsTeam/C-McLauncher.git
cd C-McLauncher
```
2. Install dependencies:
```bash
pip3 install -r requirements.txt
```
3. Running:
```bash
python3 main.py
```

# 🚀 Usage
### View help menu:
```bash
python3 main.py -h
```

### Run with using args:
```bash
python3 main.py --without_auth --username YouUsername --version 1.21.8
```

## 🔑 Authentication
Microsoft authentication is currently supported and functional. You'll be prompted to authenticate through your browser when first launching.

## ⚠️ Disclaimer
This project is not affiliated with Mojang AB or Microsoft. Minecraft is a trademark of Mojang Studios.
