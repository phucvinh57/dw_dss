from clickhouse_driver import Client
import csv
import resource
import sys


def get_memory():
    with open("/proc/meminfo", "r") as mem:
        free_memory = 0
        for i in mem:
            sline = i.split()
            if str(sline[0]) in ("MemFree:", "Buffers:", "Cached:"):
                free_memory += int(sline[1])
    return free_memory  # KiB


def set_memory_limit():
    """Limit max memory usage to half."""
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    # Convert KiB to bytes, and divide in two to half
    resource.setrlimit(resource.RLIMIT_AS, (get_memory() * 1024 / 3 * 2, hard))


DB_NAME = "movies"


def init_db():
    client = Client(host="localhost", port="9000")
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
    return client


def extract():
    readers = []
    sources = ["movies", "links", "genome-tags", "genome-scores"]
    for src in sources:
        reader = csv.reader(open(f"datasource/{src}.csv".format(src=src), "r"))
        next(reader)  # Skip header
        readers.append(reader)
    return readers


def etl_movies(readers):
    movies_reader, links_reader, _, __ = readers

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


# There are 232 930 872 records in genome-scores.csv, so need to split into chunks to insert into ClickHouse
def etl_genome_scores(readers):
    _, __, genome_tags_reader, genome_scores_reader = readers
    genome_tags = {}
    for row in genome_tags_reader:
        tag_id, tag_value = row
        tag_id = int(tag_id)
        genome_tags[tag_id] = tag_value

    scores = []
    i = 0
    for row in genome_scores_reader:
        movie_id, tag_id, relevance = int(row[0]), int(row[1]), float(row[2])

        tag_name = genome_tags.get(tag_id)
        scores.append((movie_id, tag_id, relevance, tag_name))

        if len(scores) == 200000:
            i += 200000
            client.execute("INSERT INTO genome_scores VALUES", scores)
            print(f"Inserted {i} genome scores into DB")
            scores.clear()


try:
    # set_memory_limit()
    client = init_db()
    readers = extract()
    etl_movies(readers)
    etl_genome_scores(readers)
except e:
    print(e)
    sys.exit(1)
