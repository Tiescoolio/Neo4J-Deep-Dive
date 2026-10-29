"""Inladen en controleren van uitsluitend de afgebakende filmdemo."""
import argparse
import json
import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv
from neo4j import GraphDatabase

ROOT = Path(__file__).resolve().parent
QUESTION_A = 'Met wie speelde Noor samen in een film?'
QUESTION_B = 'Welke films gaan over iemand die onder een andere identiteit leeft? Leg uit waarom.'
QUESTION_C = 'Welke film gaat over iemand die onder een andere identiteit leeft én heeft een acteur die met Noor samenspeelde? Onderbouw je antwoord.'


def catalogue():
    return json.loads((ROOT / 'data/films.json').read_text(encoding='utf-8'))


def query(name):
    return (ROOT / 'queries' / name).read_text(encoding='utf-8').strip().rstrip(';')


def settings():
    load_dotenv(ROOT / '.env')
    keys = ('PG_DSN', 'NEO4J_URI', 'NEO4J_DATABASE', 'NEO4J_USERNAME', 'NEO4J_PASSWORD',
            'NEO4J_READER_USERNAME', 'NEO4J_READER_PASSWORD', 'OLLAMA_HOST', 'EMBEDDING_MODEL', 'LLM_MODEL')
    result = {key: os.getenv(key, '') for key in keys}
    if not all(result.values()):
        raise RuntimeError('Vul de lokale .env in volgens .env.example; toon wachtwoorden niet in notebookoutputs.')
    if result['NEO4J_DATABASE'] != 'film-demo':
        raise RuntimeError('Deze demo gebruikt uitsluitend Neo4j-database film-demo.')
    return result


def graph(s, read_only=True):
    prefix = 'NEO4J_READER_' if read_only else 'NEO4J_'
    return GraphDatabase.driver(s['NEO4J_URI'], auth=(s[prefix + 'USERNAME'], s[prefix + 'PASSWORD']),
                                connection_timeout=10, connection_acquisition_timeout=30)


def postgres(s):
    conn = psycopg.connect(s['PG_DSN'], connect_timeout=10, row_factory=dict_row)
    if conn.execute('SELECT current_database() AS db').fetchone()['db'] != 'film_demo':
        conn.close()
        raise RuntimeError('Deze demo gebruikt uitsluitend PostgreSQL-database film_demo.')
    conn.commit()
    return conn


def literal(value):
    return "'" + str(value).replace("'", "''") + "'"


def generated_files():
    """GUI-scripts en leesbare bronfiches komen altijd uit dezelfde JSON-bron."""
    data = catalogue()
    pg = ['-- Gegenereerd uit data/films.json; wijzig de bron, niet dit bestand.',
          (ROOT / 'sql/schema.sql').read_text(encoding='utf-8'), 'BEGIN;']
    for table, rows in [('person', data['persons']), ('movie', data['movies']), ('acted_in', data['acted_in'])]:
        columns = list(rows[0])
        values = ',\n'.join('(' + ', '.join(literal(row[c]) for c in columns) + ')' for row in rows)
        pg.append(f"INSERT INTO {table} ({', '.join(columns)}) VALUES\n{values}\nON CONFLICT DO NOTHING;")
    pg += ['COMMIT;', 'ANALYZE person;', 'ANALYZE movie;', 'ANALYZE acted_in;']
    cy = ['// Gegenereerd uit data/films.json; kies uitsluitend database film-demo.',
          (ROOT / 'cypher/schema.cypher').read_text(encoding='utf-8')]
    for label, rows, key in [('Person', data['persons'], 'person_id'), ('Movie', data['movies'], 'movie_id')]:
        maps = ',\n'.join('{' + ', '.join(k + ': ' + json.dumps(v, ensure_ascii=False) for k, v in row.items()) + '}' for row in rows)
        cy.append(f'UNWIND [{maps}] AS rij\nMERGE (n:{label} {{{key}: rij.{key}}})\nON CREATE SET n += rij;')
    maps = ', '.join('{' + ', '.join(k + ': ' + json.dumps(v) for k, v in row.items()) + '}' for row in data['acted_in'])
    cy.append(f'UNWIND [{maps}] AS rij\nMATCH (p:Person {{person_id: rij.person_id}}), (m:Movie {{movie_id: rij.movie_id}})\nMERGE (p)-[:ACTED_IN]->(m);')
    files = {'sql/laden.sql': '\n\n'.join(pg) + '\n', 'cypher/laden.cypher': '\n\n'.join(cy) + '\n'}
    names = {p['person_id']: p['name'] for p in data['persons']}
    for movie in data['movies']:
        cast = ', '.join(names[r['person_id']] for r in data['acted_in'] if r['movie_id'] == movie['movie_id'])
        files[f"sources/{movie['source_id']}.md"] = (
            f"# {movie['source_id']} — {movie['title']}\n\nFictieve bronfiche voor onderwijs; geen extern geverifieerde filmfeiten.\n\n"
            f"- **Film-ID:** {movie['movie_id']}\n- **Genre:** {movie['genre']}\n- **Cast:** {cast}\n"
            f"- **Bron-ID:** {movie['source_id']}\n\n## Samenvatting\n\n{movie['samenvatting']}\n")
    return files


def prepare_files():
    for name, content in generated_files().items():
        target = ROOT / name
        target.parent.mkdir(exist_ok=True)
        target.write_text(content, encoding='utf-8')


def check_data(s):
    data = catalogue()
    with postgres(s) as conn, graph(s) as driver:
        for table, key, id_key in [('person', 'persons', 'person_id'), ('movie', 'movies', 'movie_id'), ('acted_in', 'acted_in', 'person_id, movie_id')]:
            actual = conn.execute(f'SELECT * FROM {table} ORDER BY {id_key}').fetchall()
            expected = sorted(data[key], key=lambda r: tuple(r[k.strip()] for k in id_key.split(',')))
            assert actual == expected, f'PostgreSQL: afwijkende inhoud in {table}'
        for label, key, props, id_key in [
            ('Person', 'persons', '{.person_id, .name}', 'person_id'),
            ('Movie', 'movies', '{.movie_id, .title, .genre, .samenvatting, .source_id}', 'movie_id')]:
            records = driver.execute_query(f'MATCH (n:{label}) RETURN n {props} AS row ORDER BY n.{id_key}',
                                            database_=s['NEO4J_DATABASE']).records
            assert [r['row'] for r in records] == sorted(data[key], key=lambda r:r[id_key]), f'Neo4j: afwijkende {label}-gegevens'
        records = driver.execute_query('MATCH (p:Person)-[:ACTED_IN]->(m:Movie) RETURN p.person_id AS person_id, m.movie_id AS movie_id ORDER BY person_id, movie_id', database_=s['NEO4J_DATABASE']).records
        assert [r.data() for r in records] == sorted(data['acted_in'], key=lambda r:(r['person_id'],r['movie_id']))
        total = driver.execute_query('MATCH (n) RETURN count(n) AS aantal', database_=s['NEO4J_DATABASE']).records[0]['aantal']
        assert total == 8, 'Onverwachte extra knopen in film-demo'
    return {'personen': 4, 'films': 4, 'deelnames': 7, 'inhoud_gelijk': True}


def load_data(s):
    prepare_files()
    with postgres(s) as conn:
        conn.execute((ROOT / 'sql/laden.sql').read_text(encoding='utf-8'))
    with graph(s, read_only=False) as driver:
        for statement in (ROOT / 'cypher/laden.cypher').read_text(encoding='utf-8').split(';\n'):
            if statement.strip():
                driver.execute_query(statement, database_=s['NEO4J_DATABASE'])
    return check_data(s)


def create_reader(s):
    if s['NEO4J_READER_USERNAME'] != 'film_demo_reader':
        raise RuntimeError('Gebruik de afzonderlijke demogebruiker film_demo_reader.')
    with graph(s,read_only=False) as driver:
        users = driver.execute_query('SHOW USERS YIELD user, roles WHERE user = $name RETURN roles',name='film_demo_reader',database_='system').records
        if users and not set(users[0]['roles']) <= {'PUBLIC','film_demo_reader_role'}:
            raise RuntimeError('Bestaande gebruiker heeft andere rollen. Deze demo verandert die gebruiker niet.')
        driver.execute_query('CREATE ROLE film_demo_reader_role IF NOT EXISTS',database_='system')
        driver.execute_query('CREATE USER film_demo_reader IF NOT EXISTS SET PASSWORD $password CHANGE NOT REQUIRED SET HOME DATABASE `film-demo`',password=s['NEO4J_READER_PASSWORD'],database_='system')
        for command in [
            'GRANT ACCESS ON DATABASE `film-demo` TO film_demo_reader_role',
            'GRANT MATCH {*} ON GRAPH `film-demo` ELEMENTS * TO film_demo_reader_role',
            'GRANT SHOW INDEX ON DATABASE `film-demo` TO film_demo_reader_role',
            'DENY WRITE ON GRAPH * TO film_demo_reader_role',
            'GRANT ROLE film_demo_reader_role TO film_demo_reader']:
            driver.execute_query(command,database_='system')
    with graph(s) as driver:
        driver.verify_connectivity()
    return {'leesaccount':'film_demo_reader', 'schrijven':'expliciet geweigerd', 'database':'film-demo'}


def answer_and_plans(s):
    with postgres(s) as conn, graph(s) as driver:
        conn.read_only = True
        rows = conn.execute(query('collegas.sql')).fetchall()
        pg_plan = conn.execute('EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) ' + query('collegas.sql')).fetchone()['QUERY PLAN'][0]
        records, summary, _ = driver.execute_query('PROFILE ' + query('collegas.cypher'), database_=s['NEO4J_DATABASE'])
        neo_rows = [r.data() for r in records]
        assert rows == neo_rows == [{'person_id': 'P28', 'name': 'Amir'}]
        version = conn.execute('SHOW server_version').fetchone()['server_version']
        components = driver.execute_query('CALL dbms.components() YIELD name, versions, edition RETURN name, versions, edition', database_=s['NEO4J_DATABASE']).records
        return {'sql': rows, 'cypher': neo_rows, 'postgres_plan': pg_plan,
                'neo4j_plan': summary.profile, 'postgres_version': version,
                'neo4j_components': [r.data() for r in components]}


def index_status(s, driver, dimension, required=True):
    records = driver.execute_query('SHOW INDEXES YIELD name, type, labelsOrTypes, properties, options, state '
                                   'WHERE name IN $names RETURN name, type, labelsOrTypes, properties, options, state',
                                   names=['film_vector','movie_text'], database_=s['NEO4J_DATABASE']).records
    found = {r['name']:r.data() for r in records}
    if required and set(found) != {'film_vector','movie_text'}:
        raise RuntimeError('De zoekindexen ontbreken. Voer eerst python film_demo.py embeddings uit.')
    for name, row in found.items():
        expected_type, expected_props = ('VECTOR',['embedding']) if name == 'film_vector' else ('FULLTEXT',['title','samenvatting'])
        if row['type'] != expected_type or row['labelsOrTypes'] != ['Movie'] or sorted(row['properties']) != sorted(expected_props):
            raise RuntimeError(f'{name} heeft een ander zoekoppervlak dan deze demo vereist.')
        if name == 'film_vector':
            config = row['options']['indexConfig']
            if config.get('vector.dimensions') != dimension or str(config.get('vector.similarity_function')).lower() != 'cosine':
                raise RuntimeError('De bestaande vectorindex heeft een andere dimensie of similariteitsfunctie.')
        if required and row['state'] != 'ONLINE':
            raise RuntimeError(f'{name} is nog niet ONLINE. Wacht op de indexopbouw.')
    return list(found.values())


def embedding_digest(embedder, model):
    return next(m.digest for m in embedder.client.list().models if m.model == model)


def check_embeddings(s, driver, embedder=None):
    from neo4j_graphrag.embeddings import OllamaEmbeddings
    embedder = embedder or OllamaEmbeddings(model=s['EMBEDDING_MODEL'],host=s['OLLAMA_HOST'])
    digest = embedding_digest(embedder,s['EMBEDDING_MODEL'])
    vector = embedder.embed_query(QUESTION_B)
    rows = driver.execute_query('MATCH (m:Movie) RETURN m.movie_id AS film, size(m.embedding) AS dimensie, '
                                 'm.embedding_model AS model, m.embedding_digest AS digest ORDER BY film',
                                 database_=s['NEO4J_DATABASE']).records
    if len(rows) != 4 or not all(r['dimensie']==len(vector) and r['model']==s['EMBEDDING_MODEL'] and r['digest']==digest for r in rows):
        raise RuntimeError('Ontbrekende of incompatibele embeddings: voer python film_demo.py embeddings opnieuw uit.')
    return {'dimensie':len(vector),'model':s['EMBEDDING_MODEL'],'modeldigest':digest,
            'films':[r.data() for r in rows], 'indexen':index_status(s,driver,len(vector))}


def prepare_embeddings(s):
    from neo4j_graphrag.embeddings import OllamaEmbeddings
    embedder = OllamaEmbeddings(model=s['EMBEDDING_MODEL'], host=s['OLLAMA_HOST'])
    movies = catalogue()['movies']
    vectors = [embedder.embed_query(movie['samenvatting']) for movie in movies]
    dimension = len(vectors[0])
    assert dimension > 0 and all(len(v) == dimension for v in vectors)
    digest = embedding_digest(embedder,s['EMBEDDING_MODEL'])
    with graph(s, read_only=False) as driver:
        # De binding tussen model en index wordt op de films bijgehouden.
        index_status(s,driver,dimension,required=False)
        driver.execute_query('UNWIND $rows AS row MATCH (m:Movie {movie_id:row.id}) SET m.embedding=row.vector, m.embedding_model=$model, m.embedding_digest=$digest',
                             rows=[{'id':m['movie_id'],'vector':v} for m,v in zip(movies,vectors)], model=s['EMBEDDING_MODEL'], digest=digest, database_=s['NEO4J_DATABASE'])
        driver.execute_query(f"CREATE VECTOR INDEX film_vector IF NOT EXISTS FOR (m:Movie) ON (m.embedding) OPTIONS {{indexConfig: {{`vector.dimensions`: {dimension}, `vector.similarity_function`: 'cosine'}}}}", database_=s['NEO4J_DATABASE'])
        driver.execute_query('CREATE FULLTEXT INDEX movie_text IF NOT EXISTS FOR (m:Movie) ON EACH [m.title, m.samenvatting]', database_=s['NEO4J_DATABASE'])
        driver.execute_query('CALL db.awaitIndexes(120)', database_=s['NEO4J_DATABASE'])
        index_status(s,driver,dimension)
    return {'model':s['EMBEDDING_MODEL'], 'dimensie':dimension, 'films':len(vectors), 'input':'uitsluitend Movie.samenvatting, ongewijzigde tekst'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('actie', choices=['bestanden', 'laden', 'leesaccount', 'embeddings', 'controleren'])
    args = parser.parse_args()
    if args.actie == 'bestanden':
        prepare_files()
        print('Importscripts en bronfiches gegenereerd uit data/films.json.')
    else:
        config = settings()
        action = {'laden':load_data, 'leesaccount':create_reader, 'embeddings':prepare_embeddings, 'controleren':check_data}[args.actie]
        print(json.dumps(action(config), ensure_ascii=False, indent=2))
