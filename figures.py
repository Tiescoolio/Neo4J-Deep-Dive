"""Statische onderwijsfiguren. Alleen matplotlib; invoer komt van de demo-data."""
from pathlib import Path
import textwrap
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle

BG = '#0b1220'
PANEL = '#142035'
INK = '#edf3ff'
MUTED = '#a1b2c9'
PURPLE = '#b59aff'
BLUE = '#6eafff'
TEAL = '#56ddc6'
ORANGE = '#ffbe79'
EDGE = '#637795'


def _canvas(title, subtitle):
    fig, ax = plt.subplots(figsize=(16, 9), facecolor=BG)
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    ax.set(xlim=(0, 16), ylim=(0, 9))
    ax.axis('off')
    ax.text(.65, 8.43, title, color=INK, fontsize=25, weight='bold', va='center')
    ax.text(.65, 7.95, subtitle, color=MUTED, fontsize=11 if len(subtitle)>100 else 12, va='center', ha='left')
    ax.text(.65, .28, 'FILMS · VAN TABELLEN NAAR VERBANDEN', color=MUTED, fontsize=9)
    ax.text(15.35, .28, 'Onderwijsdemo', color=MUTED, fontsize=9, ha='right')
    return fig, ax


def _box(ax, x, y, w, h, title='', body='', color=BLUE, size=14):
    ax.add_patch(FancyBboxPatch((x,y), w,h, boxstyle='round,pad=0.02,rounding_size=0.15',
                              facecolor=PANEL, edgecolor=color, linewidth=1.3, zorder=0.5))
    if title:
        ax.text(x+.22, y+h-.25, title, color=color, fontsize=size, weight='bold', va='top', zorder=3)
    if body:
        ax.text(x+.22, y+h-.73, body, color=INK, fontsize=12, va='top', linespacing=1.6, zorder=3)


def _edge(ax, a, b, color=EDGE, arrow=False, lw=2, style='-'):
    ax.add_patch(FancyArrowPatch(a,b,arrowstyle='-|>' if arrow else '-', mutation_scale=14,
                                linewidth=lw, color=color, linestyle=style, zorder=1))


def _node(ax, xy, label, color, radius=.43, small=''):
    ax.add_patch(Circle(xy,radius, facecolor=PANEL, edgecolor=color, linewidth=2.3, zorder=3))
    ax.text(*xy,label,ha='center',va='center',color=INK,fontsize=12, weight='bold', zorder=4)
    if small:
        ax.text(xy[0],xy[1]-max(.72, radius+.17),small,ha='center',va='top',color=color,fontsize=11,zorder=4)


def _save(fig, name, out, assets):
    for ext in ('png','svg'):
        path=out / f'{name}.{ext}'
        fig.savefig(path, dpi=150, facecolor=BG)
        if ext == 'svg':
            # Matplotlib laat spaties aan het einde van padregels staan; normaliseer voor Git.
            path.write_text('\n'.join(line.rstrip() for line in path.read_text(encoding='utf-8').splitlines())+'\n', encoding='utf-8')
        assets[f'{name}.{ext}']=str(path)
    plt.close(fig)


def _graph(ax, data, x=.9, y=1.7, width=9.8, height=4.6):
    persons=data['persons']; movies=data['movies']
    positions={}
    for i,p in enumerate(persons):
        positions[p['person_id']] = (x+i*width/max(1,len(persons)-1), y+height)
    for i,m in enumerate(movies):
        positions[m['movie_id']] = (x+i*width/max(1,len(movies)-1), y)
    highlighted={('P27','M1'),('P28','M1')}
    for r in data['acted_in']:
        pair=(r['person_id'],r['movie_id'])
        _edge(ax,positions[pair[0]],positions[pair[1]],TEAL if pair in highlighted else EDGE,lw=2.6 if pair in highlighted else 1.8)
    for p in persons:
        _node(ax,positions[p['person_id']],p['name'],PURPLE,small=p['person_id'])
    for m in movies:
        _node(ax,positions[m['movie_id']],m['movie_id'],BLUE,small='\n'.join(textwrap.wrap(m['title'],16)))
    ax.text(x+width/2,y+height/2,'ACTED_IN',color=MUTED,fontsize=11,ha='center',bbox=dict(facecolor=BG,edgecolor='none',pad=4))


def _table(ax, x,y,w,title,columns,rows,color):
    h=.48*(len(rows)+1)+.65
    _box(ax,x,y,w,h,title,color=color)
    cell_width=w/len(columns)
    for j,col in enumerate(columns):
        ax.text(x+.16+j*cell_width,y+h-.88,col,color=MUTED,fontsize=10)
    for i,row in enumerate(rows):
        yy=y+h-1.35-i*.46
        for j,value in enumerate(row):
            ax.text(x+.16+j*cell_width,yy,str(value),color=INK,fontsize=10)


def _plan_rows(plan, postgres=False):
    """Preorder preserves the actual operator tree, including every child."""
    rows = []

    def visit(node, depth=0):
        if not isinstance(node, dict):
            return
        args = node.get('args', {})
        if not isinstance(args, dict):
            args = {}
        if postgres:
            operator = node.get('Node Type', '(Node Type ontbreekt)')
            actual = node.get('Actual Rows', '—')
            hits = '—'
            details = ', '.join(str(node[k]) for k in ('Relation Name', 'Index Name') if k in node)
        else:
            operator = node.get('operatorType', '(operatorType ontbreekt)')
            actual = node.get('records', node.get('rows', args.get('Rows', '—')))
            hits = node.get('dbHits', node.get('db_hits', args.get('DbHits', '—')))
            details = str(args.get('Details', ''))
        rows.append((depth, str(operator), str(actual), str(hits), details))
        for child in node.get('Plans' if postgres else 'children', []):
            visit(child, depth+1)

    visit(plan.get('Plan', {}) if postgres else plan)
    return rows


def _plans_figure(pg_plan, neo_plan, out, assets):
    fig, ax = _canvas('Werkelijk waargenomen plannen',
        'Schema van de laatste queryuitvoering · inspringing volgt de operatorboom · geen opslagadressen')
    for x, title, plan, pg, color in ((.65, 'PostgreSQL · EXPLAIN ANALYZE', pg_plan, True, BLUE),
                                    (8.15, 'Neo4j · PROFILE', neo_plan, False, TEAL)):
        _box(ax, x, 1.55, 7.2, 5.8, title, color=color, size=16)
        rows = _plan_rows(plan, pg)
        label = 'Node Type' if pg else 'operatorType'
        ax.text(x+.2, 6.43, label+'  /  '+('relatie, index' if pg else 'details'),
                color=MUTED, fontsize=10)
        ax.text(x+6.1, 6.43, 'Rijen', color=MUTED, fontsize=10, ha='right')
        if not pg:
            ax.text(x+6.95, 6.43, 'dbHits', color=MUTED, fontsize=10, ha='right')
        # Keep all observed operators; longer trees use a compact indented table.
        dy = min(.49, 4.05/max(len(rows), 1))
        fontsize = min(11, dy*25)
        for i, (depth, operator, actual, hits, details) in enumerate(rows):
            yy = 6.04-i*dy
            indent = '  '*depth
            text = indent+operator
            fs = min(fontsize, 505/max(len(text), 1))
            ax.text(x+.2, yy, text, fontfamily='DejaVu Sans Mono', color=INK,
                    fontsize=fs, va='top')
            ax.text(x+6.1, yy, actual, color=INK, fontsize=fontsize, ha='right', va='top')
            if not pg:
                ax.text(x+6.95, yy, hits, color=INK, fontsize=fontsize, ha='right', va='top')
            if details and dy >= .40:
                # Secondary text is factual metadata, not an invented explanation.
                detail = textwrap.shorten(details, width=65, placeholder='…')
                ax.text(x+.2+depth*.12, yy-.21, detail, color=MUTED, fontsize=8, va='top')
    ax.text(.85, .95, 'Elke regel is een uitgevoerde operator; ingesprongen regels zijn de kinderen van die operator.',
            color=INK, fontsize=11)
    ax.text(.85, .62, 'Rijen = Actual Rows / records. dbHits = waargenomen Neo4j-databasetoegangen; — = niet aanwezig. Geen totalen optellen.',
            color=MUTED, fontsize=10)
    _save(fig, 'plannen', out, assets)


def build_figures(data: dict, sql_query: str, cypher_query: str,
                  pg_plan: dict | None = None, neo_plan: dict | None = None,
                  output_dir='assets') -> dict:
    """Schrijf acht PNG/SVG-paren plus werkelijke plannen als beide dicts aanwezig zijn."""
    out=Path(output_dir); out.mkdir(parents=True,exist_ok=True); assets={}
    people={p['person_id']:p['name'] for p in data['persons']}
    movies={m['movie_id']:m for m in data['movies']}
    noor=people['P27']; amir=people['P28']; first=movies['M1']['title']

    fig,ax=_canvas('Eén vraag. Alle verbanden in beeld.', 'Vier personen · vier films · zeven ACTED_IN-relaties')
    _graph(ax,data,x=1.3,y=2.0,width=8.8,height=4.45)
    _box(ax,11.2,4.75,4.1,2.1,'DE VRAAG',f'Wie speelde samen met\n{noor} in een film?',ORANGE)
    _box(ax,11.2,1.8,4.1,2.25,'HET ANTWOORD',f'{amir}\nVia {first} (M1)',TEAL)
    _save(fig,'preview',out,assets)

    fig,ax=_canvas('Dezelfde feiten, twee modellen', 'Tabellen verbinden sleutels; een graaf maakt de relaties zichtbaar.')
    _table(ax,.65,4.7,3.15,'Person',['person_id','name'],[(p['person_id'],p['name']) for p in data['persons']],PURPLE)
    _table(ax,.65,1.2,3.15,'Movie',['movie_id','title'],[(m['movie_id'],m['title']) for m in data['movies']],BLUE)
    _table(ax,4.05,2.55,3.05,'ActedIn',['person_id','movie_id'],[(r['person_id'],r['movie_id']) for r in data['acted_in']],TEAL)
    ax.text(11.35,7.2,'GRAAF',color=MUTED,fontsize=11,ha='center')
    _graph(ax,data,x=8.05,y=2.3,width=6.55,height=3.7)
    _save(fig,'modelvergelijking',out,assets)

    fig,ax=_canvas('Twee talen, dezelfde vraag', f'Wie speelde samen met {noor}? De relaties en de uitkomst blijven gelijk.')
    for x,title,query,color in ((.65,'SQL · tabellen koppelen',sql_query,BLUE),(8.15,'Cypher · patroon beschrijven',cypher_query,TEAL)):
        _box(ax,x,1.1,7.2,6.25,title,color=color,size=17)
        lines=query.strip().splitlines()
        longest=max([len(s) for s in lines] or [1])
        fs=min(12, 790/max(longest,1), 235/max(len(lines),1))
        ax.text(x+.25,6.45,query.strip(),fontfamily='DejaVu Sans Mono',fontsize=fs,color=INK,va='top',linespacing=1.65)
    _save(fig,'twee-talen',out,assets)

    fig,ax=_canvas('Het logische pad naar een medespeler', 'Logisch patroon · schematisch; geen geheugenadressen')
    pts=[(3,4.6),(8,4.6),(13,4.6)]
    _edge(ax,(3.7,4.6),(7.3,4.6),TEAL,True,lw=3)
    _edge(ax,(12.3,4.6),(8.7,4.6),TEAL,True,lw=3)
    _node(ax,pts[0],noor,PURPLE,.7,'P27 · Person')
    _node(ax,pts[1],'M1',BLUE,.7,first+'\nMovie')
    _node(ax,pts[2],amir,PURPLE,.7,'P28 · Person')
    for x in [5.5,10.5]: ax.text(x,5.05,'ACTED_IN',color=TEAL,fontsize=13,ha='center')
    _box(ax,3.1,1.2,9.8,1.3,'LEES HET PATROON',f'{noor} → dezelfde film ← {amir}',TEAL)
    _save(fig,'logisch-pad',out,assets)

    fig,ax=_canvas('RAG: van opgehaalde feiten naar een antwoord', 'Schematisch proces · een taalmodel formuleert op basis van de meegegeven context.')
    stages=[(.65,'1  RETRIEVAL','Zoek relevante films\nen volg relaties.',BLUE),(4.5,'2  CONTEXT',f'{noor} → M1 ← {amir}\nFilm: {first}\nBron: '+movies['M1']['source_id'],TEAL),(8.35,'3  TAALMODEL','Ontvang vraag + context.\nFormuleer het antwoord.',PURPLE),(12.2,'4  ANTWOORD',f'{amir} speelde samen\nmet {noor}.\nBron: '+movies['M1']['source_id'],ORANGE)]
    for x,t,b,c in stages: _box(ax,x,3.15,3.15,2.9,t,b,c,size=14)
    for x in [3.8,7.65,11.5]: _edge(ax,(x,4.55),(x+.65,4.55),MUTED,True)
    ax.text(8,1.7,'De database selecteert feiten. Het taalmodel schrijft de uitleg.',color=INK,fontsize=17,ha='center')
    _save(fig,'rag',out,assets)

    fig,ax=_canvas('Wat zit in het zoekoppervlak?', 'Zoekindexen vinden kandidaten. Relaties geven daarna betekenis en context.')
    _box(ax,.7,3.75,7.1,3.5,'VECTORINDEX · film_vector','Embedding van uitsluitend:\nMovie.samenvatting\n\nZoeken op inhoudelijke overeenkomst',BLUE,size=17)
    _box(ax,8.2,3.75,7.1,3.5,'FULLTEXTINDEX · movie_text','Doorzoekbare tekstvelden:\nMovie.title + Movie.samenvatting\n\nZoeken met woorden en teksttermen',ORANGE,size=17)
    _box(ax,2,1.05,12,1.8,'BUITEN DEZE INDEXEN','Person-nodes en ACTED_IN-relaties blijven in de domeingraaf.\nDe vectorindexgraaf is een andere graaf dan deze ACTED_IN-graaf.',TEAL,size=16)
    _save(fig,'zoekoppervlak',out,assets)

    fig,ax=_canvas('Van buurverbindingen naar HNSW-lagen', 'Schematische vectorindex · geen ACTED_IN-graaf, echte indexweergave of opslagadressen')
    _box(ax,.65,1.0,4.4,6.35,'Navigable Small World',color=BLUE,size=16)
    ax.text(.88,6.52,'NSW · buurennetwerk',color=MUTED,fontsize=11)
    nsw=[(1.4,4.8),(2.7,5.9),(4.15,4.9),(1.6,3.3),(3.4,3.4)]
    for i,j in [(0,1),(1,2),(2,4),(4,3),(3,0),(0,4),(1,4)]: _edge(ax,nsw[i],nsw[j],BLUE)
    for i,p in enumerate(nsw): _node(ax,p,str(i+1),BLUE,.24)
    ax.text(2.85,1.75,'Knooppunten zijn vectoren;\nranden koppelen nabije buren.',color=MUTED,fontsize=11,ha='center')
    _box(ax,5.35,1.0,4.45,6.35,'Lijst → skiplist',color=PURPLE,size=17)
    xs=[5.9,6.7,7.5,8.3,9.1]
    for level,ids in [(0,[0,1,2,3,4]),(1,[0,2,4]),(2,[0,4])]:
        yy=2.9+level*1.05
        for a,b in zip(ids,ids[1:]): _edge(ax,(xs[a],yy),(xs[b],yy),PURPLE)
        for i in ids:
            _node(ax,(xs[i],yy),str(i+1),PURPLE,.2)
            if level: _edge(ax,(xs[i],yy-.2),(xs[i],yy-.85),EDGE,style=':')
    ax.text(7.55,1.75,'Hogere niveaus slaan stappen over.\nDit is een analogie voor de lagen.',color=MUTED,fontsize=11,ha='center')
    _box(ax,10.1,1.0,5.25,6.35,'HNSW · gelaagde buurengraaf',color=TEAL,size=16)
    hp={1:(10.85,0),2:(11.8,0),3:(12.75,0),4:(13.7,0),5:(14.65,0)}
    levels=[[1,2,3,4,5],[1,3,5],[3,5]]
    for lev,ids in enumerate(levels):
        yy=2.75+lev*1.2
        ax.text(10.35,yy+.38,f'L{lev}',color=MUTED,fontsize=9)
        for a,b in zip(ids,ids[1:]): _edge(ax,(hp[a][0],yy),(hp[b][0],yy),TEAL)
        extra_edges = [(1,3),(2,4),(3,5)] if lev == 0 else ([(1,5)] if lev == 1 else [])
        for a,b in extra_edges:
            ax.add_patch(FancyArrowPatch((hp[a][0],yy),(hp[b][0],yy),
                arrowstyle='-', connectionstyle='arc3,rad=0.35', color=TEAL, linewidth=1.8, zorder=1))
        for i in ids:
            _node(ax,(hp[i][0],yy),str(i),TEAL,.22)
            if lev: _edge(ax,(hp[i][0],yy-.22),(hp[i][0],yy-.98),EDGE,style=':')
    ax.text(12.7,1.65,'Elke hogere laag is een subset\nvan de laag eronder.',color=MUTED,fontsize=11,ha='center')
    _save(fig,'hnsw',out,assets)

    fig,ax=_canvas('De kennislaag maakt kandidaten verklaarbaar', 'Schematische modeluitleg · inhoudelijke kandidaten zonder verzonnen vectorscores')
    _box(ax,.65,5.65,5,1.6,'INHOUDELIJKE KANDIDATEN',movies['M2']['title']+' (M2)  ·  '+movies['M4']['title']+' (M4)',ORANGE,size=15)
    # The full graph preserves the bridge through M3; only the short cast path is emphasized.
    pos={'P27':(1.6,4),'M1':(4.05,4),'P28':(6.5,4),'M2':(9.0,4),'P29':(11.4,4),'M3':(11.4,1.65),'P30':(13.75,1.65),'M4':(13.75,4)}
    short={('P27','M1'),('P28','M1'),('P28','M2')}
    for r in data['acted_in']:
        pair=(r['person_id'],r['movie_id']); _edge(ax,pos[pair[0]],pos[pair[1]],TEAL if pair in short else EDGE,lw=3 if pair in short else 1.6)
    for p in data['persons']: _node(ax,pos[p['person_id']],p['name'],PURPLE,.42)
    for m in data['movies']: _node(ax,pos[m['movie_id']],m['movie_id'],BLUE,.42, m['title'])
    _box(ax,6.05,5.65,9.3,1.6,'RELATIES ONDERSCHEIDEN',f'M2 heeft de korte castverbinding: {noor} → M1 ← {amir} → M2.',TEAL,size=15)
    ax.text(.9,1.35,'M4 is ook kandidaat op inhoud, maar heeft deze korte castverbinding niet.\nDe langere verbinding via M3 blijft zichtbaar in de graaf.',color=MUTED,fontsize=12,linespacing=1.65)
    _save(fig,'kennislaag',out,assets)
    if isinstance(pg_plan, dict) and isinstance(neo_plan, dict):
        _plans_figure(pg_plan, neo_plan, out, assets)
    return assets
