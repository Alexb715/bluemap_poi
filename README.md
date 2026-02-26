# BlueMap POI Web Editor

A simple web app for adding POI markers to a BlueMap Minecraft server map. Submit a name and coordinates through the form, and the marker gets written to the BlueMap HOCON config. A background timer batches reloads so multiple POIs can be added without constant reloads.

## Config

Copy and edit `config.yaml`:

```yaml
marker_files:
  overworld: /path/to/bluemap/config/maps/overworld.conf
  nether: /path/to/bluemap/config/maps/the_nether.conf
  end: /path/to/bluemap/config/maps/the_end.conf
reload_command: "rcon-cli bluemap reload light"
reload_interval_minutes: 60
marker_set: "user-pois"
marker_set_label: "User POIs"
```

| Option | Description |
|---|---|
| `marker_files` | Map of world names to their BlueMap `.conf` files |
| `reload_command` | Shell command to reload BlueMap after changes |
| `reload_interval_minutes` | Minutes between reload checks (only reloads if POIs were added) |
| `marker_set` | HOCON key for the marker-set to store POIs in |
| `marker_set_label` | Display label for the marker-set on the map |

The `reload_command` is just a shell command — set it to whatever works for your environment. See the deployment examples below.

## Deployment

### Bare metal / VM

Run directly on the same machine as your Minecraft server. No socket mounting needed — the reload command runs on the host.

```yaml
# config.yaml
marker_files:
  overworld: /opt/bluemap/config/maps/overworld.conf
  nether: /opt/bluemap/config/maps/the_nether.conf
  end: /opt/bluemap/config/maps/the_end.conf
reload_command: "rcon-cli bluemap reload light"
```

```bash
pip install -r requirements.txt
python app.py
```

### Docker

```yaml
# config.yaml
marker_files:
  overworld: /bluemap/config/maps/overworld.conf
  nether: /bluemap/config/maps/the_nether.conf
  end: /bluemap/config/maps/the_end.conf
reload_command: "docker exec minecraft rcon-cli bluemap reload light"
```

```yaml
# docker-compose.yml
services:
  poi-editor:
    build: .
    ports:
      - "5000:5000"
    volumes:
      - ./config.yaml:/app/config.yaml:ro
      - /path/to/bluemap/config:/bluemap/config
      - /var/run/docker.sock:/var/run/docker.sock  # needed for docker exec
    restart: unless-stopped
```

```bash
docker compose up -d
```

> Note: The container needs the Docker CLI installed to use `docker exec`. If you prefer not to mount the Docker socket, use RCON directly instead (see below).

### Podman

```yaml
# config.yaml
marker_files:
  overworld: /bluemap/config/maps/overworld.conf
  nether: /bluemap/config/maps/the_nether.conf
  end: /bluemap/config/maps/the_end.conf
reload_command: "podman exec minecraft rcon-cli bluemap reload light"
```

```yaml
# docker-compose.yml (or podman-compose)
services:
  poi-editor:
    build: .
    ports:
      - "5000:5000"
    volumes:
      - ./config.yaml:/app/config.yaml:ro
      - /path/to/bluemap/config:/bluemap/config
      - /run/podman/podman.sock:/run/podman/podman.sock  # needed for podman exec
    restart: unless-stopped
```

```bash
podman-compose up -d
```

### Using RCON directly

If you don't want to mount a container socket, you can use a standalone RCON client like `mcrcon` to connect to the Minecraft server's RCON port directly:

```yaml
# config.yaml
reload_command: "mcrcon -H minecraft-server -P 25575 -p yourpassword 'bluemap reload light'"
```

This works from any setup (bare metal, Docker, Podman, VM) as long as the RCON port is reachable.

## Usage

Open `http://localhost:5000`, select a world, fill in a POI name and coordinates, and submit. The marker is written to the `.conf` file immediately. BlueMap reloads automatically on the configured interval (only if new POIs were added).
