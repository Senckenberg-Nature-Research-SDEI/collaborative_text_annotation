#!/usr/bin/env python3
from pathlib import Path


ABSOLUTE_SPARQL_DIR = Path("/Users/sefika/projects/memory-based-mcp/sparqls")


def main() -> int:
	try:
		from rdflib import Graph
	except Exception as error:
		print(f"ERROR: rdflib import failed: {error}")
		return 1

	root = Path(__file__).resolve().parents[2]
	src_test_ttls = sorted((root / "src" / "test").glob("*.ttl"))

	if src_test_ttls:
		ttl_path = src_test_ttls[0]
		source_note = "src/test"
	else:
		ttl_path = root / "outputs" / "type_specimen_schema.ttl"
		source_note = "outputs fallback (src/test empty)"

	if not ttl_path.exists():
		print(f"ERROR: Turtle file not found: {ttl_path}")
		return 1

	graph = Graph()
	graph.parse(ttl_path)

	sparql_dirs = [root / "sparqls", ABSOLUTE_SPARQL_DIR]
	rq_file_set = set()
	for sparql_dir in sparql_dirs:
		if sparql_dir.exists():
			rq_file_set.update(sparql_dir.glob("**/*.rq"))

	rq_files = sorted(rq_file_set)
	if not rq_files:
		print("ERROR: No SPARQL .rq files found under sparqls/")
		return 1

	print(f"GRAPH: {ttl_path} [{source_note}]")
	print(f"TRIPLES: {len(graph)}")
	print("---")

	success = 0
	failed = 0

	for query_path in rq_files:
		query_text = query_path.read_text(encoding="utf-8").strip()
		if not query_text:
			continue

		print(f"FILE: {query_path}")
		try:
			result = graph.query(query_text)
			rows = len(list(result))
			print(f"  OK rows={rows}")
			success += 1
		except Exception as error:
			message = str(error).splitlines()[0]
			print(f"  FAIL {message}")
			failed += 1
		print("---")

	print(f"SUMMARY: ok={success} fail={failed} total={success + failed}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
