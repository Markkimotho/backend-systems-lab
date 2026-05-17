"""
Generate high-contrast, clearly readable architecture diagrams for Backend Systems Lab.
Produces 3 PNG images: system-architecture.png, request-flow-sequence.png, component-flows.png

Design: clean white background, bold saturated colors, large readable fonts,
thick lines, prominent labels. No faint/low-contrast elements.
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.font_manager import FontProperties
import os

# ─── Paths ───────────────────────────────────────────────────────────────────
BASE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(BASE, "fonts")
OUT_DIR = os.path.join(BASE, "docs", "diagrams")
os.makedirs(OUT_DIR, exist_ok=True)

# ─── Fonts ───────────────────────────────────────────────────────────────────
HAND = FontProperties(fname=os.path.join(FONT_DIR, "NothingYouCouldDo-Regular.ttf"))
MONO_BOLD = FontProperties(fname=os.path.join(FONT_DIR, "JetBrainsMono-Bold.ttf"))
MONO_REG = FontProperties(fname=os.path.join(FONT_DIR, "JetBrainsMono-Regular.ttf"))

# ─── High-Contrast Colour Palette ───────────────────────────────────────────
BG      = '#FFFFFF'
BG_SOFT = '#F8F9FA'
GRID_C  = '#E8E8E8'
INK     = '#1A1A2E'
INK2    = '#2D2D44'
SUBTLE  = '#5A5A7A'
MUTED   = '#8888AA'
RED     = '#D32F2F'
RED_BG  = '#FFEBEE'
BLUE    = '#1565C0'
BLUE_BG = '#E3F2FD'
GREEN   = '#2E7D32'
GREEN_BG= '#E8F5E9'
AMBER   = '#F57F17'
AMBER_BG= '#FFF8E1'
PURPLE  = '#6A1B9A'

# ─── RNG ─────────────────────────────────────────────────────────────────────
rng = np.random.default_rng(42)

# ─── Shared Drawing Helpers ──────────────────────────────────────────────────

def draw_grid(ax, xlim, ylim):
    """Draw subtle grid for alignment reference."""
    for x in np.arange(0, xlim + 0.1, 1):
        lw = 0.4 if x % 4 == 0 else 0.15
        ax.axvline(x, color=GRID_C, lw=lw, zorder=0)
    for y in np.arange(0, ylim + 0.1, 1):
        lw = 0.4 if y % 4 == 0 else 0.15
        ax.axhline(y, color=GRID_C, lw=lw, zorder=0)


def draw_box(ax, x, y, w, h, border_color, fill_color, lw=2.5,
             rounded=True, shadow=True):
    """Draw a clean rounded rectangle with optional shadow."""
    if shadow:
        sh = FancyBboxPatch((x + 0.08, y - 0.08), w, h,
                            boxstyle="round,pad=0.15" if rounded else "square,pad=0",
                            facecolor='#00000010', edgecolor='none', zorder=1)
        ax.add_patch(sh)
    box = FancyBboxPatch((x, y), w, h,
                         boxstyle="round,pad=0.15" if rounded else "square,pad=0",
                         facecolor=fill_color, edgecolor=border_color,
                         linewidth=lw, zorder=2)
    ax.add_patch(box)


def draw_arrow(ax, x1, y1, x2, y2, color, lw=2.5, dashed=False,
               head_width=0.18, head_length=0.12):
    """Draw a clean straight arrow."""
    style = (0, (6, 4)) if dashed else '-'
    dx = x2 - x1
    dy = y2 - y1
    length = np.sqrt(dx**2 + dy**2) + 1e-9
    # Shorten to leave room for arrowhead
    shorten = head_length * 1.2
    end_x = x2 - (dx / length) * shorten
    end_y = y2 - (dy / length) * shorten
    ax.plot([x1, end_x], [y1, end_y], color=color, lw=lw,
            linestyle=style, solid_capstyle='round', zorder=4)
    # Arrowhead
    ax.annotate('', xy=(x2, y2), xytext=(end_x, end_y),
                arrowprops=dict(arrowstyle='->', color=color, lw=lw,
                                mutation_scale=18),
                zorder=4)


def draw_thick_arrow(ax, x1, y1, x2, y2, color, lw=3.0, dashed=False):
    """Draw a bold arrow with large arrowhead."""
    style = (0, (7, 4)) if dashed else '-'
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color=color, lw=lw,
                                linestyle=style, mutation_scale=22,
                                shrinkA=2, shrinkB=2),
                zorder=4)


def label_text(ax, x, y, text, font=None, size=14, color=INK,
               ha='center', va='center', weight=None, alpha=1.0,
               bbox_color=None, zorder=6):
    """Draw clearly readable text with optional background highlight."""
    kwargs = dict(fontproperties=font or MONO_BOLD, fontsize=size,
                  color=color, ha=ha, va=va, alpha=alpha, zorder=zorder)
    if bbox_color:
        kwargs['bbox'] = dict(boxstyle='round,pad=0.2', facecolor=bbox_color,
                              edgecolor='none', alpha=0.85)
    ax.text(x, y, text, **kwargs)


# ═════════════════════════════════════════════════════════════════════════════
# IMAGE 1 — system-architecture.png
# ═════════════════════════════════════════════════════════════════════════════

def generate_system_architecture():
    fig, ax = plt.subplots(figsize=(18, 24))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 18)
    ax.set_ylim(0, 24)
    ax.set_aspect('equal')
    ax.axis('off')
    draw_grid(ax, 18, 24)

    CX = 9.0

    # ── Title area ────────────────────────────────────────────────────────
    ax.fill_between([0, 18], 22.0, 24, color=INK, alpha=0.06, zorder=1)
    label_text(ax, CX, 23.2, "Backend Systems Lab",
               font=MONO_BOLD, size=38, color=INK)
    label_text(ax, CX, 22.4, "Distributed Request Pipeline — Architecture",
               font=HAND, size=20, color=SUBTLE)
    label_text(ax, 16.5, 23.5, "v1.0", font=HAND, size=15, color=MUTED)
    label_text(ax, 16.5, 23.0, "March 2026", font=HAND, size=15, color=MUTED)

    # ── 1. Client ─────────────────────────────────────────────────────────
    cw, ch = 5.0, 1.4
    cx, cy = CX - cw / 2, 19.8
    draw_box(ax, cx, cy, cw, ch, INK, '#F0F0F5', lw=2.5)
    label_text(ax, CX, cy + ch / 2, "Client", font=MONO_BOLD, size=22, color=INK)

    # ── 2. Rate Limiter ──────────────────────────────────────────────────
    rw, rh = 9.0, 2.4
    rx, ry = CX - rw / 2, 16.2
    draw_box(ax, rx, ry, rw, rh, RED, RED_BG, lw=3)
    label_text(ax, CX, ry + rh / 2 + 0.35, "Rate Limiter  :8080",
               font=MONO_BOLD, size=22, color=RED)
    label_text(ax, CX, ry + rh / 2 - 0.45, "Token Bucket  |  Per-IP  |  Per-Endpoint",
               font=HAND, size=16, color=RED, alpha=0.85)

    # ── 3. Load Balancer ─────────────────────────────────────────────────
    lw_, lh = 9.4, 2.4
    lx, ly = CX - lw_ / 2, 12.4
    draw_box(ax, lx, ly, lw_, lh, BLUE, BLUE_BG, lw=3)
    label_text(ax, CX, ly + lh / 2 + 0.35, "Load Balancer  :8090",
               font=MONO_BOLD, size=22, color=BLUE)
    label_text(ax, CX, ly + lh / 2 - 0.45, "Round-Robin  |  Health Checks  |  Session Persistence",
               font=HAND, size=16, color=BLUE, alpha=0.85)

    # ── 4. Three servers ─────────────────────────────────────────────────
    sw, sh = 4.2, 1.5
    server_xs = [3.2, 9.0, 14.8]
    server_ports = [":8001", ":8002", ":8003"]
    sy = 8.8
    for i, (sx, port) in enumerate(zip(server_xs, server_ports)):
        sx0 = sx - sw / 2
        draw_box(ax, sx0, sy, sw, sh, GREEN, GREEN_BG, lw=2.5)
        label_text(ax, sx, sy + sh / 2 + 0.15, f"Server {i + 1}",
                   font=MONO_BOLD, size=20, color=GREEN)
        label_text(ax, sx, sy + sh / 2 - 0.35, port,
                   font=MONO_REG, size=16, color=GREEN, alpha=0.8)

    # ── 5. Redis Clone ───────────────────────────────────────────────────
    rdw, rdh = 10.0, 2.6
    rdx, rdy = CX - rdw / 2, 4.8
    # Double border effect
    draw_box(ax, rdx - 0.15, rdy - 0.15, rdw + 0.3, rdh + 0.3,
             AMBER, '#00000000', lw=1.5, shadow=False)
    draw_box(ax, rdx, rdy, rdw, rdh, AMBER, AMBER_BG, lw=3)
    label_text(ax, CX, rdy + rdh / 2 + 0.4, "Redis Clone  :6380",
               font=MONO_BOLD, size=22, color=AMBER)
    label_text(ax, CX, rdy + rdh / 2 - 0.45,
               "Rate Limit Counters  |  Session Store  |  RESP Protocol",
               font=HAND, size=16, color=AMBER, alpha=0.85)

    # ── Main flow arrows ─────────────────────────────────────────────────
    # Client → Rate Limiter
    draw_thick_arrow(ax, CX, cy, CX, ry + rh, INK, lw=3)
    label_text(ax, CX + 2.2, (cy + ry + rh) / 2, "HTTP Request",
               font=HAND, size=16, color=INK, bbox_color=BG)

    # Rate Limiter → Load Balancer
    draw_thick_arrow(ax, CX, ry, CX, ly + lh, INK2, lw=3)
    label_text(ax, CX + 2.0, (ry + ly + lh) / 2, "Allowed",
               font=HAND, size=16, color=INK2, bbox_color=BG)

    # Load Balancer → Servers (fan out)
    for sx in server_xs:
        draw_thick_arrow(ax, CX, ly, sx, sy + sh, GREEN, lw=2.5)

    # Servers → Redis (converge)
    for sx in server_xs:
        draw_thick_arrow(ax, sx, sy, CX, rdy + rdh, AMBER, lw=2)

    # Redis ↔ Rate Limiter feedback (dashed, prominent)
    fb_x = 2.4
    # Vertical from Redis up to Rate Limiter level
    ax.annotate('', xy=(fb_x, ry + rh / 2), xytext=(fb_x, rdy + rdh),
                arrowprops=dict(arrowstyle='-', color=RED, lw=2.5,
                                linestyle=(0, (6, 4))),
                zorder=4)
    # Horizontal into Rate Limiter
    ax.annotate('', xy=(rx, ry + rh / 2), xytext=(fb_x, ry + rh / 2),
                arrowprops=dict(arrowstyle='->', color=RED, lw=2.5,
                                linestyle=(0, (6, 4)), mutation_scale=18),
                zorder=4)
    # Horizontal from Redis to vertical line
    ax.annotate('', xy=(fb_x, rdy + rdh), xytext=(rdx, rdy + rdh / 2 + 0.5),
                arrowprops=dict(arrowstyle='-', color=RED, lw=2.5,
                                linestyle=(0, (6, 4))),
                zorder=4)
    label_text(ax, fb_x - 0.1, (rdy + rdh + ry + rh / 2) / 2,
               "INCR / EXPIRE\ncounters",
               font=HAND, size=15, color=RED, ha='right', bbox_color=BG)

    # Redis ↔ Load Balancer feedback (dashed)
    fb_x2 = 15.6
    ax.annotate('', xy=(fb_x2, ly + lh / 2), xytext=(fb_x2, rdy + rdh),
                arrowprops=dict(arrowstyle='-', color=BLUE, lw=2.5,
                                linestyle=(0, (6, 4))),
                zorder=4)
    ax.annotate('', xy=(lx + lw_, ly + lh / 2), xytext=(fb_x2, ly + lh / 2),
                arrowprops=dict(arrowstyle='->', color=BLUE, lw=2.5,
                                linestyle=(0, (6, 4)), mutation_scale=18),
                zorder=4)
    ax.annotate('', xy=(fb_x2, rdy + rdh), xytext=(rdx + rdw, rdy + rdh / 2 + 0.5),
                arrowprops=dict(arrowstyle='-', color=BLUE, lw=2.5,
                                linestyle=(0, (6, 4))),
                zorder=4)
    label_text(ax, fb_x2 + 0.1, (rdy + rdh + ly + lh / 2) / 2,
               "Session\nLookup",
               font=HAND, size=15, color=BLUE, ha='left', bbox_color=BG)

    # ── Annotations (high contrast) ──────────────────────────────────────
    # Rate limit annotation
    label_text(ax, CX + 4.6, (ry + ly + lh) / 2 + 0.6,
               "INCR + TTL atomic!",
               font=HAND, size=15, color=RED, bbox_color=RED_BG)

    # Health check annotation
    label_text(ax, CX + 4.2, sy + sh + 0.35,
               "Health check every 5s",
               font=HAND, size=15, color=GREEN, bbox_color=GREEN_BG)

    # 3x replicas annotation
    label_text(ax, 1.0, sy + sh / 2,
               "3x replicas",
               font=HAND, size=15, color=GREEN, ha='left', bbox_color=GREEN_BG)

    # ── Section labels (right margin) ────────────────────────────────────
    margin_labels = [
        (cy + ch / 2, "[1] Ingress", INK),
        (ry + rh / 2, "[2] Guard", RED),
        (ly + lh / 2, "[3] Routing", BLUE),
        (sy + sh / 2, "[4] Compute", GREEN),
        (rdy + rdh / 2, "[5] State", AMBER),
    ]
    for yy, lbl, col in margin_labels:
        label_text(ax, 17.5, yy, lbl, font=HAND, size=16, color=col, ha='right')

    # ── Legend ────────────────────────────────────────────────────────────
    leg_x, leg_y = 1.0, 3.5
    label_text(ax, leg_x, leg_y + 0.5, "Legend", font=MONO_BOLD, size=16,
               color=INK, ha='left')
    ax.plot([leg_x, leg_x + 2.0], [leg_y + 0.25, leg_y + 0.25],
            color=INK, lw=1.5, zorder=5)

    legend_items = [
        (RED, RED_BG, "Rate Limiter"),
        (BLUE, BLUE_BG, "Load Balancer"),
        (GREEN, GREEN_BG, "Backend Servers"),
        (AMBER, AMBER_BG, "Redis Clone"),
    ]
    for i, (col, bg, lbl) in enumerate(legend_items):
        ly_ = leg_y - 0.55 * i - 0.2
        draw_box(ax, leg_x, ly_ - 0.18, 0.36, 0.36, col, bg, lw=2, shadow=False)
        label_text(ax, leg_x + 0.65, ly_, lbl,
                   font=HAND, size=15, color=col, ha='left')

    # Dashed legend entry
    dy_ = leg_y - 0.55 * 4 - 0.2
    ax.plot([leg_x, leg_x + 0.36], [dy_, dy_],
            color=INK2, lw=2.5, linestyle=(0, (6, 4)), zorder=5)
    label_text(ax, leg_x + 0.65, dy_, "Redis feedback (dashed)",
               font=HAND, size=15, color=INK2, ha='left')

    # ── Page number ───────────────────────────────────────────────────────
    label_text(ax, 17, 0.5, "— 1 —", font=HAND, size=14, color=MUTED, ha='right')

    fig.savefig(os.path.join(OUT_DIR, "system-architecture.png"),
                dpi=250, bbox_inches='tight', facecolor=BG)
    plt.close(fig)
    print("✓ system-architecture.png")


# ═════════════════════════════════════════════════════════════════════════════
# IMAGE 2 — request-flow-sequence.png
# ═════════════════════════════════════════════════════════════════════════════

def generate_request_flow_sequence():
    fig, ax = plt.subplots(figsize=(24, 17))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 24)
    ax.set_ylim(0, 17)
    ax.set_aspect('equal')
    ax.axis('off')
    draw_grid(ax, 24, 17)

    # ── Actors ────────────────────────────────────────────────────────────
    actors = [
        ("Client", 3.0, INK, BG_SOFT),
        ("Rate Limiter", 7.5, RED, RED_BG),
        ("Load Balancer", 12.0, BLUE, BLUE_BG),
        ("Server N", 16.5, GREEN, GREEN_BG),
        ("Redis Clone", 21.0, AMBER, AMBER_BG),
    ]
    actor_x = {name: x for name, x, _, _ in actors}
    bw, bh = 2.6, 1.2

    # ── Title area ────────────────────────────────────────────────────────
    label_text(ax, 12, 16.3, "Request Flow — Sequence Diagram",
               font=MONO_BOLD, size=30, color=INK)
    label_text(ax, 12, 15.5,
               "Normal path: request allowed, session pinned, response returned",
               font=HAND, size=18, color=SUBTLE)

    # Header boxes
    header_y = 13.7
    for name, x, col, bg in actors:
        draw_box(ax, x - bw / 2, header_y, bw, bh, col, bg, lw=2.5)
        label_text(ax, x, header_y + bh / 2, name,
                   font=MONO_BOLD, size=16, color=col)

    # Lifelines
    for name, x, col, _ in actors:
        ys = np.linspace(header_y, 0.8, 2)
        ax.plot([x, x], ys, color=col, lw=1.5, alpha=0.35,
                linestyle=(0, (8, 5)), zorder=1)

    # Footer boxes
    footer_y = 0.2
    footer_h = 0.9
    for name, x, col, bg in actors:
        draw_box(ax, x - bw / 2, footer_y, bw, footer_h, col, bg, lw=1.5, shadow=False)
        label_text(ax, x, footer_y + footer_h / 2, name,
                   font=MONO_REG, size=13, color=col, alpha=0.8)

    # ── Messages ──────────────────────────────────────────────────────────
    messages = [
        ("Client", "Rate Limiter", "GET /api/data", INK, False),
        ("Rate Limiter", "Redis Clone", "GET rl:{ip}:{endpoint}", RED, False),
        ("Redis Clone", "Rate Limiter", "counter = 45  (limit 100)", AMBER, True),
        ("Rate Limiter", "Redis Clone", "INCR  +  EXPIRE NX 60", RED, False),
        ("Rate Limiter", "Load Balancer", "Forward request", INK2, False),
        ("Load Balancer", "Redis Clone", "GET session:{id}", BLUE, False),
        ("Redis Clone", "Load Balancer", "server-2:8002", AMBER, True),
        ("Load Balancer", "Server N", "Proxy request", INK2, False),
        ("Server N", "Load Balancer", "200 OK + JSON data", GREEN, False),
        ("Load Balancer", "Rate Limiter", "200 OK + X-Served-By", BLUE, False),
        ("Rate Limiter", "Client", "200  X-RateLimit-Remaining: 55", INK, False),
    ]

    y_start = 12.8
    y_end = 2.0
    y_positions = np.linspace(y_start, y_end, len(messages))

    for idx, ((frm, to, label, col, dashed), y) in enumerate(zip(messages, y_positions)):
        x1 = actor_x[frm]
        x2 = actor_x[to]

        # Arrow
        draw_thick_arrow(ax, x1, y, x2, y, col, lw=2.5, dashed=dashed)

        # Label above arrow with white background for readability
        mx = (x1 + x2) / 2
        label_text(ax, mx, y + 0.3, label,
                   font=HAND, size=14, color=col, bbox_color='#FFFFFFCC')

        # Step number in left margin (circled)
        step_num = idx + 1
        circle = plt.Circle((1.0, y), 0.3, facecolor=BG_SOFT,
                             edgecolor=INK, lw=1.5, zorder=5)
        ax.add_patch(circle)
        label_text(ax, 1.0, y, str(step_num), font=MONO_BOLD, size=14, color=INK)

    # Important annotations with high visibility
    y4 = y_positions[3]
    label_text(ax, (actor_x["Rate Limiter"] + actor_x["Redis Clone"]) / 2,
               y4 - 0.35, "* Atomic -- no race condition",
               font=HAND, size=14, color=RED, bbox_color=RED_BG)

    # ── Right margin annotations ──────────────────────────────────────────
    annotations = [
        (y_positions[1], "Reads counter\nbefore allowing", RED, RED_BG),
        (y_positions[5], "Sticky session\nrouting", BLUE, BLUE_BG),
    ]
    for y, txt, col, bg in annotations:
        label_text(ax, 23.2, y, txt, font=HAND, size=14, color=col,
                   ha='left', bbox_color=bg)

    # ── Page number ───────────────────────────────────────────────────────
    label_text(ax, 23, 0.3, "— 2 —", font=HAND, size=14, color=MUTED, ha='right')

    fig.savefig(os.path.join(OUT_DIR, "request-flow-sequence.png"),
                dpi=250, bbox_inches='tight', facecolor=BG)
    plt.close(fig)
    print("✓ request-flow-sequence.png")


# ═════════════════════════════════════════════════════════════════════════════
# IMAGE 3 — component-flows.png
# ═════════════════════════════════════════════════════════════════════════════

def generate_component_flows():
    fig, axes = plt.subplots(1, 3, figsize=(28, 18))
    fig.patch.set_facecolor(BG)

    # Overall title
    fig.text(0.5, 0.975, "Component Internal Flows",
             fontproperties=MONO_BOLD, fontsize=32, color=INK,
             ha='center', va='center')
    fig.text(0.5, 0.95, "Each system — step by step",
             fontproperties=HAND, fontsize=18, color=SUBTLE,
             ha='center', va='center')

    panels = [
        {
            'title': 'Redis Clone',
            'subtitle': 'TCP to In-Memory Store Pipeline',
            'color': RED,
            'bg': RED_BG,
            'steps': [
                ("TCP Client", "RESP wire format connection"),
                ("RESP Parser", "Decode arrays, bulk strings, ints"),
                ("Command Router", "GET / SET / INCR / DEL / EXPIRE"),
                ("In-Memory Store", "Hash map with per-key TTL"),
                ("Expiry Engine", "Lazy eviction on every read"),
            ],
            'notes': {
                0: 'asyncio TCP\nserver',
                2: '16 commands\nsupported',
                3: 'O(1) lookup',
                4: 'No background\nthread',
            },
        },
        {
            'title': 'Rate Limiter',
            'subtitle': 'Guard Gate for Incoming Traffic',
            'color': BLUE,
            'bg': BLUE_BG,
            'steps': [
                ("Incoming Request", "Any HTTP method, any path"),
                ("Key Builder", "rl:{client_ip}:{endpoint}"),
                ("Redis Pipeline", "INCR + EXPIRE NX (atomic)"),
                ("Threshold Check", "Compare count vs configured limit"),
                ("Forward / 429", "Pass to LB or reject with headers"),
            ],
            'notes': {
                0: 'X-Forwarded-For\nfor IP',
                2: 'Race-condition\nfree',
                4: 'X-RateLimit-\nRemaining',
            },
        },
        {
            'title': 'Load Balancer',
            'subtitle': 'Smart Routing + Session Pinning',
            'color': GREEN,
            'bg': GREEN_BG,
            'steps': [
                ("Incoming Request", "Received from rate limiter"),
                ("Session Lookup", "GET session:{id} from Redis"),
                ("Health Filter", "Remove UNHEALTHY servers"),
                ("Pick Algorithm", "Round-robin / Least-connections"),
                ("Proxy to Server", "Forward request + pin session"),
            ],
            'notes': {
                1: 'Sticky cookie\nsession_id',
                2: 'Check /health\nevery 5s',
                4: 'X-Served-By\nheader',
            },
        },
    ]

    for panel_idx, (ax, panel) in enumerate(zip(axes, panels)):
        ax.set_facecolor(BG)
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 18)
        ax.set_aspect('equal')
        ax.axis('off')
        draw_grid(ax, 10, 18)

        col = panel['color']
        bg = panel['bg']

        # Panel title with colored background
        draw_box(ax, 0.3, 16.0, 9.4, 1.6, col, bg, lw=2.5, shadow=False)
        label_text(ax, 5, 17.05, panel['title'],
                   font=MONO_BOLD, size=22, color=col)
        label_text(ax, 5, 16.4, panel['subtitle'],
                   font=HAND, size=15, color=col, alpha=0.85)

        # Step boxes — evenly spaced with connecting arrows
        step_count = len(panel['steps'])
        box_h = 1.7
        gap = 0.6
        total_h = step_count * box_h + (step_count - 1) * gap
        top_y = 15.2
        bx = 0.8
        bw = 7.0

        for step_idx, (title, subtitle) in enumerate(panel['steps']):
            by = top_y - step_idx * (box_h + gap) - box_h

            # Step box
            draw_box(ax, bx, by, bw, box_h, col, bg, lw=2.5)

            # Step number badge
            badge_x = bx + 0.55
            badge_y = by + box_h / 2
            circle = plt.Circle((badge_x, badge_y), 0.38,
                                facecolor=col, edgecolor=col, lw=2, zorder=5)
            ax.add_patch(circle)
            label_text(ax, badge_x, badge_y, str(step_idx + 1),
                       font=MONO_BOLD, size=16, color='white')

            # Step title and subtitle
            label_text(ax, bx + 1.3, by + box_h / 2 + 0.3, title,
                       font=MONO_BOLD, size=17, color=col, ha='left')
            label_text(ax, bx + 1.3, by + box_h / 2 - 0.3, subtitle,
                       font=HAND, size=14, color=SUBTLE, ha='left')

            # Connecting arrow to next box
            if step_idx < step_count - 1:
                arr_x = bx + bw / 2
                draw_thick_arrow(ax, arr_x, by, arr_x, by - gap, col, lw=2.5)

            # Side notes (right margin)
            if step_idx in panel['notes']:
                note_text = panel['notes'][step_idx]
                note_x = bx + bw + 0.3
                label_text(ax, note_x, by + box_h / 2, note_text,
                           font=HAND, size=13, color=col, ha='left',
                           alpha=0.8, bbox_color=bg)

        # Page number
        page_num = panel_idx + 3
        label_text(ax, 9.5, 0.3, f"— {page_num} —",
                   font=HAND, size=14, color=MUTED, ha='right')

    plt.subplots_adjust(wspace=0.06, top=0.93, bottom=0.01)
    fig.savefig(os.path.join(OUT_DIR, "component-flows.png"),
                dpi=250, bbox_inches='tight', facecolor=BG)
    plt.close(fig)
    print("✓ component-flows.png")


# ═════════════════════════════════════════════════════════════════════════════
# Main
# ═════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("Generating diagrams...")
    generate_system_architecture()
    generate_request_flow_sequence()
    generate_component_flows()
    print("Done — all images saved to docs/diagrams/")
