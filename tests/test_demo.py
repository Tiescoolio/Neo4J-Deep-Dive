import unittest
import json
from pathlib import Path
from film_demo import catalogue, generated_files, ROOT


class FilmDemoTest(unittest.TestCase):
    def test_zichtbare_notebookcode_is_uitvoerbare_python(self):
        notebook = json.loads((ROOT / 'demo.ipynb').read_text(encoding='utf-8'))
        for number, cell in enumerate(notebook['cells']):
            if cell['cell_type'] == 'code':
                compile(''.join(cell['source']), f'notebookcel {number}', 'exec')
    def test_gui_imports_en_bronfiches_lopen_niet_achter_op_json(self):
        for path, expected in generated_files().items():
            self.assertEqual((ROOT / path).read_text(encoding='utf-8'), expected, path)
    def test_een_bron_met_vier_personen_vier_films_en_zeven_deelnames(self):
        data = catalogue()
        self.assertEqual({k: len(v) for k, v in data.items()},
                         {'persons': 4, 'movies': 4, 'acted_in': 7})
        self.assertEqual({r['source_id'] for r in data['movies']}, {'S1', 'S2', 'S3', 'S4'})
        self.assertEqual({r['movie_id'] for r in data['movies'] if r['genre'] == 'thriller'}, {'M2', 'M4'})
        noor_films = {r['movie_id'] for r in data['acted_in'] if r['person_id'] == 'P27'}
        collegas = {r['person_id'] for r in data['acted_in'] if r['movie_id'] in noor_films} - {'P27'}
        self.assertEqual(collegas, {'P28'})
        self.assertEqual({r['movie_id'] for r in data['acted_in'] if r['person_id'] in collegas}, {'M1', 'M2'})


if __name__ == '__main__':
    unittest.main()
