# aria2 with AriaNg

A single OCI container image for long-running HTTP(S), FTP and SFTP downloads,
Build with Podman, Buildah, or Docker; run with any compatible container engine.

## What changed

- One multi-stage **Containerfile** builds aria2 from source and bundles AriaNg.
- **BitTorrent and Metalink are compiled out.**
- Persistent queue and partial-file state, unlimited retryable attempts with a
  60-second delay, and a 120-second inactivity timeout.
- One connection per file by default. Resume failure stops the job rather than
  starting the file over. Servers must support resume; expired links still need
  refreshing.
- AriaNg automatically receives the RPC secret by default. Both services run as
  the configured user, under s6 supervision.

## Build locally

From the repository root:

```sh
podman build --format oci -f aria2/Containerfile -t localhost/aria2:dev aria2
```

Or with Buildah:

```sh
buildah bud --format oci -f aria2/Containerfile -t localhost/aria2:dev aria2
```

Docker can consume the same file with
`docker build -f aria2/Containerfile -t aria2:dev aria2`.

### Windows with WSL Containers (WSLc)

[Microsoft's WSL Containers engine](https://learn.microsoft.com/en-us/windows/wsl/wsl-container)
can build and run this image directly through `wslc.exe`; Docker Desktop is not
needed. From PowerShell in the repository root:

```powershell
wslc build -f aria2/Containerfile -t aria2:dev aria2
wslc volume create aria2-config
wslc volume create aria2-downloads
wslc run -d --name aria2 --stop-timeout 60 `
  -p 127.0.0.1:8085:8080 -p 127.0.0.1:6800:6800 `
  -v aria2-config:/config -v aria2-downloads:/Downloads aria2:dev
```

Open `http://localhost:8085`. Named volumes keep Linux file permissions inside
the engine's VM. Windows bind mounts can have different ownership behavior;
use a named volume for `/config`. WSLc does not currently have a restart-policy
flag, so the example deliberately omits one. The image also works with Docker
Desktop's Linux engine and Podman with a Linux machine.

To run the same integration checks used in CI from PowerShell:

```powershell
$env:CONTAINER_ENGINE = 'wslc'
python aria2/tests/smoke.py aria2:dev
```

### Build inputs

The supported platforms are Linux amd64 and arm64. The build pins source and
frontend versions and verifies their archive SHA-256 hashes. Updating a version
requires updating its matching checksum. Alpine package updates are picked up
when rebuilding. The unmodified aria2 source archive is included in the image.

## Unraid setup

An Unraid v2 template is included as [unraid-template.xml](unraid-template.xml).
It already points to `ghcr.io/spirevipp/containers/aria2:latest` and includes both
ports, persistent paths, the supported variables, a 60-second stop timeout and
health checks for both services.

To install it, copy the XML file to
`/boot/config/plugins/dockerMan/templates-user/my-aria2-direct.xml` on your Unraid
server. Then open **Docker > Add Container**, select **aria2-direct** from the
user templates, and review the paths and ports before applying. The template
uses PUID `99`, PGID `100`, web UI port `8085`, and a fresh config directory at
`/mnt/user/appdata/aria2-direct`. The image must have been published to GHCR first.

After GitHub Actions publishes the image, use
`ghcr.io/<owner>/<repository>/aria2:latest` as the repository in an Unraid
container template. If GHCR creates the package as private, change its visibility
to public in GitHub package settings before pulling anonymously.

Use bridge networking and add these mappings:

| Type | Container | Host example |
| --- | --- | --- |
| TCP port | `8080` | `8085` (choose any unused port) |
| TCP port | `6800` | `6800` |
| Path | `/config` | `/mnt/user/appdata/aria2-direct` |
| Path | `/Downloads` | Your download directory |

Do not publish torrent ports; this binary does not implement BitTorrent.
Set the Unraid WebUI URL to `http://[IP]:[PORT:8080]/`.

| Variable | Default | Purpose |
| --- | --- | --- |
| `PUID` | `1000` | Download/config owner; typically `99` for Unraid's nobody user. |
| `PGID` | `1000` | Owner group; typically `100` for Unraid's users group. |
| `UMASK` | `022` | Permissions mask for newly created files. |
| `TZ` | `Etc/UTC` | Timezone, for example `Europe/Oslo`. |
| `ARIA2_RPC_SECRET` | Empty | Use this secret; otherwise reuse the saved secret or generate one on first start. |
| `ARIANG_RPC_SECRET_AUTO` | `true` | Embed the secret in the served UI's default settings. |
| `ARIANG_RPC_PORT` | `6800` | RPC **host-side** port used by the UI; change this if mapping RPC to a different host port. |

Enter Unraid values without surrounding quotes. A secret must not contain line
breaks or leading/trailing whitespace. `/config/aria2.conf` stores the effective
secret with permissions `0600`; it is never printed to the logs.

Internal ports stay fixed at 8080 and 6800. Changing only the web UI's host port
needs no variable changes. Changing the RPC host port also requires setting
`ARIANG_RPC_PORT` to that host port. The browser connects directly to the server's
LAN address; it must be able to reach both ports. For a reverse proxy or HTTPS,
configure the matching RPC address/protocol in AriaNg as well.

Anyone who can load the UI can recover an automatically embedded secret. This
default is intended for your trusted LAN. Set auto-fill to `false` to enter the
secret manually instead. Existing browser settings can override new defaults;
test with a private window if needed. Extensions still need the secret separately.

Give the container a 60-second stop timeout so aria2 can save state. There is a
`container-healthcheck` command that checks both the UI and RPC, usable with your
engine's health-check settings. Health-check metadata is not included because it
is not part of the OCI image specification.

## Configuration and migration

The default `/config/aria2.conf` is created only when missing. Edit it while the
container is stopped; restart afterwards. Startup manages only `rpc-secret` and
`rpc-listen-port`. The queue is `/config/aria2.session`; partial-download control
files remain beside their downloads. There is no cleanup of failed or cancelled
downloads. Only `/config` and the top of `/Downloads` have ownership adjusted;
existing download subdirectories must already be writable by PUID/PGID.

For migration from johngong/aria2, back up your configuration and use a **new
config directory**. Do not copy its aria2.conf: it contains options for features
absent from this binary. Stop the old container, copy `aria2.session` if you need
its file-download queue, and keep the same download mapping and `.aria2` files.
Remove any torrent jobs before migrating. Keep the existing RPC secret if desired.
Use `PUID`/`PGID` instead of the old image's `UID`/`GID`. Tracker, torrent, language,
and internal port variables from the old image are no longer used.

## GitHub Actions

The workflow at `.github/workflows/aria2.yml`:

1. Builds native amd64 and arm64 OCI images with Podman.
2. Tests authenticated RPC, UI secret auto-fill, disabled BitTorrent/Metalink,
   and a real HTTP range download resumed after a container restart.
3. Publishes the tested images and a multi-architecture OCI manifest to GHCR.

Pull requests build and test without publishing. Pushes to `main` publish
`:latest` and `:sha-<12-character-commit>`. Tags such as `aria2-v1.0.0` publish
`:1.0.0` and the commit tag. Manual runs on the default branch also publish.
Temporary `build-<run>-<attempt>-<architecture>` tags hold the tested images used
to assemble the manifest. No extra repository secrets are needed: publication
uses `GITHUB_TOKEN` with package-write permission. Enable Actions after creating
the GitHub repository. The workflow uses native GitHub-hosted ARM runners.

To run the integration checks locally after building:

```sh
CONTAINER_ENGINE=podman python3 aria2/tests/smoke.py localhost/aria2:dev
```

The test uses named volumes, a private container network and another instance
of the same image to serve the test file. It does not need a separate fixture
image or a host-side HTTP server. It also supports `CONTAINER_ENGINE=docker`
and `CONTAINER_ENGINE=wslc`.
