from flask import Flask, render_template, request, flash, redirect, session, jsonify

# from flask_sqlalchemy import SQLAlchemy
import bcrypt
import pickle
import pandas as pd
import requests as rq
from flask_mysqldb import MySQL
import MySQLdb.cursors
from urllib.parse import parse_qs

app = Flask(__name__)
app.secret_key = "secret_key"

app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = "password"
app.config["MYSQL_DB"] = "yaflix"

db = MySQL(app)


# Creating User Model
# class User(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(100), nullable=False)
#     email = db.Column(db.String(100), unique=True)
#     password = db.Column(db.String(100), nullable=False)

#     def __init__(self, name, email, password):
#         self.name = request.form["name"]
#         self.email = request.form["email"]
#         self.password = bcrypt.hashpw(
#             password.encode("utf-8"), bcrypt.gensalt(14)
#         ).decode("utf-8")

#     def check_password(self, password):
#         return bcrypt.checkpw(password.encode("utf-8"), self.password.encode("utf-8"))


# with app.app_context():
#     db.create_all()


# Showing user interest based movies
def recommend_movie(user_id):
    with open("datafiles/collabrative_similarity_score.pkl", "rb") as file:
        similarity_score = pickle.load(file)

    with open("datafiles/coll_movies.pkl", "rb") as file:
        movies = pickle.load(file)

    recomm_movies = sorted(
        list(enumerate(similarity_score[user_id])),
        key=lambda x: x[1],
        reverse=True,
    )[:6]
    movie_ids = [str(i[0]) for i in recomm_movies]

    recommended_movies = []

    for i in range(len(movie_ids)):
        movie_detail = []
        movie_detail.extend(
            list(
                movies[movies["id"] == movie_ids[i]][
                    ["id", "title", "vote_average", "poster_path"]
                ].values
            )
        )
        recommended_movies.append(movie_detail)
    return recommended_movies


def collabrativeMovieImage():
    
    url = "https://api.themoviedb.org/3/movie/145/images"

    headers = {
        "accept": "application/json",
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJiMGQ3ZTMwMjA0YzRjYzJiMWIxNjA3YjcwMzkxMzVkOSIsInN1YiI6IjYzZDQxN2JjZDlmNGE2MDA4ZmEwOGJmZSIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.xk9JB-8B-k5JdoKj05V9C4x8BceYQZmg8VPshTTF2-U"
    }

    response = requests.get(url, headers=headers)

    print(response.text)


@app.route("/")
def index():
    if session.get("user") is None:
        flash("Please login to enjoy yaFlix")
        return redirect("/login")
    else:
        with open("datafiles/display_movies.pkl", "rb") as file:
            dispaly_movies = pickle.load(file)
        user_id = session["user"]["id"]
        user_based_movies = recommend_movie(user_id)
        # print(user_based_movies)
        return render_template(
            "index.html",
            display_movies=dispaly_movies,
            user_based_movies=user_based_movies,
        )


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        hash_pass = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(14)).decode(
            "utf-8"
        )

        cursor = db.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute(
            """insert into users(name, email, password) values (%s, %s, %s)""",
            (name, email, hash_pass),
        )

        db.connection.commit()

        flash("User Added Successfully", "success")
        return redirect("/login")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        # {'id': 2, 'name': 'mohan', 'email': 'mohan@gmail.com', 'password': '$2b$14$tVVLabRi5ZB4yr2Jrfbu4uwGdqNE6I543TYPk2QMe3E3R8HU7bL/O', 'profile_photo': 'image'}
        # user = User.query.filter_by(email=email).first()
        cursor = db.connection.cursor(MySQLdb.cursors.DictCursor)

        cursor.execute("select * from users where email = %s", (email,))
        user_data = cursor.fetchone()

        if user_data:
            pw_check = bcrypt.checkpw(
                password.encode("utf-8"), user_data["password"].encode("utf-8")
            )
            if pw_check:
                session["user"] = user_data
                return redirect("/dashboard")
            else:
                flash("Password is wrong")
                # session.pop("user")
                return redirect("/login")
        else:
            flash("No user found with this Email")
            return redirect("/login")

    return render_template("login.html")


@app.route("/dashboard")
def userDashboard():
    if session.get("user") is not None:
        cursor = db.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute(
            "select * from users where email = %s", (session["user"]["email"],)
        )
        user_data = cursor.fetchone()
        return render_template("dashboard.html", user=user_data)
    else:
        return redirect("/login")


def getMoviePoster(movie_id):
    url = "https://api.themoviedb.org/3/movie/{}?api_key=b0d7e30204c4cc2b1b1607b7039135d9&language=en-us".format(
        movie_id
    )
    response = rq.get(url)
    response = response.json()
    poster_path = response["poster_path"]
    full_path = "https://image.tmdb.org/t/p/w500/" + poster_path
    return full_path


@app.route("/trending")
def trendingMovies():
    path = "C:/Users/HP/PythonScriptsML/trending_movies_20.pkl"
    with open(path, "rb") as file:
        movies = pickle.load(file)

    # print(movies)
    # movie_image = []
    # for i in movies['id'].items():
    #     movie_image.append(getMoviePoster(i[1]))

    return render_template("trendingmovies.html", movie_data=movies)


@app.route("/moviedetail/<movie_id>")
def openMovieDetails(movie_id):
    with open("datafiles/display_movies.pkl", "rb") as file:
        all_movies = pickle.load(file)

    key_value = 0
    for key, value in all_movies["movie_id"].items():
        # print(value)
        if int(movie_id) == int(value):
            key_value = key
            print("inside if")
            break

    movie_details_arr = []
    movie_details_arr.append(all_movies["title"][key_value])
    movie_details_arr.append(all_movies["genres"][key_value])
    movie_details_arr.append(all_movies["crew"][key_value])
    movie_details_arr.append(all_movies["cast"][key_value])
    movie_details_arr.append(all_movies["vote_average"][key_value])

    # print(movie_details_arr)

    # Recommend Movies Content Based
    similarity = pickle.load(open("datafiles/similarity.pkl", "rb"))
    movies_dict = pickle.load(open("datafiles/movies_dict.pkl", "rb"))
    movies = pd.DataFrame(movies_dict)
    # print(movies)
    movie_name = all_movies["title"][key_value]
    movie_index = movies[movies["title"] == movie_name].index[0]
    distances = similarity[movie_index]
    movie_list = sorted(list(enumerate(distances)), reverse=True, key=lambda x: x[1])[
        1:6
    ]

    recommend_movies = []
    recommend_movies_poster = []
    recommend_movies_id = []
    # return (movie_list)
    for i in movie_list:
        movie_ids = movies.iloc[i[0]]["movie_id"]
        movie_poster = "getMoviePoster(movie_id)"
        # time.sleep(3)
        recommend_movies.append(movies.iloc[i[0]].title)
        recommend_movies_poster.append(movie_poster)
        recommend_movies_id.append(movies.iloc[i[0]].movie_id)

    print(recommend_movies)

    return render_template(
        "singlemovie.html",
        movie_id=movie_id,
        movie_details=movie_details_arr,
        recommend_movies=recommend_movies,
        recommend_movies_poster=recommend_movies_poster,
        recommend_movies_id=recommend_movies_id,
    )


# add user review
@app.route("/sendreview", methods=["POST"])
def addReview():
    if request.method == "POST":
        datas = request.get_data()
        data = parse_qs(datas.decode("utf-8"))

        user_id = session["user"]["id"]
        movie_id = data["movie_id"]
        review = data["review"]
        rating = data["rating_count"]

        cursor = db.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute(
            "insert into ratings(user_id, movie_id, review, rating) values (%s, %s, %s, %s)",
            (user_id, movie_id, review, rating),
        )
        db.connection.commit()

        response = {"message": "Review added successfully", "status": "success"}

        return jsonify(response)
    else:
        return "Invalid input"


app.run(debug=True, port=5000)
