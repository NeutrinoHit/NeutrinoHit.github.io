from __future__ import annotations

import json
import argparse
import io
import os
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import media_registry as mr
import nh_media

EXTENSION = Path(__file__).resolve().parents[1] / "assets" / "media" / "_extensions" / "neutrinohit-media"


def record(**extra):
    base = {"id": "star-in-jet", "variant": "web-ru", "version": 1, "home": "media-neutrino",
            "status": "prepared", "sha256": "a" * 64, "bytes": 10, "duration_s": 1.0, "width": 2,
            "height": 2, "video_codec": "h264", "audio": False, "footer": True, "faststart": True,
            "replaces": ["assets/animations/dvnanima/x.mp4"]}
    base.update(extra)
    return base


def catalog(*records):
    return {"schema": 1, "url_prefix": "/", "github": "NeutrinoHit",
            "projects": {"media-neutrino": {"title": "t", "budget_bytes": 100}}, "media": list(records)}


class RegistryTest(unittest.TestCase):
    def test_addresses(self):
        r = record()
        self.assertEqual(mr.url_of(r, catalog()), "/media-neutrino/star-in-jet/web-ru-v1.mp4")
        self.assertEqual(mr.release_url(r, catalog()), "https://github.com/NeutrinoHit/media-neutrino"
                         "/releases/download/star-in-jet/star-in-jet--web-ru--v1.mp4")

    def test_only_published_records_replace_copies(self):
        prepared, published = record(), record(variant="web-en", sha256="b" * 64, status="published",
                                               replaces=["assets/y.mp4"])
        with patch.dict(os.environ, {"NH_MEDIA_PREVIEW": ""}):
            resolver = mr.Resolver(catalog(prepared, published))
            self.assertIsNone(resolver.url("assets/animations/dvnanima/x.mp4"))
            self.assertEqual(resolver.url("assets/y.mp4"), "/media-neutrino/star-in-jet/web-en-v1.mp4")
        with patch.dict(os.environ, {"NH_MEDIA_PREVIEW": "1"}):
            self.assertIsNotNone(mr.Resolver(catalog(prepared)).url("assets/animations/dvnanima/x.mp4"))


class CatalogTest(unittest.TestCase):
    def test_gallery_variants(self):
        item = {"id": "star-in-jet"}
        self.assertEqual(nh_media.gallery_variant(item, {"id": "star-in-jet", "label": "Звезда (русская версия)"}),
                         "web-ru")
        self.assertEqual(nh_media.gallery_variant(item, {"id": "star-in-jet-en", "label": "Star (English version)"}),
                         "web-en")
        self.assertEqual(nh_media.gallery_variant({"id": "juno"}, {"id": "survival", "label": "x"}), "web-survival")

    def test_check_finds_duplicates_budget_and_private_paths(self):
        problems = nh_media.check(catalog(
            record(bytes=60, status="published"),
            record(variant="web-en", bytes=60, status="published"),                   # same SHA-256
            record(variant="x", sha256="c" * 64, status="published", replaces=["/Users/dn/x.mp4"])))
        text = "\n".join(problems)
        self.assertIn("registered twice", text)
        self.assertIn("over the budget", text)
        self.assertIn("relative site path", text)

    def test_published_bytes_are_never_replaced(self):
        cat = catalog(record())
        info = {k: v for k, v in record().items() if k in (
            "sha256", "bytes", "duration_s", "width", "height", "video_codec", "audio", "footer", "faststart")}
        state, _ = nh_media.add(cat, Path("x"), "star-in-jet", "web-ru", "media-neutrino", ["a"], info=info)
        self.assertEqual(state, "merged")                 # same bytes: one record, one more consumer
        info["sha256"] = "d" * 64
        with self.assertRaises(SystemExit):              # other bytes under an existing version
            nh_media.add(cat, Path("x"), "star-in-jet", "web-ru", "media-neutrino", [], info=info)


class FaststartTest(unittest.TestCase):
    def box(self, kind: bytes, payload: bytes = b"") -> bytes:
        return struct.pack(">I", 8 + len(payload)) + kind + payload

    def test_moov_before_mdat(self):
        with tempfile.TemporaryDirectory() as tmp:
            good, bad = Path(tmp) / "good.mp4", Path(tmp) / "bad.mp4"
            good.write_bytes(self.box(b"ftyp", b"isom") + self.box(b"moov") + self.box(b"mdat", b"xx"))
            bad.write_bytes(self.box(b"ftyp", b"isom") + self.box(b"mdat", b"xx") + self.box(b"moov"))
            self.assertTrue(nh_media.faststart(good))
            self.assertFalse(nh_media.faststart(bad))


class ScopedPublicationTest(unittest.TestCase):
    def test_story_selection_keeps_both_languages(self):
        ru, en, other = record(), record(variant='web-en'), record(id='another-story')
        cat = catalog(ru, en, other)
        self.assertEqual(nh_media.records_of(cat, 'media-neutrino', 'star-in-jet'), [ru, en])
        with self.assertRaises(SystemExit):
            nh_media.records_of(cat, 'media-neutrino', 'typo')

    def test_dry_run_never_includes_another_prepared_story(self):
        args = argparse.Namespace(home='media-neutrino', id='star-in-jet', yes=False, online=False)
        with patch.object(mr, 'load', return_value=catalog(record(), record(id='another-story'))), \
                patch.object(nh_media, 'gh') as remote, patch('sys.stdout', new_callable=io.StringIO) as out:
            self.assertEqual(nh_media.cmd_publish(args), 0)
            self.assertIn('star-in-jet--web-ru--v1.mp4', out.getvalue())
            self.assertNotIn('another-story', out.getvalue())
            remote.assert_not_called()

    def test_verify_marks_only_selected_story(self):
        selected, other = record(), record(id='another-story')
        cat = catalog(selected, other)
        args = argparse.Namespace(home='media-neutrino', id='star-in-jet',
                                  base='http://localhost', full=False, mark=True)
        with patch.object(mr, 'load', return_value=cat), patch.object(mr, 'save') as save, \
                patch.object(nh_media, 'http_range', return_value=(200, {'Content-Type': 'video/mp4'}, b'x'*10)) as get, \
                patch('sys.stdout', new_callable=io.StringIO):
            self.assertEqual(nh_media.cmd_verify(args), 0)
            self.assertEqual(selected['status'], 'published')
            self.assertEqual(other['status'], 'prepared')
            self.assertEqual(get.call_count, 1)
            save.assert_called_once_with(cat)


class ConsumerToolTest(unittest.TestCase):
    def test_prune_removes_only_live_fallbacks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "_site" / "talk" / "media").mkdir(parents=True)
            for name in ("a.mp4", "b.mp4"):
                (root / "_site" / "talk" / "media" / name).write_bytes(b"x")
            (root / "media.lock.json").write_text(json.dumps({"media": [
                {"id": "a", "variant": "v", "status": "published", "fallback": "talk/media/a.mp4"},
                {"id": "b", "variant": "v", "status": "prepared", "fallback": "talk/media/b.mp4"}]}))
            env = {**os.environ, "QUARTO_PROJECT_DIR": str(root), "NH_MEDIA_PREVIEW": ""}
            subprocess.run([sys.executable, str(EXTENSION / "media.py"), "prune", "_site"], env=env,
                           check=True, capture_output=True)
            self.assertFalse((root / "_site/talk/media/a.mp4").exists())
            self.assertTrue((root / "_site/talk/media/b.mp4").exists())


if __name__ == "__main__":
    unittest.main()
