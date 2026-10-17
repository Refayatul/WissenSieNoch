#!/usr/bin/env python3
"""
CPU benchmark of segmentation / matting models on 9:16 video frames (Zaitoon + Autopsy).

One run = one model id. For every resolution x prep it measures:
  load time, sec/frame (pre + infer + post), peak RAM, CPU cores used,
  temporal flicker (burst frames), edge softness, and projects the matting time for a
  58 s clip (1740 frames) at several strides. Masks are saved so report.py can compare
  every model against a reference model (there is no ground truth).

  python bench.py --list
  python bench.py --verify                      # check that every download URL / HF repo exists
  python bench.py --id lite_onnx --threads 2 --out results/lite_onnx
  python bench.py --id lite_torch --res 448x800 576x1024 --preps stretch
"""
import argparse, glob, hashlib, json, os, platform, re, shutil, sys, threading, time, traceback
import urllib.request

import cv2
import numpy as np
import psutil

REL = "https://github.com/ZhengPeng7/BiRefNet/releases/download/v1/"
REMBG = "https://github.com/danielgatis/rembg/releases/download/v0.0.0/"
IMAGENET = ((0.485, 0.456, 0.406), (0.229, 0.224, 0.225))
ISNET = ((0.485, 0.456, 0.406), (1.0, 1.0, 1.0))
UNIT = ((0.0, 0.0, 0.0), (1.0, 1.0, 1.0))  # only /255, no mean/std (what production does today)

# kind=onnx : ONNX file. "stock" exports have a fixed input size AND a huge RAM peak (BiRefNet's deformable
#             convolutions are written as GatherND lattices). "dc" exports use native ONNX DeformConv
#             (needs onnxruntime >= 1.25) and are small + fast, but they are community re-exports of the
#             official weights -> pinned by sha256 where known, and compared against a reference by report.py.
# kind=torch: HuggingFace weights through transformers, any resolution (multiple of `mult`).
HF_SENTY = "https://huggingface.co/senty-au/BiRefNet_lite-ONNX-dynamic/resolve/main/onnx/model.onnx"
HF_GRAZ = "https://huggingface.co/Grazier/birefnet-matting-deformconv/resolve/main/"
MODELS = {
    # ---- native DeformConv ONNX (community re-exports of official BiRefNet weights) ----
    "lite_dc_onnx": dict(kind="onnx", url=HF_SENTY, sha256="1e0da42f0fde010e32e938bad388457ecefe35806fde9d923421997861ae9391",
                         norm=IMAGENET, out=0, res="512x512", mult=64,
                         note="BiRefNet lite (Swin-T) general, native DeformConv, dynamic size (senty-au)"),
    "matting_dc_768x1152_onnx": dict(kind="onnx", url=HF_GRAZ + "birefnet_matting_deformconv_768x1152.onnx", norm=IMAGENET, out=0,
                                     res="768x1152", mult=64, note="BiRefNet Swin-L MATTING, native DeformConv, 768x1152 (Grazier) - reference"),
    "matting_dc_1024_onnx": dict(kind="onnx", url=HF_GRAZ + "birefnet_matting_deformconv.onnx", norm=IMAGENET, out=0,
                                 res="1024x1024", mult=64, note="same, 1024x1024"),
    # ---- official stock ONNX (GitHub release v1): static size, very high RAM ----
    "lite_onnx": dict(kind="onnx", url=REL + "BiRefNet-general-bb_swin_v1_tiny-epoch_232.onnx", norm=IMAGENET, out=-1,
                      res="1024x1024", mult=64, note="STOCK lite (Swin-T) 1024. >= 4 GB RSS measured (10.5 GB reported upstream)"),
    "general512_fp16_onnx": dict(kind="onnx", url=REL + "BiRefNet-general-resolution_512x512-fp16-epoch_216.onnx", norm=IMAGENET,
                                 out=-1, res="512x512", mult=64, note="STOCK Swin-L general, 512, FP16 weights"),
    "general_onnx": dict(kind="onnx", url=REL + "BiRefNet-general-epoch_244.onnx", norm=IMAGENET, out=-1,
                         res="1024x1024", mult=64, note="STOCK Swin-L general 1024 (expect OOM)"),
    "matting_onnx": dict(kind="onnx", url=REL + "BiRefNet-matting-epoch_100.onnx", norm=IMAGENET, out=-1,
                         res="1024x1024", mult=64, note="STOCK Swin-L matting 1024 (expect OOM)"),
    "hr_matting_onnx": dict(kind="onnx", url=REL + "BiRefNet_HR-matting-epoch_135.onnx", norm=IMAGENET, out=-1,
                            res="2048x2048", mult=64, note="CURRENT PRODUCTION model (stock, static 2048)"),
    # ---- other light models (baselines) ----
    "u2netp_onnx": dict(kind="onnx", url=REMBG + "u2netp.onnx", norm=IMAGENET, out=0, res="320x320", mult=32,
                        note="U2-Net-P, tiny, low-quality floor"),
    "isnet_onnx": dict(kind="onnx", url=REMBG + "isnet-general-use.onnx", norm=ISNET, out=0, res="1024x1024", mult=32,
                       note="IS-Net general use (DIS), good thin structures"),
    # ---- BiRefNet, PyTorch via HuggingFace (any resolution) ----
    "lite_torch": dict(kind="torch", repo="zhengpeng7/BiRefNet_lite", norm=IMAGENET, res="1024x1024", mult=64,
                       note="BiRefNet lite (Swin-T), PyTorch eager"),
    "lite_matting_torch": dict(kind="torch", repo="zhengpeng7/BiRefNet_lite-matting", norm=IMAGENET, res="1024x1024", mult=64,
                               note="BiRefNet lite matting (--verify tells if this repo exists)"),
    "dynamic_torch": dict(kind="torch", repo="zhengpeng7/BiRefNet_dynamic", norm=IMAGENET, res="1024x1024", mult=64,
                          note="BiRefNet Swin-L trained on 256..2304 px"),
    "general_torch": dict(kind="torch", repo="zhengpeng7/BiRefNet", norm=IMAGENET, res="1024x1024", mult=64,
                          note="BiRefNet Swin-L general"),
}
FRAMES_58S = 58 * 30
STRIDES = (2, 3, 4, 6)
PREVIEW_W = 270

RESULT = {}
STATE = {"peak": 0, "cpu": [], "stop": False}
OUT_FILE = None


# --------------------------------------------------------------------------- utils
def parse_res(s, mult=32):
    w, h = s.lower().split("x")
    w, h = int(w), int(h)
    if w % mult or h % mult:
        raise SystemExit(f"--res {s}: both sides must be multiples of {mult} for this model (format is WIDTHxHEIGHT)")
    return w, h


def dump():
    if OUT_FILE:
        tmp = OUT_FILE + ".tmp"
        with open(tmp, "w") as f:
            json.dump(RESULT, f, indent=1)
        os.replace(tmp, OUT_FILE)


def env_info(args):
    cpu = platform.processor()
    try:
        cpu = next(l.split(":", 1)[1].strip() for l in open("/proc/cpuinfo") if l.startswith("model name"))
    except Exception:
        pass
    info = dict(cpu=cpu, logical_cores=os.cpu_count(), ram_gb=round(psutil.virtual_memory().total / 1e9, 1),
                python=platform.python_version(), threads=args.threads)
    try:
        import onnxruntime as ort
        info["onnxruntime"] = ort.__version__
    except Exception:
        pass
    try:
        import torch
        info["torch"] = torch.__version__
    except Exception:
        pass
    return info


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(url, dest, sha256=None):
    if os.path.exists(dest) and os.path.getsize(dest) > 1_000_000:
        return dest
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".part"
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "seg-bench/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r, open(tmp, "wb") as f:
                shutil.copyfileobj(r, f, 1 << 20)
            if sha256 and sha256_of(tmp) != sha256:
                os.remove(tmp)
                raise RuntimeError(f"sha256 mismatch for {url} (file changed upstream?)")
            os.replace(tmp, dest)
            return dest
        except Exception as e:
            print(f"download attempt {attempt + 1} failed: {e}", file=sys.stderr)
            if "sha256 mismatch" in str(e):
                raise
            time.sleep(3)
    raise RuntimeError(f"download failed: {url}")


def verify():
    ok_all = True
    for k, m in MODELS.items():
        if m["kind"] == "onnx":
            try:
                req = urllib.request.Request(m["url"], headers={"Range": "bytes=0-0", "User-Agent": "seg-bench/1.0"})
                with urllib.request.urlopen(req, timeout=30) as r:
                    rng = r.headers.get("Content-Range", "")
                    size = int(rng.split("/")[-1]) / 1e6 if "/" in rng else float(r.headers.get("Content-Length", 0)) / 1e6
                print(f"OK       {k:22s} {size:8.1f} MB  {m['url']}")
            except Exception as e:
                ok_all = False
                print(f"MISSING  {k:22s} {e}  {m['url']}")
        else:
            try:
                from huggingface_hub import HfApi
                HfApi().model_info(m["repo"])
                print(f"OK       {k:22s} HF repo {m['repo']}")
            except Exception as e:
                ok_all = False
                print(f"MISSING  {k:22s} HF repo {m['repo']} ({type(e).__name__})")
    return ok_all


def load_frames(d, n_stills, n_groups, per_group):
    """Deterministic selection: smaller --frames is always a prefix of a bigger one,
    so heavy reference models and light models share frames."""
    exts = ("*.jpg", "*.jpeg", "*.png", "*.webp")
    files = sorted(sum((glob.glob(os.path.join(d, e)) for e in exts), []))
    h = lambda p: hashlib.md5(os.path.basename(p).encode()).hexdigest()
    stills = sorted([f for f in files if not os.path.basename(f).startswith("burst_")], key=h)[:n_stills]
    groups = {}
    for f in files:
        b = os.path.basename(f)
        if b.startswith("burst_"):
            groups.setdefault(b.split("_")[1], []).append(f)
    out = [(os.path.splitext(os.path.basename(f))[0], f, None) for f in stills]
    for g in sorted(groups, key=lambda g: hashlib.md5(g.encode()).hexdigest())[:n_groups]:
        for f in sorted(groups[g])[:per_group]:
            out.append((os.path.splitext(os.path.basename(f))[0], f, g))
    return out


# --------------------------------------------------------------------- pre / post
def preprocess(rgb, W, H, prep, norm, dtype):
    h0, w0 = rgb.shape[:2]
    if prep == "stretch":  # what the BiRefNet authors do: plain resize to the model size
        im = cv2.resize(rgb, (W, H), interpolation=cv2.INTER_LINEAR)
        box = (0, 0, W, H)
    else:  # "letterbox": same geometry as the production code (zero padded square canvas)
        s = min(W / w0, H / h0)
        lw, lh = max(1, round(w0 * s)), max(1, round(h0 * s))
        px, py = (W - lw) // 2, (H - lh) // 2
        im = np.zeros((H, W, 3), np.uint8)
        im[py:py + lh, px:px + lw] = cv2.resize(rgb, (lw, lh), interpolation=cv2.INTER_LINEAR)
        box = (px, py, lw, lh)
    x = im.astype(np.float32) / 255.0
    mean, std = norm
    x = (x - np.array(mean, np.float32)) / np.array(std, np.float32)
    x = np.ascontiguousarray(x.transpose(2, 0, 1)[None]).astype(dtype, copy=False)
    return x, box


def to_prob(out):
    p = np.asarray(out, dtype=np.float32)
    while p.ndim > 2:
        p = p[0]
    if p.min() < 0.0 or p.max() > 1.0001:  # raw logits -> sigmoid
        p = 1.0 / (1.0 + np.exp(-np.clip(p, -30, 30)))
    return p


def crop_content(p, box, W, H, prep):
    if prep != "letterbox":
        return p
    px, py, lw, lh = box
    sx, sy = p.shape[1] / W, p.shape[0] / H
    y0, y1 = int(py * sy), max(int(py * sy) + 1, int((py + lh) * sy))
    x0, x1 = int(px * sx), max(int(px * sx) + 1, int((px + lw) * sx))
    return p[y0:y1, x0:x1]


# --------------------------------------------------------------------- backends
def make_onnx_runner(path, m, args):
    import onnxruntime as ort
    so = ort.SessionOptions()
    so.intra_op_num_threads = args.threads
    so.inter_op_num_threads = 1
    so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    sess = ort.InferenceSession(path, so, providers=["CPUExecutionProvider"])
    inp = sess.get_inputs()[0]
    dtype = np.float16 if "float16" in inp.type else np.float32
    shp = inp.shape  # [N, 3, H, W]
    native = (shp[3], shp[2]) if isinstance(shp[2], int) and isinstance(shp[3], int) else None
    idx = m["out"]

    def run(x):
        return sess.run(None, {inp.name: x})[idx]

    return run, native, dtype


def make_torch_runner(m, args):
    import torch
    torch.set_num_threads(args.threads)
    from transformers import AutoModelForImageSegmentation
    try:
        model = AutoModelForImageSegmentation.from_pretrained(m["repo"], trust_remote_code=True)
    except Exception as e:  # known meta-tensor problems with some transformers versions
        print(f"load failed ({type(e).__name__}: {str(e)[:200]}); retrying with low_cpu_mem_usage=False", file=sys.stderr)
        model = AutoModelForImageSegmentation.from_pretrained(m["repo"], trust_remote_code=True, low_cpu_mem_usage=False)
    model.eval().float()

    def run(x):
        with torch.inference_mode():
            out = model(torch.from_numpy(x))
        if isinstance(out, (list, tuple)):
            out = out[-1]
        return out.float().cpu().numpy()

    return run, None, np.float32


# --------------------------------------------------------------------- one config
def run_config(args, runner, dtype, W, H, prep, norm_name, norm, frames, out_dir):
    key = "|".join([args.id, f"{W}x{H}", prep, norm_name, f"t{args.threads}"])
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", key)
    mdir = os.path.join(out_dir, "masks", safe)
    os.makedirs(mdir, exist_ok=True)
    cfg = dict(key=key, safe=safe, res=f"{W}x{H}", prep=prep, norm=norm_name, threads=args.threads, status="OK")
    RESULT["configs"].append(cfg)
    STATE["peak"] = psutil.Process().memory_info().rss
    STATE["cpu"].clear()
    pre, inf, post, soft, cov, flick, last = [], [], [], [], [], [], {}
    t_start = time.time()
    try:
        for i, (stem, path, grp) in enumerate(frames):
            if i >= 2 and time.time() - t_start > args.max_seconds:
                break
            bgr = cv2.imread(path)
            if bgr is None:
                continue
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            h0, w0 = rgb.shape[:2]
            t0 = time.perf_counter()
            x, box = preprocess(rgb, W, H, prep, norm, dtype)
            t1 = time.perf_counter()
            out = runner(x)
            t2 = time.perf_counter()
            content = crop_content(to_prob(out), box, W, H, prep)
            _ = (cv2.resize(content, (w0, h0), interpolation=cv2.INTER_LINEAR) * 255).astype(np.uint8)  # as production
            t3 = time.perf_counter()
            pre.append(t1 - t0); inf.append(t2 - t1); post.append(t3 - t2)
            prev = cv2.resize(content, (PREVIEW_W, round(PREVIEW_W * h0 / w0)), interpolation=cv2.INTER_AREA)
            cv2.imwrite(os.path.join(mdir, stem + ".png"), (prev * 255).round().astype(np.uint8))
            if i > 0 or len(frames) == 1:
                soft.append(float(((prev > 0.05) & (prev < 0.95)).mean()))
                cov.append(float((prev > 0.5).mean()))
            if grp is not None:
                if grp in last:
                    flick.append(float(np.abs(prev - last[grp]).mean()))
                last[grp] = prev
        n = len(inf)
        if n == 0:
            raise RuntimeError("no frames processed")
        first = pre[0] + inf[0] + post[0]
        sl = slice(1, None) if n > 1 else slice(0, None)
        tot = np.array(pre[sl]) + np.array(inf[sl]) + np.array(post[sl])
        total_s = float(tot.mean())
        cfg.update(
            n_frames=int(len(tot)), first_s=round(first, 3), pre_s=round(float(np.mean(pre[sl])), 3),
            infer_s=round(float(np.mean(inf[sl])), 3), post_s=round(float(np.mean(post[sl])), 3),
            total_s=round(total_s, 3), p95_s=round(float(np.percentile(tot, 95)), 3),
            peak_rss_gb=round(STATE["peak"] / 1e9, 2),
            avg_cores=round(float(np.mean(STATE["cpu"])) / 100, 2) if STATE["cpu"] else None,
            flicker=round(float(np.mean(flick)), 4) if flick else None,
            soft_frac=round(float(np.mean(soft)), 4) if soft else None,
            coverage=round(float(np.mean(cov)), 4) if cov else None,
            proj_min={str(s): round(FRAMES_58S / s * total_s / 60, 1) for s in STRIDES},
        )
    except Exception as e:
        cfg["status"] = f"FAIL: {type(e).__name__}: {str(e)[:300]}"
        traceback.print_exc()
    dump()
    print(json.dumps({k: cfg.get(k) for k in ("key", "status", "total_s", "peak_rss_gb", "proj_min")}), flush=True)


# --------------------------------------------------------------------- main
def monitor(max_rss_gb):
    proc = psutil.Process()
    proc.cpu_percent(None)
    while not STATE["stop"]:
        rss = proc.memory_info().rss
        STATE["peak"] = max(STATE["peak"], rss)
        STATE["cpu"].append(proc.cpu_percent(None))
        if rss / 1e9 > max_rss_gb:
            RESULT["status"] = f"OOM_GUARD (RSS > {max_rss_gb} GB)"
            RESULT["peak_rss_gb"] = round(rss / 1e9, 2)
            dump()
            print(RESULT["status"], flush=True)
            os._exit(3)
        time.sleep(0.05)


def main():
    global OUT_FILE
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", help="model id (see --list)")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--samples", default="samples")
    ap.add_argument("--out", default=None)
    ap.add_argument("--cache", default=None)
    ap.add_argument("--threads", type=int, default=os.cpu_count())
    ap.add_argument("--res", nargs="+", help="WxH list (torch models, or ONNX with dynamic input). Static ONNX ignores it.")
    ap.add_argument("--preps", nargs="+", default=["stretch"], choices=["stretch", "letterbox"])
    ap.add_argument("--norm", choices=["proper", "unit"], default="proper", help="unit = only /255 (current production)")
    ap.add_argument("--frames", type=int, default=8, help="still frames")
    ap.add_argument("--groups", type=int, default=2, help="burst groups (flicker test)")
    ap.add_argument("--per-group", type=int, default=4)
    ap.add_argument("--max-seconds", type=int, default=240, help="stop a config after this long")
    ap.add_argument("--max-rss-gb", type=float, default=6.0, help="kill the run above this RSS")
    ap.add_argument("--keep", action="store_true", help="keep downloaded model files")
    args = ap.parse_args()

    if args.list:
        for k, m in MODELS.items():
            print(f"{k:22s} {m['kind']:6s} {m['res']:10s} {m['note']}")
        return 0
    if args.verify:
        return 0 if verify() else 1
    if args.id not in MODELS:
        raise SystemExit(f"--id must be one of: {', '.join(MODELS)}")
    m = MODELS[args.id]
    out_dir = args.out or os.path.join("results", args.id)
    cache = os.path.abspath(args.cache or os.path.join("_models", args.id))
    os.makedirs(out_dir, exist_ok=True)
    OUT_FILE = os.path.join(out_dir, "results.json")
    os.environ.setdefault("HF_HOME", cache)
    RESULT.update(id=args.id, note=m["note"], env=env_info(args), status="RUNNING", configs=[])
    dump()
    threading.Thread(target=monitor, args=(args.max_rss_gb,), daemon=True).start()
    print(json.dumps(RESULT["env"]), flush=True)

    norm_name, norm = ("unit", UNIT) if args.norm == "unit" else ("proper", m["norm"])
    try:
        frames = load_frames(args.samples, args.frames, args.groups, args.per_group)
        if not frames:
            raise RuntimeError(f"no images found in {args.samples}/")
        t0 = time.time()
        if m["kind"] == "onnx":
            path = fetch(m["url"], os.path.join(cache, os.path.basename(m["url"])), m.get("sha256"))
            RESULT["model_mb"] = round(os.path.getsize(path) / 1e6, 1)
            runner, native, dtype = make_onnx_runner(path, m, args)
        else:
            runner, native, dtype = make_torch_runner(m, args)
        RESULT["load_s"] = round(time.time() - t0, 1)
        RESULT["input_native"] = f"{native[0]}x{native[1]}" if native else "dynamic"
        print(f"loaded in {RESULT['load_s']} s, native input: {RESULT['input_native']}", flush=True)
        if native:
            if args.res:
                print("note: static ONNX input, --res ignored", file=sys.stderr)
            sizes = [native]
        else:
            sizes = [parse_res(r, m.get("mult", 32)) for r in (args.res or [m["res"]])]
        for (W, H) in sizes:
            for prep in args.preps:
                run_config(args, runner, dtype, W, H, prep, norm_name, norm, frames, out_dir)
        RESULT["status"] = "OK"
    except Exception as e:
        RESULT["status"] = f"FAIL: {type(e).__name__}: {str(e)[:300]}"
        traceback.print_exc()
    finally:
        RESULT["peak_rss_gb"] = round(STATE["peak"] / 1e9, 2)
        STATE["stop"] = True
        dump()
        if not args.keep:
            shutil.rmtree(cache, ignore_errors=True)
    print("STATUS:", RESULT["status"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
