
import streamlit as st
import pickle
import pandas as pd
import requests
import time

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# =====================================
# 1. PAGE CONFIGURATION
# =====================================

st.set_page_config(
    page_title="CinePick 5",
    page_icon="🎬",
    layout="wide"
)

# =====================================
# 2. TMDB API KEY
# =====================================

API_KEY = st.secrets["TMDB_API_KEY"]

# =====================================
# 3. API SESSION WITH RETRY
# =====================================

@st.cache_resource
def create_session():

    session = requests.Session()

    retry_strategy = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)

    session.mount("https://", adapter)
    session.mount("http://", adapter)

    return session


session = create_session()

# =====================================
# 4. CUSTOM CSS
# =====================================

st.markdown("""
<style>

.stApp {
    background: linear-gradient(135deg, #080914, #17132b);
    color: white;
}

h1, h2, h3, p, label {
    color: white !important;
}

.main-title {
    font-size: 48px;
    font-weight: bold;
    color: white;
}

.subtitle {
    font-size: 20px;
    color: #c7c5e8;
}

.stButton > button {
    background: linear-gradient(90deg, #713bea, #963ff0);
    color: white;
    border: none;
    border-radius: 12px;
    padding: 12px 25px;
    font-size: 18px;
    width: 100%;
}

.stButton > button:hover {
    background: #9b5cff;
    color: white;
}

</style>
""", unsafe_allow_html=True)


# =====================================
# 5. LOAD MOVIE DATA
# =====================================

@st.cache_data
def load_movies():

    with open("movie_dict.pkl", "rb") as file:
        movie_dict = pickle.load(file)

    return pd.DataFrame(movie_dict)


@st.cache_resource
def load_similarity():

    with open("similarity.pkl", "rb") as file:
        return pickle.load(file)


movies = load_movies()
similarity = load_similarity()


# =====================================
# 6. RECOMMENDATION FUNCTION
# =====================================

def recommend(name):

    matches = movies[
        movies["title"].astype(str).str.strip().str.lower()
        == name.strip().lower()
    ]

    if matches.empty:
        return []

    movie_index = matches.index[0]

    distances = similarity[movie_index]

    movie_list = sorted(
        enumerate(distances),
        reverse=True,
        key=lambda x: x[1]
    )[1:6]

    recommended_movies = []

    for i in movie_list:

        recommended_movies.append(
            movies.iloc[i[0]]["title"]
        )

    return recommended_movies


# =====================================
# 7. FETCH MOVIE DETAILS FROM TMDB
# =====================================

def fetch_movie_details(movie_name):

    url = "https://api.themoviedb.org/3/search/movie"

    params = {
        "api_key": API_KEY,
        "query": movie_name,
        "language": "en-US",
        "include_adult": False
    }

    try:

        response = session.get(
            url,
            params=params,
            timeout=(10, 25)
        )

        response.raise_for_status()

        data = response.json()

        results = data.get("results", [])

        if not results:

            return {
                "success": False,
                "error": "Movie not found in TMDB.",
                "title": movie_name,
                "overview": "",
                "poster": None,
                "rating": 0,
                "release_date": ""
            }

        # Prefer exact movie title
        movie = next(
            (
                item for item in results
                if item.get("title", "").strip().lower()
                == movie_name.strip().lower()
            ),
            results[0]
        )

        poster_path = movie.get("poster_path")

        poster = None

        if poster_path:

            poster = (
                "https://image.tmdb.org/t/p/w500"
                + poster_path
            )

        return {
            "success": True,
            "error": None,
            "title": movie.get("title", movie_name),
            "overview": movie.get("overview")
            or "Description not available.",
            "poster": poster,
            "rating": movie.get("vote_average", 0),
            "release_date": movie.get("release_date", "")
        }

    except requests.HTTPError as e:

        status = (
            e.response.status_code
            if e.response is not None
            else "Unknown"
        )

        return {
            "success": False,
            "error": f"TMDB HTTP Error: {status}",
            "title": movie_name,
            "overview": "",
            "poster": None,
            "rating": 0,
            "release_date": ""
        }

    except requests.Timeout:

        return {
            "success": False,
            "error": "Request timed out. Check your internet.",
            "title": movie_name,
            "overview": "",
            "poster": None,
            "rating": 0,
            "release_date": ""
        }

    except requests.RequestException as e:

        return {
            "success": False,
            "error": f"Connection error: {str(e)}",
            "title": movie_name,
            "overview": "",
            "poster": None,
            "rating": 0,
            "release_date": ""
        }

    except ValueError:

        return {
            "success": False,
            "error": "Invalid response from TMDB.",
            "title": movie_name,
            "overview": "",
            "poster": None,
            "rating": 0,
            "release_date": ""
        }


# =====================================
# 8. APPLICATION HEADING
# =====================================

st.markdown(
    '<div class="main-title">🎬 Movie Recommender System</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">Find movies similar to your favourite movie!</div>',
    unsafe_allow_html=True
)

st.write("")
st.divider()


# =====================================
# 9. TEST TMDB CONNECTION
# =====================================

with st.expander("🔧 Test TMDB API Connection"):

    if st.button("Test API"):

        with st.spinner("Checking TMDB connection..."):

            result = fetch_movie_details("Iron Man 3")

        if result["success"]:

            st.success("TMDB API connected successfully!")

            st.write("Movie:", result["title"])
            st.write("Rating:", result["rating"])

            if result["poster"]:
                st.image(result["poster"], width=150)

        else:

            st.error(result["error"])


# =====================================
# 10. MOVIE SELECTION
# =====================================

st.subheader("🎥 Select Your Favourite Movie")

selected_movie = st.selectbox(
    "Choose a movie",
    movies["title"].dropna().values,
    label_visibility="collapsed"
)

st.write("")


# =====================================
# 11. RECOMMEND BUTTON
# =====================================

if st.button("⭐ Recommend Movies"):

    recommendations = recommend(selected_movie)

    if recommendations:

        st.markdown("## ⭐ Recommended Movies")

        cols = st.columns(5)

        for col, movie_name in zip(cols, recommendations):

            with col:

                with st.container(border=True):

                    with st.spinner(f"Loading {movie_name}..."):

                        details = fetch_movie_details(movie_name)

                    st.markdown(f"**{details['title']}**")

                    if details["success"]:

                        if details["poster"]:

                            st.image(
                                details["poster"],
                                use_container_width=True
                            )

                        else:

                            st.info("Poster not available")

                        st.caption(details["overview"])

                        rating = details["rating"]

                        if rating:
                            st.write(f"⭐ {rating:.1f}/10")
                        else:
                            st.write("⭐ Rating unavailable")

                        release_date = details["release_date"]

                        if release_date:
                            st.write(f"📅 {release_date[:4]}")
                        else:
                            st.write("📅 Year unavailable")

                    else:

                        st.warning("Movie details unavailable")

                        st.caption(details["error"])

                        st.write("Try again later.")

    else:

        st.warning("No recommendations found!")


# =====================================
# 12. FOOTER
# =====================================

st.divider()

st.markdown(
    "<center>🎬 Movie Recommender System | Powered by TMDB</center>",
    unsafe_allow_html=True
)
