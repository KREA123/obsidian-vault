#!/usr/bin/env python3
"""hopa_motion.py -- the HOPA timeline (pure numpy, shared by soul_v5.py 'hopa' and hopa_eyes.py). CGI concept.

A nudge from off-screen right at T_NUDGE tips SOUL ~20 deg to the left; it rocks back on the rocker sole with a
decaying oscillation (1.7 Hz, each swing 0.68 of the previous => zeta ~ 0.12), stops on the flat land, then a brief
dizzy flutter, a blink and a half-lidded side-glance toward where the nudge came from.

The eyes are counter-rotated INSIDE the rocking body so they stay level with the horizon, with a 70 ms lag
(the counter-rotation is baked into the per-frame eye texture, see hopa_eyes.py).

    python3 hopa_motion.py          # prints the timeline (angles per frame, swing ratios)
"""
import math

import numpy as np

FPS = 24
DUR = 7.0
NF = int(round(FPS * DUR))            # frames 1..NF
T_NUDGE = 0.55
F_ROLL = 1.7                          # Hz (damped)
F_PITCH = 1.5
RATIO = 0.68                          # each swing / the previous one (half-period ratio)
SIGMA = 2.0 * F_ROLL * -math.log(RATIO)       # 1/s envelope decay
PHI0 = -20.0                          # first swing: top to the left (-x), deg
THETA0 = 3.5                          # a little pitch back (nudge from front-right)
LAG = 0.070                           # s, eye counter-rotation lag
STOP = (3.05, 3.55)                   # the flat land kills the last small wobble
LEAN = math.radians(8.0)
NRM = np.array([0.0, -math.cos(LEAN), math.sin(LEAN)])
UPV = np.array([0.0, math.sin(LEAN), math.cos(LEAN)])


def smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def _swing(tau, amp, f, sigma):
    """Impulse response of a damped rocker, normalised so the first peak equals amp."""
    wd = 2 * math.pi * f
    tp = math.atan(wd / sigma) / wd
    norm = math.exp(-sigma * tp) * math.sin(wd * tp)
    tau = np.maximum(tau, 0.0)
    # the finger's push lasts ~70 ms (soft start instead of a velocity step)
    soft = smooth(0.0, 0.07, tau) * 0.35 + 0.65 * (tau > 0)
    return amp * np.exp(-sigma * tau) * np.sin(wd * tau) / norm * soft


def angles(t):
    """(roll, pitch) in degrees at time t (s). roll > 0 = top toward +x, pitch > 0 = top toward +y (back)."""
    t = np.asarray(t, float)
    tau = t - T_NUDGE
    stop = 1.0 - smooth(STOP[0], STOP[1], t)
    phi = _swing(tau, PHI0, F_ROLL, SIGMA) * stop
    th = _swing(tau, THETA0, F_PITCH, SIGMA) * stop
    return phi, th


def rot(roll, pitch):
    """3x3 body rotation, identical to soul_v5.pose_soul: Ry(roll) @ Rx(-pitch)."""
    a, b = math.radians(roll), math.radians(-pitch)
    Ry = np.array([[math.cos(a), 0, math.sin(a)], [0, 1, 0], [-math.sin(a), 0, math.cos(a)]])
    Rx = np.array([[1, 0, 0], [0, math.cos(b), -math.sin(b)], [0, math.sin(b), math.cos(b)]])
    return Ry @ Rx


def level_psi(roll, pitch):
    """Angle (rad) to rotate the glass about its own normal so the eyes are level (same maths as level_eyes)."""
    Rm = rot(roll, pitch)
    X = Rm @ np.cross(UPV, NRM)
    Y = Rm @ UPV
    N = Rm @ NRM
    up = np.array([0, 0, 1.0])
    U = up - up.dot(N) * N
    U /= np.linalg.norm(U)
    return math.atan2(np.cross(Y, U).dot(N), Y.dot(U))


def roll_offset(ang, edge, rad, zc):
    """Horizontal travel (mm) of the rocker's centre for a tilt 'ang' (deg): pivot on the edge of the flat land
    (half-width 'edge') until the ellipsoid takes over, then roll without slip on radius 'rad' (brief §2.3)."""
    s = 1.0 if ang >= 0 else -1.0
    a = math.radians(abs(ang))
    a0 = math.asin(edge / rad)
    if a <= a0:
        return s * (edge * (1 - math.cos(a)) + zc * math.sin(a))
    return s * (edge * (1 - math.cos(a0)) + zc * math.sin(a0) + rad * (a - a0))


def _lerp(a, b, k):
    return {key: a[key] + (b[key] - a[key]) * k for key in a}


FRONT = dict(gx=0.0, gy=-0.05, lid_top=0.19, lid_tilt=0.16, open_=1.0, scale=1.0, split=0.0)
WIDE = dict(gx=0.0, gy=-0.35, lid_top=0.06, lid_tilt=0.12, open_=1.0, scale=1.08, split=0.0)
DIZZY = dict(gx=0.0, gy=0.0, lid_top=0.40, lid_tilt=0.10, open_=1.0, scale=1.0, split=0.035)
SMUG = dict(gx=0.95, gy=0.10, lid_top=0.34, lid_tilt=0.19, open_=1.0, scale=1.0, split=0.0)


def blink(t, t0, dur=0.16):
    """open_ multiplier: fast close, slower open."""
    x = (t - t0) / dur
    if x <= 0 or x >= 1:
        return 1.0
    if x < 0.4:
        return 1.0 - 0.93 * smooth(0, 1, x / 0.4)
    return 0.07 + 0.93 * smooth(0, 1, (x - 0.4) / 0.6)


def eyes(t):
    """eyes.render() keyword arguments at time t (cream, day)."""
    if t < T_NUDGE + 0.03:
        e = dict(FRONT)
    elif t < 1.45:                                        # startled: wide
        e = _lerp(FRONT, WIDE, float(smooth(T_NUDGE + 0.03, T_NUDGE + 0.12, t)))
    elif t < 2.75:                                        # the rocking wears it out: lids droop toward dizzy
        e = _lerp(WIDE, dict(DIZZY, split=0.0), float(smooth(1.45, 2.6, t)))
    elif t < 3.45:                                        # brief dizzy flutter: the eyes see-saw
        e = dict(DIZZY)
        k = float(smooth(2.75, 2.9, t) * (1 - smooth(3.3, 3.45, t)))
        e['split'] = 0.035 * k * math.sin(2 * math.pi * 6.0 * (t - 2.75))
        e['gx'] = 0.10 * k * math.sin(2 * math.pi * 3.0 * (t - 2.75) + 1.0)
    elif t < 3.72:                                        # shake it off (blink at 3.47)
        e = _lerp(dict(DIZZY, split=0.0), FRONT, float(smooth(3.45, 3.60, t)))
    else:                                                 # half-lidded side-glance toward the nudger (+x)
        e = _lerp(FRONT, SMUG, float(smooth(3.72, 4.05, t)))
        # a small settle-overshoot of the glance and one slow, lazy blink
        e['gx'] += 0.06 * math.sin(math.pi * float(smooth(3.95, 4.25, t)))
    e['open_'] *= blink(t, 0.18) * blink(t, 3.47) * blink(t, 5.55, 0.26)
    return e


def frame_time(f):
    return (f - 1) / FPS


def table():
    rows = []
    for f in range(1, NF + 1):
        t = frame_time(f)
        phi, th = angles(t)
        rows.append((f, t, float(phi), float(th)))
    return rows


def psi_lagged(t):
    """Glass counter-rotation (rad) actually applied at t: the level angle of the pose LAG seconds ago."""
    phi, th = angles(max(t - LAG, 0.0))
    return level_psi(float(phi), float(th))


if __name__ == '__main__':
    tt = np.linspace(0, DUR, 7001)
    ph, th = angles(tt)
    ext = [(tt[i], ph[i]) for i in range(1, len(tt) - 1) if abs(ph[i]) > 0.3 and
           (ph[i] - ph[i - 1]) * (ph[i + 1] - ph[i]) < 0]
    print('sigma %.3f 1/s, zeta %.3f' % (SIGMA, SIGMA / math.hypot(SIGMA, 2 * math.pi * F_ROLL)))
    for i, (t, p) in enumerate(ext):
        r = '' if i == 0 else '  ratio %.2f' % abs(p / ext[i - 1][1])
        print('extreme t=%.3f s  roll %+6.2f deg  travel %+5.1f mm%s' % (t, p, roll_offset(p, 6.9, 40.0, 39.4), r))
    for f in (1, 14, 20, 40, 70, 80, 100, 168):
        t = frame_time(f)
        p, q = angles(t)
        print(f, round(t, 3), round(float(p), 2), round(float(q), 2), 'psi_lag %.2f' % math.degrees(psi_lagged(t)),
              eyes(t))
