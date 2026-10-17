#!/usr/bin/env python3
"""
Aggregate all results/**/results.json into
  report/summary.md       table + verdicts (also goes to the GitHub Actions summary page)
  report/results.csv      same data for a spreadsheet
  report/contact_sheet.jpg  cut-outs of the same frames for every config (look at it with your eyes!)

There is no ground truth, so quality is measured two ways:
  * agreement (IoU / MAE) against a REFERENCE config = the best model that fits in RAM
  * temporal flicker on burst frames, and "soft_frac" = share of semi-transparent pixels

  python report.py results --samples samples --out report
"""
import argparse, csv, glob, json, os

import cv2
import numpy as np

DEFAULT_REF = ["matting_dc_768x1152_onnx", "matting_dc_1024_onnx", "dynamic_torch|576x1024",
               "lite_dc_onnx|576x1024", "lite_torch|576x1024"]
STRIDES = (2, 3, 4, 6)


def system_of(stem):
    if stem.startswith(("zaitoon", "burst_z")):
        return "zaitoon"
    if stem.startswith(("autopsy", "burst_a")):
        return "autopsy"
    return "other"


def load_all(root):
    rows = []
    for f in sorted(glob.glob(os.path.join(root, "**", "results.json"), recursive=True)):
        d = json.load(open(f))
        base = os.path.dirname(f)
        run_status = d.get("status", "?")
        cfgs = d.get("configs") or []
        if not cfgs:
            rows.append(dict(model=d.get("id", "?"), key=d.get("id", "?"), res="-", prep="-", norm="-", threads=None,
                             status=run_status, dir=base, peak_rss_gb=d.get("peak_rss_gb"), load_s=d.get("load_s")))
        for c in cfgs:
            c = dict(c)
            c.update(model=d.get("id", "?"), dir=base, load_s=d.get("load_s"), cpu=d.get("env", {}).get("cpu", ""))
            if c.get("total_s") is None and c.get("status") == "OK":
                c["status"] = run_status if run_status != "OK" else "INCOMPLETE"
                c["peak_rss_gb"] = c.get("peak_rss_gb") or d.get("peak_rss_gb")
            rows.append(c)
    return rows


def read_masks(c):
    out = {}
    if not c.get("safe"):
        return out
    for p in glob.glob(os.path.join(c["dir"], "masks", c["safe"], "*.png")):
        m = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
        if m is not None:
            out[os.path.splitext(os.path.basename(p))[0]] = m.astype(np.float32) / 255.0
    return out


def agreement(masks, ref):
    res = {}
    for stem, m in masks.items():
        r = ref.get(stem)
        if r is None or r.shape != m.shape:
            continue
        a, b = m >= 0.5, r >= 0.5
        iou = (a & b).sum() / max((a | b).sum(), 1)
        res.setdefault(system_of(stem), []).append((float(np.abs(m - r).mean()), float(iou)))
    return {s: (round(float(np.mean([x[0] for x in v])), 4), round(float(np.mean([x[1] for x in v])), 3)) for s, v in res.items()}


def verdict(c, budget, ram):
    if c.get("total_s") is None:
        st = str(c.get("status"))
        if st == "RUNNING":
            return "KILLED (no result: OS out-of-memory kill or timeout?)"
        return "FAILED: " + st[:60]
    fits = [s for s in STRIDES if c["proj_min"][str(s)] <= budget]
    speed = f"fits at stride {fits[0]}" if fits else f"too slow (> {budget:g} min even at stride {STRIDES[-1]})"
    mem = "RAM ok" if (c.get("peak_rss_gb") or 0) <= ram else f"RAM {c['peak_rss_gb']} GB > {ram:g}"
    return f"{speed}; {mem}"


def contact_sheet(rows, ref_key, samples, path, max_rows=16, cols=6):
    ok = [c for c in rows if c.get("total_s") is not None and c.get("masks")]
    if not ok:
        return False
    ok.sort(key=lambda c: (c["key"] != ref_key, c["total_s"]))
    ok = ok[:max_rows]
    stems = sorted({s for c in ok for s in c["masks"] if not s.startswith("burst_")})
    z = [s for s in stems if system_of(s) == "zaitoon"]
    a = [s for s in stems if system_of(s) == "autopsy"]
    pick = (z[:cols // 2] + a[:cols // 2] + z[cols // 2:] + a[cols // 2:] + stems)[:cols]
    pick = list(dict.fromkeys(pick))[:cols]
    if not pick:
        return False
    cw, ch, lw = 135, 240, 330
    sheet = np.full((ch * (len(ok) + 1), lw + cw * len(pick), 3), 255, np.uint8)
    magenta = np.array([255, 0, 255], np.float32)
    frames = {}
    for s in pick:
        for ext in (".jpg", ".jpeg", ".png", ".webp"):
            f = os.path.join(samples, s + ext)
            if os.path.exists(f):
                frames[s] = cv2.resize(cv2.imread(f), (cw, ch), interpolation=cv2.INTER_AREA)
                break
    cv2.putText(sheet, "ORIGINAL", (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1, cv2.LINE_AA)
    for j, s in enumerate(pick):
        if s in frames:
            sheet[0:ch, lw + j * cw: lw + (j + 1) * cw] = frames[s]
    for i, c in enumerate(ok, start=1):
        y = i * ch
        label = c["key"].replace("|", " ")
        for k, line in enumerate([label[:44], label[44:88], f"{c['total_s']} s/frame  RAM {c.get('peak_rss_gb')} GB"]):
            cv2.putText(sheet, line, (8, y + 24 + 20 * k), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 0), 1, cv2.LINE_AA)
        for j, s in enumerate(pick):
            m = c["masks"].get(s)
            if m is None or s not in frames:
                continue
            m = cv2.resize(m, (cw, ch), interpolation=cv2.INTER_LINEAR)[..., None]
            cut = frames[s].astype(np.float32)[..., ::-1] * m + magenta * (1 - m)  # RGB, magenta shows halos
            sheet[y:y + ch, lw + j * cw: lw + (j + 1) * cw] = cut[..., ::-1].astype(np.uint8)
    cv2.imwrite(path, sheet, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return True


def fmt(v, nd=3):
    return "-" if v is None else (f"{v:.{nd}f}" if isinstance(v, float) else str(v))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results", nargs="?", default="results")
    ap.add_argument("--samples", default="samples")
    ap.add_argument("--out", default="report")
    ap.add_argument("--ref", nargs="+", default=DEFAULT_REF, help="substrings tried in order to pick the reference config")
    ap.add_argument("--budget-min", type=float, default=10.0, help="max minutes of matting per 58 s video")
    ap.add_argument("--ram-gb", type=float, default=3.0, help="max RAM per process (Autopsy runs 2 in parallel)")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    rows = load_all(args.results)
    for c in rows:
        c["masks"] = read_masks(c)
    ref_key, ref_masks = None, {}
    for sub in args.ref:
        cand = [c for c in rows if sub in c["key"] and c.get("total_s") is not None and c["masks"]]
        if cand:
            ref_key, ref_masks = cand[0]["key"], cand[0]["masks"]
            break
    for c in rows:
        c["agree"] = agreement(c["masks"], ref_masks) if ref_masks and c["key"] != ref_key else {}
        c["verdict"] = verdict(c, args.budget_min, args.ram_gb)

    rows.sort(key=lambda c: (c.get("total_s") is None, c.get("total_s") or 0))
    cpu = next((c.get("cpu") for c in rows if c.get("cpu")), "?")

    md = ["# Segmentation benchmark", "",
          f"Runner CPU: `{cpu}`  |  budget: {args.budget_min:g} min of matting per 58 s video, {args.ram_gb:g} GB RAM per process",
          f"Reference for agreement (not ground truth): `{ref_key or 'none found'}`", "",
          "| config | s/frame | min @stride 2 / 4 / 6 | peak GB | load s | cores | flicker | soft | IoU zait / auto | MAE zait / auto | verdict |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    csv_rows = []
    for c in rows:
        pm = c.get("proj_min") or {}
        ag = c.get("agree") or {}
        z, a = ag.get("zaitoon", (None, None)), ag.get("autopsy", (None, None))
        md.append("| {} | {} | {} / {} / {} | {} | {} | {} | {} | {} | {} / {} | {} / {} | {} |".format(
            c["key"].replace("|", " · "), fmt(c.get("total_s")), pm.get("2", "-"), pm.get("4", "-"), pm.get("6", "-"),
            fmt(c.get("peak_rss_gb"), 2), fmt(c.get("load_s"), 1), fmt(c.get("avg_cores"), 2), fmt(c.get("flicker"), 4),
            fmt(c.get("soft_frac"), 3), fmt(z[1]), fmt(a[1]), fmt(z[0], 4), fmt(a[0], 4), c["verdict"]))
        csv_rows.append(dict(key=c["key"], model=c["model"], res=c.get("res"), prep=c.get("prep"), norm=c.get("norm"),
                             threads=c.get("threads"), status=c.get("status"), total_s=c.get("total_s"),
                             infer_s=c.get("infer_s"), first_s=c.get("first_s"), p95_s=c.get("p95_s"),
                             peak_rss_gb=c.get("peak_rss_gb"), load_s=c.get("load_s"), avg_cores=c.get("avg_cores"),
                             flicker=c.get("flicker"), soft_frac=c.get("soft_frac"),
                             proj_min_s2=pm.get("2"), proj_min_s3=pm.get("3"), proj_min_s4=pm.get("4"), proj_min_s6=pm.get("6"),
                             iou_zaitoon=z[1], iou_autopsy=a[1], mae_zaitoon=z[0], mae_autopsy=a[0], verdict=c["verdict"]))
    md += ["", "How to read: *s/frame* = pre + inference + post (incl. resize to 1080x1920), warm-up frame excluded. "
           "*min @stride N* = matting time for a 58 s / 30 fps clip when only every Nth frame is inferred. "
           "*flicker* = mean change between consecutive frames (lower = steadier). *soft* = share of semi-transparent pixels. "
           "IoU/MAE compare with the reference, so they say 'similar to the best model', not 'correct'. "
           "Judge edges on contact_sheet.jpg (magenta background reveals halos).", ""]
    open(os.path.join(args.out, "summary.md"), "w").write("\n".join(md))
    if csv_rows:
        with open(os.path.join(args.out, "results.csv"), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(csv_rows[0].keys()))
            w.writeheader()
            w.writerows(csv_rows)
    made = contact_sheet(rows, ref_key, args.samples, os.path.join(args.out, "contact_sheet.jpg"))
    print("\n".join(md))
    print(f"\nwrote {args.out}/summary.md, results.csv" + (", contact_sheet.jpg" if made else ""))


if __name__ == "__main__":
    main()
