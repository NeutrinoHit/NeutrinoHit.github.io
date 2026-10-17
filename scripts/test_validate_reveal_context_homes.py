import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import validate_reveal_context_homes as validator


class CourseHomeValidationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.workspace = Path(self.temporary.name)
        self.central = self.workspace / "neutrinohit-map"
        self.central.mkdir()
        self.course = self.workspace / "qft-lectures"
        self.url = "https://neutrinohit.github.io/qft-lectures/vacuum/"
        self.addCleanup(patch.stopall)
        patch.object(validator, "ROOT", self.central).start()
        patch.object(validator, "WORKSPACE", self.workspace).start()
        patch.object(validator, "SOURCE_ROOTS", [self.central, self.course]).start()
        self.remote = patch.object(validator, "remote_target_exists", return_value=False).start()

    def occurrence(self):
        return validator.Occurrence(
            self.course / "vacuum/ru/slides/_metadata.yml",
            20,
            {"data-context-home": self.url, "data-context-home-label": "Vacuum course"},
        )

    def test_sibling_build_satisfies_a_used_course_home(self):
        page = self.course / "_site/vacuum/index.html"
        page.parent.mkdir(parents=True)
        page.write_text("<html>Vacuum course</html>", encoding="utf-8")
        self.assertEqual(validator.validate_occurrence(self.occurrence(), {self.url: "course-home"}), [])
        self.remote.assert_not_called()

    def test_used_course_without_local_or_published_page_still_fails(self):
        errors = validator.validate_occurrence(self.occurrence(), {self.url: "course-home"})
        self.assertEqual(len(errors), 1)
        self.assertIn("does not exist", errors[0])
        self.remote.assert_called_once_with(self.url)

    def test_unused_course_registration_does_not_require_publication(self):
        registry = self.central / "registry.json"
        registry.write_text(json.dumps({"allowed_context_homes": [
            {"url": self.url, "type": "course-home"}
        ]}), encoding="utf-8")
        with patch.object(validator, "REGISTRY", registry), patch.dict(
            validator.os.environ, {"NEUTRINOHIT_VALIDATE_REVEAL_CONTEXTS": "1"}
        ), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(validator.main(), 0)
        self.remote.assert_not_called()

    def test_map_card_requires_its_rendered_anchor(self):
        url = "https://neutrinohit.github.io/ru/education.html#qft"
        page = self.central / "_site/ru/education.html"
        page.parent.mkdir(parents=True)
        page.write_text('<html><div id="other"></div></html>', encoding="utf-8")
        self.assertFalse(validator.target_exists_for_type(url, "map-card"))
        page.write_text('<html><div id="qft"></div></html>', encoding="utf-8")
        self.assertTrue(validator.target_exists_for_type(url, "map-card"))

    def test_exact_disabled_source_and_stale_aggregate_do_not_block(self):
        self.course.mkdir()
        (self.course / '_quarto.yml').write_text('project:\n  render:\n    - "active.qmd"\n    - "!disabled.qmd"\n')
        invalid = '<script src="neutrinohit-reveal-footer.js"></script>'
        (self.course / 'disabled.qmd').write_text(invalid)
        stale = self.central / '_site/qft-lectures/disabled.html'
        stale.parent.mkdir(parents=True); stale.write_text(invalid)
        registry = self.central / 'registry.json'
        registry.write_text(json.dumps({'allowed_context_homes': [{'url':self.url,'type':'course-home'}]}))
        with patch.object(validator,'REGISTRY',registry), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(validator.main(),0)
        (self.course / 'active.qmd').write_text(invalid)
        with patch.object(validator,'REGISTRY',registry), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(validator.main(),1)

    def test_exclusions_are_exact_local_project_render_files(self):
        self.course.mkdir()
        (self.course / '_quarto.yml').write_text('project:\n  render:\n    - "!skip.qmd"\n    - "!*.qmd"\n    - "!../outside.qmd"\n    - "active.qmd"\nother:\n  render:\n    - "!not-project.qmd"\n')
        self.assertEqual(validator.explicit_render_exclusions(self.course),{self.course / 'skip.qmd'})


    def test_course_page_must_be_a_rendered_page_of_this_site(self):
        url = "https://neutrinohit.github.io/ru/courses/unruh.html"
        self.assertTrue(validator.target_type_is_valid(url, "course-page"))
        self.assertFalse(validator.target_type_is_valid(url + "#lecture-01", "course-page"))
        self.assertFalse(validator.target_exists_for_type(url, "course-page"))
        page = self.central / "_site/ru/courses/unruh.html"
        page.parent.mkdir(parents=True)
        page.write_text("<html>Unruh</html>", encoding="utf-8")
        self.assertTrue(validator.target_exists_for_type(url, "course-page"))

if __name__ == "__main__":
    unittest.main()
