"""Deterministic prose and module-local AST checks."""
import ast
import re
from pathlib import Path
from .phrases import (IMAGECROPPING, NOIMAGECROPPING, GENERIC_NAMES,
                      PIL_METHODS, CROP_CLASSES, TRANSFORM_SOURCES)

EXCLUDED = {'.git', '__pycache__', '.venv', 'venv', 'env', '.env', 'virtualenv'}


def match_phrases(text, phrases):
    text = text.lower()
    matches = []
    for phrase in sorted(phrases, key=len, reverse=True):
        start = text.find(phrase)
        while start >= 0:
            matches.append(phrase)
            text = text[:start] + ' ' * len(phrase) + text[start + len(phrase):]
            start = text.find(phrase)
    return matches, text


def prose(text):
    lines = []
    fenced = False
    for line in text.splitlines():
        if re.match(r'^\s*```', line):
            fenced = not fenced
        elif not fenced:
            lines.append(line.replace('`', ''))
    return '\n'.join(lines)


def claims(text):
    denials, remaining = match_phrases(text, NOIMAGECROPPING)
    positives, _ = match_phrases(remaining, IMAGECROPPING)
    return positives, denials


def module_evidence(source):
    tree = ast.parse(source)
    nodes = list(ast.walk(tree))
    shadowed = {n.name for n in nodes if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
    imports = {}
    for n in nodes:
        if isinstance(n, ast.Import):
            for a in n.names:
                imports[a.asname or a.name.split('.')[0]] = a.name if a.asname else a.name.split('.')[0]
        elif isinstance(n, ast.ImportFrom) and n.module:
            for a in n.names:
                imports[a.asname or a.name] = n.module + '.' + a.name

    def resolve(n):
        if isinstance(n, ast.Name):
            return imports.get(n.id, '') if n.id not in shadowed else ''
        if isinstance(n, ast.Attribute):
            base = resolve(n.value)
            return base + '.' + n.attr if base and n.attr not in shadowed else ''
        return ''

    def call_path(n):
        return resolve(n.func) if isinstance(n, ast.Call) else ''

    pil = set()
    cv = set()
    transforms = set()
    for n in nodes:
        if isinstance(n, (ast.Assign, ast.AnnAssign)):
            value = n.value
            targets = n.targets if isinstance(n, ast.Assign) else [n.target]
            path = call_path(value)
            for target in targets:
                if not isinstance(target, ast.Name) or target.id in shadowed:
                    continue
                if path == 'PIL.Image.open':
                    pil.add(target.id)
                if path == 'cv2.imread':
                    cv.add(target.id)
                if any(path == base + '.' + cls for base in TRANSFORM_SOURCES for cls in CROP_CLASSES):
                    transforms.add(target.id)

    def region(n):
        # Index wrappers exist on older supported interpreters.
        if isinstance(n, ast.Index):
            n = n.value
        parts = n.elts[:2] if isinstance(n, ast.Tuple) else [n]
        return any(isinstance(p, ast.Slice) and (p.lower is not None or p.upper is not None) for p in parts)

    for n in nodes:
        if isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name) and n.value.id in cv and region(n.slice):
            return True
        if not isinstance(n, ast.Call):
            continue
        path = resolve(n.func)
        if path in ('PIL.ImageOps.crop', 'skimage.util.crop', 'torchvision.transforms.functional.crop'):
            return True
        if isinstance(n.func, ast.Attribute):
            if n.func.attr in GENERIC_NAMES and n.func.attr not in shadowed:
                return True
            if n.func.attr in PIL_METHODS and n.func.attr not in shadowed:
                base = n.func.value
                if (isinstance(base, ast.Name) and base.id in pil) or call_path(base) == 'PIL.Image.open':
                    return True
        elif isinstance(n.func, ast.Name):
            name = n.func.id
            if name in transforms and name not in shadowed:
                return True
            if path and path.rsplit('.', 1)[-1] in GENERIC_NAMES:
                return True
        elif isinstance(n.func, ast.Call):
            path = call_path(n.func)
            if any(path == base + '.' + cls for base in TRANSFORM_SOURCES for cls in CROP_CLASSES):
                return True
    return False


def audit(repo='.', ignore=(), decisions=None):
    root = Path(repo)
    if not root.is_dir():
        raise OSError('Repository is not a directory: ' + str(root))
    positive = denial = test_positive = evidence = False
    for path in sorted(root.rglob('*')):
        rel = path.relative_to(root).as_posix()
        if any(part in EXCLUDED for part in path.relative_to(root).parts) or any(rel.startswith(p) for p in ignore):
            continue
        if any((parent / 'pyvenv.cfg').exists() for parent in path.parents if parent != root.parent and root in (parent, *parent.parents)):
            continue
        if not path.is_file():
            continue
        is_test = 'tests' in path.relative_to(root).parts[:-1]
        is_doc = rel == 'README.md' or (rel.startswith('docs/') and path.suffix == '.md')
        if is_doc or is_test:
            text = path.read_text(encoding='utf-8')
            yes, no = claims(prose(text) if path.suffix == '.md' else text)
            if is_doc and not is_test:
                positive |= bool(yes)
                denial |= bool(no)
            elif is_test:
                test_positive |= bool(yes)
        if path.suffix == '.py':
            try:
                found = module_evidence(path.read_text(encoding='utf-8'))
            except SyntaxError:
                found = False
                if decisions is not None:
                    decisions.append(rel + ': invalid syntax; no evidence')
            evidence |= found
            if decisions is not None:
                decisions.append(rel + (': evidence' if found else ': no evidence'))
        elif is_doc and decisions is not None:
            decisions.append(rel + ': documentation scanned')
    findings = []
    if positive and not evidence:
        findings.append({'rule': 'documented-image-cropping-claim-false', 'verdict': 'HIGH', 'message': 'Documentation asserts the checked capability without source evidence.'})
    elif test_positive and not positive and not evidence:
        findings.append({'rule': 'documented-image-cropping-claim-false', 'verdict': 'MEDIUM', 'message': 'Only test fixtures assert the checked capability without source evidence.'})
    if denial and evidence:
        findings.append({'rule': 'documented-no-image-cropping-claim-false', 'verdict': 'HIGH', 'message': 'Documentation denies the checked capability despite source evidence.'})
    return findings
