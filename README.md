# AniVerse - Anime Recommendation System

A modern, web-based Anime Recommendation Application powered by Machine Learning algorithms (Content-Based TF-IDF, Collaborative Filtering, and Metadata Weighting).

Designed with a cyber/anime glassmorphism aesthetic, **AniVerse** provides instant recommendations via **Search by Title** and **Metadata Filters** (Genres, Types, Studios, Rating).

---

##  Features

###  1. Search by Title
- Real-time **Autocomplete Title Suggestions** using `rapidfuzz` string similarity.
- Content-Based TF-IDF cosine similarity vectorization & Nearest Neighbors algorithm derived from `app2.ipynb`.
- Generates recommendations matching plot, genres, and studio aesthetics.

###  2. Metadata Filters (Genres, Types, Studios, Rating)
- Dynamically populated from dataset unique values (`app3.ipynb` logic):
  - **Genres**: Action, Romance, Sci-Fi, Fantasy, Slice of Life, etc. (21 unique genres)
  - **Types**: TV, Movie, OVA, ONA, Special, Music
  - **Studios**: Kyoto Animation, Wit Studio, MAPPA, Bones, Madhouse, etc.
  - **Ratings**: G - All Ages, PG-13, R - 17+, R+, Rx
- **Smart Mode Auto-Routing**:
  - **Individual Function**: Triggers automatically when a single filter category is selected (`recommend_by_genres`, `recommend_by_type`, `recommend_by_studios`, `recommend_by_rating`).
  - **Hybrid Function**: Triggers automatically when mixed options are selected across multiple categories (`hybrid_metadata_recommend`).

###  3. 25-Per-Page Pagination & Configurable Limits
- **Recommendation Limit Selector**: Generate 50, 100, 150, or 200 recommendations per query.
- **Grid Layout**: Displays **25 anime cards per page** (Poster Image on top, Title/Name underneath).
- **Navigation Bar**: Includes Left Arrow (`←`), Page Numbers (`1`, `2`, `3`, `4`, ...), and Right Arrow (`→`).

###  4. Modern GUI & Aesthetics
- Glassmorphism containers (`backdrop-filter: blur(16px)`).
- Cyberpunk/Anime color palette (Deep Violet `#0a0714`, Neon Magenta `#ff2a75`, Electric Cyan `#00f2fe`, Gold `#ffb703`).
- Detail modal overlay for viewing full synopsis, episode count, scores, and high-res poster images.

---

## 📁 Project Structure

```
Anime Recommendation Sysytem/
├── anime-dataset-2023.csv      # Primary anime dataset (24,905 entries)
├── engine.py                   # Recommendation engine & ML algorithms
├── server.py                   # Flask REST API server
├── index.html                  # Main Web UI
├── style.css                   # Cyber/Anime styling & responsive layout
├── app.js                      # Frontend logic, API calls, & pagination
├── requirements.txt            # Required Python dependencies
├── README.md                   # Project documentation
├── app2.ipynb                  # Original Notebook for Content/Collaborative Filtering
└── app3.ipynb                  # Original Notebook for Metadata Filtering
```

---

##  Setup & Installation

### 1. Install Dependencies
Ensure Python 3.8+ is installed, then run:
```bash
pip install -r requirements.txt
```

### 2. Run Web Server
Launch the Flask backend server:
```bash
python server.py
```

### 3. Open in Browser
Open your browser and navigate to:
```
http://127.0.0.1:5000/
```

---

##  API Endpoints

- `GET /api/options`: Returns unique lists of Genres, Types, Studios, and Ratings.
- `GET /api/autocomplete?q=<query>`: Autocomplete title suggestions.
- `GET /api/search?title=<name>&top_n=100`: Search recommendations by anime title.
- `POST /api/filter`: Filter recommendations by Genres, Types, Studios, and Ratings. Accepts JSON:
  ```json
  {
    "genres": ["Romance"],
    "types": ["TV"],
    "studios": ["Kyoto Animation"],
    "ratings": ["PG-13 - Teens 13 or older"],
    "top_n": 100
  }
  ```
