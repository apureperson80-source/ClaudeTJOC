"""Screen content for the control room.

* ``render_feeds`` renders every CCTV camera of the CCTV Sets scene to a PNG
  (kept in ``props_gen/images`` so normal builds need not render them again);
* ``build_atlas`` grades those renders into security-camera footage (cool
  tint, grain, vignette, on-screen labels and timestamps) and lays them out in
  the *Screens Atlas* together with generated monitor UIs: a 3x3 and a 2x2
  camera grid, an event log, a floor plan and a dashboard.

Atlas tiles (row-major from the top left), see ``facility.screen_tile``:
  0-9  CCTV feeds 01-10      10  3x3 camera grid     11  event log
  12   floor plan            13  2x2 camera grid     14  dashboard
  15   "no signal" screen
"""

import math
import os
import random

import bpy
import numpy as np

from .facility import ATLAS_COLS, ATLAS_ROWS
from .textures import Canvas, load_png, packed_image, resize

TILE_W, TILE_H = 800, 450
IMAGES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'images')
STAMP = '2026-10-08'

BG = '#0b1622'
PANEL = '#13263a'
CYAN = '#3fd0ff'
DIM = '#5f7d96'
TEXT = '#cfe6f5'


def feed_path(i):
    return os.path.join(IMAGES, 'cctv_%02d.png' % (i + 1))


# ---------------------------------------------------------------------------
# Rendering the feeds
# ---------------------------------------------------------------------------

def render_feeds(scene, feeds, samples=48):
    """Render each CCTV camera to images/cctv_XX.png (raw, ungraded)."""
    os.makedirs(IMAGES, exist_ok=True)
    r = scene.render
    r.resolution_x, r.resolution_y = TILE_W, TILE_H
    r.resolution_percentage = 100
    scene.cycles.samples = samples
    for i, (cam, label) in enumerate(feeds):
        scene.camera = cam
        r.filepath = feed_path(i)
        bpy.ops.render.render(write_still=True, scene=scene.name)
        print('  feed %2d  %s' % (i + 1, label))


# ---------------------------------------------------------------------------
# Footage look
# ---------------------------------------------------------------------------

def _cctv_grade(px, label, cam_no, seed):
    rng = np.random.default_rng(seed)
    h, w = px.shape[:2]
    lum = (px * np.array([0.2126, 0.7152, 0.0722])).sum(-1, keepdims=True)
    px = lum + (px - lum) * 0.5                        # washed-out colour
    px = px * np.array([0.74, 0.94, 1.04]) + np.array([0.0, 0.012, 0.03])   # cool camera tint
    px = np.clip((px - 0.05) * 1.1, 0, 1) ** 1.25
    ys, xs = np.mgrid[0:h, 0:w]
    r2 = ((xs - w / 2) / (w / 2)) ** 2 + ((ys - h / 2) / (h / 2)) ** 2
    px *= (1.0 - 0.28 * np.clip(r2 - 0.2, 0, 1))[..., None]
    px += rng.normal(0, 0.022, (h, w, 1))
    px *= (0.97 + 0.03 * np.sin(ys * math.pi / 1.5))[..., None]   # faint scan lines
    cv = Canvas(w, h)
    cv.px = np.clip(px, 0, 1)
    t = '%02d:%02d:%02d' % (14, 32 + cam_no // 3, (7 + cam_no * 13) % 60)
    cv.text('CAM %02d  %s' % (cam_no, label), 18, h - 34, 15, '#ffffff', weight=0.45,
            outline=0.35, outline_color='#000000')
    cv.text('%s  %s' % (STAMP, t), w - 18, h - 34, 15, '#ffffff', weight=0.45, align='right',
            outline=0.35, outline_color='#000000')
    cv.ellipse(26, 26, 6, 6, '#ff2a2a')
    cv.text('REC', 38, 20, 13, '#ffffff', weight=0.45, outline=0.35, outline_color='#000000')
    return cv.px


def _no_signal(label, cam_no):
    cv = Canvas(TILE_W, TILE_H, '#0a1a2e')
    for k in range(0, TILE_W, 40):
        cv.rect(k, 0, k + 1, TILE_H, '#10243c')
    cv.text('NO SIGNAL', TILE_W / 2, TILE_H / 2 - 12, 34, '#7fb2e0', weight=0.6, align='center')
    cv.text('CAM %02d  %s' % (cam_no, label), TILE_W / 2, TILE_H / 2 - 54, 14, DIM, weight=0.45,
            align='center')
    return cv.px


# ---------------------------------------------------------------------------
# Monitor UIs
# ---------------------------------------------------------------------------

def _chrome(title):
    cv = Canvas(TILE_W, TILE_H, BG)
    cv.rect(0, TILE_H - 34, TILE_W, TILE_H, PANEL)
    cv.text(title, 14, TILE_H - 24, 13, TEXT, weight=0.5)
    cv.text('%s 14:32:18' % STAMP, TILE_W - 14, TILE_H - 24, 13, DIM, weight=0.45, align='right')
    for k, c in enumerate(('#ff5f56', '#ffbd2e', '#27c93f')):
        cv.ellipse(TILE_W - 300 + k * 18, TILE_H - 17, 5, 5, c)
    return cv


def _camera_grid(feeds, n, title):
    cv = _chrome(title)
    side = 120 if n == 3 else 0
    if side:
        cv.rect(0, 0, side, TILE_H - 34, PANEL)
        for k in range(10):
            y = TILE_H - 62 - k * 30
            cv.ellipse(14, y + 4, 4, 4, '#27c93f' if k != 6 else '#ff5f56')
            cv.text('CAM %02d' % (k + 1), 26, y, 10, TEXT if k < 9 else DIM, weight=0.4)
    gx0, gy0, gx1, gy1 = side + 6, 6, TILE_W - 6, TILE_H - 40
    cw, ch = (gx1 - gx0) / n, (gy1 - gy0) / n
    for k in range(n * n):
        i, j = k % n, n - 1 - k // n
        x0, y0 = int(gx0 + i * cw + 2), int(gy0 + j * ch + 2)
        x1, y1 = int(gx0 + (i + 1) * cw - 2), int(gy0 + (j + 1) * ch - 2)
        tile = resize(feeds[k % len(feeds)], x1 - x0, y1 - y0)
        cv.px[y0:y1, x0:x1] = tile
        if k == 4 and n == 3:
            cv.frame(x0 - 2, y0 - 2, x1 + 2, y1 + 2, 2, '#ff5f56')
    return cv.px


def _event_log():
    rng = random.Random(4)
    cv = _chrome('EVENT LOG  -  SITE 01')
    cols = [14, 120, 230, 470, 640]
    heads = ['TIME', 'CAMERA', 'EVENT', 'ZONE', 'STATUS']
    y = TILE_H - 62
    for x, hname in zip(cols, heads):
        cv.text(hname, x, y, 11, CYAN, weight=0.5)
    cv.rect(10, y - 8, TILE_W - 10, y - 7, DIM)
    events = ['MOTION DETECTED', 'DOOR OPENED', 'DOOR CLOSED', 'BADGE ACCEPTED', 'LINE CROSSING',
              'TAMPER CHECK OK', 'VIDEO LOSS', 'MOTION DETECTED', 'PERSON DETECTED']
    zones = ['BREAK ROOM', 'WAREHOUSE', 'DESPATCH', 'PRINT ROOM', 'OFFICE', 'CORRIDOR B',
             'SERVER ROOM', 'LOBBY']
    for k in range(13):
        y -= 27
        if k % 2 == 0:
            cv.rect(10, y - 7, TILE_W - 10, y + 17, '#0f1e2e')
        ev = rng.choice(events)
        status = 'ALARM' if ev in ('VIDEO LOSS', 'LINE CROSSING') else rng.choice(['OK', 'OK', 'ACK'])
        col = '#ff5f56' if status == 'ALARM' else ('#27c93f' if status == 'OK' else '#ffbd2e')
        cv.text('14:%02d:%02d' % (31 - k // 3, rng.randint(0, 59)), cols[0], y, 11, TEXT, weight=0.4)
        cv.text('CAM %02d' % rng.randint(1, 10), cols[1], y, 11, TEXT, weight=0.4)
        cv.text(ev, cols[2], y, 11, TEXT, weight=0.4)
        cv.text(rng.choice(zones), cols[3], y, 11, DIM, weight=0.4)
        cv.rect(cols[4], y - 2, cols[4] + 70, y + 13, col, r=3)
        cv.text(status, cols[4] + 35, y + 1, 10, '#0b1622', weight=0.5, align='center')
    return cv.px


def _floor_plan():
    cv = _chrome('SITE MAP  -  GROUND FLOOR')
    rooms = [(40, 40, 260, 220, 'WAREHOUSE'), (260, 40, 420, 150, 'DESPATCH'),
             (420, 40, 560, 150, 'PRINT'), (560, 40, 760, 220, 'OFFICE'),
             (260, 150, 560, 200, 'CORRIDOR B'), (40, 220, 300, 380, 'BREAK ROOM'),
             (300, 220, 520, 380, 'LOBBY'), (520, 220, 760, 380, 'SERVER ROOM')]
    for (x0, y0, x1, y1, name) in rooms:
        cv.rect(x0, y0, x1, y1, '#102236')
        cv.frame(x0, y0, x1, y1, 2, '#2f5d80')
        cv.text(name, (x0 + x1) / 2, (y0 + y1) / 2 - 5, 11, DIM, weight=0.45, align='center')
    cams = [(70, 360), (110, 200), (280, 60), (440, 130), (740, 60), (290, 175), (740, 360),
            (320, 360), (740, 200), (60, 250)]
    for k, (x, y) in enumerate(cams):
        cv.ellipse(x, y, 9, 9, '#0b1622')
        cv.ring(x, y, 9, 2.5, CYAN if k != 6 else '#ff5f56')
        cv.ellipse(x, y, 3, 3, CYAN if k != 6 else '#ff5f56')
        cv.text('%02d' % (k + 1), x + 13, y - 4, 9, TEXT, weight=0.4)
    cv.rect(520, 220, 760, 380, '#ff5f56', opacity=0.12)
    return cv.px


def _dashboard():
    rng = random.Random(9)
    cv = _chrome('SYSTEM STATUS')
    # tiles with numbers
    for k, (title, val, col) in enumerate((('CAMERAS ONLINE', '10/10', '#27c93f'),
                                           ('OPEN ALARMS', '2', '#ff5f56'),
                                           ('DOORS SECURED', '24', CYAN),
                                           ('STORAGE', '71%', '#ffbd2e'))):
        x0 = 14 + k * 194
        cv.rect(x0, TILE_H - 150, x0 + 180, TILE_H - 50, PANEL, r=6)
        cv.text(title, x0 + 12, TILE_H - 74, 10, DIM, weight=0.45)
        cv.text(val, x0 + 12, TILE_H - 130, 34, col, weight=0.6)
    # bar chart
    cv.rect(14, 14, 520, TILE_H - 166, PANEL, r=6)
    cv.text('EVENTS PER HOUR', 26, TILE_H - 190, 10, DIM, weight=0.45)
    for k in range(18):
        hgt = 20 + rng.random() * 170
        x = 34 + k * 26
        cv.rect(x, 30, x + 16, 30 + hgt, CYAN if k != 13 else '#ff5f56', r=2)
    # line graph
    cv.rect(534, 14, TILE_W - 14, TILE_H - 166, PANEL, r=6)
    cv.text('NETWORK', 546, TILE_H - 190, 10, DIM, weight=0.45)
    pts = []
    v = 120
    for k in range(30):
        v = min(220, max(40, v + rng.uniform(-25, 25)))
        pts.append((548 + k * 7.4, v))
    cv.polyline(pts, 2.5, '#27c93f')
    return cv.px


# ---------------------------------------------------------------------------
# Atlas
# ---------------------------------------------------------------------------

def build_atlas(labels):
    """Compose the Screens Atlas image from the feed renders (falls back to
    'no signal' for feeds that have not been rendered)."""
    feeds = []
    for i, label in enumerate(labels):
        p = feed_path(i)
        if os.path.exists(p):
            raw = load_png(p)
            if raw.shape[:2] != (TILE_H, TILE_W):
                raw = resize(raw, TILE_W, TILE_H)
            feeds.append(_cctv_grade(raw, label, i + 1, 100 + i))
        else:
            feeds.append(_no_signal(label, i + 1))
    tiles = list(feeds)
    while len(tiles) < 10:
        tiles.append(_no_signal('SPARE', len(tiles) + 1))
    tiles += [_camera_grid(feeds, 3, 'LIVE VIEW  -  ALL CAMERAS'), _event_log(), _floor_plan(),
              _camera_grid(feeds[:4], 2, 'LIVE VIEW  -  QUAD'), _dashboard(),
              _no_signal('SPARE', 16)]
    W, H = TILE_W * ATLAS_COLS, TILE_H * ATLAS_ROWS
    atlas = np.zeros((H, W, 3))
    for k, t in enumerate(tiles[:ATLAS_COLS * ATLAS_ROWS]):
        col, row = k % ATLAS_COLS, ATLAS_ROWS - 1 - k // ATLAS_COLS
        atlas[row * TILE_H:(row + 1) * TILE_H, col * TILE_W:(col + 1) * TILE_W] = t
    return packed_image('Screens Atlas', atlas, quality=90)
