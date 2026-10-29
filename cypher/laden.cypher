// Gegenereerd uit data/films.json; kies uitsluitend database film-demo.

// Uitsluitend voor de afzonderlijke database film-demo.
CREATE CONSTRAINT person_id_unique IF NOT EXISTS
FOR (p:Person) REQUIRE p.person_id IS UNIQUE;
CREATE CONSTRAINT movie_id_unique IF NOT EXISTS
FOR (m:Movie) REQUIRE m.movie_id IS UNIQUE;


UNWIND [{person_id: "P27", name: "Noor"},
{person_id: "P28", name: "Amir"},
{person_id: "P29", name: "Sara"},
{person_id: "P30", name: "Luca"}] AS rij
MERGE (n:Person {person_id: rij.person_id})
ON CREATE SET n += rij;

UNWIND [{movie_id: "M1", title: "Laatste Ronde", genre: "actie", source_id: "S1", samenvatting: "Een jonge bokser probeert na een zware nederlaag terug te keren in de ring. Met hulp van een onverwachte trainingspartner bereidt hij zich voor op zijn laatste kans op een titel."},
{movie_id: "M2", title: "Tweede Naam", genre: "thriller", source_id: "S2", samenvatting: "Een vrouw bouwt na een vlucht een nieuw leven op onder andermans naam. Wanneer haar verleden opduikt, moet ze kiezen tussen haar aangenomen identiteit en de waarheid."},
{movie_id: "M3", title: "Zomerlicht", genre: "drama", source_id: "S3", samenvatting: "Twee familieleden keren terug naar hun geboortedorp om een geërfd huis op te knappen. Tijdens de zomer ontdekken ze waarom hun familie jarenlang uit elkaar bleef."},
{movie_id: "M4", title: "Schaduwspel", genre: "thriller", source_id: "S4", samenvatting: "Een koerier ontdekt dat iemand zijn identiteit gebruikt. Hij neemt zelf een andere naam aan om de dader te vinden en raakt steeds verder verstrikt in een leven dat niet van hem is."}] AS rij
MERGE (n:Movie {movie_id: rij.movie_id})
ON CREATE SET n += rij;

UNWIND [{person_id: "P27", movie_id: "M1"}, {person_id: "P28", movie_id: "M1"}, {person_id: "P28", movie_id: "M2"}, {person_id: "P29", movie_id: "M2"}, {person_id: "P29", movie_id: "M3"}, {person_id: "P30", movie_id: "M3"}, {person_id: "P30", movie_id: "M4"}] AS rij
MATCH (p:Person {person_id: rij.person_id}), (m:Movie {movie_id: rij.movie_id})
MERGE (p)-[:ACTED_IN]->(m);
