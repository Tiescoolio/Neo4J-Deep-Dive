MATCH (noor:Person {person_id: 'P27'})-[:ACTED_IN]->(:Movie)
      <-[:ACTED_IN]-(collega:Person)
WHERE collega.person_id <> noor.person_id
RETURN DISTINCT collega.person_id AS person_id, collega.name AS name
ORDER BY name, person_id;
