"""Kleine weergavehulpen voor leesbare, statische notebookoutputs."""
import html
import json
from IPython.display import HTML, Markdown, display


def table(rows):
    if not rows:
        display(Markdown('*Geen rijen opgehaald.*'))
        return
    columns = list(rows[0])
    header = ''.join('<th>'+html.escape(str(k))+'</th>' for k in columns)
    body = ''.join('<tr>'+''.join('<td>'+html.escape(str(row.get(k,'')))+'</td>' for k in columns)+'</tr>' for row in rows)
    display(HTML('<table><thead><tr>'+header+'</tr></thead><tbody>'+body+'</tbody></table>'))


def pg_rows(node, depth=0):
    rows = [{'stap':'  '*depth+node['Node Type'], 'object':node.get('Relation Name',node.get('Index Name','')),
             'werkelijke_rijen':node.get('Actual Rows'), 'lussen':node.get('Actual Loops')}]
    for child in node.get('Plans',[]):
        rows.extend(pg_rows(child,depth+1))
    return rows


def neo_rows(node, depth=0):
    rows = [{'stap':'  '*depth+node.get('operatorType','').split('@')[0],
             'werkelijke_rijen':node.get('rows',node.get('records',node.get('args',{}).get('Rows'))), 'DB_hits':node.get('dbHits'),
             'details':node.get('args',{}).get('Details','')}]
    for child in node.get('children',[]):
        rows.extend(neo_rows(child,depth+1))
    return rows


def route_overview(route):
    table([json.loads(item['content']) for item in route['items']])
    display(Markdown('**Werkelijk uitgevoerde zoekquery of queryketen**'))
    for call in route['zoekqueries']:
        display(Markdown('```cypher\n'+call['cypher']+'\n```'))
        print(json.dumps(call['parameters'],ensure_ascii=False,indent=2))


def route_answer(route):
    display(Markdown('**Exacte context voor de antwoordgenerator**'))
    print(route['exacte_context'])
    display(Markdown('**Werkelijk gegenereerd antwoord**\n\n'+route['antwoord']))


def explain_plans(results):
    pg = {row['stap'].strip() for row in pg_rows(results['postgres_plan']['Plan'])}
    neo = {row['stap'].strip() for row in neo_rows(results['neo4j_plan'])}
    pg_scan = sorted(t for t in pg if 'Scan' in t)
    pg_join = sorted(t for t in pg if 'Join' in t or 'Loop' in t)
    neo_scan = sorted(t for t in neo if 'Scan' in t or 'Seek' in t)
    expands = sorted(t for t in neo if 'Expand' in t)
    display(Markdown(
        '**Dit koos deze uitvoering werkelijk:**\n\n'
        f'- PostgreSQL: toegang via **{", ".join(pg_scan)}**; koppeling via **{", ".join(pg_join)}**. '
        'De planner kiest deze combinatie voor de huidige tabellen, indexen en statistieken.\n'
        f'- Neo4j: beginpunt via **{", ".join(neo_scan)}**; relatie-uitbreiding via **{", ".join(expands)}**. '
        'Een index-zoekactie wordt dus alleen genoemd als die echt in dit plan staat.\n'
        '- Sortering en ontdubbelen horen ook bij de query; een logisch pad is niet het volledige fysieke plan.\n'
        '- Rijen en DB hits zijn verschillende meeteenheden. PostgreSQL-bufferhits zijn geen Neo4j-DB hits.'))
