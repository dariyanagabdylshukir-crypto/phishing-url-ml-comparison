"""Figures for the report.

Input:  results of process_data.py
Output: reports/figures/fig1_latency_vs_load.pdf/.png, fig2_distribution_boxplot.pdf/.png
"""
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

from process_data import MODELS, NAMES, ROOT, bootstrap_ci

FIG_DIR = ROOT / "reports" / "figures"

# colorblind-safe colors + different markers and line styles for b/w printing
COLORS = dict(zip(MODELS, sns.color_palette("colorblind", 4)))
MARKERS = dict(zip(MODELS, ["o", "s", "^", "D"]))
LINES = dict(zip(MODELS, ["-", "--", "-.", ":"]))
FS_TITLE = {"full": "Full feature set (16)", "selected": "Selected feature set (7)"}


def setup_style():
    sns.set_theme(style="whitegrid", context="paper")
    plt.rcParams.update({"font.size": 9, "legend.fontsize": 8, "pdf.fonttype": 42})


def save(fig, name):
    """Save as vector pdf and png with 300 dpi."""
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG_DIR / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(FIG_DIR / f"{name}.png", dpi=300, bbox_inches="tight")


def plot_latency_vs_load(lat_tab):
    """Median latency vs batch size, error bars = 95% CI, band = IQR."""
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.2), sharey=True)
    for ax, fs in zip(axes, ["full", "selected"]):
        for m in MODELS:
            d = lat_tab[(lat_tab["model"] == m) & (lat_tab["feature_set"] == fs)]
            d = d.sort_values("batch_size")
            ax.fill_between(d["batch_size"], d["p25"], d["p75"], color=COLORS[m], alpha=0.18)
            ax.errorbar(d["batch_size"], d["median"],
                        yerr=[d["median"] - d["ci_low"], d["ci_high"] - d["median"]],
                        color=COLORS[m], marker=MARKERS[m], linestyle=LINES[m],
                        markersize=5, capsize=3, label=NAMES[m])
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_title(FS_TITLE[fs])
        ax.set_xlabel("Load, batch size (URLs per request)")
    axes[0].set_ylabel("Latency per request (ms)")
    handles, labels = axes[0].get_legend_handles_labels()
    handles.append(plt.Rectangle((0, 0), 1, 1, color="0.6", alpha=0.35))
    labels.append("IQR (p25–p75)")
    fig.legend(handles, labels, loc="lower center", ncol=5, bbox_to_anchor=(0.5, -0.16),
               frameon=False)
    fig.suptitle("Latency vs load (median, error bars = 95% bootstrap CI)", y=1.02)
    return fig


def plot_boxplots(q, lat):
    """(a) F1 over 10 repeats, (b) latency for 1 URL. Diamonds = estimate with 95% CI."""
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.4))
    fs_colors = {"full": sns.color_palette("colorblind")[4],
                 "selected": sns.color_palette("colorblind")[5]}
    one_url = lat[lat["batch_size"] == 1]
    panels = [(axes[0], q, "f1", np.mean, "Phishing-class F1-score (0–1)", "(a) F1-score, 10 repeats"),
              (axes[1], one_url, "latency_ms", np.median, "Latency for 1 URL (ms, log scale)",
               "(b) Latency, batch = 1")]
    for ax, data, col, stat, ylabel, title in panels:
        sns.boxplot(data=data, x="model", y=col, hue="feature_set", order=MODELS,
                    hue_order=["full", "selected"], palette=fs_colors, ax=ax,
                    width=0.7, fliersize=1.5, linewidth=0.8, showfliers=(col != "f1"))
        for patch in ax.patches[4:8]:  # hatching for the selected set (b/w printing)
            patch.set_hatch("//")
        if col == "f1":
            sns.stripplot(data=data, x="model", y=col, hue="feature_set", order=MODELS,
                          hue_order=["full", "selected"], dodge=True, ax=ax, size=2.5,
                          palette=["0.25", "0.25"], legend=False)
        else:
            ax.set_yscale("log")
        # estimate with 95% CI on top of each box
        for i, m in enumerate(MODELS):
            for fs, shift in [("full", -0.2), ("selected", 0.2)]:
                v = data[(data["model"] == m) & (data["feature_set"] == fs)][col]
                lo, hi = bootstrap_ci(v, stat=stat)
                c = stat(v.to_numpy())
                ax.errorbar(i + shift, c, yerr=[[c - lo], [hi - c]], fmt="D", color="black",
                            markersize=3.5, capsize=3, zorder=5)
        ax.set_xticks(range(4), [NAMES[m] for m in MODELS], rotation=15)
        ax.set_xlabel("Model")
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.get_legend().remove()
    handles = [plt.Rectangle((0, 0), 1, 1, facecolor=fs_colors["full"], edgecolor="0.3"),
               plt.Rectangle((0, 0), 1, 1, facecolor=fs_colors["selected"], hatch="//",
                             edgecolor="0.3"),
               plt.Line2D([], [], marker="D", color="black", linestyle="none")]
    fig.legend(handles, [FS_TITLE["full"], FS_TITLE["selected"],
                         "Mean (a) / median (b) ± 95% CI"],
               loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.08), frameon=False)
    fig.tight_layout()
    return fig


if __name__ == "__main__":
    import matplotlib
    matplotlib.use("Agg")
    from process_data import run

    raw, q, lat, lat_tab, guard, summary = run()
    setup_style()
    save(plot_latency_vs_load(lat_tab), "fig1_latency_vs_load")
    save(plot_boxplots(q, lat), "fig2_distribution_boxplot")
    print("saved to", FIG_DIR)
