import os
import re
import subprocess
import threading
import time

import yaml
from flask import Flask, render_template, request, redirect, url_for, flash
from pyhocon import ConfigFactory, HOCONConverter

app = Flask(__name__)
app.secret_key = os.urandom(24)

dirty = False
dirty_lock = threading.Lock()


def load_config():
    config_path = os.environ.get("APP_CONFIG", "config.yaml")
    with open(config_path) as f:
        return yaml.safe_load(f)


def slugify(name):
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug or "marker"


def read_marker_conf(cfg):
    marker_file = cfg["marker_file"]
    if os.path.exists(marker_file):
        return ConfigFactory.parse_file(marker_file)
    return ConfigFactory.parse_string("")


def ensure_marker_set(conf, cfg):
    ms = cfg["marker_set"]
    label = cfg.get("marker_set_label", "User POIs")
    path = f"marker-sets.{ms}"

    if not conf.get(path, None):
        conf = ConfigFactory.parse_string(
            f"""
            marker-sets.{ms} {{
                label = "{label}"
                toggleable = true
                default-hidden = false
                sorting = 0
                markers {{}}
            }}
            """
        ).with_fallback(conf)
    return conf


def get_existing_markers(conf, cfg):
    ms = cfg["marker_set"]
    path = f"marker-sets.{ms}.markers"
    try:
        markers_conf = conf[path]
        markers = []
        for key in markers_conf:
            m = markers_conf[key]
            markers.append({
                "id": key,
                "label": m.get("label", key),
                "x": m.get("position.x", 0),
                "y": m.get("position.y", 0),
                "z": m.get("position.z", 0),
            })
        return markers
    except Exception:
        return []


def make_unique_id(conf, cfg, base_slug):
    ms = cfg["marker_set"]
    path = f"marker-sets.{ms}.markers"
    try:
        existing = conf[path]
    except Exception:
        return base_slug

    slug = base_slug
    counter = 2
    while slug in existing:
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


def add_marker(cfg, name, x, y, z):
    global dirty
    conf = read_marker_conf(cfg)
    conf = ensure_marker_set(conf, cfg)

    ms = cfg["marker_set"]
    base_slug = slugify(name)
    marker_id = make_unique_id(conf, cfg, base_slug)

    marker_hocon = f"""
    marker-sets.{ms}.markers.{marker_id} {{
        type = "poi"
        label = "{name}"
        position {{
            x = {x}
            y = {y}
            z = {z}
        }}
        sorting = 0
    }}
    """
    new_conf = ConfigFactory.parse_string(marker_hocon)
    merged = new_conf.with_fallback(conf)

    hocon_str = HOCONConverter.to_hocon(merged)
    with open(cfg["marker_file"], "w") as f:
        f.write(hocon_str)

    with dirty_lock:
        dirty = True


def reload_worker(cfg):
    global dirty
    interval = cfg.get("reload_interval_minutes", 60) * 60

    while True:
        time.sleep(interval)
        with dirty_lock:
            should_reload = dirty
            dirty = False

        if should_reload:
            cmd = cfg.get("reload_command", "")
            if cmd:
                try:
                    subprocess.run(cmd, shell=True, check=True, timeout=30)
                    print(f"[reload] Executed: {cmd}")
                except Exception as e:
                    print(f"[reload] Failed: {e}")
                    with dirty_lock:
                        dirty = True


@app.route("/", methods=["GET"])
def index():
    cfg = load_config()
    try:
        conf = read_marker_conf(cfg)
        markers = get_existing_markers(conf, cfg)
    except Exception:
        markers = []
    return render_template("index.html", markers=markers)


@app.route("/add", methods=["POST"])
def add_poi():
    cfg = load_config()
    name = request.form.get("name", "").strip()
    x = request.form.get("x", "").strip()
    y = request.form.get("y", "").strip()
    z = request.form.get("z", "").strip()

    if not name:
        flash("POI name is required.", "error")
        return redirect(url_for("index"))

    try:
        x = int(x)
        y = int(y)
        z = int(z)
    except ValueError:
        flash("Coordinates must be whole numbers.", "error")
        return redirect(url_for("index"))

    try:
        add_marker(cfg, name, x, y, z)
        flash(f'Added POI "{name}" at {x}, {y}, {z}.', "success")
    except Exception as e:
        flash(f"Error adding POI: {e}", "error")

    return redirect(url_for("index"))


if __name__ == "__main__":
    cfg = load_config()
    t = threading.Thread(target=reload_worker, args=(cfg,), daemon=True)
    t.start()
    app.run(host="0.0.0.0", port=5000)
