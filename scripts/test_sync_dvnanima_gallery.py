from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sync_dvnanima_gallery as gallery


class SelectiveSyncTest(unittest.TestCase):
    def test_selected_media_only_and_complete_gallery(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sources = root / 'source'
            assets = root / 'assets'
            sources.mkdir()
            assets.mkdir()
            (sources/'first.mp4').write_bytes(b'new first')
            # Nonselected source can be absent: the published asset is preserved.
            (assets/'section-second-film.mp4').write_bytes(b'old second')
            (assets/'section-second-film.jpg').write_bytes(b'old poster')
            catalog = {'sections':[{'id':'section','title':'Test','summary':'Test',
                           'items':[{'id':i,'title':i,'description':i,'source_dir':'scene',
                           'videos':[{'id':'film','label':i,'path':i+'.mp4'}]}
                           for i in ('first','second')]}]}
            def poster(source, target, force, at):
                target.write_bytes(b'new poster')
            with patch.object(gallery,'SITE_ROOT',root), \
                 patch.object(gallery,'build_poster',side_effect=poster) as build:
                records=gallery.sync_assets(catalog,sources,assets,False,True,True,4.0,
                                            only_items={('section','first')})
                page=gallery.render_qmd(catalog,records,root/'ru'/'animations.qmd')
            self.assertEqual((assets/'section-first-film.mp4').read_bytes(),b'new first')
            self.assertEqual((assets/'section-second-film.mp4').read_bytes(),b'old second')
            self.assertEqual((assets/'section-second-film.jpg').read_bytes(),b'old poster')
            self.assertEqual(build.call_count,1)
            self.assertEqual(len(records),2)
            self.assertIn('animation-section-first',page)
            self.assertIn('animation-section-second',page)
            self.assertNotIn('Исходный код',page)  # source_dir is internal

    def test_english_page_and_language_versions(self):
        item = {'id':'film','title':'Фильм','title_en':'Film','description':'Описание',
                'description_en':'Description','videos':[
                    {'id':'v','label':'Фильм (русская версия)'},
                    {'id':'v-en','label':'Film (English version)'}]}
        catalog = {'sections':[{'id':'s','title':'Раздел','title_en':'Section','summary':'С',
                                'summary_en':'S','items':[item]}]}
        records = {('s','film',v):{'movie':f'assets/{v}.mp4','poster':'','size':'1 MB'}
                   for v in ('v','v-en')}
        root = Path('/site')
        with patch.object(gallery,'SITE_ROOT',root):
            ru = gallery.render_qmd(catalog,records,root/'ru'/'animations.qmd','ru')
            en = gallery.render_qmd(catalog,records,root/'en'/'animations.qmd','en')
        self.assertIn('id="animation-s-film"',en)
        self.assertIn('>Film</h3>',en)
        self.assertIn('>Фильм</h3>',ru)
        # one film in two languages: the page language plays first
        self.assertIn('href="../assets/v-en.mp4" data-play title="MP4, 1 MB">EN',en)
        self.assertIn('class="anim-chip is-current" href="../assets/v.mp4"',ru)


if __name__ == '__main__':
    unittest.main()
