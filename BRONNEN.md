# Bronnen, versies en betekenis van de uitvoer

Geraadpleegd op 28 oktober 2026. De filmcatalogus en bronfiches S1–S4 zijn fictief;
onderstaande primaire bronnen onderbouwen de technische uitleg, niet de filmfeiten.
Versiegebonden details zijn daarnaast gecontroleerd in de geïnstalleerde package.

## Databases en queryomgevingen

- [PostgreSQL 18: EXPLAIN](https://www.postgresql.org/docs/18/using-explain.html):
  geschatte plannen tegenover werkelijk uitvoeren met ANALYZE; buffer- en tijdinformatie
  zijn metingen van een specifieke uitvoering.
- [PostgreSQL 18: constraints](https://www.postgresql.org/docs/18/ddl-constraints.html):
  primaire sleutels, verwijzende sleutels en unieke waarden.
- [pgAdmin 4: Query Tool](https://www.pgadmin.org/docs/pgadmin4/9.18/query_tool.html).
- [Neo4j Desktop: Query](https://neo4j.com/docs/desktop/current/query/).
- [Neo4j: queryplannen](https://neo4j.com/docs/cypher-manual/current/planning-and-tuning/execution-plans/):
  EXPLAIN voert niet uit, PROFILE wel. DB hits zijn geen milliseconden.
- [Neo4j: opslagformaten](https://neo4j.com/docs/operations-manual/current/database-internals/store-formats/):
  een klassiek recorddiagram beschrijft niet automatisch blockopslag of live RAM-adressen.
- [Neo4j: constraints](https://neo4j.com/docs/cypher-manual/current/schema/constraints/):
  de demo gebruikt zakelijke ID's met uniekheidsregels.

## Officiële Neo4j GraphRAG-package

Getest: `neo4j-graphrag 1.23.0`; gebruikte query's staan bovendien letterlijk in de uitvoer.

- [RAG-handleiding](https://neo4j.com/docs/neo4j-graphrag-python/current/user_guide_rag.html).
- [API-overzicht](https://neo4j.com/docs/neo4j-graphrag-python/current/api.html).
- [VectorRetriever en VectorCypherRetriever: implementatie](https://neo4j.com/docs/neo4j-graphrag-python/current/_modules/neo4j_graphrag/retrievers/vector.html).
- [HybridRetriever en HybridCypherRetriever: implementatie](https://neo4j.com/docs/neo4j-graphrag-python/current/_modules/neo4j_graphrag/retrievers/hybrid.html).
- [Text2CypherRetriever: implementatie](https://neo4j.com/docs/neo4j-graphrag-python/current/_modules/neo4j_graphrag/retrievers/text2cypher.html).
- [GraphRAG: implementatie](https://neo4j.com/docs/neo4j-graphrag-python/current/_modules/neo4j_graphrag/generation/graphrag.html).
- [Gegenereerde zoekquery's](https://github.com/neo4j/neo4j-graphrag-python/blob/main/src/neo4j_graphrag/neo4j_queries.py).
- [Metadatafiltering](https://github.com/neo4j/neo4j-graphrag-python/blob/main/src/neo4j_graphrag/filters.py).
- [Neo4j-vectorindexen](https://neo4j.com/docs/cypher-manual/current/indexes/search-indexes/vector-indexes/).

In deze versie gebruikt Hybrid standaard `ranker='naive'`: iedere branch normaliseert
met zijn eigen maximum; per film wordt de hoogste genormaliseerde branchescore gebruikt.
Dat is geen reciprocal rank fusion. Een andere ranker bestaat, maar wordt hier niet gebruikt.

Vectorfilters hebben afhankelijk van de mogelijkheden van de index en filteroperatoren
een in-indexpad of een exact cosine-pad. De gebruikte index heeft geen genre-filterproperty;
de daadwerkelijke filterquery is zichtbaar. Hybrid heeft hier geen `filters`-parameter.
De vaste Cypher-verrijking filtert na selectie/fusion. De ondersteuning van een nieuwere
database is niet automatisch gelijk aan de mogelijkheden van deze packageversie.

GraphRAG bouwt context uit `item.content`; `item.metadata` wordt niet automatisch aan het
model toegevoegd. Daarom zet deze demo bron-ID's expliciet in de leesbare content.
Text2Cypher bevat in deze versie een EXPLAIN-controle op alleen-lezen queries. De demo
gebruikt daarnaast een databaseaccount met een afzonderlijke leesrol en expliciet geweigerde writes.

## Modellen en vectorindexen

- [EmbeddingGemma: officiële modelkaart](https://ai.google.dev/gemma/docs/embeddinggemma/model_card):
  meertaligheid, modelmogelijkheden en aanbevolen taakprefixen.
- [EmbeddingGemma in Ollama](https://ollama.com/library/embeddinggemma).
- [Gemma 4 26B in Ollama](https://ollama.com/library/gemma4:26b).
- [Ollama: embeddings](https://docs.ollama.com/capabilities/embeddings).
- [Malkov & Yashunin: HNSW-paper](https://arxiv.org/abs/1603.09320):
  *Efficient and robust approximate nearest neighbor search using Hierarchical Navigable Small World graphs*.

De lokale embeddinginput is bewust alleen de ongewijzigde samenvatting. Ook vragen gaan
als ruwe tekst naar hetzelfde embeddingmodel. Dit wijkt af van gebruik van taakprefixen;
het is een transparante invoerkeuze, geen claim over optimale retrievalkwaliteit.
Modeldigest en dimensie worden opgeslagen/gecontroleerd, omdat een `latest`-tag later kan veranderen.

De HNSW-, lijst- en skiplistafbeelding is een vereenvoudigde didactische illustratie.
De lagen vormen correcte deelverzamelingen. Zij is niet uit de daadwerkelijke vectorindex geëxporteerd
en toont geen fysieke adressen. `ACTED_IN`-relaties vertegenwoordigen expliciete filmfeiten;
indexranden vertegenwoordigen nabijheid tussen vectoren.

De vaste verrijkingsquery is getoetst met de inhoudelijke kandidaten M2 en M4, beide
verschillend van de gedeelde film M1. Cypher gebruikt binnen één MATCH een relatie
niet tweemaal. Wie dit patroon later wil uitbreiden naar het geval waarin gevonden
film en gedeelde film dezelfde zijn, moet de acteur→gevonden-film-stap in een
afzonderlijke MATCH zetten. Deze begrenzing verandert geen antwoord in de meegeleverde fixture.

## Wat is echt uitgevoerd?

- `artifacts/uitvoering.json` bevat de daadwerkelijke resultaten en plannen van de notebookuitvoering.
- De teruggegeven zoekquery's en scores zijn afkomstig uit echte databasecalls.
- Contexten en antwoorden zijn echte applicatie-uitvoer van lokale modellen; onjuistheden
  of ontbrekend bewijs worden niet achteraf omgeschreven tot een gewenst antwoord.
- `assets/plannen.*` krijgt uitsluitend de werkelijk teruggegeven operatorbomen als invoer.
- De andere afbeeldingen zijn gelabelde schema's, reproduceerbaar met `figures.py`.
- Er wordt geen prestatieverhouding tussen de databases berekend. Eventuele ruwe server-/profieltijden
  horen bij één uitvoering na de gewone query; cache, profilering en clientoverhead verhinderen
  een algemene snelheidsconclusie.

De bovenliggende bibliotheken houden hun eigen licenties. De repository neemt geen
broncode van die pakketten over. Productnamen en primaire bronverwijzingen blijven behouden.
