"""Compara duas execuções do smoke_test.py (ex.: baseline x pós-refatoração).

Uso:
    python scripts/compare_results.py antes.json depois.json

Para cada requisição compara o status HTTP e as chaves de primeiro nível da resposta
(ou o tipo, quando a resposta não é um objeto JSON). Sai com código 1 se houver diferenças.
"""
import json
import sys


def shape(response):
    if isinstance(response, dict):
        return sorted(response)
    if isinstance(response, list):
        return f"list[{len(response)}]" if not response or not isinstance(response[0], dict) else f"list of {sorted(response[0])}"
    return type(response).__name__


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    before, after = (json.load(open(path, encoding="utf-8")) for path in sys.argv[1:3])
    diffs = 0
    for b, a in zip(before, after):
        same = b["status"] == a["status"] and shape(b["response"]) == shape(a["response"])
        mark = "=" if same else "≠"
        diffs += not same
        print(f"{mark} {b['method']:6} {b['path']:60} {b['status']} -> {a['status']}"
              + ("" if same else f"   {shape(b['response'])} -> {shape(a['response'])}"))
    print(f"\n{len(before)} requisições comparadas | {len(before) - diffs} iguais | {diffs} diferentes")
    sys.exit(1 if diffs else 0)


if __name__ == "__main__":
    main()
