"""Guardado de documentos sin truncar el destino antes de completar la escritura."""
import os
from pathlib import Path
import tempfile


def atomic_write_text(path: str | Path, text: str) -> None:
    target = Path(path)
    descriptor, name = tempfile.mkstemp(prefix=f'.{target.name}.', suffix='.tmp', dir=target.parent)
    temporary = Path(name)
    try:
        os.close(descriptor)
        temporary.write_text(text, encoding='utf-8')
        with temporary.open('r+b') as stream:
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
