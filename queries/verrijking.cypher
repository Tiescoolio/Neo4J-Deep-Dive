MATCH (noor:Person {person_id: $noor_id})-[:ACTED_IN]->(gedeeld:Movie)
      <-[:ACTED_IN]-(acteur:Person)-[:ACTED_IN]->(node)
WHERE acteur <> noor
RETURN node.movie_id AS movie_id, node.title AS title,
       node.samenvatting AS samenvatting, node.source_id AS source_id,
       score, acteur.name AS acteur, acteur.person_id AS acteur_id,
       gedeeld.title AS gedeelde_film, gedeeld.movie_id AS gedeelde_film_id,
       gedeeld.source_id AS gedeelde_bron, noor.name AS noor
ORDER BY score DESC, movie_id, acteur_id;
