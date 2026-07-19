"""
Loads the real GNDU MCA catalog data (aliases, courses, subjects, notes,
pyqs, resources) and provides:

  - subject resolution: turns free text ("daa", "DBMS", "operating systems")
    into a canonical subject name, even though the six source files don't
    use perfectly consistent naming (verified against the real data — e.g.
    "Cloud Computing" appears in notes/pyqs/resources but has no entry in
    aliases.json or subjects.json at all).
  - metadata search over notes/pyqs (subject/semester/course/exam type)
  - TF-IDF semantic fallback when metadata filtering finds nothing
  - resource lookup by topic

This is intentionally the single source of truth for "what do we know
about this subject" so every agent resolves subjects the same way.
"""
import json
import logging
from pathlib import Path
from typing import Optional

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger("acadease.data")

DATA_DIR = Path(__file__).resolve().parent / "data"


def _load(name: str):
    path = DATA_DIR / name
    if not path.exists():
        logger.warning("Data file missing: %s", path)
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _norm(s: Optional[str]) -> str:
    return (s or "").strip().lower()


class CatalogStore:
    def __init__(self):
        self.aliases: list[dict] = []
        self.courses: list[dict] = []
        self.subjects: list[dict] = []
        self.notes: list[dict] = []
        self.pyqs: list[dict] = []
        self.resources: list[dict] = []
        self.reload()

    def reload(self):
        self.aliases = _load("aliases.json")
        self.courses = _load("courses.json")
        self.subjects = _load("subjects.json")
        self.notes = _load("notes.json")
        self.pyqs = _load("pyqs.json")
        self.resources = _load("resources.json")
        self._build_resolution_index()
        self._build_semantic_index()
        logger.info(
            "Catalog loaded: %d subjects, %d notes, %d pyqs, %d resource topics",
            len(self.subjects), len(self.notes), len(self.pyqs), len(self.resources),
        )

    # ------------------------------------------------------------------ #
    # Subject resolution
    # ------------------------------------------------------------------ #
    def _build_resolution_index(self):
        # alias string -> canonical subject_name (from aliases.json, the
        # authoritative source when a subject is listed there)
        self.alias_index: dict[str, str] = {}
        # subject_name -> subject_code (first match wins; a few subject
        # names map to more than one code, e.g. "Soft Computing")
        self.name_to_code: dict[str, str] = {}
        for entry in self.aliases:
            canon = entry["subject_name"]
            self.name_to_code.setdefault(_norm(canon), entry["subject_code"])
            for alias in entry.get("aliases", []):
                self.alias_index[_norm(alias)] = canon
            self.alias_index[_norm(canon)] = canon

        # Not every subject that has notes/pyqs/resources is in aliases.json
        # (confirmed against the real data) — so the canonical pool also
        # includes subject names/topics seen directly in those files.
        pool = set(self.alias_index.values())
        pool.update(n["subject_name"] for n in self.notes if n.get("subject_name"))
        pool.update(p["subject_name"] for p in self.pyqs if p.get("subject_name"))
        pool.update(r["topic"] for r in self.resources if r.get("topic"))
        self.canonical_pool: list[str] = sorted(pool)

        # subject_code -> subjects.json row. Some subject codes are offered
        # under more than one course (e.g. CSL4050 appears for both the
        # 2-year and 5-year integrated programs) — keep the first listed
        # rather than silently letting a later row overwrite it.
        self.code_to_subject: dict[str, dict] = {}
        for s in self.subjects:
            self.code_to_subject.setdefault(s["subject_code"], s)
        self.course_by_id: dict[str, dict] = {c["course_id"]: c for c in self.courses}

    def resolve_subject(self, text: Optional[str]) -> Optional[str]:
        """Best-effort: free text -> canonical subject name, or None.

        Both the alias index and the raw canonical pool are scored together
        and the LONGEST matching string wins overall — otherwise a short
        alias (e.g. "cloud" -> Cloud Native Application Development) can
        beat a more specific direct match (e.g. "Cloud Computing") just
        because alias matching was checked first.
        """
        if not text:
            return None
        normalized = _norm(text)

        best, best_len = None, 0

        # Candidate 1: alias matches contained in the query
        for alias_key, canon in self.alias_index.items():
            if alias_key and alias_key in normalized and len(alias_key) > best_len:
                best, best_len = canon, len(alias_key)

        # Candidate 2: direct containment against the full canonical pool
        # (covers subjects missing from aliases.json, e.g. "Cloud Computing")
        for canon in self.canonical_pool:
            c_norm = _norm(canon)
            if c_norm and (c_norm in normalized or normalized in c_norm) and len(c_norm) > best_len:
                best, best_len = canon, len(c_norm)

        if best:
            return best

        # 3. TF-IDF nearest match as a last resort
        return self._semantic_resolve(normalized)

    def get_subject_context(self, subject_name: str) -> dict:
        """Department/semester/course info for a resolved subject, if known."""
        code = self.name_to_code.get(_norm(subject_name))
        if not code:
            return {}
        subj = self.code_to_subject.get(code, {})
        course = self.course_by_id.get(subj.get("course_id"), {})
        course_name = subj.get("course_name") or course.get("course_name") or subj.get("course_id")
        return {
            "subject_code": code,
            "department": subj.get("department"),
            "semester": subj.get("semester"),
            "course_id": subj.get("course_id"),
            "course_name": course_name,
            "is_elective": subj.get("is_elective"),
        }

    # ------------------------------------------------------------------ #
    # Semantic fallback (TF-IDF)
    # ------------------------------------------------------------------ #
    def _build_semantic_index(self):
        if not self.canonical_pool:
            self._subject_vectorizer = None
            return
        self._subject_vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        self._subject_matrix = self._subject_vectorizer.fit_transform(self.canonical_pool)

        def doc(item, fields):
            return " ".join(str(item.get(f, "")) for f in fields) + " " + " ".join(item.get("tags", []))

        self._notes_vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        note_docs = [doc(n, ["title", "subject_name", "description"]) for n in self.notes] or [""]
        self._notes_matrix = self._notes_vectorizer.fit_transform(note_docs) if self.notes else None

        self._pyq_vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        pyq_docs = [doc(p, ["subject_name", "exam_type"]) for p in self.pyqs] or [""]
        self._pyq_matrix = self._pyq_vectorizer.fit_transform(pyq_docs) if self.pyqs else None

    def _semantic_resolve(self, normalized_query: str, min_score: float = 0.2) -> Optional[str]:
        if not self._subject_vectorizer or not normalized_query.strip():
            return None
        vec = self._subject_vectorizer.transform([normalized_query])
        sims = cosine_similarity(vec, self._subject_matrix).flatten()
        idx = sims.argmax()
        if sims[idx] < min_score:
            return None
        return self.canonical_pool[idx]

    def semantic_search_notes(self, query: str, top_k: int = 5, min_score: float = 0.08) -> list[dict]:
        return self._semantic_search(query, self.notes, self._notes_vectorizer, self._notes_matrix, top_k, min_score)

    def semantic_search_pyqs(self, query: str, top_k: int = 5, min_score: float = 0.08) -> list[dict]:
        return self._semantic_search(query, self.pyqs, self._pyq_vectorizer, self._pyq_matrix, top_k, min_score)

    @staticmethod
    def _semantic_search(query, pool, vectorizer, matrix, top_k, min_score):
        if matrix is None or not query.strip():
            return []
        vec = vectorizer.transform([query])
        sims = cosine_similarity(vec, matrix).flatten()
        ranked = sims.argsort()[::-1][:top_k]
        results = []
        for i in ranked:
            if sims[i] < min_score:
                continue
            item = dict(pool[i])
            item["score"] = round(float(sims[i]), 3)
            results.append(item)
        return results

    # ------------------------------------------------------------------ #
    # Metadata search
    # ------------------------------------------------------------------ #
    def find_notes(self, subject_name: Optional[str]) -> list[dict]:
        if not subject_name:
            return []
        target = _norm(subject_name)
        return [n for n in self.notes if _norm(n.get("subject_name")) == target]

    def find_pyqs(
        self,
        subject_name: Optional[str],
        semester: Optional[int] = None,
        course_id: Optional[str] = None,
        exam_type: Optional[str] = None,
    ) -> list[dict]:
        if not subject_name:
            return []
        target = _norm(subject_name)
        results = [p for p in self.pyqs if _norm(p.get("subject_name")) == target]
        if semester:
            results = [p for p in results if p.get("semester") == semester]
        if course_id:
            results = [p for p in results if _norm(p.get("course_id")) == _norm(course_id)]
        if exam_type:
            results = [p for p in results if _norm(exam_type) in _norm(p.get("exam_type"))]
        return results

    def find_resources(self, subject_name: Optional[str]) -> Optional[dict]:
        if not subject_name:
            return None
        target = _norm(subject_name)
        for r in self.resources:
            if _norm(r.get("topic")) == target:
                return r.get("resources", {})
        return None


store = CatalogStore()
