#!/usr/bin/env python3
"""Swept-area animation for the TankGuard cleaning arm (design-stage model).

Geometry - from the CAD and the constraints given on 30 Oct 2026:

    tank radius          50 cm
    main arm             20 cm   (pipe -> outer motor)
    secondary arm        20 cm   (outer motor -> outer brush, fully extended)
    inner brush centre   10 cm   (direct drive near the pipe)
    brush radius          5 cm   (dia 10; --brush to change)

Motion constraint: the arm cannot rotate continuously - the water hose and the
wires would wind up. It oscillates between -L and +L and returns, so the twist
never accumulates. Coverage of the full circle therefore needs

    2 * L * arms >= 360 deg          (twist each way = L)

    arms=1  L=180   twist 180   full circle      <- the only single-arm option
    arms=2  L= 90   twist  90   full circle
    arms=3  L= 60   twist  60   full circle
    arms=1  L=170   twist 170   20 deg dead wedge (fails "every area")

Modes
    concentric  one oscillation per radius, radii spaced 1.6 x brush radius (default)
    spiral      radius extends across several oscillations (pitch must stay < 2b)

Usage
    python tools/swept_area.py                          # 1 arm, +/-180, concentric
    python tools/swept_area.py --arms 2 --limit 90
    python tools/swept_area.py --limit 170              # shows the dead wedge
    python tools/swept_area.py --mode spiral --osc 3
    python tools/swept_area.py --pump 25                # draw the dia-5 cup at r=25
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
    p.add_argument("--mode", choices=["concentric", "spiral"], default="concentric")
    p.add_argument("--arms", type=int, default=1, help="equally spaced arms on the hub (default 1)")
    p.add_argument("--limit", type=float, default=None, help="sweep half-range in degrees (default 180/arms)")
    p.add_argument("--osc", type=float, default=3.0, help="oscillations per radial sweep in spiral mode (default 3)")
    p.add_argument("--brush", type=float, default=5.0, help="brush radius in cm (default 5 -> dia 10)")
    p.add_argument("--pump", type=float, default=None, help="radius of the dia-5 pump cup, if placed")
    p.add_argument("--fps", type=int, default=24)
    p.add_argument("--save", metavar="FILE.gif", help="write the animation (gif)")
    p.add_argument("--still", metavar="FILE.png", help="write the final frame")
    p.add_argument("--no-show", action="store_true")
    return p.parse_args()


def triangle(phi: float, limit_deg: float) -> float:
    """Fold an unwrapped angle (radians) into [-limit, +limit], returned in radians."""
    lim = math.radians(limit_deg)
    period = 4.0 * lim
    x = phi % period
    return -lim + x if x <= 2.0 * lim else 3.0 * lim - x


def pass_radii(brush: float) -> list[float]:
    """Radii spaced 1.6 x brush radius so adjacent tracks overlap."""
    radii: list[float] = []
    r = MAIN_ARM
    while r < MAIN_ARM + SECOND_ARM - 0.5:
        radii.append(r)
        r += 1.6 * brush
    radii.append(MAIN_ARM + SECOND_ARM)
    return radii


def build_schedule(mode: str, osc: float, brush: float) -> list[tuple[float, float]]:
    """Return [(phi, outer_brush_radius), ...] - phi is the *unwrapped* angle.

    phi is folded through triangle() at draw time, so the schedule describes the
    cleaning path while the mechanism only ever sees +/-limit of rotation.
    """
    per_osc = 48
    step = 2 * math.pi / per_osc
    r_min = MAIN_ARM
    r_max = MAIN_ARM + SECOND_ARM

    frames: list[tuple[float, float]] = []
    if mode == "concentric":
        for radius in pass_radii(brush):
            phi = 0.0
            for _ in range(per_osc + 1):
                frames.append((phi, radius))
                phi += step
        return frames

    # spiral: dwell at the inner radius, extend across several oscillations,
    # dwell at the outer radius (each extreme radius is otherwise visited at a
    # single angle, which costs ~6 points of coverage)
    total = int(per_osc * osc)
    phi = 0.0
    for _ in range(per_osc):
        frames.append((phi, r_min))
        phi += step
    for i in range(total + 1):
        t = i / total
        frames.append((phi, r_min + (r_max - r_min) * t))
        phi += step
    for _ in range(per_osc):
        frames.append((phi, r_max))
        phi += step
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
    from matplotlib.patches import Annulus, Circle, Wedge

    b = args.brush
    arms = max(1, args.arms)
    limit = args.limit if args.limit is not None else 180.0 / arms
    reach = MAIN_ARM + SECOND_ARM
    edge = reach + b
    span = 2.0 * limit * arms  # covered angular span, degrees

    # ---- coverage grid -----------------------------------------------------
    res = 0.25
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

    # dead wedge(s) when the sweep cannot reach the whole circle
    if span < 360.0:
        gap = 360.0 - span
        start = limit
        ax.add_patch(
            Wedge((0, 0), TANK_R, start, start + gap, facecolor=BAD, alpha=0.10, edgecolor="none", zorder=2)
        )
        mid = math.radians(start + gap / 2)
        ax.annotate(
            f"dead sector {gap:.0f} deg",
            (TANK_R * 0.72 * math.cos(mid), TANK_R * 0.72 * math.sin(mid)),
            fontsize=7.5,
            color=BAD,
            ha="center",
        )

    for r in (MAIN_ARM, reach):
        ax.add_patch(
            Circle((0, 0), r, facecolor="none", edgecolor=INK_3,
                   linewidth=0.5, linestyle=(0, (2, 5)), alpha=0.5, zorder=3)
        )

    img = np.zeros((*covered.shape, 4), dtype=float)
    img[..., 0], img[..., 1], img[..., 2] = 0.149, 0.278, 0.941
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

    # arm artists - one set per arm
    main_lines, second_lines, motors, inner_brushes, outer_brushes = [], [], [], [], []
    for _ in range(arms):
        (ml,) = ax.plot([], [], color=INK, linewidth=3.2, solid_capstyle="round", zorder=8)
        (sl,) = ax.plot([], [], color=INK, linewidth=2.2, solid_capstyle="round", zorder=8)
        mo = Circle((0, 0), 3.0, facecolor="white", edgecolor=INK, linewidth=1.2, zorder=9)
        ib = Circle((INNER_BRUSH_R, 0), b, facecolor="none", edgecolor=INK_3,
                    linewidth=1.0, linestyle=(0, (3, 3)), zorder=9)
        ob = Circle((MAIN_ARM, 0), b, facecolor="none", edgecolor=INK_3,
                    linewidth=1.0, linestyle=(0, (3, 3)), zorder=9)
        for patch in (mo, ib, ob):
            ax.add_patch(patch)
        main_lines.append(ml)
        second_lines.append(sl)
        motors.append(mo)
        inner_brushes.append(ib)
        outer_brushes.append(ob)
    ax.add_patch(Circle((0, 0), 2.6, facecolor=INK, edgecolor="none", zorder=10))  # pipe

    title = ax.set_title("", fontsize=10, color=INK, loc="left", pad=10)
    readout = ax.text(-lim + 1, lim - 1, "", fontsize=9, color=INK, family="monospace", va="top")
    note = ax.text(lim - 1, lim - 1, "", fontsize=8, color=INK_3, ha="right", va="top")

    frames = build_schedule(args.mode, args.osc, b)
    total = len(frames)
    mode_label = args.mode + (" passes" if args.mode == "concentric" else f", {args.osc:g} oscillations")

    def update(i: int):
        phi, r_outer = frames[i]
        theta = triangle(phi, limit)

        for k in range(arms):
            a = theta + 2.0 * math.pi * k / arms
            cx, cy = math.cos(a), math.sin(a)
            stamp(INNER_BRUSH_R * cx, INNER_BRUSH_R * cy)
            stamp(r_outer * cx, r_outer * cy)
            main_lines[k].set_data([0, MAIN_ARM * cx], [0, MAIN_ARM * cy])
            second_lines[k].set_data([MAIN_ARM * cx, r_outer * cx], [MAIN_ARM * cy, r_outer * cy])
            motors[k].set_center((MAIN_ARM * cx, MAIN_ARM * cy))
            inner_brushes[k].set_center((INNER_BRUSH_R * cx, INNER_BRUSH_R * cy))
            outer_brushes[k].set_center((r_outer * cx, r_outer * cy))

        img[..., 3] = covered.astype(float) * 0.30
        im.set_data(img)

        pct = 100.0 * covered[in_tank].sum() / floor_cells
        title.set_text(
            f"TankGuard - swept area ({mode_label}, {arms} arm{'s' if arms > 1 else ''}, +/-{limit:g} deg)"
        )
        readout.set_text(
            f"coverage  {pct:5.1f} %\n"
            f"outer r   {r_outer:5.1f} cm\n"
            f"frame     {i + 1:3d}/{total}"
        )
        note.set_text(f"brush dia {2 * b:g} cm - hose twist +/-{limit:g} deg - tank r 50 cm")
        return (im, *main_lines, *second_lines, *motors, *inner_brushes, *outer_brushes, title, readout, note)

    if args.save:
        anim = FuncAnimation(fig, update, frames=total, interval=1000 / args.fps, blit=False, repeat=False)
        anim.save(args.save, writer=PillowWriter(fps=args.fps))
        print(f"wrote {args.save}")

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
    print(f"arms            {arms} (spaced {360 / arms:g} deg)")
    print(f"sweep           +/-{limit:g} deg  -> hose twist {limit:g} deg each way")
    print(f"angular span    {span:g} deg of 360" + ("  OK" if span >= 360 else "  DEAD SECTOR"))
    if span < 360:
        print(f"dead sector     {360 - span:g} deg at the turnaround (brush edge softens it - trust 'covered')")
    print(f"brush radius    {b:g} cm (dia {2 * b:g})")
    print(f"inner track     r {INNER_BRUSH_R - b:g} - {inner_edge:g} cm")
    print(f"outer track     r {outer_start:g} - {edge:g} cm")
    if gap > 0:
        print(f"GAP             {gap:.1f} cm band between brush tracks (r {inner_edge:g} - {outer_start:g})")
    if edge < TANK_R:
        ring = math.pi * (TANK_R**2 - edge**2)
        print(f"unreached ring  {TANK_R - edge:.1f} cm - {ring:.0f} cm2 - {100 * ring / (math.pi * TANK_R**2):.1f} % of floor")
    if args.mode == "spiral":
        pitch = SECOND_ARM / args.osc
        verdict = "ok" if pitch < 2 * b else "TOO WIDE - gaps between turns"
        print(f"spiral pitch    {pitch:.2f} cm per oscillation (band is {2 * b:g} cm) - {verdict}")
    print(f"covered         {pct:.1f} % of the tank floor")

    if not args.no_show and not saving:
        plt.show()


if __name__ == "__main__":
    main()
