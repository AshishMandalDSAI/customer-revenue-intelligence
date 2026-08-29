"""
EDA Visualizations
====================
Generates the core exploratory charts required by the spec and saves them
as PNGs under reports/figures/ for inclusion in the report/README.
"""
import sys
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.config import DATA_PROCESSED_DIR, REPORTS_DIR

sns.set_theme(style="whitegrid")
FIG_DIR = REPORTS_DIR / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)


def save(fig, name):
    fig.tight_layout()
    fig.savefig(FIG_DIR / name, dpi=130)
    plt.close(fig)


def main():
    orders = pd.read_csv(DATA_PROCESSED_DIR / "orders_clean.csv", parse_dates=["order_date"])
    feats = pd.read_csv(DATA_PROCESSED_DIR / "customer_features.csv")
    rfm = pd.read_csv(DATA_PROCESSED_DIR / "customer_rfm.csv")
    order_items = pd.read_csv(DATA_PROCESSED_DIR / "order_items_clean.csv")
    segs = pd.read_csv(DATA_PROCESSED_DIR / "customer_segments.csv")

    # 1. Revenue trend
    monthly = orders.groupby(orders["order_date"].dt.to_period("M"))["order_value"].sum()
    fig, ax = plt.subplots(figsize=(9, 4))
    monthly.plot(ax=ax, marker="o", color="#2563eb")
    ax.set_title("Monthly Revenue Trend")
    ax.set_ylabel("Revenue")
    save(fig, "01_revenue_trend.png")

    # 2. Monthly orders
    monthly_orders = orders.groupby(orders["order_date"].dt.to_period("M")).size()
    fig, ax = plt.subplots(figsize=(9, 4))
    monthly_orders.plot(kind="bar", ax=ax, color="#0ea5e9")
    ax.set_title("Monthly Order Volume")
    ax.set_xticklabels([str(x) for x in monthly_orders.index], rotation=90, fontsize=6)
    save(fig, "02_monthly_orders.png")

    # 3. AOV distribution
    fig, ax = plt.subplots(figsize=(7, 4))
    sns.histplot(orders["order_value"], bins=60, ax=ax, color="#7c3aed")
    ax.set_title("Average Order Value Distribution")
    ax.set_xlim(0, orders["order_value"].quantile(0.98))
    save(fig, "03_aov_distribution.png")

    # 4. Revenue by category
    rev_cat = order_items.groupby("category")["line_total"].sum().sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(8, 5))
    rev_cat.plot(kind="barh", ax=ax, color="#16a34a")
    ax.invert_yaxis()
    ax.set_title("Revenue by Product Category")
    save(fig, "04_revenue_by_category.png")

    # 5. Revenue by region
    rev_region = orders.groupby("region")["order_value"].sum().sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(6, 4))
    rev_region.plot(kind="bar", ax=ax, color="#f59e0b")
    ax.set_title("Revenue by Region")
    save(fig, "05_revenue_by_region.png")

    # 6. RFM segment distribution
    fig, ax = plt.subplots(figsize=(8, 5))
    rfm["segment"].value_counts().plot(kind="barh", ax=ax, color="#dc2626")
    ax.invert_yaxis()
    ax.set_title("RFM Segment Distribution")
    save(fig, "06_rfm_segments.png")

    # 7. Churn distribution
    fig, ax = plt.subplots(figsize=(5, 4))
    feats["churned"].value_counts().rename({0: "Retained", 1: "Churned"}).plot(
        kind="pie", ax=ax, autopct="%1.1f%%", colors=["#22c55e", "#ef4444"]
    )
    ax.set_ylabel("")
    ax.set_title("Churn Distribution (label window)")
    save(fig, "07_churn_distribution.png")

    # 8. Customer segment distribution (K-Means)
    fig, ax = plt.subplots(figsize=(8, 5))
    segs["segment_name"].value_counts().plot(kind="barh", ax=ax, color="#0891b2")
    ax.invert_yaxis()
    ax.set_title("ML Customer Segment Distribution")
    save(fig, "08_ml_segments.png")

    # 9. PCA scatter of clusters
    fig, ax = plt.subplots(figsize=(7, 6))
    for name, g in segs.groupby("segment_name"):
        ax.scatter(g["pca_1"], g["pca_2"], label=name, alpha=0.5, s=10)
    ax.set_title("Customer Segments (PCA projection)")
    ax.legend(fontsize=7, markerscale=2)
    save(fig, "09_pca_clusters.png")

    # 10. Recency / Frequency / Monetary distributions
    fig, axes = plt.subplots(1, 3, figsize=(13, 4))
    sns.histplot(feats["recency_days"], bins=50, ax=axes[0], color="#6366f1")
    axes[0].set_title("Recency Distribution")
    sns.histplot(feats["frequency"], bins=50, ax=axes[1], color="#f97316")
    axes[1].set_title("Frequency Distribution")
    axes[1].set_xlim(0, feats["frequency"].quantile(0.98))
    sns.histplot(feats["monetary"], bins=50, ax=axes[2], color="#10b981")
    axes[2].set_title("Monetary Distribution")
    axes[2].set_xlim(0, feats["monetary"].quantile(0.98))
    save(fig, "10_rfm_distributions.png")

    print(f"Saved {len(list(FIG_DIR.glob('*.png')))} charts to {FIG_DIR}")


if __name__ == "__main__":
    main()
