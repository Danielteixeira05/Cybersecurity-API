from pathlib import Path
from uuid import uuid4
import hashlib

from django.conf import settings
from django.utils.text import get_valid_filename


def guardar_documento(ficheiro) -> dict:
    pasta = Path(settings.MEDIA_ROOT) / 'private_uploads' / 'documentos'
    pasta.mkdir(parents=True, exist_ok=True)
    nome_original = get_valid_filename(Path(ficheiro.name).name)
    extensao = Path(nome_original).suffix.lower()
    nome_guardado = f'{uuid4().hex}{extensao}'
    caminho = pasta / nome_guardado
    sha256 = hashlib.sha256()
    tamanho = 0
    with caminho.open('wb') as destino:
        for bloco in ficheiro.chunks():
            destino.write(bloco)
            sha256.update(bloco)
            tamanho += len(bloco)
    return {
        'nome_ficheiro_original': nome_original,
        'nome_ficheiro_guardado': nome_guardado,
        'caminho_ficheiro': caminho.relative_to(settings.MEDIA_ROOT).as_posix(),
        'tipo_mime': ficheiro.content_type or 'application/octet-stream',
        'tamanho_bytes': tamanho,
        'hash_sha256': sha256.hexdigest(),
    }


def caminho_privado(relativo: str) -> Path:
    raiz = Path(settings.MEDIA_ROOT).resolve()
    caminho = (raiz / relativo).resolve()
    if raiz not in caminho.parents:
        raise ValueError('Caminho de ficheiro invalido.')
    return caminho
