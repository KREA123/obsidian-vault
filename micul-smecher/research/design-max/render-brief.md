# Render brief v5: SOUL final + OU capsule + ALT A (PIATRA) + ALT B (MĂRGĂRITAR) (2026-09-24)

This brief goes with `research/09-product-design-max-2026-09-24.md`: the numbers there are the spec and this file tells Blender how to show them. **Rev. 2026-09-25:** loft to z 0 from the tables, tone-on-tone soles, elliptical land and arc pads, corrected rolling poses, hero shot from −x, flat glass on ALT B, and new COCON and unboxing frames. **Every image is a CGI concept.** Per the v4 README rule, it must be labelled „randare / concept (CGI)" wherever it is used.

## 0. Hard rules for every frame
1. **SOUL's front = body + black glass only.** No polished ring (delete v4's `R_RING` ring), no grille or dot holes, no logo, no light, no button, no loop or bail anywhere on SOUL.
2. **Eyes:** cream #FFF0C8 by day, amber #FFC96B only at night. Never pastel eye tints.
3. **The glass stays true black** (L* < 5), with at most **one** clean diagonal glint covering ≤ 12 % of the glass.
4. **No hand, strap or text in the hero.** The silhouette must read at 20 px tall.
5. **Light rule: SOUL itself never emits light except its eyes.** All other light comes from the OU capsule, and it never falls on SOUL's face.
6. **Soles are tone-on-tone by default** (Perlă = `sole_pearl`, Onix = onyx, and so on). A contrast sole (ember, cream, Founders aluminium) is **visible from the front whenever the camera is below ≈ 20°**: at table level it is a band 1.7–2.4 mm tall × ~50 mm wide (≈ 100 mm²); 1.3–1.7 mm at 3.6° (the real ray angle to the base in shot 2's "0°" camera); 0.8–0.9 mm at 8–9° (shot 1); 0.2–0.3 mm at 15° [E, 09 §3.2]. So contrast soles appear only in shot 2b (founder check #1), the sole-swap frame G and the bottom shot 5, never in a hero or front frame.

## 1. Pipeline and conventions
- **New script:** `renders/v5/src/soul_v5.py`. It loads `concepts.py` → `soul_scene.py` exactly as `soul_v4.py` does (the `exec(compile(...))` header), and reuses:
  - `mesh_from_rings`, `revolve`, `revolve_closed`, `glass_eye`, `mat_screen`
  - `new_mat`, `set_in`, `assign`, `parent_all`, `new_par`, `settle`
  - `sweep`, `world_color`, `studio`, `studio3`, `area_light`, `camera`, `flag`, `protect_screens`, `screen_highlight`
  - `mat_wood`, `build_hand_v4` (copy from `soul_v4.py`), `build_amulet` (the v1 coin, for scale)
  - `post.py` (OIDN denoise, bloom, AgX) and `annotate.py` (labels).
- **Output:** `renders/v5/soul_v5_<shot>.png`, plus a `renders/v5/README.md` in Romanian in the v4 style. Engine: Cycles CPU, 128 spp (night 192), OIDN in post, `POST['exposure'] = -0.35` unless stated.
- **Units and axes:** all numbers are in **mm** (multiply by `MM` = 0.001).
  - **World frame:** origin = SOUL's land centre on the table; +z up; **the face looks toward −y**; +x = the viewer's right when facing SOUL. (v4 built in a local frame with x right, y up, z toward the viewer and then stood it up with `stand_v4`. For v5, build directly in this world frame.)
  - **Camera placement:** "azimuth A / elevation E / distance D to target T" means `cam = T + D·(sin A·cos E, −cos A·cos E, sin E)`, with A > 0 toward +x.
  - **Yaw:** positive yaw about z turns the face toward +x.

---

## 2. FINAL SOUL: geometry (63 × 74 × 27.1 mm)

### 2.1 Tables (interpolate with monotone cubic / PCHIP)
**Front half-width w(z)** (mirrored in x):
| z | 0 | 1.2 | 2.2 | 4 | 6.3 | 8 | 10.5 | 14 | 18.5 | 23 | 28 | 34 | 40.5 | 48 | 55.5 | 60 | 63 | 66 | 69.5 | 71.5 | 73.2 | 74 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| w | 6.9 | 11.9 | 14.7 | 18.6 | 22.5 | 24.3 | 26.0 | 27.7 | 28.9 | 29.9 | 30.6 | 31.2 | 31.5 | 31.2 | 30.4 | 29.4 | 28.3 | 26.4 | 22.8 | 19.0 | 12.5 | 0 |

**Side lines** (y_f = front, y_b = back):
| z | 1.9 | 3 | 4.5 | 6.3 | 8 | 10.5 | 14 | 18.5 | 23 | 28 | 34 | 40.5 | 48 | 55.5 | 60 | 63 | 66 | 69.5 | 71.5 | 73.2 | 74 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| y_f | −12.5 | −13.2 | −13.8 | −14.2 | −14.4 | −14.4 | −14.2 | −13.7 | −13.1 | −12.4 | −11.5 | −10.6 | −9.6 | −8.5 | −7.9 | −7.4 | −7.0 | −5.9 | −4.7 | −2.8 | −1.0 |
| y_b | +12.0 | +12.4 | +12.7 | +12.8 | +12.7 | +12.4 | +11.8 | +11.0 | +10.4 | +9.9 | +9.6 | +9.4 | +8.7 | +7.6 | +6.7 | +5.8 | +4.6 | +2.7 | +1.3 | −0.1 | −1.0 |
- **Face plane:** leans back 8°, normal **n = (0, −0.990, 0.139)**, through the glass centre **G = (0, −10.6, 40.5)**. On the centreline, y_f(z) = −10.6 + 0.1405·(z − 40.5) for 14.6 ≤ z ≤ 66.4.
- **Depth:** D(z) = y_b − y_f. **Seam line:** y_s(z) = y_f + 0.36·D. This is where the width w is reached, i.e. the silhouette.

### 2.2 Body construction
1. **Loft body L.** Use 160 rings from z = −1 to 74, dense near 0–10 and 64–74, with 256 points per ring. **Use the table values all the way down; do not hold the z = 8 section** (that moves the rim to 2.6 / 1.85 / 7.6 mm and makes a contrast band 2.6–3.0 mm at 0°). Below z 1.9 extend y_f and y_b linearly with the slope of the first two points (y_f(0) ≈ −11.3, y_b(0) ≈ +11.3). Below z 8, widen w by δ(z) = 1.0 × smoothstep((8 − z)/2) (0 at z ≥ 8, 1.0 mm at z ≤ 6), so the loft stays just outside E and the Boolean has a clean crossing on the flanks. Each ring at height z is a closed curve in (x, y):
   - **Back half** (from (−w, y_s) through (0, y_b) to (+w, y_s)): a superellipse with exponent **2.2**, semi-axes w and (y_b − y_s).
   - **Front half, inside the glass band** (14.6 < z < 66.4): a **flat table** y = y_f for |x| ≤ c(z), where c(z) = √(26.2² − ((z − 40.5)/cos 8°)²). From (±c, y_f) it runs to (±w, y_s) as a quarter-superellipse with exponent **2.4** (a roll of about 5 × 7 mm at z 40.5).
   - Within 1.5 mm of the band ends, fade c → 0 with a smoothstep so there is no crease where the table starts and stops.
   - **Front half, outside the band:** a superellipse with exponent **2.6** from (−w, y_s) via (0, y_f) to (+w, y_s).
   - Cap the crown at z 74 with a single pole.
2. Add **Subdivision Surface** level 2 (render 2) and Shade Smooth. **Zebra-check:** the reflections must flow across the table edge and the crown without kinks (G2 target).
3. **Sole ellipsoid E:** (x/40)² + (y/36.9)² + ((z − 39.4)/40)² ≤ 1, at z ≥ 0. **Body = L ∩ E** (Boolean INTERSECT, Exact solver, applied after the subdivision).
   - The table clips E into the flat **land**: an **ellipse 13.8 (x) × 12.7 (y)**.
   - The intersection edge is the **sole rim**. **Check:** z ≈ 1.7 at the front, 1.5 at the back and 6.8 ± 0.5 on the sides; in plan about 46 × 24.5 mm. If the side rim misses, tune δ.
   - Bevel the rim edge **R1.5** (4 segments, on the sole side).
4. **Split into two objects:** the SOLE (everything below the rim, including the bevel) and the SHELL. Put a **0.10 mm dark groove** at the split (the only line near the chin, 1.7 mm above the table): a tube of r 0.05 sunk 0.05 mm, material `gap_dark`.
5. **Glass seat:** Boolean-subtract a cylinder Ø52.3 × 0.8 along −n at G from the flat table.
6. **Glass:** `glass_eye(tag, r_glass=26.0, z_edge=0.0, z_top=0.08, z_floor=-0.7, eyes=..., strength=2.6, r_screen=21.88)`.
   - This builds a flat 2.5D disc (the dome radius is about 4 m, so it reads flat) with an R0.35 edge. Everything outside r 21.88 is mask black.
   - Orient it so its local +z = n and local +y = (0, 0.139, 0.990). The top face sits **0.05–0.10 mm below** the table (reads flush; drop protection, 09 §3.2).
   - Shadow gap: a 0.15 mm-wide `gap_dark` ring between the glass and the seat.
   - **Level-eyes trick:** to counter-rotate the eyes, rotate the glass object about its own local z by −roll. The disc is round, so only the eye texture turns.
7. **Seam and openings:**
   - **Girdle seam:** a 0.2 × 0.2 V-groove along the curve (±w(z), y_s(z), z) from the sole rim on one side over the crown to the other side. Model it as a sunk tube, r 0.1, `gap_dark`.
   - **Speaker slot:** 12.0 (along the seam, z 46–58) × 0.9 mm, 2 mm deep, cut into the **+x** seam and following its curve, `gap_dark`.
   - **Mic pinholes:** Ø0.7, radial, in the **−x** seam at z 50 and z 22.
   - **Not modelled** (invisible): the crown FPC electrode, the IR window, the antenna and the internal speaker box.
8. **Bottom details** (all visible only in shot 5):
   - **Land coin:** elliptical FR4, 12.0 (x) × 10.9 (y) × 1.0 mm, inset flush in the land, `fr4`.
   - **5 gold pads,** recessed 0.15, `gold`: a Ø1.8 centre pad at (0, 0) plus 4 **arc pads** on r 4.0 (width 1.2, each spanning 60°, centred at 0°, 90°, 180° and 270°).
   - **TPU ring:** elliptical, OD 13.6 × 12.5, ID 12.0 × 10.9, 0.2 mm proud, `tpu_clear`.
   - **2 × Torx T5 heads,** Ø2.6, flush, at (±14, +3), projected onto E, `screw`.
   - **Engraving, 2 rings** on the sole, DejaVu Sans ExtraLight caps, as a roughness + bump mask (0.3 → 0.55 roughness, bump 0.05 mm). Outer ring (r ≈ 10.5, 1.0 mm caps): „SOUL · Nº 00417 · PROIECTAT ÎN ROMÂNIA". Inner ring (r ≈ 8.3, 0.6 mm caps): „SOUL S1 · SN 26-00417 · [manufacturer] SRL · [street, city] RO · [e-mail]", plus a CE mark 5 mm tall on the +x wing of the sole at (+16, −4) and the crossed-bin symbol at (−16, −4), clear of the Torx heads.

### 2.3 Poses
- **Upright:** as built (land at z 0).
- **Stills with a rock:** rotate about the land centre, then `settle(par)`.
- **True rolling** (strobe and animation only):
  - **Sideways roll φ:** for |φ| < 10°, pivot about the land edge at x = ±6.9. Beyond that, rotate about the body point C = (0, 0, 39.4), then **place C at height 40.0** (R = 40, i.e. lift 0.6 mm) and translate x by 40·φ (radians, toward the lean).
  - **Pitch θ:** for |θ| < 11°, pivot about the land edge at y = ±6.4. Beyond that, rotate about C = (0, 0, 33.4), **place C at height 34.0** (R = 34.0) and translate y by 34.0·θ.
  - Using 39.4 / 33.3 as the heights sinks un-settled frames 0.6–0.7 mm into the table. The sole is an ellipsoid, not a sphere, so **call `settle(par)` on every frame** as the final correction.
- In every rocked pose, counter-rotate the glass by −roll so the eyes stay level with the horizon.

---

## 3. OU capsule geometry (77 W × 88 H × 42 D, origin at its base centre)
1. **Outline** (a solid of "super-revolution", in horizontal sections):
   - **Front half-width:** above z 32, |x/38.5|^2.7 + |(z−32)/56|^2.7 = 1; below, |x/38.5|^3.5 + |(32−z)/36|^3.5 = 1, clipped at z 0.
   - **Semi-depth:** the same two equations with 21 in place of 38.5. Sections are centred at y = +1.0.
   - **Each horizontal section** is a superellipse with exponent 2.3 and semi-axes (w, d):
| z | 0 | 4 | 10 | 18 | 26–40 | 48 | 56 | 64 | 72 | 78 | 82 | 85 | 87 | 88 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| w | 28.2 | 33.0 | 36.4 | 38.1 | 38.5 | 38.0 | 37.0 | 35.1 | 31.8 | 27.7 | 23.5 | 18.5 | 12.5 | 0 |
| d | 15.4 | 18.0 | 19.9 | 20.8 | 21.0 | 20.7 | 20.2 | 19.1 | 17.3 | 15.1 | 12.8 | 10.1 | 6.8 | 0 |
   - Solidify the walls to 2.2 mm. The flat base land is 56 × 31, with a 0.5 mm cork foot ring (`cork`).
2. **Parting plane:** through (y −21, z 18) and (y +22, z 48), spanning x. Below it is the **cup** (body colour); above it is the **lid**. When closed, the lid sits **0.6 mm above** the plane, on 3 bumps: this is the **halo line**.
3. **Hinge:** axis along x at (y +20.5, z 48.3). Two stainless knuckles Ø4 × 8 at x = ±10 and a recessed **loop bar** Ø2 × 14 at x = 0 (`steel`). **Open pose:** the lid is rotated **100°** about the hinge, front rim up and back.
4. **Liner and socket:** SOUL's pose inside the OU: land at (0, −2, 9), then tilted **6° back** about the x-axis through the land (the top moves toward +y).
   - The liner surface is SOUL's ellipsoid E offset outward by **0.5 mm**, placed in that pose, with a Ø15 flat floor at z 9.
   - It is filled up to the cup's inner wall, leaving a 2 mm visible lip at the cup rim (`liner` = the colourway's accent: Perlă = ember). The Ø15 floor is `pom_floor`. **Check:** the cup's front rim sits ≥ 3 mm below SOUL's glass bottom edge.
   - A Ø1 recovery pinhole under the hinge, next to the USB-C (09 §3.8), `gap_dark`.
5. **Lights:**
   - A 1 × 1 mm emissive strip under the **rear 180°** of the cup rim lip, aimed at the lid's interior: Blackbody 2200 K.
   - A base slit, 1 × 40 mm at z 1 on the front of the base, 2200 K, washing the table.
   - **Closed:** an emissive 0.6 mm band in the halo gap (2200 K).
   - **Neither ever lights SOUL's face.**
6. USB-C opening 9 × 3.2 at the back, z 8, under the hinge.

## 3b. COCON sleeve and unboxing props (09 §5–6)
- **COCON:** offset SOUL's body outward by 2.25 mm (0.5 fit + 1.75 knit wall) and cut it at z 76 → about 67 W × 76 H × 31 D. Add a **fold-over flap**: a 2 mm sheet continuing the back wall up, arching 4–6 mm over the crown (2 × Ø6 × 1.5 magnets in its tip) and 10 mm down the front, ending at z ≈ 68, just above the glass (closed height ≈ 84). Add a **woven loop**, 8 wide × 45 long × 1.2 thick, sewn at the top of the back seam and hanging as a U. Materials: `knit` (below), loop `knit_loop`. **Open pose:** flap folded back, SOUL half out (lifted 35 mm), eyes `soul_wide`.
- **Sleeve box:** 118 × 78 × 150, 1.2 mm board, `board_cream`. Two hot-foil eye ovals on the front (the eye shape at 40 % scale, `foil_cream`); the "SOUL" spine; a paper seal 30 × 12 printed „Nº 00417". **Back panel** (visible only in frame 10b): a legal block 60 × 40 mm at 6 pt (CE, crossed bin, battery data, manufacturer address, „Companion AI · vorbești cu o inteligență artificială", „Nu este o jucărie · 14+"). Use real text, not lorem ipsum.
- **Pulp egg carton:** a single cell, a superegg of revolution |r/44|^2.5 + |(z−40)/52|^2.5 = 1, cut at z 58, 1.5 mm wall, `pulp`, holding the closed OU upright with its hinge loop up; a crimped rim flange 6 mm wide at z 58.
- Cards: 70 × 100 cream cards with the two Romanian lines from 09 §5.

---

## 4. ALT A: PIATRA + OU nest (62 × 70 × 26 mm)
- **Front outline:** above z 38.5, |x/31|^2.6 + |(z−38.5)/31.5|^2.6 = 1 (top at z 70); below, |x/31|^2.4 + |(38.5−z)/40.5|^2.4 = 1, clipped at z 1.2.
  - Half-widths: z 1.2: 15.1 · 5: 20.4 · 10: 24.5 · 17.5: 28.1 · 25: 30.1 · 38.5: 31.0 · 52.5: 29.5 · 60: 25.9 · 66: 19.4 · 70: 0.
- **Depth D:**
| z | 1.2 | 8 | 20 | 38.5 | 50 | 62 |
|---|---|---|---|---|---|---|
| D | 25 | 26 | 23.5 | 21.3 | 19 | 17 |
  - Above z 62 it closes over the crown, keeping D/W ≥ 0.55.
  - Front line: y_f = −12.5 + 0.1405·(z − 1.2), an 8° lean.
- **Sections:** the front 36 % of D uses a superellipse exponent **3.2**, the back 64 % uses **2.2**. The seam sits **on the silhouette** (the judge-2 fix).
- **Face:** a flat Ø52 table centred at z 38.1, built with the same table method as §2.2. Glass Ø50 × 0.7, flush, **no ring**.
- **Foot:**
  - Ø25 × 1.2 dark-champagne zinc (`zinc_champ`), inset 1 mm, so the hull ends 1.2 mm above the table (hover shadow line).
  - Underside: 4 gold rings (radii 4.0 / 6.5 / 9.0 / 11.0, width 1.1) plus a Ø2.5 gold dot.
- **Nest + dome:** a Piet Hein superegg of revolution, |r/36|^2.5 + |(z−45)/48|^2.5 = 1, clipped at z 0 (Ø33.6 flat base), top at z 93.
  - **Nest** = z 0–23 (rim Ø67.7), 4 mm wall, in `pearl` PC. The socket floor is at z 12. SOUL stands upright in it with its glass bottom 2 mm above the rim.
  - **Dome** = z 23–93, 2.5 mm wall, `dome_frost`. A 2 mm frosted light-guide ring inside the rim (2200 K, rear half only).
- **Rule 2:** speaker slot 12 × 0.9 in the +x seam at z 44–56; mics Ø0.7 in the −x seam at z 48 and z 20 (`gap_dark`). Nothing on the front.

## 5. ALT B: MĂRGĂRITAR + SCRIN (63 × 72 × 24 mm)
- **Half-widths:**
| z | 0 | 4 | 8 | 18 | 30 | 39.6 | 54 | 62 | 67 | 70 | 72 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| w | 14.0 | 21.5 | 25.0 | 27.5 | 30.5 | 31.5 | 29.25 | 25.5 | 19.0 | 11.0 | 0 |
- **Depths:**
| z | 0 | 6 | 12 | 30 | 40 | 55 | 62 | 68 | 72 |
|---|---|---|---|---|---|---|---|---|---|
| D | 17 | 22 | 24 | 22 | 20.5 | 17.5 | 16 | 12 | 0 |
- **Body:** the face leans back 8°. Sections as in §2.2, with a flat table under the flat glass; outside a Ø56 zone the table bends at R150 (vertical convexity) into the forehead and chin. The base is a flat **28 × 17 land**.
- **Face:** **flat Ø52 2.5D glass at launch** (09 §7–§8: the cabochon is rejected for launch), built with the same `glass_eye` call as §2.2 step 6. Centre at z 38.9, 0.05–0.10 mm below the table, 0.13 gap. (Optional extra frame only: the later R200 cabochon on the same seat, labelled "later".)
- **Details:**
  - Girdle: a 0.3 mm V-groove at the widest point.
  - Speaker: a 12 × 0.9 slot in the girdle on the +x side, at z 42–54. Mics: Ø0.7 pinholes in the −x girdle at z 46 and z 20.
  - **Golden sole:** a 28 × 17 plate, `zamak_gold`, with a 0.5 reveal.
- **SCRIN:**
  - **Plinth:** an 86 × 60 × 24 oval with R6 top edges (`lacquer_pearl`), a 5 mm socket, a 14 mm backrest and 8 × 2200 K points.
  - **Lid:** the upper part of an ovoid continuing the plinth outline, 75 mm tall; walls 3.5 mm (5 mm at the crown); `surlyn`, gloss outside and frosted inside.
  - **Shot pose:** the lid **inverted beside the plinth as a bowl**.

---

## 6. Eyes (`eyes.py` VARIANTS to add)
`render()` defaults already give the loved proportions: each eye is 30.8 % of the Ø tall, W/H ≈ 0.78 and the V is 9.2°.
- Keep the existing `cream_look`, `cream_down`, `listen_up` and `amber_sleepy`.
- Add these variants:
| Variant | color | gx | gy | lid_top | lid_tilt | other | Use |
|---|---|---|---|---|---|---|---|
| `soul_front` | #FFF0C8 | 0.0 | −0.05 | 0.19 | 0.16 | | default gaze |
| `soul_smug` | #FFF0C8 | 0.95 | 0.10 | 0.30 | 0.19 | | after hopa (≈ 11°, below the 15° limit) |
| `soul_wide` | #FFF0C8 | 0.0 | −0.35 | 0.06 | 0.12 | scale 1.08 | lift |
| `soul_left` | #FFF0C8 | −0.6 | −0.10 | 0.22 | 0.16 | | glance |
| `soul_closed` | #FFC96B | 0.0 | 0.2 | 0.0 | 0.0 | open_ 0.07, glow 0.6 | asleep in a closed OU |
| `soul_dizzy` | #FFF0C8 | 0.0 | 0.0 | 0.40 | 0.10 | new `split` = 0.035 | strobe |
- **`split`:** a one-line code change. Add `ey += side * split * S` inside the per-eye loop, so the two eyes sit at opposite vertical offsets.
- Optional: an `asym` parameter that makes the right eye 8 % larger (per r-creatures).
- **Emission strength:** 2.6 by day and 0.8 at night.

## 7. Materials (Principled BSDF, Blender 4.0 input names)
Blender 4.0 has no thin film. **Nacre is faked with Layer Weight → Facing (Blend 0.45) → ColorRamp → Base Color.**
| Name | Settings |
|---|---|
| `pearl` (PERLĂ R1) | Ramp: 0.0 #F6F1E8 · 0.55 #F3E7EA · 1.0 #E8ECF4 · Roughness 0.20 · Metallic 0.06 · Specular IOR Level 0.5 · Subsurface Weight 0.12, Radius (1.0, 0.8, 0.6), Scale 0.0015 · **Coat** Weight 1.0, Roughness 0.03, IOR 1.5 · **Sheen** 0.25, Roughness 0.35, Tint #F6EDFF · micro-flake: Voronoi 3D (scale 30000) → Bump strength 0.02, distance 0.00001, on the base Normal only |
| `onyx` (R4) | Base #0A0A0B · Roughness 0.10 · Spec 0.5 · Coat 1.0 / 0.015 / 1.5 · optional sparkle: Voronoi (scale 60000) thresholded at 0.998 → metallic #BFBFBF |
| `lapis` (LAC) | Ramp: facing #1B3A8F → grazing #2A4FB0 · Metallic 0.20 · Roughness 0.28 · **Coat** 1.0 / 0.012 / IOR 1.55, **Coat Tint #C9D6FF** · gold flecks: Voronoi (scale 12000) mask ≈ 0.3 % → #D4AF37, metallic 1, roughness 0.25 · lit side L* ≈ 30 |
| `amber` (CHIHLIMBAR LAC) | Ramp: facing #7A3A10 → grazing #C98A3A · Metallic 0.25 · Roughness 0.25 · Subsurface 0.05, Radius (1.0, 0.5, 0.2), Scale 0.002 · Coat 1.0 / 0.012 / 1.55, Coat Tint #FFD9A0 · gold flecks 0.15 % |
| `ghost` (FUM R6) | Base #7A7A80 · **Transmission 0.35** · Roughness 0.38 (matte UV coat) · IOR 1.585 · Volume Absorption #9A9AA0, density 150 · inside: a heart-plate disc Ø46 × 1, #F2EEE7, roughness 0.3, **and an inner pearl liner** (the body offset 2.3 mm inward, `pearl`, roughness 0.4) that hides everything else |
| `sole_ember` | Base #D8572A · Roughness 0.30 · Coat 1.0 / 0.10 / 1.5 (satin-gloss) |
| `sole_pearl` (**Perlă default**) · `sole_onyx` (Onix default) · `sole_lapis` · `sole_amber` · `sole_cream` · `sole_glow` (Fum default) | `pearl` with coat roughness 0.10 · `onyx` with coat roughness 0.10 · solid #1E3E96 and #8A4A18, roughness 0.30, coat 1.0 / 0.10 · #FFF0C8, same finish (accessory) · #F2EEE7, Transmission 0.9, Roughness 0.45, IOR 1.585 |
| `sole_alu` (Founders) | #D8C3A0 · Metallic 1 · Roughness 0.28 · Anisotropic 0.3 |
| `glass` | `mat_screen` as in v4: Base #000000 · Roughness 0.02 · IOR 1.52 · Specular IOR Level 0.35 (AR) · mask and panel both #020202, so the screen edge disappears |
| `gap_dark` · `fr4` · `gold` · `tpu_clear` · `screw` | #030303 r 0.8 · #121212 r 0.55 spec 0.4 · #E3C07A metallic 1 r 0.18 · #F2F2F2 transmission 0.9 r 0.3 IOR 1.5 · #BDB8B0 metallic 1 r 0.30 |
| `ou_lid` | Two material slots via Solidify material offset: **outer** faces Roughness 0.05, **inner** faces 0.45 · Base #F4EFE8 · Transmission 0.9 · IOR 1.58 · Onyx/Fum lids: Base #3A3A3F, Transmission 0.8 |
| `liner` · `steel` · `cork` · `pom_floor` | = the colourway's accent (Perlă: `sole_ember`) · #C9C7C3 metallic 1 r 0.25 anisotropic 0.5 · #A8845E r 0.9 · #EDEAE4 r 0.35 |
| `knit` · `knit_loop` · `board_cream` · `foil_cream` · `pulp` | Base #E9E2D6 (Perlă) / #1A1A1C (Onix), Roughness 0.9, Sheen 0.6, Voronoi + wave bump 0.3 mm rib texture · #D8572A r 0.8 · #F1E9DA r 0.85 · #FFF0C8 metallic 0.8 r 0.3 · #CFC6B6 r 0.95 + noise bump 0.4 mm |
| `led_2200` | Emission via Blackbody 2200 K: strip strength 1.6 (day, 20 %) / 4 (night); base slit 1.5; halo band 6 (closed) |
| `zinc_champ` · `zamak_gold` | #B9A688 metallic 1 r 0.35 · #E3C89A metallic 1 r 0.18 |
| `lacquer_pearl` (ALT B) | Two surfaces 2.2 mm apart: outer Transmission 1.0, IOR 1.585, Roughness 0.02, Coat 1.0 / 0.01; inner = `pearl` with Metallic 0.15, Sheen 0.3 |
| `dome_frost` · `surlyn` | outer Transmission 1, IOR 1.47, Roughness 0, faint warm absorption; inner Roughness 0.45 · IOR 1.51, outer Roughness 0.02, inner 0.45 |
| Sets | sweep `#D9CDBE` (v1 hero), roughness 0.85 · walnut = `mat_wood('walnut', '#3B2A20', '#24170F', 0.35)` · limestone #D8CFC2 r 0.6 + noise bump · skin as in v4 (#D2B39C) |

## 8. Lighting
- **Day: the v1 warm studio the founder loved.**
  - `world_color((0.95, 0.92, 0.88), 0.03)` and `sweep('#D9CDBE')`.
  - `studio3(T, k=1.0, bg=7.5)`:
| Light | Size | Offset from T (m) | Power | Colour temp. | Spread |
|---|---|---|---|---|---|
| key (disk) | 0.5 m | (−0.42, −0.32, +0.42) | 2.2 W | 5600 K | 70° |
| fill | 0.8 m | (+0.55, −0.25, +0.12) | 0.6 W | 5000 K | — |
| rim | 0.3 m | (−0.22, +0.35, +0.20) | 2.6 W | 5000 K | 50° |
| top | 0.5 m | (0, 0, +0.55) | 0.7 W | 5600 K | — |
| bg | 1.2 m | (0, −0.1, 0.9), aimed at (0, 0.55, 0.25) | 7.5 W | 4500 K | — |
  - **Add for v5:**
    - A **flank strip:** RECTANGLE 1.0 × 0.08 m, 5000 K, 1.2 W, at T + (+0.30, +0.30, +0.10). It draws **one continuous highlight** down the +x flank and over the crown.
    - A **chin bounce:** 0.3 × 0.2 m, 3000 K, 0.15 W, at T + (0, −0.25, −0.02), aimed up. It opens the chin without lighting the glass.
  - **Keep the glass black:** `protect_screens(cam, T, 1.6, -0.012)` + `flag(cam, T)`, and exactly one glint via `screen_highlight(par, cam, up_deg=11, side_deg=8.5, size=(0.022, 0.3), tilt_deg=-30, strength=6)`.
  - **Exposure targets:** the lit pearl flank reads **L* 90–93**, the glass stays **< 5**, and the eyes do not clip.
- **Night:**
  - `world_color((0.02, 0.025, 0.035), 0.004)`, a walnut top and no studio lights.
  - A window: area 1.0 × 1.5 m, 6500 K, 2.5 m behind-right, reading at about 3 %.
  - All other light comes from the OU `led_2200` meshes (they must light the walnut and the pearl chin by bounce).
  - `POST['exposure'] = +0.4`.

## 9. Shots (the final design: 12 required frames, 1–10b)
| # | File | Scene | Camera (T; A / E / D; lens; f) | Eyes | Must read |
|---|---|---|---|---|---|
| 1 | `soul_v5_hero.png` 1600 × 2000 (+1600 × 1200 crop) | Perlă SOUL (**pearl sole**), upright, **yaw −8°**. OU Perlă open (lid 100°, strip at 20 %) at (−95, +120, 0), yaw +20°, soft in the background. v1 studio (the flank strip now rims the far +x silhouette). | T (0, −2, 37); **−24° / +9° / 375**; 100 mm; f/8, focus on the eyes | `cream_look` | SOUL fills ~55 % of the frame height; one flank highlight; **no contrast sole; the speaker slot out of frame** (from +24° the +x flank is seen at ≈ 32° and the slot shows); only the two Ø0.7 mic pinholes on the −x seam, as ≈ 10 px dots; a helmet-headed creature at 20 px |
| 2 | `soul_v5_front_00.png` + `_15.png` 1600 × 1600 | Perlă (pearl sole), yaw 0, on the sweep | T (0, 0, 37); **0° / 0° and 0° / 15°** / 590; 200 mm (near-orthographic); f/16. Note: at T z 37 the "0°" ray reaches the base at ≈ 3.6° | `soul_front` | **Nothing but body + glass**; the pearl sole reads as body, with a 0.1 mm split line 1.7 mm above the table. Also export `soul_v5_shadow20.png`: a black silhouette scaled to 20 px tall, next to the v1 Ø52 coin and the v4 pebble. |
| 2b | `soul_v5_check1.png` 2400 × 1200 | **Founder check #1:** four Perlă panels: pearl sole vs **ember** sole (`sole_ember`), each at table level and at 9° | T (0, 0, 5) for table level (camera z 5, a true 0°) and T (0, 0, 37) at +9°; 0° or +9° / 590; 200 mm; f/16 | `soul_front` | the ember band honestly shown: ≈ 1.7–2.4 × 50 mm at table level, ≈ 0.8–0.9 mm at 9°; label with `annotate.py` |
| 3 | `soul_v5_side.png` 1600 × 1200 | Perlă, seen from +x (the speaker side) | T (0, 0, 37); **+90° / 0° / 630**; 150 mm; f/16; add a thin rim strip behind (−x) to separate the silhouette from the sweep | `soul_front` | the 8° lean and wedge (27 → 20 → 15 mm), the girdle seam on the silhouette, the 12 × 0.9 slot at z 46–58, the rocker curve with the pearl sole underneath (split line at z 1.7 front, 6.8 on the flank), no loop |
| 4 | `soul_v5_back.png` 1600 × 1200 | Perlă | T (0, +2, 38); **−150° / +12° / 420**; 100 mm; f/11 | (screen off) | a blank glossy dome with no text or screws; 2 mic pinholes in the −x seam; the crown; one clean highlight line |
| 5 | `soul_v5_bottom.png` 1600 × 1200 | Perlă **"plays dead"**: rotated −90° about x, settled on its back, sole facing the camera | T = the land centre after posing; **0° / +18° / 260**; 100 mm macro; f/8; add a raking key: 0.15 m disk at 10° elevation from the left, 5600 K, 0.8 W | `cream_down` (it looks toward you) | the pearl sole, the elliptical FR4 coin with the centre pad and 4 arc pads, the elliptical TPU ring, 2 Torx heads, both engraving rings legible (CE and bin symbol included) |
| 6 | `soul_v5_ou_night.png` 1600 × 2000 + `soul_v5_ou_closed.png` | walnut bedside. **6a:** OU Perlă open, SOUL seated at 14°. **6b:** same frame, lid **closed**, the halo line glowing and the frosted lid a soft lantern. | T (0, 0, 45) in OU coords; **−28° / +20° / 420**; 50 mm; f/2.8, focus on the eyes | 6a `amber_sleepy` (0.8); 6b `soul_closed` | light only from the OU: a halo behind the head, a warm pool on the walnut, **no light on the face**; 6b is a lantern egg with a thin glowing line |
| 7 | `soul_v5_hand.png` 1600 × 1200 | `build_hand_v4('hand', (0, 0, 0.030), 18)`; SOUL **cradled face-up** (rotate −90° about x, then (18°, −6°, 14°)) at (0.003, 0.010, 0.042) m; sweep #CDBFAE | T = SOUL's centre; offset (0.13, −0.30, 0.15) m; 70 mm; f/5.6 | `cream_down` | the scale: fills the palm, a heavy pebble, the glass under the thumb |
| 8 | `soul_v5_family.png` 2000 × 1125 | L → R, **each on its tone-on-tone sole**: **ONIX** (roll −5°), **CHIHLIMBAR** (pitch 6° back), **PERLĂ** (upright, 10 mm forward), **LAPIS** (roll +6°), **FUM** (glow sole, roll −3°). 14 mm gaps on a shallow arc (R 400). Glass counter-rotated so the eyes are level. | T (0, 2, 36); camera (0, −660, 110) as in v4 family; 70 mm; f/11; `studio(T, 1.6)` | smug · left · front · look · wide | a family that is *alive*; ownable colour at 3 m; no pastels; no contrast band at any chin |
| 9 | `soul_v5_cocon.png` 1600 × 1200 | Perlă COCON (§3b) on the sweep: one closed and standing, with the loop hanging; one open beside it, flap back and SOUL half out | T (0, 0, 40); −20° / +12° / 480; 100 mm; f/8 | `soul_wide` (the one coming out) | the rule-3 carry: the loop lives on the sleeve, never on SOUL; knit texture reads at 100 % |
| 10a / 10b | `soul_v5_unbox.png` 1600 × 2000 + `soul_v5_boxback.png` 1600 × 1200 | 10a: overhead unboxing on the sweep: the sleeve lifted beside it, the pulp egg carton with the closed OU standing in it, a card, and a second, opened OU with SOUL's eyes just opened. 10b: the sleeve's back panel | 10a: T (0, 0, 30); 0° / +62° / 520; 50 mm; f/5.6. 10b: straight on, 0° / 0° / 400 | 10a `soul_wide` | 10a: "a birth", warm and calm; 10b: the legal block and the AI notice legible |

**One shot per alternate** (same v1 studio, so all three can be compared):
| # | File | Scene | Camera | Eyes |
|---|---|---|---|---|
| A | `soul_v5_altA_piatra.png` 1600 × 1200 | Perlă PIATRA upright in its pearl nest; the frosted dome standing rim-down 90 mm behind-left; the hover shadow line visible | T (0, 0, 40); +20° / +8° / 520; 100 mm; f/8 | `cream_look` |
| B | `soul_v5_altB_margaritar.png` 1600 × 1200 | Perlă MĂRGĂRITAR on a 200 × 120 × 12 limestone slab, yaw +20°; SCRIN plinth 120 mm behind-right, empty socket, crystal lid inverted beside as a bowl; one curved glint on the cabochon at 10–11 o'clock that never crosses the eyes | T (0, 0, 37); +22° / +7° / 480; 100 mm; f/8 | `soul_smug` |

**Optional:**
- **F.** `soul_v5_ou_day.png`: the OU open on a walnut desk by day, SOUL seated at 14°, a laptop edge soft behind; T (0, 0, 45) in OU coords; −30° / +18° / 450; 70 mm; `soul_left`.
- **G.** `soul_v5_sole_swap.png`: Perlă lying on its back, the pearl sole lifted off with a T5 driver beside it, the ember accessory sole next to it (the only frame that sells the contrast sole); also PUCK (Ø36 × 10 zinc cup) and CUIB (porcelain nest, 12° backrest) as small still-life props.
- **C.** `soul_v5_choice.png`: FINAL, ALT A and ALT B dead-front at the same scale, labelled with `annotate.py`. This is the founder's decision board.
- **D.** `soul_v5_hopa_strobe.png` 2400 × 1350. Background sweep #D9CFC4; 100 mm; +30° / +4°.
  - Four ghost poses at 22 % opacity, then the sharp final upright pose with `soul_smug`.
  - Ghosts: (φ −18°, θ −6°), (φ +12°, θ +4°), (φ −7°), (φ +3°). Use true rolling from §2.3 and level eyes in each.
- **E.** `soul_v5_hopa_nudge.mp4`, 4 s at 30 fps:
  - At t = 0.3 s a nudge hits the right cheek.
  - φ(t) = −20°·e^(−ζω₁t)·cos(ω₁t) with f₁ = 2.0 Hz; θ(t) = −6°·(same form) with f₂ = 1.75 Hz; ζ = 0.12.
  - The eyes counter-rotate with a 70 ms lag and 10 % overshoot.
  - At 2.8 s, `soul_dizzy` for 300 ms; at 3.4 s, `soul_smug`.

## 10. Acceptance checks before delivery
1. **Front:** nothing on the face but body and glass (no ring, dots, seam or logo). The glass reads L* < 5 with one glint. No speaker slot in shots 1 and 2.
2. **Proportions, measured on the front render:** glass centre at 54–56 % of height; eye line at 50–52 %; glass ≈ 52 % of the front; broad end up by ≈ 5 %.
3. **Sole:** every hero, front and family frame uses the tone-on-tone sole. Contrast soles appear only in 2b, 5 and G; in 2b, measure the band on the render (≈ 1.7–2.4 mm at table level, ≈ 0.8–0.9 mm at 9°) against 09 §3.2.
4. **Light:** no light on SOUL except its eyes; OU light never on the face.
5. **Materials and labelling:** no pastels, no loop on SOUL, cream eyes (amber only at night). Every file is listed in `renders/v5/README.md` as „randare / concept (CGI)".
6. **Budget:** about 6–9 minutes per frame on 4 CPU cores at 128 spp (v4 measure). Night frames and the strobe take about 2 ×.
