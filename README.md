# GoobyDDNS_Windows

GoobyDDNS Client for Windows. It's like the NoIP DUC but for your own domain and with Akamai / Linode Name Servers. __I'll add multi-platform support at 10 Stars.__

__Current Version:__ v0.9.5

__Release Date:__ 2026-08-15

![DefaultView](https://github.com/user-attachments/assets/afa44bbe-99a1-45f1-96e5-ee5c0beffe2b)

__You'll need...__

- Linode API/PAT Key with Domain R/W Access
- Linode-CLI Domain Record ID
- Linode-CLI Subdomain Record ID

## Build Process

```shell
python -m pip install -r requirements.txt
pyinstaller --onefile --noconsole \
  --icon "assets/icon.ico" \
  --hidden-import requests \
  --hidden-import pystray \
  --hidden-import PIL \
  --add-data "template.ini;." \
  --add-data "assets/icon.ico;assets" \
  --name GoobyDDNS app.py
```

If `pystray` is not available in a frozen build, the application will fall back to a normal window close instead of crashing.

Linux Users should consider [GoobyDDNS_Linux](https://github.com/GoobyFRS/GoobyDDNS)
