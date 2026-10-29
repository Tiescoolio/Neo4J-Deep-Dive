"""Vijf officiële retrievers, met zichtbare zoekqueries, context en lokale modeluitvoer."""
import json
from contextlib import contextmanager

from neo4j_graphrag.embeddings import OllamaEmbeddings
from neo4j_graphrag.generation import GraphRAG
from neo4j_graphrag.generation.prompts import RagTemplate
from neo4j_graphrag.llm import OllamaLLM
from neo4j_graphrag.retrievers import (VectorRetriever, HybridRetriever, VectorCypherRetriever,
                                      HybridCypherRetriever, Text2CypherRetriever)
from neo4j_graphrag.types import RetrieverResultItem

from film_demo import QUESTION_A, QUESTION_B, QUESTION_C, query, check_embeddings

SCHEMA = '''Node properties:
Person {person_id: STRING, name: STRING}
Movie {movie_id: STRING, title: STRING, genre: STRING, samenvatting: STRING, source_id: STRING, embedding: LIST<FLOAT>}
Relationships:
(:Person)-[:ACTED_IN]->(:Movie)
Constraints: Person.person_id is uniek; Movie.movie_id is uniek.
Genre is een property; er bestaat geen Genre-label.
Zakelijke identifier voor Noor in deze demo: P27. Dit is geen interne Neo4j-ID.'''

TEXT2CYPHER_PROMPT = '''Vertaal de vraag naar precies één leesbare Cypher-leesquery.
Gebruik alleen onderstaand schema. Geen mutaties, procedures of dynamische query-uitvoering.
Geef uitsluitend de query terug. Gebruik voor Noor person_id 'P27'.
Bij vragen naar collega's: sluit Noor uit, verwijder dubbelen en sorteer stabiel.
Retourneer precies de kolommen person_id, name, source_id, noor en gedeelde_film.
source_id is de bron-ID van de gedeelde film; noor is de naam van de startpersoon;
gedeelde_film is de titel van de gedeelde film. Zo is de betekenis van de opgehaalde feiten expliciet.
Schema:
{schema}
Voorbeelden:
{examples}
Vraag:
{query_text}'''

RAG_SYSTEM = '''Je beantwoordt Nederlandse vragen over fictieve films. Gebruik uitsluitend de meegeleverde broncontext.
Geef maximaal 100 woorden: eerst het antwoord, daarna de onderbouwing met bron-ID's zoals [S2].
Verzin geen castleden of relaties. Een ontbrekende relatie in de context betekent: onvoldoende bewijs voor die voorwaarde.
source_id onderbouwt de gevonden film; gedeelde_bron onderbouwt de gedeelde_film en de samenwerking daarin.
Een acteur mag in een andere gedeelde film met Noor hebben gespeeld; Noor hoeft niet in de gevonden film te spelen.
Een thematisch passende samenvatting bewijst geen samenwerking. Geef bij ontbrekend relatiebewijs dat expliciet aan.'''
RAG_PROMPT = '''BRONCONTEXT (JSON-regels, letterlijk opgehaald):
{context}
EINDE BRONCONTEXT
Voorbeelden: {examples}
BEANTWOORD NU DEZE VRAAG:
{query_text}'''


class RecordedLLM(OllamaLLM):
    """Leg echte applicatieprompts en antwoorden vast; geen vooraf geschreven antwoorden."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.calls = []

    def invoke(self, input, *args, **kwargs):
        response = super().invoke(input, *args, **kwargs)
        messages = input if isinstance(input, str) else [m.model_dump() if hasattr(m, 'model_dump') else m for m in input]
        self.calls.append({'input': messages, 'system_instruction': kwargs.get('system_instruction'), 'output':response.content})
        return response


def compact(value):
    if isinstance(value, (list, tuple)):
        if len(value) > 64 and all(isinstance(v, (int, float)) for v in value):
            return {'vector_dimensie':len(value), 'weergave':'vectorwaarden weggelaten; geen wijziging van zoekvector'}
        return [compact(v) for v in value]
    if isinstance(value, dict):
        return {k:compact(v) for k,v in value.items()}
    return value


@contextmanager
def query_trace(driver):
    """Registreer echte driveraanroepen; index-query's worden niet nagetekend."""
    original = driver.execute_query
    calls = []
    def record(*args, **kwargs):
        text = args[0] if args else kwargs.get('query_', '')
        params = dict(args[1]) if len(args) > 1 and isinstance(args[1], dict) else {}
        params.update(kwargs.get('parameters_', {}))
        params.update({k:v for k,v in kwargs.items() if not k.endswith('_')})
        calls.append({'cypher':str(text), 'parameters':compact(params)})
        return original(*args, **kwargs)
    driver.execute_query = record
    try:
        yield calls
    finally:
        driver.execute_query = original


def item(record):
    """Alle broninformatie komt in content: metadata gaat niet automatisch naar het LLM."""
    values = dict(record['node']) if 'node' in record.keys() else record.data()
    if 'score' in record.keys():
        values['score'] = record['score']
    values.pop('embedding', None)
    # Dit zijn uit databasekolommen geformatteerde feiten, geen voorgeschreven modelantwoord.
    if all(k in values for k in ('acteur','title','noor','gedeelde_film','gedeelde_bron','source_id')):
        values['relatiebewijs'] = [
            f"{values['acteur']} speelt in {values['title']} [{values['source_id']}].",
            f"{values['acteur']} en {values['noor']} spelen beiden in {values['gedeelde_film']} [{values['gedeelde_bron']}].",
        ]
    elif all(k in values for k in ('name','noor','gedeelde_film','source_id')):
        values['relatiebewijs'] = [
            f"{values['name']} en {values['noor']} spelen beiden in {values['gedeelde_film']} [{values['source_id']}]."
        ]
    return RetrieverResultItem(content=json.dumps(values, ensure_ascii=False, sort_keys=True),
                               metadata={k:values[k] for k in ('movie_id','source_id','score') if k in values})


def result_data(result):
    return {'items':[{'content':i.content, 'metadata':i.metadata} for i in result.items],
            'metadata':compact(result.metadata or {})}


def retrieve_all(s, driver):
    """Leesstap: geen imports of indexschrijfacties; de modelcalls zijn echt en lokaal."""
    embedder = OllamaEmbeddings(model=s['EMBEDDING_MODEL'], host=s['OLLAMA_HOST'])
    check_embeddings(s,driver,embedder)
    llm = RecordedLLM(model_name=s['LLM_MODEL'], host=s['OLLAMA_HOST'],
                      model_params={'options':{'temperature':0, 'num_ctx':8192, 'num_predict':400},
                                    'think':False, 'keep_alive':'10m'})
    common = {'driver':driver, 'embedder':embedder, 'neo4j_database':s['NEO4J_DATABASE'], 'result_formatter':item}
    props = ['movie_id','title','genre','samenvatting','source_id']
    vector = VectorRetriever(index_name='film_vector', return_properties=props, **common)
    hybrid = HybridRetriever(vector_index_name='film_vector', fulltext_index_name='movie_text', return_properties=props, **common)
    vc = VectorCypherRetriever(index_name='film_vector', retrieval_query=query('verrijking.cypher'), **common)
    hc = HybridCypherRetriever(vector_index_name='film_vector', fulltext_index_name='movie_text', retrieval_query=query('verrijking.cypher'), **common)
    t2c = Text2CypherRetriever(driver=driver, llm=llm, neo4j_schema=SCHEMA,
                              custom_prompt=TEXT2CYPHER_PROMPT, neo4j_database=s['NEO4J_DATABASE'], result_formatter=item)
    llm_digest = next(m.digest for m in embedder.client.list().models if m.model == s['LLM_MODEL'])
    output = {'model':s['LLM_MODEL'], 'modeldigest':llm_digest, 'embeddingmodel':s['EMBEDDING_MODEL'], 'top_k':2,
              'schema_voor_Text2Cypher':SCHEMA, 'routes':{}, 'kandidaten_vraag_C':{}}
    # Twee kandidaten op basis van de echte ranking; geen vaste film-ID-selectie.
    for name, retriever in [('Vector',vector),('Hybrid',hybrid)]:
        with query_trace(driver) as trace:
            result = retriever.search(query_text=QUESTION_C, top_k=2)
        output['kandidaten_vraag_C'][name] = {**result_data(result), 'zoekqueries':trace}
    configs = [('Vector',vector,QUESTION_B,{'top_k':2}), ('Hybrid',hybrid,QUESTION_B,{'top_k':2}),
               ('VectorCypher',vc,QUESTION_C,{'top_k':2,'query_params':{'noor_id':'P27'}}),
               ('HybridCypher',hc,QUESTION_C,{'top_k':2,'query_params':{'noor_id':'P27'}}),
               ('Text2Cypher',t2c,QUESTION_A,{})]
    template = RagTemplate(template=RAG_PROMPT,system_instructions=RAG_SYSTEM)
    for name, retriever, question, config in configs:
        first_call = len(llm.calls)
        with query_trace(driver) as trace:
            rag = GraphRAG(retriever=retriever, llm=llm, prompt_template=template)
            result = rag.search(query_text=question, retriever_config=config, return_context=True)
        retrieved = result.retriever_result
        output['routes'][name] = {'vraag':question, 'config':config, 'zoekqueries':trace,
                                  **result_data(retrieved), 'exacte_context':'\n'.join(i.content for i in retrieved.items),
                                  'modelcalls':llm.calls[first_call:], 'antwoord':result.answer}
    # Laat ook zien welke relatie-informatie een gewone vectorroute níet ophaalt.
    with query_trace(driver) as trace:
        result = GraphRAG(retriever=vector,llm=llm,prompt_template=template).search(
            query_text=QUESTION_C,retriever_config={'top_k':2},return_context=True)
    output['vector_zonder_relatiebewijs'] = {'vraag':QUESTION_C, 'exacte_context':'\n'.join(i.content for i in result.retriever_result.items),
                                            'antwoord':result.answer,'zoekqueries':trace}
    with query_trace(driver) as trace:
        filtered = vector.search(query_text=QUESTION_B,top_k=4,filters={'genre':{'$eq':'thriller'}})
    ids = {json.loads(i.content)['movie_id'] for i in filtered.items}
    assert ids == {'M2','M4'}, 'Beide thrillers moeten het propertyfilter overleven.'
    output['genre_filter'] = {**result_data(filtered), 'zoekqueries':trace,
                              'filter':{'genre':{'$eq':'thriller'}}}
    for name in ('VectorCypher','HybridCypher'):
        ids = {json.loads(i['content'])['movie_id'] for i in output['routes'][name]['items']}
        assert ids == {'M2'}, f'{name}: de relatievoorwaarde moet uitsluitend M2 selecteren.'
        assert all(json.loads(i['content'])['gedeelde_bron']=='S1' for i in output['routes'][name]['items'])
    assert 'Amir' in output['routes']['Text2Cypher']['exacte_context']
    return output
