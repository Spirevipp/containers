#!/usr/bin/env python3
"""Test a built image with Podman, Docker, or WSLc; Python stdlib only.

All fixtures live in temporary engine-managed containers/volumes, so the test
does not depend on Linux host paths, UID mapping, or a host-network gateway.
"""

import base64
import json
import os
import re
import shlex
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

ENGINE = shlex.split(os.environ.get("CONTAINER_ENGINE", "podman"))
IMAGE = sys.argv[1] if len(sys.argv) > 1 else "localhost/aria2:dev"


def engine(*args, check=True):
    result = subprocess.run([*ENGINE, *args], text=True, capture_output=True, check=False)
    if check and result.returncode:
        raise RuntimeError(f"Container command failed: {args[0]}\n{result.stdout}\n{result.stderr}")
    return result.stdout.strip()


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_for(check, description, timeout=60):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            result = check()
            if result:
                return result
        except (OSError, ValueError, urllib.error.URLError):
            pass
        time.sleep(0.25)
    raise AssertionError(f"Timed out waiting for {description}")


def main():
    name = "aria2-smoke-" + uuid.uuid4().hex[:10]
    source = name + "-source"
    config = name + "-config"
    downloads = name + "-downloads"
    network = name + "-net"
    ports = {8080: free_port(), 6800: free_port()}
    secret = r"test-&|/+=\secret"
    try:
        engine("network", "create", network)
        engine("volume", "create", config)
        engine("volume", "create", downloads)
        # Serve a controlled file with HTTP range support using the bundled web
        # server. No extra images or access to external download sites is needed.
        engine("run", "-d", "--name", source, "--network", network,
               "--network-alias", "source", "--entrypoint", "/bin/sh", IMAGE, "-ec",
               "mkdir /tmp/fixtures; "
               "dd if=/dev/urandom of=/tmp/fixtures/payload.bin bs=65536 count=64; "
               "exec darkhttpd /tmp/fixtures --port 8080")

        def start(auto=True, supplied_secret=secret):
            engine("run", "-d", "--name", name, "--network", network,
                   "--stop-timeout", "60",
                   "-p", f"127.0.0.1:{ports[8080]}:8080",
                   "-p", f"127.0.0.1:{ports[6800]}:6800",
                   "-v", f"{config}:/config", "-v", f"{downloads}:/Downloads",
                   "-e", f"ARIA2_RPC_SECRET={supplied_secret}",
                   "-e", f"ARIANG_RPC_SECRET_AUTO={str(auto).lower()}",
                   "-e", f"ARIANG_RPC_PORT={ports[6800]}", "-e", "UMASK=077", IMAGE)

        start()

        def rpc(method, args=None, token=secret):
            request = urllib.request.Request(
                f"http://127.0.0.1:{ports[6800]}/jsonrpc",
                data=json.dumps({"jsonrpc": "2.0", "id": "test", "method": method,
                                 "params": [f"token:{token}", *(args or [])]}).encode(),
                headers={"Content-Type": "application/json"},
            )
            try:
                response = urllib.request.urlopen(request, timeout=5)
            except urllib.error.HTTPError as error:
                # aria2 also returns JSON-RPC error bodies with HTTP 400.
                response = error
            with response:
                return json.load(response)

        def ready():
            return rpc("aria2.getVersion").get("result")

        version = wait_for(ready, "RPC startup")
        assert "BitTorrent" not in version["enabledFeatures"], version
        assert "Metalink" not in version["enabledFeatures"], version
        assert "error" in rpc("aria2.getVersion", token="wrong-secret")
        engine("exec", name, "container-healthcheck")

        def web_assets():
            with urllib.request.urlopen(f"http://127.0.0.1:{ports[8080]}/", timeout=5) as response:
                page = response.read().decode()
            paths = re.findall(r'<script[^>]+src=["\']([^"\']+)', page)
            scripts = []
            for path in paths:
                with urllib.request.urlopen(
                        f"http://127.0.0.1:{ports[8080]}/{path.lstrip('/')}", timeout=5) as response:
                    scripts.append(response.read().decode())
            return "\n".join(scripts)

        scripts = wait_for(web_assets, "web UI startup")
        encoded = base64.b64encode(secret.encode()).decode()
        assert f'secret:"{encoded}"' in scripts
        assert f'rpcPort:"{ports[6800]}"' in scripts
        magnet = "magnet:?xt=urn:btih:" + "0" * 40
        assert "error" in rpc("aria2.addUri", [[magnet]])
        assert "error" in rpc("aria2.addTorrent", [base64.b64encode(b"not-a-torrent").decode()])

        added = rpc("aria2.addUri", [["http://source:8080/payload.bin"],
                                    {"out": "payload.bin", "max-download-limit": "512K"}])
        gid = added["result"]

        def status():
            result = rpc("aria2.tellStatus", [gid])["result"]
            if result["status"] == "error":
                raise AssertionError(result)
            return result

        wait_for(lambda: int(status()["completedLength"]) > 262144, "partial download")
        engine("stop", "--time", "60", name)
        session = engine("run", "--rm", "--entrypoint", "/bin/cat",
                         "-v", f"{config}:/config", IMAGE, "/config/aria2.session")
        assert "payload.bin" in session, session
        engine("run", "--rm", "--name", name + "-inspect", "--entrypoint", "/bin/busybox",
               "-v", f"{downloads}:/Downloads", IMAGE, "test", "-f", "/Downloads/payload.bin.aria2")
        engine("start", name)
        wait_for(ready, "RPC after restart")
        wait_for(lambda: status()["status"] == "complete", "resumed download")
        expected = engine("exec", source, "sha256sum", "/tmp/fixtures/payload.bin").split()[0]
        actual = engine("exec", name, "sha256sum", "/Downloads/payload.bin").split()[0]
        assert actual == expected, (actual, expected)
        assert re.search(r'"GET [^"\n]+" 206 ', engine("logs", source)), "No resumed range request"

        # Turning off auto-fill must restore the original secret-free assets.
        # Reuse the persisted config without supplying an environment secret.
        engine("stop", "--time", "60", name)
        engine("rm", name)
        start(auto=False, supplied_secret="")
        wait_for(ready, "persisted secret after recreation")
        scripts = wait_for(web_assets, "web UI with auto-fill disabled")
        assert f'secret:"{encoded}"' not in scripts
        assert 'secret:""' in scripts
        engine("exec", name, "container-healthcheck")

        # Exercise the no-secret first-run default with Unraid's usual IDs.
        engine("stop", "--time", "60", name)
        engine("rm", name)
        engine("run", "--rm", "--entrypoint", "/bin/rm",
               "-v", f"{config}:/config", "-v", f"{downloads}:/Downloads",
               IMAGE, "/config/aria2.conf")
        engine("run", "-d", "--name", name, "--stop-timeout", "60",
               "-p", f"127.0.0.1:{ports[8080]}:8080", "-p", f"127.0.0.1:{ports[6800]}:6800",
               "-v", f"{config}:/config", "-v", f"{downloads}:/Downloads",
               "-e", "PUID=99", "-e", "PGID=100", IMAGE)

        def generated_ready():
            try:
                engine("exec", name, "container-healthcheck")
                return True
            except RuntimeError:
                return False

        wait_for(generated_ready, "generated secret startup")
        effective_config = engine("exec", name, "cat", "/config/aria2.conf")
        generated = re.search(r"^rpc-secret=([0-9a-f]{64})$", effective_config, re.MULTILINE)[1]
        assert "result" in rpc("aria2.getVersion", token=generated)
        generated_encoded = base64.b64encode(generated.encode()).decode()
        assert f'secret:"{generated_encoded}"' in web_assets()
        assert generated not in engine("logs", name)
        assert engine("exec", name, "stat", "-c", "%u:%g:%a", "/config/aria2.conf") == "99:100:600"
        print("PASS: authenticated RPC, UI auto-fill/removal, disabled BitTorrent/Metalink,")
        print("      special-character/generated secrets, Unraid IDs, and verified restart resume.")
    except Exception:
        print(engine("logs", name, check=False), file=sys.stderr)
        print(engine("logs", source, check=False), file=sys.stderr)
        raise
    finally:
        engine("stop", "--time", "60", name, check=False)
        engine("rm", "-f", "-v", name, source, name + "-inspect", check=False)
        engine("volume", "rm", config, downloads, check=False)
        engine("network", "rm", network, check=False)


if __name__ == "__main__":
    main()
