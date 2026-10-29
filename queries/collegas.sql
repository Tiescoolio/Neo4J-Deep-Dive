SELECT DISTINCT collega.person_id, collega.name
FROM acted_in AS noor
JOIN acted_in AS samen ON samen.movie_id = noor.movie_id
JOIN person AS collega ON collega.person_id = samen.person_id
WHERE noor.person_id = 'P27'
  AND collega.person_id <> 'P27'
ORDER BY collega.name, collega.person_id;
