import base64
import bz2
import hashlib
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
PATCH = ROOT / "patches" / "phase15-film-context-native.patch.bz2.b64"
EXPECTED_SHA256 = "a8dc28c9e679d65d0551f997515ee0603983e373d1ab545def8d7fd5593e217a"


class FilmContextNativePatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw = bz2.decompress(base64.b64decode(PATCH.read_text(encoding="ascii")))
        cls.patch = raw.decode("utf-8")
        cls.digest = hashlib.sha256(raw).hexdigest()

    def test_checksum(self):
        self.assertEqual(self.digest, EXPECTED_SHA256)

    def test_optional_ui_exists(self):
        self.assertIn("Film Context", self.patch)
        self.assertIn("Enable Film Context tools for the AI agent", self.patch)
        self.assertIn("filmContextEnabled", self.patch)
        self.assertIn("Build Index", self.patch)
        self.assertIn("Build Visual Index (Optional)", self.patch)
        self.assertIn("filmContextOperation", self.patch)

    def test_agent_tool_surface(self):
        for name in (
            "movie_context_status",
            "movie_search",
            "movie_get_scene",
            "movie_get_context",
            "movie_get_keyframes",
        ):
            self.assertIn(name, self.patch)

    def test_local_backend_is_installed(self):
        self.assertIn("filmcontext/film_context.py", self.patch)
        blueprint = (ROOT / "craft" / "editaja" / "editaja.py").read_text(encoding="utf-8")
        self.assertIn('("phase15.patch", 1)', blueprint)
        self.assertIn("film_context.txt", blueprint)

    def test_small_vision_escalation(self):
        self.assertIn("agent_image_paths", self.patch)
        self.assertIn("movie_get_keyframes", self.patch)
        self.assertIn("Never request the whole film", self.patch)

    def test_windows_build_contract(self):
        workflow = (ROOT / ".github" / "workflows" / "build-windows.yml").read_text(encoding="utf-8")
        self.assertIn("PHASE15_SHA256", workflow)
        self.assertIn("phase15-film-context-native.patch.bz2.b64", workflow)
        self.assertIn("craft/editaja/phase15.patch", workflow)
        self.assertIn("tools/film_context/film_context.py craft/editaja/film_context.txt", workflow)
        self.assertIn("corresponding-source/data/scripts/filmcontext/film_context.py", workflow)
        self.assertIn("Patch Craft gettext MinGW libxml2 linking", workflow)
        self.assertIn("gl_cv_LTLIBXML", workflow)
        self.assertIn("$LIBXML2 $LTLIBICONV", workflow)

    def test_ai_edit_json_stays_separate(self):
        docs = (ROOT / "FILM_CONTEXT.md").read_text(encoding="utf-8")
        self.assertIn("Film Context itself never edits the timeline", docs)
        self.assertIn("AI Edit JSON", docs)


if __name__ == "__main__":
    unittest.main()
