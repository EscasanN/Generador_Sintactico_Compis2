"""Copia distribuciones locales a un venv vacío para QA sin acceso a PyPI.

No sustituye una instalación desde PyPI: el informe debe indicar ese límite.
Uso: py scripts/prepare_offline_dependencies.py ruta/al/venv/python.exe
"""
from importlib.metadata import distribution
import json
from pathlib import Path
import shutil
import subprocess
import sys
from packaging.requirements import Requirement


def main():
    python = Path(sys.argv[1]).resolve()
    info = json.loads(subprocess.check_output([str(python), '-I', '-c',
        'import json,sys,sysconfig; print(json.dumps([sys.prefix,sys.base_prefix,sysconfig.get_path("purelib")]))'],text=True))
    if info[0] == info[1]:
        raise SystemExit('Se requiere un entorno virtual, no Python global')
    destination = Path(info[2])
    copied = {}
    def install(name):
        dist = distribution(name)
        canonical = dist.metadata['Name'].lower().replace('_','-')
        if canonical in copied:
            return
        copied[canonical] = dist.version
        for item in dist.files or []:
            if '..' in item.parts or item.is_absolute():
                continue
            source = Path(dist.locate_file(item))
            if source.is_file():
                target = destination / str(item)
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(source,target)
        for text in dist.requires or []:
            req = Requirement(text)
            if req.marker is None or req.marker.evaluate({'extra':''}):
                install(req.name)
    for name in ('antlr4-python3-runtime','PyQt6','pytest'):
        install(name)
    print(json.dumps(copied,indent=2))


if __name__ == '__main__':
    main()
