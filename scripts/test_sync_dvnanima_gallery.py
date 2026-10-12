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
            catalog = {'repository_url':'https://example.org/repo',
                       'source_base_url':'https://example.org/source',
                       'sections':[{'id':'section','title':'Test','summary':'Test',
                           'items':[{'id':i,'title':i,'description':i,
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


if __name__ == '__main__':
    unittest.main()
