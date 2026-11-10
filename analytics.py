"""Data preparation, RFM segmentation, visualization, and product recommendations."""
from __future__ import annotations

from pathlib import Path
import re
import warnings

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity


BASE_DIR = Path(__file__).resolve().parent
SEGMENT_ORDER = ["Champions", "Regular Customers", "Occasional Buyers", "At-Risk Customers"]
SEGMENT_NOTES = {
    "Champions": {
        "summary": "Recent, frequent, high-value shoppers who already show strong loyalty.",
        "action": "Reward loyalty, offer early access, and introduce complementary products."
    },
    "Regular Customers": {
        "summary": "Steady shoppers with repeat purchases and dependable spending.",
        "action": "Use bundles, helpful product suggestions, and repeat-purchase reminders."
    },
    "Occasional Buyers": {
        "summary": "Customers with a smaller purchase history or less frequent visits.",
        "action": "Share curated collections, useful offers, and simple reasons to return."
    },
    "At-Risk Customers": {
        "summary": "Customers whose last purchase was relatively long ago or whose activity is fading.",
        "action": "Try a friendly win-back campaign and highlight relevant new arrivals."
    },
}


class DataValidationError(ValueError):
    """Raised when an uploaded file cannot support the analysis."""


class AnalyticsEngine:
    def __init__(self, data_path: str | Path, source_label: str = "Demo sample dataset"):
        self.data_path = Path(data_path)
        self.source_label = source_label
        self.raw = pd.DataFrame()
        self.cleaned = pd.DataFrame()
        self.customers = pd.DataFrame()
        self.profiles = pd.DataFrame()
        self.elbow = pd.DataFrame()
        self.product_matrix = pd.DataFrame()
        self.silhouette = None
        self.cluster_count = 4
        self.summary = {}

    @staticmethod
    def _key(value: str) -> str:
        return re.sub(r"[^a-z0-9]", "", str(value).lower())

    def _standardize_columns(self, frame: pd.DataFrame) -> pd.DataFrame:
        aliases = {
            "InvoiceNo": {"invoiceno", "invoice", "invoicenumber", "billno"},
            "StockCode": {"stockcode", "productcode", "itemcode", "sku"},
            "Description": {"description", "productname", "itemdescription", "product"},
            "Quantity": {"quantity", "qty", "units"},
            "InvoiceDate": {"invoicedate", "date", "transactiondate", "orderdate"},
            "UnitPrice": {"unitprice", "price", "unitcost", "sellingprice"},
            "CustomerID": {"customerid", "customer", "clientid", "customernumber"},
            "Country": {"country", "customercountry", "region"},
        }
        lookup = {self._key(column): column for column in frame.columns}
        rename = {}
        for standard, candidates in aliases.items():
            for candidate in candidates:
                if candidate in lookup:
                    rename[lookup[candidate]] = standard
                    break
        frame = frame.rename(columns=rename).copy()

        required = ["InvoiceNo", "Quantity", "InvoiceDate", "UnitPrice", "CustomerID"]
        missing = [column for column in required if column not in frame.columns]
        if missing:
            raise DataValidationError(
                "Missing required column(s): " + ", ".join(missing) + ". "
                "Use a retail CSV with InvoiceNo, Quantity, InvoiceDate, UnitPrice, and CustomerID."
            )
        if "Description" not in frame.columns:
            if "StockCode" in frame.columns:
                frame["Description"] = "Product " + frame["StockCode"].astype(str)
            else:
                raise DataValidationError("Add a Description or StockCode column so products can be recommended.")
        if "Country" not in frame.columns:
            frame["Country"] = "Not provided"
        return frame

    def load_and_clean(self) -> None:
        try:
            raw = pd.read_csv(self.data_path, encoding="utf-8-sig", low_memory=False)
        except UnicodeDecodeError:
            raw = pd.read_csv(self.data_path, encoding="latin-1", low_memory=False)
        except Exception as exc:
            raise DataValidationError(f"Could not read this CSV file: {exc}") from exc

        if raw.empty:
            raise DataValidationError("The CSV file is empty. Please choose a file containing retail transactions.")
        raw = self._standardize_columns(raw)
        raw["InvoiceNo"] = raw["InvoiceNo"].astype("string").str.strip()
        raw["CustomerID"] = raw["CustomerID"].astype("string").str.replace(r"\.0$", "", regex=True).str.strip()
        raw["Description"] = raw["Description"].astype("string").str.strip()
        raw["Country"] = raw["Country"].astype("string").str.strip().fillna("Not provided")
        raw["Quantity"] = pd.to_numeric(raw["Quantity"], errors="coerce")
        raw["UnitPrice"] = pd.to_numeric(raw["UnitPrice"], errors="coerce")
        # UCI Online Retail dates are day-first; this also accepts ISO date strings.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            raw["InvoiceDate"] = pd.to_datetime(raw["InvoiceDate"], errors="coerce", dayfirst=True)

        valid = raw.dropna(subset=["InvoiceNo", "CustomerID", "Quantity", "UnitPrice", "InvoiceDate", "Description"]).copy()
        valid = valid[valid["CustomerID"].astype(str).str.lower().ne("nan")]
        valid = valid[~valid["InvoiceNo"].astype(str).str.upper().str.startswith("C")]
        valid = valid[(valid["Quantity"] > 0) & (valid["UnitPrice"] > 0)]
        valid["TotalPrice"] = valid["Quantity"] * valid["UnitPrice"]
        valid = valid[np.isfinite(valid["TotalPrice"]) & (valid["TotalPrice"] > 0)]
        if valid.empty:
            raise DataValidationError(
                "No valid purchase rows remain after cleaning. Check the date, customer, quantity, and price columns."
            )
        if valid["CustomerID"].nunique() < 4:
            raise DataValidationError("At least 4 distinct customers are required for the four-segment K-Means analysis.")

        keep = ["InvoiceNo", "StockCode", "Description", "Quantity", "InvoiceDate", "UnitPrice", "CustomerID", "Country", "TotalPrice"]
        for optional in ["StockCode"]:
            if optional not in valid.columns:
                valid[optional] = ""
        self.raw = raw
        self.cleaned = valid[keep].sort_values("InvoiceDate").reset_index(drop=True)
        self.cleaned.to_csv(BASE_DIR / "cleaned_transactions.csv", index=False)

    def build_rfm(self) -> None:
        snapshot = self.cleaned["InvoiceDate"].max().normalize() + pd.Timedelta(days=1)
        grouped = self.cleaned.groupby("CustomerID", as_index=False).agg(
            LastPurchase=("InvoiceDate", "max"),
            Frequency=("InvoiceNo", "nunique"),
            Monetary=("TotalPrice", "sum"),
            ProductsPurchased=("Description", "nunique"),
            Country=("Country", lambda values: values.mode().iloc[0] if not values.mode().empty else "Not provided"),
        )
        grouped["Recency"] = (snapshot - grouped["LastPurchase"].dt.normalize()).dt.days
        grouped["AverageOrderValue"] = grouped["Monetary"] / grouped["Frequency"].clip(lower=1)
        grouped["Recency"] = grouped["Recency"].clip(lower=0)
        self.customers = grouped[[
            "CustomerID", "Recency", "Frequency", "Monetary", "AverageOrderValue", "ProductsPurchased", "Country", "LastPurchase"
        ]].copy()

    def segment_customers(self) -> None:
        feature_cols = ["Recency", "Frequency", "Monetary"]
        features = self.customers[feature_cols].clip(lower=0)
        transformed = np.log1p(features)
        scaler = StandardScaler()
        scaled = scaler.fit_transform(transformed)

        self.cluster_count = min(4, len(self.customers))
        model = KMeans(n_clusters=self.cluster_count, random_state=42, n_init=10, max_iter=300)
        self.customers["Cluster"] = model.fit_predict(scaled)
        if self.cluster_count > 1 and len(self.customers) > self.cluster_count:
            try:
                self.silhouette = float(silhouette_score(
                    scaled, self.customers["Cluster"], sample_size=min(1000, len(self.customers)), random_state=42
                ))
            except Exception:
                self.silhouette = None

        profile = self.customers.groupby("Cluster").agg(
            Customers=("CustomerID", "count"),
            AvgRecency=("Recency", "mean"),
            AvgFrequency=("Frequency", "mean"),
            AvgMonetary=("Monetary", "mean"),
            AvgOrderValue=("AverageOrderValue", "mean"),
        )
        # Rank the unsupervised clusters by RFM behaviour, then attach readable business labels.
        recency_rank = profile["AvgRecency"].rank(pct=True, ascending=True)
        frequency_rank = profile["AvgFrequency"].rank(pct=True, ascending=True)
        monetary_rank = profile["AvgMonetary"].rank(pct=True, ascending=True)
        profile["BusinessScore"] = frequency_rank + monetary_rank + (1 - recency_rank)
        ranked = profile.sort_values("BusinessScore", ascending=False).index.tolist()
        names = ["Champions", "Regular Customers", "Occasional Buyers", "At-Risk Customers"]
        mapping = {}
        if len(ranked) == 4:
            mapping = {cluster: name for cluster, name in zip(ranked, names)}
        elif len(ranked) == 3:
            mapping = {ranked[0]: names[0], ranked[1]: names[1], ranked[2]: names[3]}
        else:
            mapping = {ranked[0]: names[0], ranked[-1]: names[-1]}
        self.customers["Segment"] = self.customers["Cluster"].map(mapping).fillna("Occasional Buyers")
        profile["Segment"] = profile.index.map(mapping).fillna("Occasional Buyers")
        profile["Share"] = profile["Customers"] / len(self.customers) * 100
        self.profiles = profile.reset_index().sort_values(
            "Segment", key=lambda s: s.map({name: i for i, name in enumerate(SEGMENT_ORDER)}).fillna(99)
        )
        self.customers["Segment"] = pd.Categorical(self.customers["Segment"], categories=SEGMENT_ORDER, ordered=True)
        self.customers = self.customers.sort_values(["Segment", "Monetary"], ascending=[True, False]).reset_index(drop=True)

        # Keep a compact, business-friendly customer feature table for inspection and download.
        self.customers.drop(columns=["LastPurchase"]).to_csv(BASE_DIR / "customer_segments.csv", index=False)
        self.profiles.to_csv(BASE_DIR / "segment_profiles.csv", index=False)

        self.elbow = self._elbow_curve(scaled)
        self._make_charts(scaled)

    def _elbow_curve(self, scaled: np.ndarray) -> pd.DataFrame:
        max_k = min(7, len(scaled) - 1)
        rows = []
        for k in range(2, max_k + 1):
            model = KMeans(n_clusters=k, random_state=42, n_init=10, max_iter=250)
            model.fit(scaled)
            rows.append({"K": k, "Inertia": float(model.inertia_)})
        return pd.DataFrame(rows)

    def _make_charts(self, scaled: np.ndarray) -> None:
        sns.set_theme(style="whitegrid", font_scale=0.9)
        plot_df = self.customers.copy()
        plot_df["ScaledRecency"] = scaled[:, 0]
        plot_df["ScaledFrequency"] = scaled[:, 1]
        plot_df["ScaledMonetary"] = scaled[:, 2]
        palette = {
            "Champions": "#D8F36A",
            "Regular Customers": "#62D8C7",
            "Occasional Buyers": "#7F9CF5",
            "At-Risk Customers": "#FF946E",
        }

        fig, ax = plt.subplots(figsize=(8.4, 4.5))
        sns.scatterplot(data=plot_df, x="ScaledFrequency", y="ScaledMonetary", hue="Segment",
                        hue_order=SEGMENT_ORDER, palette=palette, s=48, alpha=0.78, linewidth=0, ax=ax)
        ax.set_title("Customer clusters · frequency vs monetary value", loc="left", weight="bold", pad=14)
        ax.set_xlabel("Scaled purchase frequency")
        ax.set_ylabel("Scaled monetary value")
        ax.legend(title="Customer segment", frameon=False, loc="best", fontsize=8)
        fig.tight_layout()
        fig.savefig(BASE_DIR / "segment_scatter.png", dpi=150, bbox_inches="tight")
        plt.close(fig)

        counts = self.customers["Segment"].value_counts().reindex(SEGMENT_ORDER).dropna().reset_index()
        counts.columns = ["Segment", "Customers"]
        fig, ax = plt.subplots(figsize=(8.4, 4.5))
        sns.barplot(data=counts, x="Segment", y="Customers", hue="Segment", palette=palette,
                    legend=False, ax=ax)
        ax.set_title("Customer mix by segment", loc="left", weight="bold", pad=14)
        ax.set_xlabel("")
        ax.set_ylabel("Customers")
        ax.tick_params(axis="x", rotation=12)
        fig.tight_layout()
        fig.savefig(BASE_DIR / "segment_mix.png", dpi=150, bbox_inches="tight")
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(8.4, 4.5))
        if not self.elbow.empty:
            sns.lineplot(data=self.elbow, x="K", y="Inertia", marker="o", linewidth=2.5,
                         color="#6688F5", ax=ax)
        ax.axvline(self.cluster_count, color="#F28B63", linestyle="--", linewidth=1.4,
                   label=f"Selected K = {self.cluster_count}")
        ax.set_title("Elbow method · choosing the number of clusters", loc="left", weight="bold", pad=14)
        ax.set_xlabel("Number of clusters (K)")
        ax.set_ylabel("Within-cluster sum of squares")
        ax.legend(frameon=False)
        fig.tight_layout()
        fig.savefig(BASE_DIR / "elbow_curve.png", dpi=150, bbox_inches="tight")
        plt.close(fig)

    def build_product_matrix(self) -> None:
        product_totals = self.cleaned.groupby("Description")["Quantity"].sum().sort_values(ascending=False)
        top_products = product_totals.head(180).index
        rows = self.cleaned[self.cleaned["Description"].isin(top_products)]
        matrix = rows.pivot_table(index="CustomerID", columns="Description", values="Quantity", aggfunc="sum", fill_value=0)
        self.product_matrix = matrix.astype(float)

    def build_summary(self) -> None:
        order_totals = self.cleaned.groupby("InvoiceNo")["TotalPrice"].sum()
        revenue = float(self.cleaned["TotalPrice"].sum())
        orders = int(self.cleaned["InvoiceNo"].nunique())
        self.summary = {
            "customers": int(self.customers["CustomerID"].nunique()),
            "orders": orders,
            "revenue": revenue,
            "averageOrderValue": float(order_totals.mean()) if len(order_totals) else 0.0,
            "transactionLines": int(len(self.cleaned)),
            "products": int(self.cleaned["Description"].nunique()),
            "countries": int(self.cleaned["Country"].nunique()),
            "silhouette": self.silhouette,
            "clusterCount": int(self.cluster_count),
            "dataSource": self.source_label,
            "dateRange": {
                "from": self.cleaned["InvoiceDate"].min().strftime("%d %b %Y"),
                "to": self.cleaned["InvoiceDate"].max().strftime("%d %b %Y"),
            },
        }

    def run(self) -> "AnalyticsEngine":
        self.load_and_clean()
        self.build_rfm()
        self.segment_customers()
        self.build_product_matrix()
        self.build_summary()
        return self

    def dashboard_payload(self) -> dict:
        segments = []
        for _, row in self.profiles.iterrows():
            name = str(row["Segment"])
            segments.append({
                "name": name,
                "customers": int(row["Customers"]),
                "share": round(float(row["Share"]), 1),
                "avgRecency": round(float(row["AvgRecency"]), 1),
                "avgFrequency": round(float(row["AvgFrequency"]), 1),
                "avgMonetary": round(float(row["AvgMonetary"]), 2),
                "avgOrderValue": round(float(row["AvgOrderValue"]), 2),
                "summary": SEGMENT_NOTES.get(name, {}).get("summary", "Customer group identified by K-Means."),
                "action": SEGMENT_NOTES.get(name, {}).get("action", "Review this segment's buying patterns."),
            })
        top_customers = self.customers.head(10).copy()
        customer_rows = []
        for _, row in top_customers.iterrows():
            customer_rows.append({
                "customerId": str(row["CustomerID"]),
                "segment": str(row["Segment"]),
                "recency": int(row["Recency"]),
                "frequency": int(row["Frequency"]),
                "monetary": round(float(row["Monetary"]), 2),
                "country": str(row["Country"]),
            })
        return {"summary": self.summary, "segments": segments, "featuredCustomers": customer_rows}

    def customer_payload(self, limit: int = 250, search: str = "") -> list[dict]:
        frame = self.customers
        if search:
            matched = frame[frame["CustomerID"].astype(str).str.contains(re.escape(search), case=False, na=False)]
            frame = matched
        frame = frame.head(max(1, min(limit, 1000)))
        return [{
            "customerId": str(row.CustomerID),
            "segment": str(row.Segment),
            "recency": int(row.Recency),
            "frequency": int(row.Frequency),
            "monetary": round(float(row.Monetary), 2),
            "country": str(row.Country),
        } for row in frame.itertuples(index=False)]

    def recommendation_payload(self, customer_id: str) -> dict:
        customer_id = str(customer_id)
        if customer_id not in self.product_matrix.index:
            raise DataValidationError(f"Customer {customer_id} was not found in the product purchase table.")
        customer = self.customers[self.customers["CustomerID"].astype(str) == customer_id].iloc[0]
        matrix = self.product_matrix
        similarity = cosine_similarity(matrix.loc[[customer_id]], matrix).ravel()
        similarity_series = pd.Series(similarity, index=matrix.index).drop(index=customer_id, errors="ignore")
        similar = similarity_series.sort_values(ascending=False).head(6)
        similar = similar[similar > 0]

        bought = matrix.loc[customer_id]
        bought_names = bought[bought > 0].sort_values(ascending=False).head(5).index.tolist()
        recommendations = []
        if not similar.empty:
            neighbour_rows = matrix.loc[similar.index]
            weighted_scores = neighbour_rows.mul(similar, axis=0).sum(axis=0)
            weighted_scores = weighted_scores[bought.eq(0)].sort_values(ascending=False)
            recommendations = [
                {"product": str(name), "score": round(float(score), 3)}
                for name, score in weighted_scores.head(6).items() if score > 0
            ]
        if len(recommendations) < 4:
            popular = self.cleaned.groupby("Description")["Quantity"].sum().sort_values(ascending=False)
            for name, score in popular.items():
                if bought.get(name, 0) == 0 and name not in [item["product"] for item in recommendations]:
                    recommendations.append({"product": str(name), "score": round(float(score), 3)})
                if len(recommendations) >= 6:
                    break

        similar_customers = []
        for other_id, score in similar.head(5).items():
            other = self.customers[self.customers["CustomerID"].astype(str) == str(other_id)]
            similar_customers.append({"customerId": str(other_id), "similarity": round(float(score), 3),
                                      "segment": str(other.iloc[0]["Segment"]) if not other.empty else "Customer"})
        segment = str(customer["Segment"])
        return {
            "customer": {
                "customerId": customer_id,
                "segment": segment,
                "recency": int(customer["Recency"]),
                "frequency": int(customer["Frequency"]),
                "monetary": round(float(customer["Monetary"]), 2),
                "country": str(customer["Country"]),
            },
            "purchasedProducts": [str(name) for name in bought_names],
            "recommendations": recommendations,
            "similarCustomers": similar_customers,
            "method": "Cosine similarity across customer purchase profiles",
            "segmentAction": SEGMENT_NOTES.get(segment, {}).get("action", "Review customer purchase patterns."),
        }

    def recent_transactions(self, limit: int = 25) -> list[dict]:
        frame = self.cleaned.sort_values("InvoiceDate", ascending=False).head(max(1, min(limit, 100)))
        return [{
            "invoice": str(row.InvoiceNo),
            "date": row.InvoiceDate.strftime("%d %b %Y, %H:%M"),
            "customerId": str(row.CustomerID),
            "product": str(row.Description),
            "quantity": int(row.Quantity),
            "unitPrice": round(float(row.UnitPrice), 2),
            "total": round(float(row.TotalPrice), 2),
            "country": str(row.Country),
        } for row in frame.itertuples(index=False)]

    def export_csv(self, kind: str) -> str:
        if kind == "segments":
            return self.customers.drop(columns=["LastPurchase"]).to_csv(index=False)
        if kind == "profiles":
            return self.profiles.to_csv(index=False)
        if kind == "cleaned":
            return self.cleaned.to_csv(index=False)
        raise ValueError("Unknown export type")
