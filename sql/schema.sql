-- Uitsluitend voor de afzonderlijke database film_demo.
DO $$ BEGIN
  IF current_database() <> 'film_demo' THEN
    RAISE EXCEPTION 'Gebruik uitsluitend de database film_demo.';
  END IF;
END $$;
CREATE TABLE IF NOT EXISTS person (
  person_id text PRIMARY KEY,
  name text NOT NULL
);
CREATE TABLE IF NOT EXISTS movie (
  movie_id text PRIMARY KEY,
  title text NOT NULL,
  genre text NOT NULL,
  samenvatting text NOT NULL,
  source_id text NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS acted_in (
  person_id text NOT NULL REFERENCES person(person_id),
  movie_id text NOT NULL REFERENCES movie(movie_id),
  PRIMARY KEY (person_id, movie_id)
);
CREATE INDEX IF NOT EXISTS acted_in_movie_person ON acted_in(movie_id, person_id);
