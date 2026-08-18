import os
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors
from rapidfuzz import process, fuzz

DATASET_PATH = os.path.join(os.path.dirname(__file__), "anime-dataset-2023.csv")

class AnimeEngine:
    def __init__(self, csv_path=DATASET_PATH):
        print(f"Loading dataset from: {csv_path}")
        self.df = pd.read_csv(csv_path)
        self._prepare_data()
        self._build_tfidf()
        self._extract_unique_options()
        print("Anime Engine initialized successfully.")

    def _prepare_data(self):
        # Convert Score and Scored By to numeric
        self.df["Score"] = pd.to_numeric(self.df["Score"], errors="coerce")
        self.df["Scored By"] = pd.to_numeric(self.df["Scored By"], errors="coerce")

        # Fill missing values
        self.df["Score_missing"] = self.df["Score"].isna().astype(int)
        self.df["Score"] = self.df["Score"].fillna(self.df["Score"].median())
        self.df["Scored By"] = self.df["Scored By"].fillna(0)

        # Calculate weighted score (Bayesian average)
        R = self.df["Score"]
        v = self.df["Scored By"]
        C = self.df["Score"].mean()
        m = self.df["Scored By"].quantile(0.75)
        self.df["weighted_score"] = (R * v + C * m) / (v + m)

        # Scale metrics for final score
        scaler = MinMaxScaler()
        # Invert Popularity so lower rank = higher scaled value
        pop_max = self.df["Popularity"].max()
        self.df["Popularity_scaled"] = scaler.fit_transform(
            (pop_max - self.df["Popularity"]).values.reshape(-1, 1)
        )
        self.df["weighted_score_scaled"] = scaler.fit_transform(
            self.df[["weighted_score"]]
        )

        self.df["final_score"] = (
            0.85 * self.df["weighted_score_scaled"] +
            0.15 * self.df["Popularity_scaled"]
        )

        # Pre-clean string columns
        for col in ["Name", "English name", "Genres", "Type", "Studios", "Rating", "Synopsis", "Image URL"]:
            if col in self.df.columns:
                self.df[col] = self.df[col].astype(str).fillna("UNKNOWN")

    def _build_tfidf(self):
        # Build TF-IDF vectorizer for content matching (from app2.ipynb)
        clean_df = self.df[self.df["Type"].str.upper() != "UNKNOWN"].copy()
        genres_clean = clean_df["Genres"].str.replace(",", " ")
        combined = genres_clean + " " + clean_df["Type"] + " " + clean_df["Studios"]
        
        self.tfidf = TfidfVectorizer(stop_words="english")
        self.tfidf_matrix = self.tfidf.fit_transform(combined)
        self.tfidf_df_index = clean_df.index.tolist()

        # Nearest Neighbors model for content recommendations
        self.nn = NearestNeighbors(n_neighbors=250, metric="cosine")
        self.nn.fit(self.tfidf_matrix)

        # Title mappings for fast fuzzy search
        self.titles_dict = {}
        for idx, row in self.df.iterrows():
            name = str(row["Name"]).strip()
            eng_name = str(row["English name"]).strip()
            if name and name.upper() != "UNKNOWN":
                self.titles_dict[name.lower()] = idx
            if eng_name and eng_name.upper() != "UNKNOWN":
                self.titles_dict[eng_name.lower()] = idx

        self.all_title_keys = list(self.titles_dict.keys())

    def _extract_unique_options(self):
        # Unique option extractor from app3.ipynb
        def get_unique(column):
            values = (
                self.df.loc[self.df[column].str.upper() != "UNKNOWN", column]
                .dropna()
                .astype(str)
                .str.split(",")
                .explode()
                .str.strip()
            )
            values = values[values != ""]
            return sorted(values.unique(), key=str.lower)

        self.unique_genres = get_unique("Genres")
        self.unique_types = get_unique("Type")
        self.unique_studios = get_unique("Studios")
        self.unique_ratings = get_unique("Rating")

    def get_options(self):
        return {
            "genres": self.unique_genres,
            "types": self.unique_types,
            "studios": self.unique_studios,
            "ratings": self.unique_ratings
        }

    def _get_best_title_match(self, title, score_cutoff=60):
        query = title.lower().strip()
        if query in self.titles_dict:
            return self.titles_dict[query], query, 100.0

        match = process.extractOne(
            query,
            self.all_title_keys,
            scorer=fuzz.WRatio,
            score_cutoff=score_cutoff
        )
        if match:
            matched_key, score, _ = match
            return self.titles_dict[matched_key], matched_key, score
        return None, None, 0.0

    def autocomplete_titles(self, query, limit=10):
        q = query.lower().strip()
        if not q:
            return []
        matches = process.extract(
            q,
            self.all_title_keys,
            scorer=fuzz.WRatio,
            limit=limit
        )
        results = []
        seen_ids = set()
        for matched_key, score, _ in matches:
            idx = self.titles_dict[matched_key]
            if idx not in seen_ids:
                seen_ids.add(idx)
                row = self.df.iloc[idx]
                results.append({
                    "anime_id": int(row["anime_id"]),
                    "name": row["Name"],
                    "english_name": row["English name"] if row["English name"] != "UNKNOWN" else "",
                    "score": float(row["Score"]) if pd.notna(row["Score"]) else None
                })
        return results

    def _row_to_dict(self, row):
        return {
            "anime_id": int(row["anime_id"]),
            "name": str(row["Name"]),
            "english_name": str(row["English name"]) if str(row["English name"]).upper() != "UNKNOWN" else "",
            "image_url": str(row["Image URL"]),
            "score": round(float(row["Score"]), 2) if pd.notna(row["Score"]) else "N/A",
            "genres": str(row["Genres"]),
            "type": str(row["Type"]),
            "episodes": str(row["Episodes"]),
            "studios": str(row["Studios"]),
            "rating": str(row["Rating"]),
            "synopsis": str(row["Synopsis"]),
            "popularity": int(row["Popularity"]) if pd.notna(row["Popularity"]) else "N/A"
        }

    # -------------------------------------------------------------
    # Search by Title (app2.ipynb logic)
    # -------------------------------------------------------------
    def recommend_by_title(self, title, top_n=100):
        matched_idx, matched_title, match_score = self._get_best_title_match(title)
        if matched_idx is None:
            return {"status": "error", "message": f"Anime '{title}' not found.", "results": []}

        matched_row = self.df.iloc[matched_idx]
        
        # Check if index in tfidf matrix
        if matched_idx in self.tfidf_df_index:
            tfidf_pos = self.tfidf_df_index.index(matched_idx)
            distances, indices = self.nn.kneighbors(self.tfidf_matrix[tfidf_pos], n_neighbors=top_n + 1)
            rec_indices = [self.tfidf_df_index[i] for i in indices[0][1:]]
        else:
            # Fallback to genre similarity
            genres = [g.strip() for g in str(matched_row["Genres"]).split(",") if g.strip()]
            res = self.recommend_by_genres(genres, top_n=top_n + 1)
            rec_indices = [r["anime_id"] for r in res.get("results", []) if r["anime_id"] != matched_row["anime_id"]]

        results = [self._row_to_dict(matched_row)]  # include searched anime first
        for idx in rec_indices:
            row = self.df.iloc[idx]
            if int(row["anime_id"]) != int(matched_row["anime_id"]):
                results.append(self._row_to_dict(row))
            if len(results) >= top_n + 1:
                break

        return {
            "status": "success",
            "matched_anime": str(matched_row["Name"]),
            "match_score": round(match_score, 1),
            "results": results
        }

    # -------------------------------------------------------------
    # Metadata Helper Functions (app3.ipynb logic)
    # -------------------------------------------------------------
    def _as_list(self, values):
        if values is None:
            return []
        if isinstance(values, str):
            return [values]
        return list(values)

    def _split_values(self, value):
        if pd.isna(value):
            return []
        return [item.strip().lower() for item in str(value).split(",") if item.strip()]

    def _match_inputs(self, values, choices, label):
        matched = []
        choice_map = {choice.lower(): choice for choice in choices}
        for val in self._as_list(values):
            val_clean = str(val).lower().strip()
            if not val_clean:
                continue
            if val_clean in choice_map:
                matched.append(choice_map[val_clean].lower().strip())
            else:
                m = process.extractOne(val_clean, choice_map.keys(), scorer=fuzz.WRatio, score_cutoff=70)
                if m:
                    matched.append(m[0].lower().strip())
        return set(matched)

    def _metadata_recommend(self, column, values, top_n=100, label=None):
        label = label or column
        choices_map = {
            "Genres": self.unique_genres,
            "Type": self.unique_types,
            "Studios": self.unique_studios,
            "Rating": self.unique_ratings
        }
        choices = choices_map.get(column, self.unique_genres)
        selected = self._match_inputs(values, choices, label)

        if not selected:
            return {"status": "error", "message": f"No valid {label.lower()} found.", "results": []}

        sub_df = self.df[self.df[column].str.upper() != "UNKNOWN"].copy()
        col_sets = sub_df[column].apply(lambda v: set(self._split_values(v)))
        sub_df["metadata_score"] = col_sets.apply(lambda r_vals: len(selected & r_vals) / len(selected))
        
        filtered = sub_df[sub_df["metadata_score"] > 0].copy()
        if filtered.empty:
            return {"status": "error", "message": f"No anime matched selected {label.lower()}.", "results": []}

        filtered["recommendation_score"] = 0.7 * filtered["metadata_score"] + 0.3 * filtered["final_score"]
        top_recs = filtered.nlargest(top_n, "recommendation_score")

        results = [self._row_to_dict(row) for _, row in top_recs.iterrows()]
        return {"status": "success", "mode": "individual", "filter_type": label, "results": results}

    # -------------------------------------------------------------
    # Individual Recommendation API endpoints (app3.ipynb)
    # -------------------------------------------------------------
    def recommend_by_genres(self, genres, top_n=100):
        return self._metadata_recommend("Genres", genres, top_n=top_n, label="Genre")

    def recommend_by_type(self, type_name, top_n=100):
        return self._metadata_recommend("Type", type_name, top_n=top_n, label="Type")

    def recommend_by_studios(self, studios, top_n=100):
        return self._metadata_recommend("Studios", studios, top_n=top_n, label="Studio")

    def recommend_by_rating(self, rating, top_n=100):
        return self._metadata_recommend("Rating", rating, top_n=top_n, label="Rating")

    # -------------------------------------------------------------
    # Hybrid Metadata Recommendation (app3.ipynb)
    # -------------------------------------------------------------
    def hybrid_metadata_recommend(self, genres=None, type_name=None, studios=None, rating=None, top_n=100):
        filters = {
            "Genres": self._match_inputs(genres, self.unique_genres, "Genre"),
            "Type": self._match_inputs(type_name, self.unique_types, "Type"),
            "Studios": self._match_inputs(studios, self.unique_studios, "Studio"),
            "Rating": self._match_inputs(rating, self.unique_ratings, "Rating"),
        }
        active_filters = {col: selected for col, selected in filters.items() if selected}

        if not active_filters:
            return {"status": "error", "message": "No valid metadata filters selected.", "results": []}

        # If only 1 filter category active, call individual function
        if len(active_filters) == 1:
            col_name = list(active_filters.keys())[0]
            val_selected = list(active_filters[col_name])
            if col_name == "Genres":
                return self.recommend_by_genres(val_selected, top_n=top_n)
            elif col_name == "Type":
                return self.recommend_by_type(val_selected, top_n=top_n)
            elif col_name == "Studios":
                return self.recommend_by_studios(val_selected, top_n=top_n)
            elif col_name == "Rating":
                return self.recommend_by_rating(val_selected, top_n=top_n)

        # Mixed filter selected -> Hybrid metadata algorithm
        recommendations = self.df.copy()
        score_cols = []

        for col, selected in active_filters.items():
            sc_col = f"{col.lower()}_match_score"
            score_cols.append(sc_col)
            recommendations[sc_col] = recommendations[col].apply(
                lambda val: len(selected & set(self._split_values(val))) / len(selected)
            )

        recommendations["metadata_score"] = recommendations[score_cols].mean(axis=1)
        filtered = recommendations[recommendations["metadata_score"] > 0].copy()

        if filtered.empty:
            return {"status": "error", "message": "No anime matches the combination of selected filters.", "results": []}

        filtered["recommendation_score"] = 0.7 * filtered["metadata_score"] + 0.3 * filtered["final_score"]
        top_recs = filtered.nlargest(top_n, "recommendation_score")

        results = [self._row_to_dict(row) for _, row in top_recs.iterrows()]
        return {"status": "success", "mode": "hybrid", "active_filters": list(active_filters.keys()), "results": results}
