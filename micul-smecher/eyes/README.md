# SOUL eyes

The eye engine for SOUL's round black glass: flat, bold, vector-only eyes with After Effects-style motion. The approved signature pair is v2 (cream whites, cobalt and tangerine heterochromia, pebble glint).

| File | What it is |
|---|---|
| `eyes.js` | The engine. One classic script, no dependencies. In the browser it defines `window.SoulEyes`, in Node it uses `module.exports`. |
| `designs.json` | Every eye design (the collection) as plain JSON specs. |
| `designs.js` | The same data as `window.SOUL_DESIGNS`, for pages opened from disk (`file://` cannot fetch JSON). |
| `one.html` | The signature pair: the 15 s loop, every expression, six colourways, and **Motion** (a phone's sensors, or a desktop simulator: turn, tip, spin, tap). |
| `index.html` | The collection gallery with a "Birth a SOUL" roll. |
| `soul_eye_v2.mp4`, `.gif` | 1080×1080 60 fps render of the 15 s loop. |
| `soul_eye_motion.mp4` | 1080×1080 demo of the motion behaviours, rendered by the firmware simulator (`firmware/tools/motion_clip.py`). |

## Quick start

```html
<canvas id="soul" style="width:320px;height:320px"></canvas>
<script src="eyes/eyes.js"></script>
<script>
  const eyes = SoulEyes.createEyes(document.getElementById('soul'), {
    white: '#FFF0C8', pupil: { L: '#2440FF', R: '#FF5A1F' }   // anything left out uses the Original design
  });
  eyes.setExpression('happy');
</script>
```

The canvas is sized from its CSS box (with devicePixelRatio and a ResizeObserver). All instances share one `requestAnimationFrame` loop and pause while off-screen (IntersectionObserver), so a page can hold dozens.

## API (stable)

`SoulEyes.createEyes(canvas, design?, opts?)` returns an instance.

**Options** (all optional):

| Option | Default | Meaning |
|---|---|---|
| `mode` | `'live'` | `'live'`: idle life (glances, micro-saccades, blinks, hops). `'loop'`: the scripted 15 s demo. |
| `fit` | `0.9` | Glass diameter as a fraction of the canvas' short side. |
| `bezel` | `true` | Draw the aluminium ring. |
| `sheen` | `true` | Draw the glass reflection. |
| `glass` | `true` | Set to `false` to draw the eyes only, with no disc. |
| `background` | `null` | Canvas fill behind the disc; `null` leaves it transparent. |
| `hetero` | `true` | `false` uses the left pupil colour for both eyes. |
| `interactive` | `true` | The eyes follow the pointer over the canvas; a tap makes it smile. |
| `randomMood` | `false` | Plays a random reaction every few seconds. |
| `moodPool` | all | The expression names `randomMood` picks from. |
| `moodEvery` | `[3.2, 6.7]` | Seconds between random moods, as `[min, max]`. |
| `seed` | from the design | Seeds the idle behaviour. |
| `speed` | `1` | Time multiplier. |
| `manual` | `false` | No auto loop or resize; call `step(dt)` and `draw()` yourself (used for video export). |
| `onChange` | `null` | `fn(name)`, called when the expression changes. |
| `onMotion` | `null` | `fn(cue, eyes)`, called for each motion cue (see *Motion* below). |

**Methods** (each returns the instance unless noted):

| Method | What it does |
|---|---|
| `setExpression(name)` | A **mood** holds until changed. A **reaction** plays once, then returns to the mood. |
| `react(name, holdSeconds?)` | A one-shot. A mood passed here is held for `holdSeconds` (default 2.4), then the previous mood returns. |
| `lookAt(x, y)` | `x` and `y` in -1..1. `lookAt(null)` returns to idle glances. |
| `blink(n)` | `n` = 1 or 2 (double blink). |
| `hop()` | A little idle bounce. |
| `setDesign(design, {instant})` | Swaps while the eyes are shut, unless `instant` is set. |
| `setMode('live' \| 'loop')` | Switches between idle life and the 15 s demo. |
| `setHetero(bool)` | Turns heterochromia on or off. |
| `setRandomMood(bool)` | Turns random mood mode on or off. |
| `setLevel(0..1 \| null)` | Drives `listening` (pupil pulse) and `charging` (fill level) from real data; `null` = synthetic. |
| `setMotion({ax, ay, az, gx?, gy?, gz?}, dt?)` | One IMU sample (see *Motion*). `null` turns motion off. |
| `setOrientation({beta, gamma}, dt?)` | DeviceOrientation angles (degrees) when there is no accelerometer: gravity only. |
| `hide()` | Snaps the eyes to nothing; follow with `react('hello')` to pop them in. |
| `pause(bool)` | Pauses or resumes this instance. |
| `step(dt)` | Advances the animation by `dt` seconds. |
| `draw()` | Renders the current frame. |
| `resize()` | Re-reads the canvas size. |
| `destroy()` | Removes listeners and observers and leaves the shared loop. |

**Read-only:** `expression`, `mode`, `loopTime`, `design`, `motion` (the `Motion` object: `.pose`, `.active`).

**Statics:**
- `SoulEyes.EXPRESSIONS`: `[{name, label, kind: 'mood' | 'reaction'}]`
- `MOODS`, `REACTIONS`, `RARITIES`
- `roll(designs, seedHi, seedLo)`, `rollFromChipId(designs, 'A1B2C3D4E5F6')`, `rollRandom(designs)`
- `render(ctx, rig, design, cx, cy, D, opts)` for custom compositing (`opts.motion` = a `Motion` pose), `normalizeDesign(d)`, `VERSION`
- `bindDeviceMotion(eyes, {flip?, onSample?})` → `{start(), stop(), flip, active, receiving}`; `Motion`, `PoseImu`, `TapDetector`, `NodDetector`, `MOTION_CUES`, `levelAngle`, `softClampRoll`

### Motion

SOUL M has a 6-axis IMU (QMI8658). Feed its samples and the eyes feel the world, the same way on the
web and on the device (the firmware's `lib/Suflet/src/EyeMotion.cpp` is a line-by-line port, checked
against this file by a parity trace in the native tests).

```js
// device frame: +x right, +y up (top of the glass), +z out of the glass. Accel in g (lying face up
// reads 0,0,+1), gyro in rad/s (right-handed). Feed every sample, 60-200 Hz.
eyes.setMotion({ ax, ay, az, gx, gy, gz });
// a phone: maps DeviceMotion (m/s², deg/s, screen rotation, iOS sign) for you. Call in a tap (iOS asks).
const imu = SoulEyes.bindDeviceMotion(eyes); await imu.start();
```

| Behaviour | What drives it | What the eyes do |
|---|---|---|
| Level keeping | roll of gravity in the glass plane (complementary filter: gyro + accel) | the pair counter-rotates to stay level, on a spring (k 80, ζ 0.5: a little lag and ~16 % overshoot); linear to ±120°, eased to ±150° at 180°; off when lying flat (gravity has no say in the plane); given up while too dizzy |
| Marble pupils | "down" in the eyes' levelled frame against a 2 s neutral, + the gyro as inertia | pupils roll to the low side on an under-damped spring (the right eye a beat behind), then drift back; kept inside each design's pupil travel; halved while `lookAt` is active |
| Spin → dizzy | a leaky bucket of the rotation rate (dead zone 0.8 rad/s, τ 1.3 s) | wobble + orbiting pupils in proportion; past 0.75 the `dizzy` mood (spiral pupils), then **ufff** (droopy lids, slow double blink, a sag) |
| Orientation | gravity, with hysteresis and hold times | on its back → looks up at you (bigger pupils, 2.5 s); face down → grumble (`suspicious`), dimmed, lids half shut; upside down → `shocked`; held still in a hand (tremor, not a stand) → calm lids |
| Gestures | accel spikes / gyro swings | double tap on the case → `approve`; nod (3 pitch swings) → `approve`; tilt left-right (3 roll/yaw swings) → `confused` |

Cues (`onMotion`): `dizzyStart`, `ufff`, `onBack`, `faceDown`, `faceUp`, `upsideDown`, `upright`, `calm`,
`tapTap`, `nodYes`, `nodNo`. On the device, `tapTap` / `nodYes` / `nodNo` also reach SoulOS as events
(`Ev::TapTap`, `Ev::NodYes`, `Ev::NodNo`): with a Claude request open, a nod approves and a head shake denies.
Without a sample the pose stays neutral and the eyes draw exactly as before.

### Expressions

**Moods** (hold): `neutral`, `happy`, `surprised`, `sleepy`, `love`, `smirk` (Șmecher), `sad`, `cry`, `angry`, `dizzy`, `suspicious`, `smug`, `shy`, `excited`, `thinking`, `listening`, `confused`, `bored`, `plan` (evil plan), `working` (Claude is working), `hungry` (low battery), `charging`.

**Reactions** (play once): `laugh`, `wink`, `shocked`, `sneeze`, `startled` (shaken), `approve`, `hello`, `goodbye`, `wake`.

Every change follows the same After Effects grammar: an anticipation move in the opposite direction, then the action on a damped spring that overshoots and settles. The right pupil follows the left about 45 ms later.

## Design spec

Sizes are fractions of the screen diameter (`shape`) or of the eye radii (`pupil`). Anything left out uses the defaults below.

```json
{
  "id": "original", "n": 1, "name": "Original", "rarity": "common", "family": "egg",
  "shape": { "type": "egg", "rx": 0.163, "ry": 0.2, "spacing": 0.19, "y": 0.005, "egg": 0.09, "lean": 0.13 },
  "white": "#FFF0C8",
  "pupil": { "type": "round", "L": "#2440FF", "R": "#FF5A1F", "rx": 0.42, "ry": 0.5, "inset": 0.16, "travel": 0.5 },
  "glint": { "color": "#FFF6E2", "size": 1 },
  "fx": []
}
```

- **`shape.type`**: `egg`, `squircle` (with `n`), `almond` (with `q` and `flick`), `drop`, `crescent` (with `dip`). For a round or wide oval, use `egg` with `egg: 0` and your own `rx` and `ry`.
- **`whiteR`** (optional): a different colour for the right eye's white.
- **`pupil.type`**: `round`, `slit`, `plus`, `star`, `heart`, `ring`, `double`, `pebble`, `crescent`, `diamond`, `spiral`.
- **`glint`**: the pebble glint on the pupils. `null` turns it off.
- **`fx`** (flat effects, for the rarer designs): `shimmer`, `rainbow`, `chrome`, `aurora` (with `auroraColors`), `starfield`, `folk` (with `folkBase` and `folkThread`), `glitter` (with `glitterColor`), `outline`.

## Birth roll

Each SOUL is born with one design. The firmware seeds the roll from the chip's 48-bit eFuse MAC, so a given unit always gets the same pair and can never re-roll:

1. `h = mix32(lo ^ mix32(hi ^ 0x534F554C))`, where `0x534F554C` is "SOUL".
2. The tier comes from `mix32(h) / 2^32` against the cumulative rates below.
3. The design within the tier is `floor(mix32(h ^ 0x9E3779B9) / 2^32 * count)`.

| Rarity | Rate |
|---|---|
| Common | 50% |
| Uncommon | 25% |
| Rare | 15% |
| Epic | 7% |
| Legendary | 2.5% |
| Mythic | 0.5% |

`mix32` is the hash already used in `Face.cpp` (`hash01`), so the device and the web give identical results.
