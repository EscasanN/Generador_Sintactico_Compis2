"""Generación explícita: python scripts/generate_parser.py --jar tools/antlr-4.13.2-complete.jar."""
import argparse
import hashlib
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SHA = 'eae2dfa119a64327444672aff63e9ec35a20180dc5b8090b7a6ab85125df4d76'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--jar', type=Path, required=True)
    args = parser.parse_args()
    jar = args.jar.resolve()
    if hashlib.sha256(jar.read_bytes()).hexdigest() != SHA:
        parser.error('JAR incorrecto: se requiere ANTLR 4.13.2 oficial')
    target = ROOT / 'src/sql_interpreter/generated'
    target.mkdir(parents=True, exist_ok=True)
    subprocess.run(['java', '-jar', str(jar), '-Dlanguage=Python3', '-visitor', '-no-listener', '-o', str(target), 'SQL.g4'], cwd=ROOT / 'src/sql_interpreter/grammar', check=True)
    (target / '__init__.py').touch()


if __name__ == '__main__':
    main()
