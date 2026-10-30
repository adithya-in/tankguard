#!/usr/bin/env python3
"""Swept-area animation for the TankGuard cleaning arm (design-stage model).

Geometry - from the CAD and the constraints given on 30 Oct 2026:

    tank radius          50 cm
    main arm             20 cm   (pipe -> outer motor)
    secondary arm        20 cm   (outer motor -> outer brush, fully extended)
    inner brush centre   10 cm   (direct drive near the pipe)
    brush radius          5 cm   (dia 10; --brush to change)

Modes
    spiral       three turns while the secondary arm extends 20 -> 40 cm (default)
    concentric   fixed passes at r = 20, 30, 40 (one turn each)

Usage
    python tools/swept_area.py                         # on screen
    python tools/swept_area.py --mode concentric
    python tools/swept_area.py --brush 4               # reveals the inner/outer gap
    python tools/swept_area.py --turns 2               # shows the scalloped gaps
    python tools/swept_area.py --pump 25               # draw the dia-5 pump cup at r=25
    python tools/swept_area.py --save sweep.gif --still sweep-final.png

The coverage mask is the union of the brush discs actually swept, so the printed
percentage is measured, not estimated.
"""

from __future__ import annotations

import argparse
import math
import os
import sys

import numpy as np

TANK_R = 50.0
MAIN_ARM = 20.0
SECOND_ARM = 20.0
INNER_BRUSH_R = 10.0

INK = "#14171B"
INK_3 = "#8A9099"
BAD = "#D93A2B"
PAPER = "#F2F1ED"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--mode", choices=["spiral", "concentric"], default="spiral")
    p.add_argument("--brush", type=float, default=5.0, help="brush radius in cm (default 5 -> dia 10)")
    p.add_argument("--turns", type=float, default=3.0, help="spiral turns (default 3; 2 leaves gaps at pitch = band width)")
    p.add_argument("--pump", type=float, default=None, help="radius of the dia-5 pump cup, if placed")
    p.add_argument("--fps", type=int, default=20)
    p.add_argument("--save", metavar="FILE.gif", help="write the animation (gif)")
    p.add_argument("--still", metavar="FILE.png", help="write the final frame")
    p.add_argument("--no-show", action="store_true")
    return p.parse_args()


def concentric_radii(brush: float) -> list[float]:
    """Pass radii spaced 1.6 x brush radius so adjacent tracks overlap."""
    radii: list[float] = []
    r = MAIN_ARM
    while r < MAIN_ARM + SECOND_ARM - 0.5:
        radii.append(r)
        r += 1.6 * brush
    radii.append(MAIN_ARM + SECOND_ARM)
    return radii


def build_schedule(mode: str, turns: float, brush: float) -> list[tuple[float, float]]:
    """Return [(theta, outer_brush_radius), ...] - one entry per animation frame.

    Both patterns must overlap their tracks: passes spaced at exactly the band
    width (2 x brush radius) touch tangentially and leave scalloped rings of
    unscrubbed floor. The spiral is bracketed by a full turn at each extreme
    radius for the same reason (a monotonic spiral visits each extreme at one
    angle only).
    """
    per_turn = 48
    step = 2 * math.pi / per_turn
    r_min = MAIN_ARM
    r_max = MAIN_ARM + SECOND_ARM

    if mode == "spiral":
        frames: list[tuple[float, float]] = []
        theta = 0.0
        for _ in range(per_turn):  # dwell at the inner radius
            frames.append((theta, r_min))
            theta += step
        total = int(per_turn * turns)
        for i in range(total + 1):  # spiral out
            t = i / total
            frames.append((theta, r_min + (r_max - r_min) * t))
            theta += step
        for _ in range(per_turn):  # dwell at the outer radius
            frames.append((theta, r_max))
            theta += step
        return frames

    # concentric: full turns at overlapping radii
    frames = []
    for radius in concentric_radii(brush):
        for i in range(per_turn + 1):
            frames.append((2 * math.pi * i / per_turn, radius))
    return frames


def main() -> None:
    args = parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    saving = bool(args.save or args.still)
    if saving:
        os.environ.setdefault("MPLBACKEND", "Agg")

    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation, PillowWriter
    from matplotlib.patches import Annulus, Circle

    b = args.brush
    reach = MAIN_ARM + SECOND_ARM  # 40 cm
    edge = reach + b  # outermost point any brush can touch

    # ---- coverage grid -----------------------------------------------------
    res = 0.25  # cm per cell
    lim = TANK_R + 5
    xs = np.arange(-lim, lim + res, res)
    X, Y = np.meshgrid(xs, xs)
    in_tank = (X**2 + Y**2) <= TANK_R**2
    covered = np.zeros_like(in_tank)
    floor_cells = int(in_tank.sum())

    def stamp(cx: float, cy: float) -> None:
        nonlocal covered
        covered |= ((X - cx) ** 2 + (Y - cy) ** 2) <= b**2

    # ---- figure ------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(7.2, 7.2), dpi=110)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.set_aspect("equal")
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.set_xticks([-50, -40, -20, 0, 20, 40, 50])
    ax.set_yticks([-50, -40, -20, 0, 20, 40, 50])
    ax.tick_params(colors=INK_3, labelsize=7)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.grid(color="#E4E2DC", linewidth=0.5, zorder=0)

    ax.add_patch(Circle((0, 0), TANK_R, facecolor=PAPER, edgecolor="none", zorder=1))
    ax.add_patch(Circle((0, 0), TANK_R, facecolor="none", edgecolor=INK, linewidth=1.2, zorder=6))

    # unreached band: everything beyond the furthest brush edge
    if edge < TANK_R:
        ax.add_patch(Annulus((0, 0), TANK_R, TANK_R - edge, facecolor=BAD, alpha=0.07, edgecolor="none", zorder=2))
        ax.add_patch(
            Circle((0, 0), edge, facecolor="none", edgecolor=BAD, linewidth=0.8,
                   linestyle=(0, (4, 4)), alpha=0.65, zorder=3)
        )
        ax.annotate(
            f"unreached: {TANK_R - edge:.1f} cm",
            (0, (edge + TANK_R) / 2),
            xytext=(12, 12),
            textcoords="offset points",
            fontsize=7.5,
            color=BAD,
        )

    # reference circles: outer motor radius and full extension
    for r in (MAIN_ARM, reach):
        ax.add_patch(
            Circle((0, 0), r, facecolor="none", edgecolor=INK_3,
                   linewidth=0.5, linestyle=(0, (2, 5)), alpha=0.5, zorder=3)
        )

    # covered mask as an RGBA layer
    img = np.zeros((*covered.shape, 4), dtype=float)
    img[..., 0], img[..., 1], img[..., 2] = 0.149, 0.278, 0.941  # #2647F0
    img[..., 3] = 0.0
    im = ax.imshow(img, extent=(-lim, lim, -lim, lim), origin="lower", interpolation="nearest", zorder=4)

    if args.pump is not None:
        ax.add_patch(Circle((args.pump, 0), 2.5, facecolor="white", edgecolor=INK, linewidth=1.0, zorder=7))
        ax.annotate(
            "pump cup (dia 5)",
            (args.pump, 0),
            xytext=(args.pump + 4, -9),
            fontsize=7,
            color=INK,
            zorder=8,
            arrowprops=dict(arrowstyle="-", color=INK_3, linewidth=0.6),
        )

    # arm
    (main_line,) = ax.plot([], [], color=INK, linewidth=3.2, solid_capstyle="round", zorder=8)
    (second_line,) = ax.plot([], [], color=INK, linewidth=2.2, solid_capstyle="round", zorder=8)
    ax.add_patch(Circle((0, 0), 2.6, facecolor=INK, edgecolor="none", zorder=9))  # pipe
    outer_motor = Circle((0, 0), 3.0, facecolor="white", edgecolor=INK, linewidth=1.2, zorder=9)
    ax.add_patch(outer_motor)
    inner_brush = Circle((INNER_BRUSH_R, 0), b, facecolor="none", edgecolor=INK_3,
                         linewidth=1.0, linestyle=(0, (3, 3)), zorder=9)
    outer_brush = Circle((MAIN_ARM, 0), b, facecolor="none", edgecolor=INK_3,
                         linewidth=1.0, linestyle=(0, (3, 3)), zorder=9)
    ax.add_patch(inner_brush)
    ax.add_patch(outer_brush)

    title = ax.set_title("", fontsize=10, color=INK, loc="left", pad=10)
    readout = ax.text(-lim + 1, lim - 1, "", fontsize=9, color=INK, family="monospace", va="top")
    note = ax.text(lim - 1, lim - 1, "", fontsize=8, color=INK_3, ha="right", va="top")

    frames = build_schedule(args.mode, args.turns, args.brush)
    total = len(frames)
    mode_label = (
        f"spiral, {args.turns:g} turns, r 20 -> 40 cm"
        if args.mode == "spiral"
        else "concentric, r " + " / ".join(f"{r:g}" for r in concentric_radii(b)) + " cm"
    )

    def update(i: int):
        theta, r_outer = frames[i]
        cx, cy = math.cos(theta), math.sin(theta)

        stamp(INNER_BRUSH_R * cx, INNER_BRUSH_R * cy)
        stamp(r_outer * cx, r_outer * cy)

        img[..., 3] = covered.astype(float) * 0.30
        im.set_data(img)

        main_line.set_data([0, MAIN_ARM * cx], [0, MAIN_ARM * cy])
        second_line.set_data([MAIN_ARM * cx, r_outer * cx], [MAIN_ARM * cy, r_outer * cy])
        outer_motor.set_center((MAIN_ARM * cx, MAIN_ARM * cy))
        inner_brush.set_center((INNER_BRUSH_R * cx, INNER_BRUSH_R * cy))
        outer_brush.set_center((r_outer * cx, r_outer * cy))

        pct = 100.0 * covered[in_tank].sum() / floor_cells
        title.set_text(f"TankGuard - swept area ({mode_label})")
        readout.set_text(
            f"coverage  {pct:5.1f} %\n"
            f"outer r   {r_outer:5.1f} cm\n"
            f"frame     {i + 1:3d}/{total}"
        )
        note.set_text(f"brush dia {2 * b:g} cm - arm 20 + 20 cm - tank r 50 cm")
        return im, main_line, second_line, outer_motor, inner_brush, outer_brush, title, readout, note

    if args.save:
        anim = FuncAnimation(fig, update, frames=total, interval=1000 / args.fps, blit=False, repeat=False)
        anim.save(args.save, writer=PillowWriter(fps=args.fps))
        print(f"wrote {args.save}")

    # run to the end so the still shows the finished sweep
    for i in range(total):
        update(i)
    if args.still:
        fig.savefig(args.still, dpi=150, bbox_inches="tight", facecolor="white")
        print(f"wrote {args.still}")

    pct = 100.0 * covered[in_tank].sum() / floor_cells
    inner_edge = INNER_BRUSH_R + b
    outer_start = MAIN_ARM - b
    gap = outer_start - inner_edge
    print(f"mode            {args.mode}")
    print(f"brush radius    {b:g} cm (dia {2 * b:g})")
    print(f"inner track     r {INNER_BRUSH_R - b:g} - {inner_edge:g} cm")
    print(f"outer track     r {outer_start:g} - {edge:g} cm")
    if gap > 0:
        print(f"GAP             {gap:.1f} cm band between brush tracks (r {inner_edge:g} - {outer_start:g})")
    if edge < TANK_R:
        ring = math.pi * (TANK_R**2 - edge**2)
        print(f"unreached ring  {TANK_R - edge:.1f} cm - {ring:.0f} cm2 - {100 * ring / (math.pi * TANK_R**2):.1f} % of floor")
    if args.mode == "spiral":
        pitch = SECOND_ARM / args.turns
        verdict = "ok" if pitch < 2 * b else "TOO WIDE - gaps between turns"
        print(f"spiral pitch    {pitch:.2f} cm per turn (band is {2 * b:g} cm) - {verdict}")
    print(f"covered         {pct:.1f} % of the tank floor")

    if not args.no_show and not saving:
        plt.show()


if __name__ == "__main__":
    main()
