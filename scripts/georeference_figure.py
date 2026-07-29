#!/usr/bin/env python3
"""Georeference a report/EIS figure with a satellite-imagery basemap and read
lat/lon off it (Georeference SOP, docs/sops/georeference.md; workflows §10).

This is the LAST rung of the SOP's decision ladder — use it only after (0) the
built facility can't be located in mapping services/OSM, (1) no published
coordinates exist, and (2) the figure has no lat/lon graticule to interpolate.

Three subcommands, run from scripts/ with a per-figure --workdir:

  # 1. Fetch an Esri World Imagery reference mosaic covering the figure's area
  #    (bbox from eyeballing the figure; generous margins are cheap)
  python georeference_figure.py fetch --workdir W --bbox LAT_S LAT_N LON_W LON_E [--zoom 15]

  # 2. Fit figure->world: seed with >=2 rough correspondences (figure pixel x,y
  #    of a recognizable feature + its lat,lon read off any mapping service;
  #    +/-10 px / +/-100 m is fine), then automatic coastline patch matching
  #    refines to a closed-form similarity fit with outlier trim + RMSE.
  python georeference_figure.py fit --workdir W --fig FIG.png \
      --seed FX,FY,LAT,LON --seed FX,FY,LAT,LON [--map-bottom N] [--seed-only]

  # 3. Read a point: explicit pixel, or auto-detect a colored marker
  python georeference_figure.py point --workdir W --fig FIG.png --at FX,FY
  python georeference_figure.py point --workdir W --fig FIG.png --detect cyan

Method notes (the hard-won bits — see the SOP for the full pitfall list):
- Match satellite-to-satellite. The reference is Esri World Imagery, NOT an OSM
  cartographic render: cross-modal NCC has a flat correlation surface and is why
  brute-force searches crawl and misconverge.
- Never grid-search the 4-D transform. Two rough seed points pin scale/rotation/
  translation; local +/-N px NCC around each auto-GCP does the rest.
- Auto-GCPs sit on blueness gradients (coastlines/rivers). For line-drawn (non-
  imagery) figures NCC matching fails: give >=4 careful --seed pairs + --seed-only.
- 'point' extrapolates the similarity fit, so leave-one-out spread is reported;
  an offshore marker's accuracy is entirely the global fit's.
- 'point' writes THREE overlays: verify_point.png (satellite crop), verify_full.png
  (whole mosaic), verify_fig.png (the derived point + lat/lon marked ON the source
  figure itself). Viewing all three is mandatory and they ship with the deliverable.
- The fitted m/px is printed: cross-check it against the figure's scale bar, and
  the result against any documented distance ("N miles offshore of X").

Requires numpy, PIL, scipy (all already used by this repo). Read-only; network
access only in `fetch` (Esri tile endpoint).
"""
import argparse, json, math, os, sys
import numpy as np
from PIL import Image, ImageDraw

TILE_URL = 'https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'
MARKER_RULES = {  # loose RGB gates for common figure marker colors
    'cyan':    lambda R,G,B: (G>170)&(B>170)&(R<140),
    'green':   lambda R,G,B: (G>170)&(R<140)&(B<140),
    'red':     lambda R,G,B: (R>170)&(G<120)&(B<120),
    'magenta': lambda R,G,B: (R>170)&(B>170)&(G<120),
    'yellow':  lambda R,G,B: (R>190)&(G>170)&(B<120),
}

def deg2tile(lat, lon, z):
    n = 2**z
    x = (lon+180.0)/360.0*n
    y = (1.0-math.log(math.tan(math.radians(lat))+1/math.cos(math.radians(lat)))/math.pi)/2.0*n
    return x, y

class Ref:
    def __init__(self, workdir):
        m = json.load(open(os.path.join(workdir, 'ref_meta.json')))
        self.z, self.x0, self.y0 = m['zoom'], m['x0'], m['y0']
        self.n = 2**self.z
        self.center_lat = m['center_lat']
        self.mpp = 156543.034*math.cos(math.radians(self.center_lat))/self.n  # ground m per ref px
    def px2lonlat(self, px, py):
        X = (self.x0*256+px)/256.0; Y = (self.y0*256+py)/256.0
        return X/self.n*360.0-180.0, math.degrees(math.atan(math.sinh(math.pi*(1-2*Y/self.n))))
    def lonlat2px(self, lon, lat):
        x, y = deg2tile(lat, lon, self.z)
        return x*256-self.x0*256, y*256-self.y0*256

def cmd_fetch(a):
    import urllib.request, concurrent.futures
    lat_s, lat_n, lon_w, lon_e = a.bbox
    if lat_s >= lat_n or lon_w >= lon_e:
        sys.exit('bbox must be LAT_S LAT_N LON_W LON_E with S<N and W<E')
    os.makedirs(a.workdir, exist_ok=True)
    tdir = os.path.join(a.workdir, 'tiles'); os.makedirs(tdir, exist_ok=True)
    x0f, y0f = deg2tile(lat_n, lon_w, a.zoom); x1f, y1f = deg2tile(lat_s, lon_e, a.zoom)
    X0, Y0, X1, Y1 = int(x0f), int(y0f), int(x1f), int(y1f)
    count = (X1-X0+1)*(Y1-Y0+1)
    print(f'zoom {a.zoom}: {count} tiles, mosaic {(X1-X0+1)*256}x{(Y1-Y0+1)*256} px')
    if count > 600:
        sys.exit('>600 tiles — lower --zoom or shrink the bbox')
    def get(xy):
        x, y = xy
        p = os.path.join(tdir, f'{a.zoom}_{x}_{y}.jpg')
        if os.path.exists(p) and os.path.getsize(p) > 0: return
        req = urllib.request.Request(TILE_URL.format(z=a.zoom, x=x, y=y),
                                     headers={'User-Agent': 'Mozilla/5.0'})
        open(p, 'wb').write(urllib.request.urlopen(req, timeout=30).read())
    jobs = [(x, y) for x in range(X0, X1+1) for y in range(Y0, Y1+1)]
    with concurrent.futures.ThreadPoolExecutor(8) as ex:
        list(ex.map(get, jobs))
    mosaic = Image.new('RGB', ((X1-X0+1)*256, (Y1-Y0+1)*256))
    for x in range(X0, X1+1):
        for y in range(Y0, Y1+1):
            mosaic.paste(Image.open(os.path.join(tdir, f'{a.zoom}_{x}_{y}.jpg')),
                         ((x-X0)*256, (y-Y0)*256))
    mosaic.save(os.path.join(a.workdir, 'ref.png'))
    json.dump({'zoom': a.zoom, 'x0': X0, 'y0': Y0, 'x1': X1, 'y1': Y1,
               'center_lat': (lat_s+lat_n)/2, 'bbox': a.bbox},
              open(os.path.join(a.workdir, 'ref_meta.json'), 'w'), indent=1)
    ref = Ref(a.workdir)
    print(f'ref.png saved; {ref.mpp:.2f} ground m per ref px')
    ext = max((X1-X0+1)*256, (Y1-Y0+1)*256)*ref.mpp/1000
    if ext > 40:
        print(f'WARNING: extent ~{ext:.0f} km — similarity-fit projection error grows; '
              'consider splitting the figure or a tighter bbox')

def blueness(a):
    return a[:, :, 2]/(a.sum(axis=2)+1e-6)

def fit_sim(F, R):
    """Closed-form 2-D similarity F->R (least squares; exact for 2 points)."""
    fm, rm = F.mean(axis=0), R.mean(axis=0)
    Fc, Rc = F-fm, R-rm
    a = (Fc[:, 0]*Rc[:, 0]+Fc[:, 1]*Rc[:, 1]).sum()
    b = (Fc[:, 0]*Rc[:, 1]-Fc[:, 1]*Rc[:, 0]).sum()
    d = (Fc*Fc).sum()
    A, B = a/d, b/d
    s, rot = math.hypot(A, B), math.atan2(B, A)
    t = rm-np.array([A*fm[0]-B*fm[1], B*fm[0]+A*fm[1]])
    return s, t[0], t[1], rot

def transform(pts, s, tx, ty, rot):
    cr, sr = math.cos(rot), math.sin(rot)
    x, y = pts[:, 0], pts[:, 1]
    return np.stack([tx+s*(cr*x-sr*y), ty+s*(sr*x+cr*y)], axis=1)

def load_fig(path, map_bottom):
    fig = np.asarray(Image.open(path).convert('RGB')).astype(float)
    return fig, (map_bottom if map_bottom else fig.shape[0])

def cmd_fit(a):
    from scipy import ndimage
    ref = Ref(a.workdir)
    fig, bot = load_fig(a.fig, a.map_bottom)
    rb = blueness(np.asarray(Image.open(os.path.join(a.workdir, 'ref.png')).convert('RGB')).astype(float))
    fb = blueness(fig)
    seeds = []
    for s in a.seed:
        fx, fy, lat, lon = map(float, s.split(','))
        seeds.append((fx, fy) + ref.lonlat2px(lon, lat))
    seeds = np.array(seeds)
    if len(seeds) < 2:
        sys.exit('need >=2 --seed FX,FY,LAT,LON correspondences')
    p0 = fit_sim(seeds[:, 0:2], seeds[:, 2:4])
    print('seed fit: %.2f m/figpx, rot %.2f deg' % (p0[0]*ref.mpp, math.degrees(p0[3])))

    F, R = seeds[:, 0:2], seeds[:, 2:4]
    if not a.seed_only:
        # auto-GCPs on blueness gradients (coastlines), masked to imagery pixels
        mx, mn = fig.max(axis=2), fig.min(axis=2)
        valid = (mx-mn < 55) & (mn < 185) & (mx > 25)
        valid[bot:, :] = False; valid[:8, :] = False; valid[:, :8] = False; valid[:, -8:] = False
        valid = ndimage.binary_erosion(valid, np.ones((9, 9)))
        g = ndimage.gaussian_gradient_magnitude(fb, 2.0); g[~valid] = 0
        HP = a.patch
        cands, gg = [], g.copy()
        while len(cands) < a.max_gcps:
            i = np.argmax(gg); y, x = np.unravel_index(i, gg.shape)
            if gg[y, x] <= 0: break
            if HP < x < fig.shape[1]-HP and HP < y < bot-HP and \
               valid[y-HP:y+HP+1, x-HP:x+HP+1].mean() > 0.85:
                cands.append((x, y))
            gg[max(0, y-2*HP):y+2*HP, max(0, x-2*HP):x+2*HP] = 0

        def sample(rx, ry):
            x0 = np.clip(np.floor(rx).astype(int), 0, rb.shape[1]-2)
            y0 = np.clip(np.floor(ry).astype(int), 0, rb.shape[0]-2)
            wx, wy = rx-x0, ry-y0
            return (rb[y0, x0]*(1-wx)*(1-wy)+rb[y0, x0+1]*wx*(1-wy)
                    + rb[y0+1, x0]*(1-wx)*wy+rb[y0+1, x0+1]*wx*wy)

        W = a.search
        mF, mR = [], []
        for (cx, cy) in cands:
            yy, xx = np.mgrid[cy-HP:cy+HP+1, cx-HP:cx+HP+1]
            pv = fb[yy, xx].ravel(); pvc = pv-pv.mean()
            if pvc.std() < 0.004: continue
            base = transform(np.stack([xx.ravel(), yy.ravel()], axis=1).astype(float), *p0)
            best, scores = (-2, 0, 0), {}
            for dy in range(-W, W+1):
                for dx in range(-W, W+1):
                    v = sample(base[:, 0]+dx, base[:, 1]+dy)
                    vc = v-v.mean(); den = np.sqrt((pvc*pvc).sum()*(vc*vc).sum())
                    sc = (pvc*vc).sum()/den if den > 0 else -1
                    scores[(dx, dy)] = sc
                    if sc > best[0]: best = (sc, dx, dy)
            sc, dx, dy = best
            if sc < a.min_ncc or abs(dx) >= W or abs(dy) >= W: continue
            fx = 0.5*(scores[(dx-1, dy)]-scores[(dx+1, dy)])/(scores[(dx-1, dy)]-2*sc+scores[(dx+1, dy)]+1e-12)
            fy = 0.5*(scores[(dx, dy-1)]-scores[(dx, dy+1)])/(scores[(dx, dy-1)]-2*sc+scores[(dx, dy+1)]+1e-12)
            pred = transform(np.array([[cx, cy]], float), *p0)[0]
            mF.append((cx, cy)); mR.append((pred[0]+dx+np.clip(fx, -1, 1), pred[1]+dy+np.clip(fy, -1, 1)))
            print('GCP fig(%4d,%4d) offset (%+5.1f,%+5.1f) ncc %.3f' % (cx, cy, dx+fx, dy+fy, sc))
        if len(mF) >= 4:
            F, R = np.array(mF), np.array(mR)   # auto-GCPs replace the rough seeds
        else:
            print('WARNING: only %d auto-GCPs matched — falling back to the seed pairs '
                  '(line-drawn figure? give more/better seeds, or --seed-only)' % len(mF))

    for _ in range(3):  # outlier-trimmed refit
        p = fit_sim(F, R)
        err = np.hypot(*(transform(F, *p)-R).T)
        keep = err < max(2.0, 2.5*np.median(err))
        if keep.all() or keep.sum() < 3: break
        F, R = F[keep], R[keep]
    p = fit_sim(F, R)
    err = np.hypot(*(transform(F, *p)-R).T)
    rmse_m = float(np.sqrt((err**2).mean())*ref.mpp)
    print('\nfit on %d GCPs: %.2f m/figpx (cross-check the scale bar), rot %.3f deg, RMSE %.1f m'
          % (len(F), p[0]*ref.mpp, math.degrees(p[3]), rmse_m))
    json.dump({'s': p[0], 'tx': p[1], 'ty': p[2], 'rot': p[3], 'rmse_m': rmse_m,
               'gcps_fig': np.asarray(F).tolist(), 'gcps_ref': np.asarray(R).tolist(),
               'fig': os.path.abspath(a.fig), 'seed_only': bool(a.seed_only)},
              open(os.path.join(a.workdir, 'fit.json'), 'w'), indent=1)
    print('fit.json saved')

def cmd_point(a):
    ref = Ref(a.workdir)
    fit = json.load(open(os.path.join(a.workdir, 'fit.json')))
    p = (fit['s'], fit['tx'], fit['ty'], fit['rot'])
    F, R = np.array(fit['gcps_fig']), np.array(fit['gcps_ref'])
    fig, bot = load_fig(a.fig, a.map_bottom)
    pts = []
    for at in a.at or []:
        parts = at.split(','); pts.append((float(parts[0]), float(parts[1]),
                                           parts[2] if len(parts) > 2 else 'point'))
    if a.detect:
        from scipy import ndimage
        Rc, Gc, Bc = fig[:, :, 0], fig[:, :, 1], fig[:, :, 2]
        m = MARKER_RULES[a.detect](Rc, Gc, Bc)
        m[bot:, :] = False
        lab, nc = ndimage.label(m)
        best = None
        for i in range(1, nc+1):
            ys, xs = np.nonzero(lab == i)
            if len(xs) < 25: continue
            w, h = xs.max()-xs.min()+1, ys.max()-ys.min()+1
            if not (0.4 < w/h < 2.5): continue
            if best is None or len(xs) > best[0]:
                best = (len(xs), (xs.min()+xs.max())/2, (ys.min()+ys.max())/2, w, h)
        if best is None:
            sys.exit(f'no {a.detect} marker blob found (>=25 px, squarish)')
        print('detected %s marker: fig(%.1f, %.1f), %dx%d px = %.0fx%.0f ground m'
              % (a.detect, best[1], best[2], best[3], best[4],
                 best[3]*p[0]*ref.mpp, best[4]*p[0]*ref.mpp))
        pts.append((best[1], best[2], f'{a.detect}-marker'))
    if not pts:
        sys.exit('give --at FX,FY[,label] and/or --detect COLOR')

    out = Image.open(os.path.join(a.workdir, 'ref.png')).convert('RGB')
    d = ImageDraw.Draw(out)
    figimg = Image.open(a.fig).convert('RGB')
    df = ImageDraw.Draw(figimg)
    for (rx, ry) in R:
        d.ellipse([rx-6, ry-6, rx+6, ry+6], outline=(0, 255, 0), width=2)
    for (fx, fy) in F:
        df.ellipse([fx-5, fy-5, fx+5, fy+5], outline=(0, 255, 0), width=2)
    for (fx, fy, label) in pts:
        q = transform(np.array([[fx, fy]]), *p)[0]
        lon, lat = ref.px2lonlat(*q)
        loo = []
        for i in range(len(F)):
            idx = [j for j in range(len(F)) if j != i]
            loo.append(transform(np.array([[fx, fy]]), *fit_sim(F[idx], R[idx]))[0])
        spread = np.hypot(*(np.array(loo)-q).T)*ref.mpp
        print('%-14s lat %.6f  lon %.6f   (fit RMSE %.1f m; leave-one-out at point: '
              'rms %.1f m, max %.1f m)' % (label, lat, lon, fit['rmse_m'],
                                           float(np.sqrt((spread**2).mean())), float(spread.max())))
        x, y = q
        d.line([(x-14, y), (x+14, y)], fill=(255, 0, 0), width=3)
        d.line([(x, y-14), (x, y+14)], fill=(255, 0, 0), width=3)
        d.ellipse([x-30, y-30, x+30, y+30], outline=(255, 255, 0), width=3)
        out.crop((int(x)-320, int(y)-320, int(x)+320, int(y)+320)).save(
            os.path.join(a.workdir, 'verify_point.png'))
        # figure-side overlay: the same derived point marked ON the source figure
        # (round-trips the fit; a marker landing off the figure's own symbol = bad fit)
        df.line([(fx-12, fy), (fx+12, fy)], fill=(255, 0, 0), width=2)
        df.line([(fx, fy-12), (fx, fy+12)], fill=(255, 0, 0), width=2)
        df.ellipse([fx-24, fy-24, fx+24, fy+24], outline=(255, 0, 0), width=2)
        df.text((fx+28, fy-8), '%s  %.6f, %.6f' % (label, lat, lon), fill=(255, 0, 0))
    full = out.copy(); full.thumbnail((1400, 1400))
    full.save(os.path.join(a.workdir, 'verify_full.png'))
    figimg.save(os.path.join(a.workdir, 'verify_fig.png'))
    print('verify_point.png / verify_full.png / verify_fig.png saved — VIEW ALL THREE '
          '(verification is mandatory, SOP §4; the overlays ship with the deliverable)')

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    f = sub.add_parser('fetch', help='download Esri World Imagery mosaic for a bbox')
    f.add_argument('--workdir', required=True)
    f.add_argument('--bbox', nargs=4, type=float, required=True, metavar=('LAT_S', 'LAT_N', 'LON_W', 'LON_E'))
    f.add_argument('--zoom', type=int, default=15)
    f.set_defaults(func=cmd_fetch)
    t = sub.add_parser('fit', help='fit figure->world similarity from seeds + auto-GCPs')
    t.add_argument('--workdir', required=True)
    t.add_argument('--fig', required=True)
    t.add_argument('--seed', action='append', default=[], metavar='FX,FY,LAT,LON')
    t.add_argument('--map-bottom', type=int, default=0, help='first figure row BELOW the map area (mask title block/legend)')
    t.add_argument('--search', type=int, default=20, help='local NCC window, +/- ref px')
    t.add_argument('--patch', type=int, default=34, help='GCP patch half-size, fig px')
    t.add_argument('--max-gcps', type=int, default=14)
    t.add_argument('--min-ncc', type=float, default=0.55)
    t.add_argument('--seed-only', action='store_true', help='fit on the seed pairs only (line-drawn figures)')
    t.set_defaults(func=cmd_fit)
    q = sub.add_parser('point', help='read lat/lon for a figure pixel or detected marker')
    q.add_argument('--workdir', required=True)
    q.add_argument('--fig', required=True)
    q.add_argument('--at', action='append', metavar='FX,FY[,label]')
    q.add_argument('--detect', choices=sorted(MARKER_RULES))
    q.add_argument('--map-bottom', type=int, default=0)
    q.set_defaults(func=cmd_point)
    a = ap.parse_args()
    a.func(a)

if __name__ == '__main__':
    main()
