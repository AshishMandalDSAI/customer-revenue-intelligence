"""
Customer Segmentation (Unsupervised ML)
========================================
K-Means clustering over behavioral features, with the number of clusters
selected using the elbow method + silhouette score, then PCA for 2D
visualization and business-readable cluster naming.
"""
import sys
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.decomposition import PCA
import joblib

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.config import DATA_PROCESSED_DIR, MODELS_DIR, RANDOM_SEED, REPORTS_DIR

CLUSTER_FEATURES = [
    "recency_days", "frequency", "monetary", "avg_order_value",
    "tenure_days", "engagement_score", "return_rate", "avg_discount_pct",
]


def select_k(X_scaled, k_range=range(2, 9)):
    inertias, sil_scores = [], []
    for k in k_range:
        km = KMeans(n_clusters=k, random_state=RANDOM_SEED, n_init=10)
        labels = km.fit_predict(X_scaled)
        inertias.append(km.inertia_)
        sil_scores.append(silhouette_score(X_scaled, labels, sample_size=min(3000, len(X_scaled)),
                                            random_state=RANDOM_SEED))
    return list(k_range), inertias, sil_scores


def name_clusters(profile_df):
    """
    Assign a business-readable name to each cluster based on its relative
    monetary value, frequency, and churn-risk proxy (recency / engagement).
    """
    names = {}
    monetary_rank = profile_df["monetary"].rank(ascending=False)
    engagement_rank = profile_df["engagement_score"].rank(ascending=False)

    for cid in profile_df.index:
        m_rank = monetary_rank[cid]
        e_rank = engagement_rank[cid]
        n = len(profile_df)
        if m_rank <= n * 0.25 and e_rank <= n * 0.35:
            names[cid] = "High-Value Loyalists"
        elif m_rank <= n * 0.25 and e_rank > n * 0.6:
            names[cid] = "High-Value At-Risk"
        elif m_rank > n * 0.6 and e_rank > n * 0.6:
            names[cid] = "Low-Engagement / Dormant"
        elif e_rank <= n * 0.3:
            names[cid] = "Growing Regulars"
        else:
            names[cid] = "Mid-Value Occasional Shoppers"
    return names


def run_segmentation():
    feats = pd.read_csv(DATA_PROCESSED_DIR / "customer_features.csv")
    X = feats[CLUSTER_FEATURES].fillna(0)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    k_range, inertias, sil_scores = select_k(X_scaled)

    # Business constraint: a 2-cluster split (though it maximizes raw silhouette)
    # is not operationally actionable for a marketing/CRM team -- it collapses
    # to "big spenders vs everyone else" and gives no room for differentiated
    # campaigns. We therefore select the best silhouette score within a
    # business-usable range of 4-7 segments, which is documented here as an
    # explicit, defensible analytical decision (not an accident of the metric).
    USABLE_K_MIN, USABLE_K_MAX = 4, 7
    usable_idx = [i for i, k in enumerate(k_range) if USABLE_K_MIN <= k <= USABLE_K_MAX]
    best_k_idx = max(usable_idx, key=lambda i: sil_scores[i])
    best_k = k_range[best_k_idx]

    print("=== K Selection ===")
    for k, inertia, sil in zip(k_range, inertias, sil_scores):
        marker = "  <-- selected" if k == best_k else ""
        print(f"k={k}: inertia={inertia:,.0f}, silhouette={sil:.4f}{marker}")

    final_km = KMeans(n_clusters=best_k, random_state=RANDOM_SEED, n_init=10)
    cluster_labels = final_km.fit_predict(X_scaled)
    feats["cluster_id"] = cluster_labels

    # PCA for visualization
    pca = PCA(n_components=2, random_state=RANDOM_SEED)
    pcs = pca.fit_transform(X_scaled)
    feats["pca_1"] = pcs[:, 0]
    feats["pca_2"] = pcs[:, 1]
    explained_var = pca.explained_variance_ratio_

    # Cluster profiles
    profile = feats.groupby("cluster_id")[CLUSTER_FEATURES + ["churned"]].mean()
    profile["customer_count"] = feats.groupby("cluster_id").size()
    profile["total_revenue"] = feats.groupby("cluster_id")["monetary"].sum()
    profile["churn_rate"] = feats.groupby("cluster_id")["churned"].mean()

    cluster_names = name_clusters(profile)
    feats["segment_name"] = feats["cluster_id"].map(cluster_names)
    profile["segment_name"] = profile.index.map(cluster_names)

    # Recommended action per cluster
    def recommend(row):
        if row["segment_name"] == "High-Value Loyalists":
            return "Premium loyalty program & early access to new products"
        if row["segment_name"] == "High-Value At-Risk":
            return "Urgent, personalized retention offer (highest revenue-at-risk)"
        if row["segment_name"] == "Low-Engagement / Dormant":
            return "Low-cost automated reactivation email series"
        if row["segment_name"] == "Growing Regulars":
            return "Upsell / cross-sell adjacent categories"
        return "Standard engagement nurture campaigns"

    profile["recommended_action"] = profile.apply(recommend, axis=1)

    # Save artifacts
    joblib.dump({"scaler": scaler, "kmeans": final_km, "features": CLUSTER_FEATURES},
                MODELS_DIR / "segmentation_model.pkl")
    feats[["customer_id", "cluster_id", "segment_name", "pca_1", "pca_2"]].to_csv(
        DATA_PROCESSED_DIR / "customer_segments.csv", index=False
    )
    profile.round(3).to_csv(REPORTS_DIR.parent / "reports" / "segment_profiles.csv")

    with open(REPORTS_DIR / "segmentation_summary.json", "w") as f:
        json.dump({
            "best_k": int(best_k),
            "silhouette_score": float(sil_scores[best_k_idx]),
            "pca_explained_variance": explained_var.tolist(),
            "k_selection": {"k": k_range, "inertia": inertias, "silhouette": sil_scores},
        }, f, indent=2)

    print(f"\n=== Selected k={best_k} (silhouette={sil_scores[best_k_idx]:.4f}) ===")
    print(f"PCA explained variance (2 components): {explained_var.sum():.1%}")
    print("\n=== Cluster Profiles ===")
    print(profile[["customer_count", "total_revenue", "churn_rate", "monetary",
                    "engagement_score", "segment_name", "recommended_action"]].round(2))

    return feats, profile


def main():
    run_segmentation()


if __name__ == "__main__":
    main()
