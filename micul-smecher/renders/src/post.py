#!/usr/bin/env python3
"""post.py -- denoise + bloom + AgX tone-map the EXR passes written by suflet_scene.py.

    python3 post.py /tmp/.../hero            (reads hero.json + hero_{color,albedo,normal}_NNNN.exr)
            [--out file.png | --outdir DIR] [--exposure 0.3] [--bloom 0.06] [--look "AgX - Punchy"]

Needs: numpy, OpenEXR, Pillow, PyOpenColorIO (pip install opencolorio) and the 'oidn'
wheel (pip install oidn==0.2.1, Intel Open Image Denoise 1.4). Uses Blender's own OCIO
config so the result matches Blender's AgX view transform.
"""
import argparse
import ctypes
import glob
import json
import os

import numpy as np
import OpenEXR
import Imath
from PIL import Image

OCIO_CFG = next((p for p in ('/usr/share/blender/datafiles/colormanagement/config.ocio',
                             '/usr/share/blender/4.0/datafiles/colormanagement/config.ocio')
                 if os.path.exists(p)), None)


def read_exr(path):
    f = OpenEXR.InputFile(path)
    dw = f.header()['dataWindow']
    w, h = dw.max.x - dw.min.x + 1, dw.max.y - dw.min.y + 1
    pt = Imath.PixelType(Imath.PixelType.FLOAT)
    ch = f.header()['channels'].keys()
    names = ['R', 'G', 'B'] if 'R' in ch else sorted(ch)[:3]
    arr = [np.frombuffer(f.channel(c, pt), np.float32).reshape(h, w) for c in names]
    return np.ascontiguousarray(np.stack(arr, -1))


def denoise(col, alb, nrm):
    import oidn
    h, w, _ = col.shape
    dev = oidn.NewDevice()
    oidn.CommitDevice(dev)
    flt = oidn.NewFilter(dev, 'RT')
    out = np.zeros_like(col)
    for name, a in (('color', col), ('albedo', alb), ('normal', nrm), ('output', out)):
        oidn.SetSharedFilterImage(flt, name, a, oidn.FORMAT_FLOAT3, w, h)
    lib = ctypes.CDLL(glob.glob(os.path.join(os.path.dirname(oidn.__file__), 'lib.linux.x64',
                                             'libOpenImageDenoise.so*'))[0])
    lib.oidnSetFilter1b.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_bool]
    lib.oidnSetFilter1b(flt, b'hdr', True)
    oidn.CommitFilter(flt)
    oidn.ExecuteFilter(flt)
    oidn.ReleaseFilter(flt)
    oidn.ReleaseDevice(dev)
    return out


def blur(img, sigma):
    h, w, _ = img.shape
    ph, pw = int(h + 6 * sigma), int(w + 6 * sigma)
    fy = np.fft.fftfreq(ph)[:, None]
    fx = np.fft.rfftfreq(pw)[None, :]
    g = np.exp(-2 * (np.pi * sigma) ** 2 * (fx * fx + fy * fy))
    out = np.empty_like(img)
    for c in range(3):
        pad = np.zeros((ph, pw), np.float32)
        pad[:h, :w] = img[:, :, c]
        out[:, :, c] = np.fft.irfft2(np.fft.rfft2(pad) * g, s=(ph, pw))[:h, :w]
    return out


def agx(col, look):
    import PyOpenColorIO as oc
    cfg = oc.Config.CreateFromFile(OCIO_CFG)
    vp = oc.LegacyViewingPipeline()
    vp.setDisplayViewTransform(oc.DisplayViewTransform(src='Linear Rec.709', display='sRGB', view='AgX'))
    if look and look != 'None':
        vp.setLooksOverrideEnabled(True)
        vp.setLooksOverride(look)
    proc = vp.getProcessor(cfg).getDefaultCPUProcessor()
    img = np.ascontiguousarray(col.astype(np.float32))
    proc.applyRGB(img)
    return img


def process(base, frame, out_png, exposure, bloom, look, do_denoise=True):
    col = read_exr('%s_color_%04d.exr' % (base, frame))
    if do_denoise:
        alb = read_exr('%s_albedo_%04d.exr' % (base, frame))
        nrm = read_exr('%s_normal_%04d.exr' % (base, frame))
        col = denoise(col, alb, nrm)
    col = np.maximum(col, 0) * (2.0 ** exposure)
    if bloom > 0:
        w = col.shape[1]
        hi = np.clip(col - 0.9, 0, 30)
        col = col + bloom * (blur(hi, w * 0.003) + 0.6 * blur(hi, w * 0.015))
    img = agx(col, look)
    img = (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)
    Image.fromarray(img).save(out_png, optimize=True)
    print('wrote', out_png)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('base')
    ap.add_argument('--out')
    ap.add_argument('--outdir')
    ap.add_argument('--exposure', type=float)
    ap.add_argument('--bloom', type=float)
    ap.add_argument('--look')
    ap.add_argument('--no-denoise', action='store_true')
    a = ap.parse_args()
    meta = json.load(open(a.base + '.json'))
    exp = meta.get('exposure', 0.0) if a.exposure is None else a.exposure
    bl = meta.get('bloom', 0.06) if a.bloom is None else a.bloom
    look = meta.get('look', 'AgX - Medium High Contrast') if a.look is None else a.look
    frames = meta['frames']
    for f in frames:
        if len(frames) == 1:
            out = a.out or os.path.join(a.outdir or '.', meta['stem'] + '.png')
        else:
            os.makedirs(a.outdir, exist_ok=True)
            out = os.path.join(a.outdir, 'f%04d.png' % f)
        process(a.base, f, out, exp, bl, look, not a.no_denoise)


if __name__ == '__main__':
    main()
