from clickhouse_driver import Client
import csv

DB_NAME = "movies"
RECORDS_PER_CHUNK = 200000


def init_db(reset_db: bool = False):
    client = Client(host="localhost", port="9000")
    if reset_db:
        client.execute("DROP DATABASE IF EXISTS {db}".format(db=DB_NAME))
        client.execute("CREATE DATABASE IF NOT EXISTS {db}".format(db=DB_NAME))
        client.execute("USE {db}".format(db=DB_NAME))
        client.execute(
            """
            CREATE TABLE IF NOT EXISTS movies (
                id Int32,
                title String,
                genres Array(String),
                imdb_id Nullable(Int32),
                tmdb_id Nullable(Int32)
            ) ENGINE = MergeTree()
            PRIMARY KEY id
            """
        )
        client.execute(
            """
            CREATE TABLE IF NOT EXISTS genome_scores (
                movie_id Int32,
                tag_id Int32,
                relevance Float32,
                tag_name Nullable(String)
            ) ENGINE = MergeTree()
            PRIMARY KEY (movie_id, tag_id)
            """
        )
        client.execute(
            """
            CREATE TABLE IF NOT EXISTS ratings (
                user_id Int32,
                movie_id Int32,
                rating Float32,
                timestamp UInt32
            ) ENGINE = MergeTree()
            PRIMARY KEY (movie_id, user_id)
            """
        )
        client.execute(
            """
            CREATE TABLE IF NOT EXISTS tags (
                user_id Int32,
                movie_id Int32,
                tag String,
                timestamp UInt32
            ) ENGINE = MergeTree()
            PRIMARY KEY (movie_id, user_id)
            """
        )
    else:
        client.execute("USE {db}".format(db=DB_NAME))
    return client


def get_reader(filename):
    reader = csv.reader(open(filename, "r"))
    return reader


def etl_movies():
    movies_reader = get_reader("datasource/movies.csv")
    links_reader = get_reader("datasource/links.csv")
    next(movies_reader)
    next(links_reader)

    movies = {}
    for row in movies_reader:
        movie_id, title, genres = row
        movie_id = int(movie_id)
        genres = genres.split("|")
        movies[movie_id] = {
            "id": movie_id,
            "title": title,
            "genres": genres,
            "imdb_id": None,
            "tmdb_id": None,
        }

    for row in links_reader:
        movie_id, imdb_id, tmdb_id = [int(x) if len(x) > 0 else None for x in row]
        movies[movie_id]["imdb_id"] = imdb_id
        movies[movie_id]["tmdb_id"] = tmdb_id

    print(f"Inserting {len(movies)} movies into DB")
    client.execute("INSERT INTO movies VALUES", list(movies.values()))


def extract_genome_tags():
    genome_tags_reader = get_reader("datasource/genome-tags.csv")
    next(genome_tags_reader)
    genome_tags = {}
    for row in genome_tags_reader:
        tag_id, tag_value = row
        tag_id = int(tag_id)
        genome_tags[tag_id] = tag_value
    return genome_tags


def etl_genome_scores(genome_tags: dict):
    reader = get_reader("datasource/genome-scores.csv")

    next(reader)
    scores = []
    i = 0
    for row in reader:
        movie_id, tag_id, relevance = int(row[0]), int(row[1]), float(row[2])

        tag_name = genome_tags.get(tag_id)
        scores.append((movie_id, tag_id, relevance, tag_name))

        if len(scores) == RECORDS_PER_CHUNK:
            i += len(scores)
            client.execute("INSERT INTO genome_scores VALUES", scores)
            print(f"Inserted {i} genome scores into DB")
            scores.clear()

    if len(scores) > 0:
        i += len(scores)
        client.execute("INSERT INTO genome_scores VALUES", scores)
        print(f"Inserted {i} genome scores into DB")
        scores.clear()


def etl_tags():
    reader = get_reader("datasource/tags.csv")
    next(reader)
    tags = []
    i = 0
    for row in reader:
        user_id, movie_id, tag, timestamp = (
            int(row[0]),
            int(row[1]),
            row[2],
            int(row[3]),
        )
        tags.append((user_id, movie_id, tag, timestamp))

        if len(tags) == RECORDS_PER_CHUNK:
            i += len(tags)
            client.execute("INSERT INTO tags VALUES", tags)
            print(f"Inserted {i} tags into DB")
            tags.clear()

    if len(tags) > 0:
        i += len(tags)
        client.execute("INSERT INTO tags VALUES", tags)
        print(f"Inserted {i} tags into DB")
        tags.clear()


def etl_ratings():
    reader = get_reader("datasource/ratings.csv")
    next(reader)
    ratings = []
    i = 0
    for row in reader:
        user_id, movie_id, rating, timestamp = (
            int(row[0]),
            int(row[1]),
            float(row[2]),
            int(row[3]),
        )
        ratings.append((user_id, movie_id, rating, timestamp))

        if len(ratings) == RECORDS_PER_CHUNK:
            i += len(ratings)
            client.execute("INSERT INTO ratings VALUES", ratings)
            print(f"Inserted {i} ratings into DB")
            ratings.clear()

    if len(ratings) > 0:
        i += len(ratings)
        client.execute("INSERT INTO ratings VALUES", ratings)
        print(f"Inserted {i} ratings into DB")
        ratings.clear()


client = init_db(reset_db=True)
etl_movies()
etl_ratings()
etl_tags()

genome_tags = extract_genome_tags()
etl_genome_scores(genome_tags)
