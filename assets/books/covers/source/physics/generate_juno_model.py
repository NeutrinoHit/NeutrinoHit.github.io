
from pathlib import Path
import math
import re
import numpy as np
from scipy import optimize
from scipy.special import ndtr
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import cairosvg

PROJECT = Path(__file__).resolve().parents[2]
ROOT = PROJECT / "build"
ROOT.mkdir(parents=True, exist_ok=True)
PANEL_DIR = ROOT / "juno_cover_panels"
PANEL_DIR.mkdir(exist_ok=True)

OUT_SVG = ROOT / "juno_like_central_figure_v1.svg"
OUT_PNG = ROOT / "juno_like_central_figure_v1_preview.png"
OUT_NPZ = PROJECT / "data" / "juno_like_central_figure_v1_data.npz"
OUT_NPZ.parent.mkdir(parents=True, exist_ok=True)

plt.rcParams["svg.fonttype"] = "none"
plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["axes.unicode_minus"] = False

FLUX_COMPONENTS = [
    (0.58, [4.367, -4.577, 2.100, -0.5294, 0.06186, -0.002777]),
    (0.07, [0.4833, 0.1927, -0.1283, -0.006762, 0.002233, -0.0001536]),
    (0.30, [4.757, -5.392, 2.563, -0.6596, 0.07820, -0.003536]),
    (0.05, [2.990, -2.882, 1.278, -0.3343, 0.03905, -0.001754]),
]

BASELINES_KM = np.array([
    52.77, 52.64,
    52.74, 52.82, 52.41, 52.49, 52.11, 52.19,
    215.0
])
SOURCE_WEIGHTS = np.array([
    0.160, 0.161,
    0.101, 0.101, 0.103, 0.102, 0.104, 0.104,
    0.064
], dtype=float)
SOURCE_WEIGHTS /= SOURCE_WEIGHTS.sum()

SIN2_THETA12_TRUE = 0.3092
DM21_TRUE = 7.50e-5
SIN2_THETA13 = 0.0220
DM31 = 2.50e-3

RES_A = 0.0261
RES_B = 0.0082
RES_C = 0.0123

EXPOSURE_DAYS = 6.0 * 365.25
TARGET_EVENTS = 47.1 * EXPOSURE_DAYS

SIGMA_NORM = 0.010
SIGMA_ESCALE = 0.003
SIGMA_RES_SCALE = 0.050

SEED = 20260904

E_NU = np.linspace(1.806, 8.0, 700)
D_E = E_NU[1] - E_NU[0]

def isotope_flux(E, coeffs):
    poly = np.zeros_like(E)
    for p, a in enumerate(coeffs):
        poly += a * E**p
    return np.exp(poly)

def reactor_flux(E):
    ans = np.zeros_like(E)
    for fraction, coeffs in FLUX_COMPONENTS:
        ans += fraction * isotope_flux(E, coeffs)
    return ans

def ibd_xs_shape(E):
    Ee = E - 1.293
    pe = np.sqrt(np.clip(Ee**2 - 0.511**2, 0.0, None))
    return np.clip(Ee * pe, 0.0, None)

BASE_TRUE_E = reactor_flux(E_NU) * ibd_xs_shape(E_NU)

def weighted_sin2(dm2):
    ans = np.zeros_like(E_NU)
    for L, w in zip(BASELINES_KM, SOURCE_WEIGHTS):
        phase = 1.267 * dm2 * (L * 1000.0) / E_NU
        ans += w * np.sin(phase)**2
    return ans

S31 = weighted_sin2(DM31)

def survival_from_precomputed(s12, s21, s32):
    c13 = 1.0 - SIN2_THETA13
    c12 = 1.0 - s12
    u1 = c13 * c12
    u2 = c13 * s12
    u3 = SIN2_THETA13
    return (
        1.0
        - 4.0*u1*u2*s21
        - 4.0*u1*u3*S31
        - 4.0*u2*u3*s32
    )

E_VIS_TRUE = E_NU - 0.78
E_EDGES = np.linspace(1.0, 7.3, 127)
E_CENTERS = 0.5 * (E_EDGES[:-1] + E_EDGES[1:])

def sigma_evis(evis, resolution_scale=0.0):
    e = np.maximum(evis, 0.1)
    rel = np.sqrt((RES_A/np.sqrt(e))**2 + RES_B**2 + (RES_C/e)**2)
    return evis * rel * (1.0 + resolution_scale)

def response_matrix(resolution_scale=0.0):
    sig = sigma_evis(E_VIS_TRUE, resolution_scale)
    hi = ndtr((E_EDGES[1:, None] - E_VIS_TRUE[None, :]) / sig[None, :])
    lo = ndtr((E_EDGES[:-1, None] - E_VIS_TRUE[None, :]) / sig[None, :])
    return hi - lo

R0 = response_matrix(0.0)
RES_EPS = 0.03
R_PLUS = response_matrix(+RES_EPS)
R_MINUS = response_matrix(-RES_EPS)
DR_DRES = (R_PLUS - R_MINUS) / (2.0 * RES_EPS)

s21_true = weighted_sin2(DM21_TRUE)
s32_true = weighted_sin2(DM31 - DM21_TRUE)
pee_true = survival_from_precomputed(SIN2_THETA12_TRUE, s21_true, s32_true)
raw_true = BASE_TRUE_E * pee_true * D_E
spec_true_unscaled = R0 @ raw_true
ABS_SCALE = TARGET_EVENTS / spec_true_unscaled.sum()
SPEC_TRUE = ABS_SCALE * spec_true_unscaled

rng = np.random.default_rng(SEED)
DATA = rng.poisson(SPEC_TRUE)

S12_GRID = np.linspace(0.300, 0.318, 61)
DM21_GRID = np.linspace(7.32e-5, 7.68e-5, 61)

S21_GRID = np.stack([weighted_sin2(dm) for dm in DM21_GRID])
S32_GRID = np.stack([weighted_sin2(DM31 - dm) for dm in DM21_GRID])

MODELS = np.empty((len(S12_GRID), len(DM21_GRID), len(E_CENTERS)))
DMODELS_DRES = np.empty_like(MODELS)

for ia, s12 in enumerate(S12_GRID):
    c13 = 1.0 - SIN2_THETA13
    c12 = 1.0 - s12
    u1 = c13*c12
    u2 = c13*s12
    u3 = SIN2_THETA13
    c21 = 4.0*u1*u2
    c31 = 4.0*u1*u3
    c32 = 4.0*u2*u3

    pee = 1.0 - c21*S21_GRID - c31*S31[None, :] - c32*S32_GRID
    raw = pee * BASE_TRUE_E[None, :] * D_E
    MODELS[ia] = ABS_SCALE * (raw @ R0.T)
    DMODELS_DRES[ia] = ABS_SCALE * (raw @ DR_DRES.T)

NOBS = DATA.sum()

def shift_energy_scale(spec, delta):
    source_x = E_CENTERS / (1.0 + delta)
    return np.interp(source_x, E_CENTERS, spec, left=0.0, right=0.0) / (1.0 + delta)

def profiled_norm(shape):
    S = shape.sum()
    b = S * SIGMA_NORM**2 - 1.0
    c = -NOBS * SIGMA_NORM**2
    return 0.5 * (-b + math.sqrt(b*b - 4.0*c))

def nuisance_objective(x, nominal, dres):
    de, dr = x
    shape = nominal + dr*dres
    shape = shift_energy_scale(shape, de)
    shape = np.clip(shape, 1e-12, None)

    k = profiled_norm(shape)
    mu = np.clip(k*shape, 1e-12, None)

    with np.errstate(divide="ignore", invalid="ignore"):
        pois = np.where(DATA > 0,
                        mu - DATA + DATA*np.log(DATA/mu),
                        mu)

    return (
        2.0*np.sum(pois)
        + ((k - 1.0)/SIGMA_NORM)**2
        + (de/SIGMA_ESCALE)**2
        + (dr/SIGMA_RES_SCALE)**2
    )

QRAW = np.empty((len(S12_GRID), len(DM21_GRID)))
NUIS = np.empty((len(S12_GRID), len(DM21_GRID), 2))

for ia in range(len(S12_GRID)):
    for idm in range(len(DM21_GRID)):
        res = optimize.minimize(
            nuisance_objective,
            x0=np.array([0.0, 0.0]),
            args=(MODELS[ia, idm], DMODELS_DRES[ia, idm]),
            method="L-BFGS-B",
            bounds=[(-4*SIGMA_ESCALE, 4*SIGMA_ESCALE),
                    (-4*SIGMA_RES_SCALE, 4*SIGMA_RES_SCALE)],
            options={"maxiter": 35, "ftol": 1e-9, "eps": 1e-5},
        )
        QRAW[ia, idm] = res.fun
        NUIS[ia, idm] = res.x

Q = QRAW - np.min(QRAW)
IBEST = np.unravel_index(np.argmin(QRAW), QRAW.shape)
S12_BEST = S12_GRID[IBEST[0]]
DM21_BEST = DM21_GRID[IBEST[1]]
DE_BEST, DR_BEST = NUIS[IBEST]

best_shape = MODELS[IBEST] + DR_BEST*DMODELS_DRES[IBEST]
best_shape = shift_energy_scale(best_shape, DE_BEST)
K_BEST = profiled_norm(best_shape)
SPEC_BEST = K_BEST * best_shape

PROFILE_S12 = Q.min(axis=1)
PROFILE_DM21 = Q.min(axis=0)

RAW_NOOSC = BASE_TRUE_E * D_E
SPEC_NOOSC = ABS_SCALE * (R0 @ RAW_NOOSC)
RATIO_DATA = DATA / np.clip(SPEC_NOOSC, 1e-12, None)
RATIO_BEST = SPEC_BEST / np.clip(SPEC_NOOSC, 1e-12, None)
RATIO_ERR = np.sqrt(np.maximum(DATA, 1.0)) / np.clip(SPEC_NOOSC, 1e-12, None)
RESID = (DATA - SPEC_BEST) / np.sqrt(np.clip(SPEC_BEST, 1.0, None))

np.savez(
    OUT_NPZ,
    e_centers=E_CENTERS,
    data=DATA,
    spec_true=SPEC_TRUE,
    spec_best=SPEC_BEST,
    spec_noosc=SPEC_NOOSC,
    residuals=RESID,
    s12_grid=S12_GRID,
    dm21_grid=DM21_GRID,
    q=Q,
    profile_s12=PROFILE_S12,
    profile_dm21=PROFILE_DM21,
    s12_true=SIN2_THETA12_TRUE,
    dm21_true=DM21_TRUE,
    s12_best=S12_BEST,
    dm21_best=DM21_BEST,
)

def clean_axes(ax):
    ax.tick_params(direction="out", length=3.2, width=0.8)
    for spine in ax.spines.values():
        spine.set_linewidth(0.8)

def save_map(path):
    fig = plt.figure(figsize=(5.4, 4.3))
    ax = fig.add_axes([0.16, 0.16, 0.80, 0.78])
    X, Y = np.meshgrid(DM21_GRID*1e5, S12_GRID)
    qplot = np.minimum(Q, 12.5)
    ax.contourf(X, Y, qplot, levels=[0.0, 2.30, 6.18, 11.83, 12.5], alpha=0.55)
    cs = ax.contour(X, Y, Q, levels=[2.30, 6.18, 11.83], linewidths=1.2)
    ax.clabel(cs, inline=True, fontsize=8,
              fmt={2.30: "1σ", 6.18: "2σ", 11.83: "3σ"})
    ax.plot(DM21_TRUE*1e5, SIN2_THETA12_TRUE, marker="x",
            markersize=8, markeredgewidth=1.7, linestyle="none", label="генерация")
    ax.plot(DM21_BEST*1e5, S12_BEST, marker="o",
            markersize=5.5, linestyle="none", label="максимум")
    ax.set_xlabel("Δm²₂₁  [10⁻⁵ эВ²]")
    ax.set_ylabel("sin² θ₁₂")
    ax.set_xlim(DM21_GRID[0]*1e5, DM21_GRID[-1]*1e5)
    ax.set_ylim(S12_GRID[0], S12_GRID[-1])
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    clean_axes(ax)
    fig.savefig(path, format="svg", transparent=True)
    plt.close(fig)

def save_profile_dm(path):
    fig = plt.figure(figsize=(5.4, 1.35))
    ax = fig.add_axes([0.16, 0.26, 0.80, 0.68])
    ax.plot(DM21_GRID*1e5, np.minimum(PROFILE_DM21, 12.0), linewidth=1.6)
    ax.set_ylabel("qₚ")
    ax.set_xticklabels([])
    ax.set_ylim(0, 10)
    ax.set_xlim(DM21_GRID[0]*1e5, DM21_GRID[-1]*1e5)
    clean_axes(ax)
    fig.savefig(path, format="svg", transparent=True)
    plt.close(fig)

def save_profile_s12(path):
    fig = plt.figure(figsize=(1.9, 4.3))
    ax = fig.add_axes([0.16, 0.16, 0.70, 0.78])
    ax.plot(np.minimum(PROFILE_S12, 12.0), S12_GRID, linewidth=1.6)
    ax.set_xlabel("qₚ")
    ax.set_yticklabels([])
    ax.set_xlim(0, 10)
    ax.set_ylim(S12_GRID[0], S12_GRID[-1])
    clean_axes(ax)
    fig.savefig(path, format="svg", transparent=True)
    plt.close(fig)

def save_ratio(path):
    fig = plt.figure(figsize=(7.4, 1.75))
    ax = fig.add_axes([0.11, 0.25, 0.86, 0.70])
    mask = (E_CENTERS >= 1.2) & (E_CENTERS <= 7.0)
    ax.errorbar(E_CENTERS[mask], RATIO_DATA[mask],
                yerr=RATIO_ERR[mask], fmt=".", markersize=2.4,
                linewidth=0.55, capsize=0)
    ax.plot(E_CENTERS[mask], RATIO_BEST[mask], linewidth=1.5)
    ax.set_xlim(1.2, 7.0)
    ax.set_ylim(0.10, 0.90)
    ax.set_ylabel("N / N₀")
    ax.set_xticklabels([])
    clean_axes(ax)
    fig.savefig(path, format="svg", transparent=True)
    plt.close(fig)

def save_residual(path):
    fig = plt.figure(figsize=(7.4, 1.25))
    ax = fig.add_axes([0.11, 0.32, 0.86, 0.62])
    mask = (E_CENTERS >= 1.2) & (E_CENTERS <= 7.0)
    ax.plot(E_CENTERS[mask], RESID[mask], marker="o",
            markersize=2.4, linewidth=0.6)
    ax.axhline(0.0, linewidth=0.8)
    ax.set_xlim(1.2, 7.0)
    ax.set_ylim(-3.8, 3.8)
    ax.set_xlabel("Eвид, МэВ")
    ax.set_ylabel("(n−μ̂)/√μ̂")
    clean_axes(ax)
    fig.savefig(path, format="svg", transparent=True)
    plt.close(fig)

panel_files = {
    "map": PANEL_DIR / "map.svg",
    "pdm": PANEL_DIR / "profile_dm.svg",
    "ps12": PANEL_DIR / "profile_s12.svg",
    "ratio": PANEL_DIR / "ratio.svg",
    "resid": PANEL_DIR / "residual.svg",
}
save_map(panel_files["map"])
save_profile_dm(panel_files["pdm"])
save_profile_s12(panel_files["ps12"])
save_ratio(panel_files["ratio"])
save_residual(panel_files["resid"])

def prepare_nested_svg(path, prefix):
    txt = Path(path).read_text(encoding="utf-8")
    txt = re.sub(r"<\?xml[^>]*\?>", "", txt)
    txt = re.sub(r"<!DOCTYPE[^>]*>", "", txt)

    root = re.search(r"<svg\b([^>]*)>", txt, re.S)
    attrs = root.group(1)
    vb = re.search(r'viewBox="([^"]+)"', attrs)
    if not vb:
        raise RuntimeError(f"No viewBox in {path}")
    viewbox = vb.group(1)

    ids = re.findall(r'id="([^"]+)"', txt)
    for old in sorted(ids, key=len, reverse=True):
        new = f"{prefix}_{old}"
        txt = txt.replace(f'id="{old}"', f'id="{new}"')
        txt = txt.replace(f'url(#{old})', f'url(#{new})')
        txt = txt.replace(f'href="#{old}"', f'href="#{new}"')
        txt = txt.replace(f'xlink:href="#{old}"', f'xlink:href="#{new}"')

    inner = re.sub(r"^.*?<svg\b[^>]*>", "", txt, count=1, flags=re.S)
    inner = re.sub(r"</svg>\s*$", "", inner, count=1, flags=re.S)
    return viewbox, inner

placements = [
    ("pdm",   75,  18, 590, 120),
    ("map",   75, 138, 590, 450),
    ("ps12", 670, 138, 205, 450),
    ("ratio", 75, 615, 800, 175),
    ("resid", 75, 792, 800, 125),
]

nested = []
for key, x, y, w, h in placements:
    vb, inner = prepare_nested_svg(panel_files[key], key)
    nested.append(
        f'<svg x="{x}" y="{y}" width="{w}" height="{h}" '
        f'viewBox="{vb}" preserveAspectRatio="xMidYMid meet">{inner}</svg>'
    )

master = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:xlink="http://www.w3.org/1999/xlink"
     viewBox="0 0 950 930"
     role="img"
     aria-labelledby="title desc">
  <title id="title">JUNO-like reactor-neutrino profile-likelihood analysis</title>
  <desc id="desc">Six-year deterministic reactor-antineutrino pseudoexperiment with a three-flavor oscillation model, JUNO reactor baselines, detector energy resolution, Poisson statistics, and profiled normalization, energy-scale, and resolution nuisances.</desc>
  <metadata>Seed={SEED}; true sin2theta12={SIN2_THETA12_TRUE}; true dm21={DM21_TRUE}; best sin2theta12={S12_BEST}; best dm21={DM21_BEST}; events={int(DATA.sum())}.</metadata>
  {''.join(nested)}
  <text x="82" y="610" font-family="DejaVu Sans" font-size="12">JUNO-like simulation · 6 лет · фиксированный Poisson seed</text>
</svg>
'''
OUT_SVG.write_text(master, encoding="utf-8")

cairosvg.svg2png(
    bytestring=master.encode("utf-8"),
    write_to=str(OUT_PNG),
    output_width=1425,
    output_height=1395,
    background_color="white",
)

print("JUNO-like central figure v1 generated")
print(f"events            : {int(DATA.sum())}")
print(f"true sin^2 theta12: {SIN2_THETA12_TRUE:.5f}")
print(f"fit  sin^2 theta12: {S12_BEST:.5f}")
print(f"true dm21         : {DM21_TRUE*1e5:.4f} x 10^-5 eV^2")
print(f"fit  dm21         : {DM21_BEST*1e5:.4f} x 10^-5 eV^2")
print(f"profiled norm     : {K_BEST:.6f}")
print(f"profiled E scale  : {DE_BEST:+.6f}")
print(f"profiled res scale: {DR_BEST:+.6f}")
print("SVG :", OUT_SVG)
print("PNG :", OUT_PNG)
print("NPZ :", OUT_NPZ)
