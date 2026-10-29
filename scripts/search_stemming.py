"""Restore stemming for ordinary prefix queries in Material 9.8.0.

Material adds a trailing wildcard to ordinary queries. Lunr skips its search
pipeline for wildcard terms. Normalize each term before adding the wildcard,
then execute it without applying the pipeline a second time.
Only generated assets are changed; installed packages remain untouched.
"""

import hashlib
import re
from pathlib import Path

from mkdocs.exceptions import PluginError

# Fail visibly on theme upgrades rather than silently patching different code.
EXPECTED_SHA256 = "da1b3df5e5f00cc73083c9e21ff0ec28bde85cd247057bdd05b7a167e5903bd4"
ORIGINAL_QUERY = (
    "let r=le(e).filter(s=>s.presence!==lunr.Query.presence.PROHIBITED),"
    "n=this.index.search(e)"
)
FIXED_QUERY = (
    "let clauses=researchQueryClauses(this.index,e),"
    "r=clauses.filter(s=>s.presence!==lunr.Query.presence.PROHIBITED),"
    "n=this.index.query(query=>{"
    "for(const clause of clauses)query.clause({...clause})})"
)
QUERY_HELPER = """
function researchQueryClauses(index, text) {
  return le(text).flatMap(clause => {
    // Preserve explicit internal wildcards; stem ordinary terms first.
    const terms = clause.term.includes("*")
      ? [clause.term]
      : index.pipeline.runString(clause.term, { fields: clause.fields });
    return terms.map(term => ({ ...clause, term, usePipeline: false }));
  });
}
"""


def on_post_build(config):
    site = Path(config["site_dir"])
    workers = list((site / "assets/javascripts/workers").glob("search.*.min.js"))
    if len(workers) != 1:
        raise PluginError("Search fix: expected one Material search worker.")
    worker = workers[0]
    original = worker.read_bytes()
    if hashlib.sha256(original).hexdigest() != EXPECTED_SHA256:
        raise PluginError(
            "Search fix: Material worker changed. Review scripts/search_stemming.py "
            "before using a different theme version."
        )
    source = original.decode("utf-8")
    if source.count(ORIGINAL_QUERY) != 1 or source.count("var U=class") != 1:
        raise PluginError("Search fix: expected query implementation not found.")
    source = source.replace("var U=class", QUERY_HELPER + "var U=class", 1)
    source = source.replace(ORIGINAL_QUERY, FIXED_QUERY, 1)
    source = re.sub(r"//# sourceMappingURL=[^\n]*", "", source)
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()[:12]
    patched = worker.with_name(f"search.{digest}.min.js")
    patched.write_text(source, encoding="utf-8")

    # A new asset URL prevents browsers from reusing the original cached worker.
    references = 0
    for page in site.rglob("*.html"):
        html = page.read_text(encoding="utf-8")
        if worker.name in html:
            page.write_text(html.replace(worker.name, patched.name), encoding="utf-8")
            references += 1
    if not references:
        raise PluginError("Search fix: no HTML references to search worker found.")
    worker.unlink()
    worker.with_suffix(worker.suffix + ".map").unlink(missing_ok=True)
