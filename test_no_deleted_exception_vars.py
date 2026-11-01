"""Guards against the Python gotcha behind 'NameError: cannot access free variable e':
a lambda/def inside `except ... as e:` that uses `e` runs LATER, after Python has deleted `e`."""
import ast, sys
from pathlib import Path

def main():
    bad = []
    for f in list(Path(__file__).resolve().parent.glob("*.py")) + list((Path(__file__).resolve().parent / "stemscore_ai").glob("*.py")):
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for h in [n for n in ast.walk(tree) if isinstance(n, ast.ExceptHandler) and n.name]:
            for node in ast.walk(h):
                if isinstance(node, (ast.Lambda, ast.FunctionDef)):
                    args = {a.arg for a in node.args.args + node.args.kwonlyargs}
                    for n in ast.walk(node):
                        if isinstance(n, ast.Name) and n.id == h.name and n.id not in args:
                            bad.append(f"{f.name}:{n.lineno} uses '{h.name}' inside a deferred function")
    assert not bad, "\n".join(bad)
    print("PASS: no deferred function uses a deleted exception variable")

if __name__ == "__main__": main()
