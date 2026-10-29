-- Gegenereerd uit data/films.json; wijzig de bron, niet dit bestand.

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


BEGIN;

INSERT INTO person (person_id, name) VALUES
('P27', 'Noor'),
('P28', 'Amir'),
('P29', 'Sara'),
('P30', 'Luca')
ON CONFLICT DO NOTHING;

INSERT INTO movie (movie_id, title, genre, source_id, samenvatting) VALUES
('M1', 'Laatste Ronde', 'actie', 'S1', 'Een jonge bokser probeert na een zware nederlaag terug te keren in de ring. Met hulp van een onverwachte trainingspartner bereidt hij zich voor op zijn laatste kans op een titel.'),
('M2', 'Tweede Naam', 'thriller', 'S2', 'Een vrouw bouwt na een vlucht een nieuw leven op onder andermans naam. Wanneer haar verleden opduikt, moet ze kiezen tussen haar aangenomen identiteit en de waarheid.'),
('M3', 'Zomerlicht', 'drama', 'S3', 'Twee familieleden keren terug naar hun geboortedorp om een geërfd huis op te knappen. Tijdens de zomer ontdekken ze waarom hun familie jarenlang uit elkaar bleef.'),
('M4', 'Schaduwspel', 'thriller', 'S4', 'Een koerier ontdekt dat iemand zijn identiteit gebruikt. Hij neemt zelf een andere naam aan om de dader te vinden en raakt steeds verder verstrikt in een leven dat niet van hem is.')
ON CONFLICT DO NOTHING;

INSERT INTO acted_in (person_id, movie_id) VALUES
('P27', 'M1'),
('P28', 'M1'),
('P28', 'M2'),
('P29', 'M2'),
('P29', 'M3'),
('P30', 'M3'),
('P30', 'M4')
ON CONFLICT DO NOTHING;

COMMIT;

ANALYZE person;

ANALYZE movie;

ANALYZE acted_in;
