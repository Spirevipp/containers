# aria2 with AriaNg

Resumable HTTP(S), FTP and SFTP downloads with a bundled web UI. BitTorrent and
Metalink are compiled out. Queues and partial downloads persist across restarts;
retryable failures retry every 60 seconds, with one connection per file by default.
Resuming requires server support; expired links need refreshing.

Image: `ghcr.io/spirevipp/containers/aria2:latest` (Linux amd64/arm64).

## Run

```sh
podman volume create aria2-config
podman volume create aria2-downloads
podman run -d --name aria2 --stop-timeout 60 -p 8085:8080 -p 6800:6800 -v aria2-config:/config -v aria2-downloads:/Downloads ghcr.io/spirevipp/containers/aria2:latest
```

Open `http://<server>:8085`. The same commands work with `docker` or `wslc` in
place of `podman`. For WSLc, prefer a named volume for `/config` to preserve Linux
permissions. Mount your download directory at `/Downloads` if needed.

## Unraid

Copy [unraid-template.xml](unraid-template.xml) to
`/boot/config/plugins/dockerMan/templates-user/my-aria2-direct.xml`, then select
**aria2-direct** under **Docker > Add Container**. Review paths and ports before
applying. The template uses PUID `99`, PGID `100` and a 60-second stop timeout.

| Container port/path | Host example |
| --- | --- |
| `8080/tcp` (web UI) | `8085` |
| `6800/tcp` (RPC) | `6800` |
| `/config` | `/mnt/user/appdata/aria2-direct` |
| `/Downloads` | Your download directory |

For a manually configured template, use WebUI URL `http://[IP]:[PORT:8080]/`.
Enter environment values without surrounding quotes.

## Settings

| Variable | Default | Purpose |
| --- | --- | --- |
| `PUID` / `PGID` | `1000` / `1000` | File owner; typically `99` / `100` on Unraid. |
| `UMASK` | `022` | Permissions mask for new files. |
| `TZ` | `Etc/UTC` | Timezone, e.g. `Europe/Oslo`. |
| `ARIA2_RPC_SECRET` | Empty | Reuse the saved secret or generate one; set to override. No line breaks or surrounding whitespace. |
| `ARIANG_RPC_SECRET_AUTO` | `true` | Supply the secret to AriaNg automatically. |
| `ARIANG_RPC_PORT` | `6800` | Host-side RPC port used by AriaNg. |

Changing the web UI's host port needs no setting changes. Changing the RPC host
port requires the same value in `ARIANG_RPC_PORT`. The browser must reach both
ports. Configure the RPC address/protocol in AriaNg when using a reverse proxy.
If defaults appear stale, try a private browser window.

Automatic secret setup is intended for a trusted LAN: anyone who can load the UI
can retrieve the secret. Set `ARIANG_RPC_SECRET_AUTO=false` to enter it manually.
Browser extensions and API clients use `http://<server>:<rpc-port>/jsonrpc` and
need the secret separately.

## Persistent data

- `/config/aria2.conf`: created on first start; edit while stopped. Startup manages
  the RPC secret and internal RPC port. The effective secret is stored here.
- `/config/aria2.session`: saved queue.
- `/Downloads`: files and their `.aria2` resume metadata; failed/cancelled files
  are retained. Existing subdirectories must be writable by `PUID`/`PGID`.

Allow 60 seconds for shutdown to save state. Set your engine's health-check command
to `container-healthcheck` if desired; the Unraid template includes it.

When migrating from another image, use a fresh config directory. Preserve the
session file, download paths and `.aria2` files, and remove torrent jobs first.

Build, test and release instructions: [AGENTS.md](AGENTS.md).
