# unstucked
An easy way to connect to "eduroam".

## Script

Run:

```bash
python3 eduroam.py
```

The script supports:

- Linux (NetworkManager / `nmcli`)
- Windows (`netsh` + `wlanapi.dll`)

It asks only for username and password, configures WPA2-Enterprise (PEAP/MSCHAPv2), and disables server certificate validation.
