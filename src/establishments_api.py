"""Operações REST autenticadas dos estabelecimentos no Supabase.

Somente a chave PUBLICÁVEL está no cliente; o JWT do Google/Supabase
identifica o proprietário e as policies RLS isolam os dados.
"""

import json
import urllib.error
import urllib.parse
import urllib.request
import uuid

from supabase_config import SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY


class ErroEstabelecimento(Exception):
    """Erro controlado que pode ser mostrado no formulário."""


def _requisitar(metodo: str, token: str, query: str, dados=None):
    if not token:
        raise ErroEstabelecimento("Entre com Google para continuar.")
    url = f"{SUPABASE_URL}/rest/v1/establishments{query}"
    headers = {
        "apikey": SUPABASE_PUBLISHABLE_KEY,
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    corpo = None
    if dados is not None:
        corpo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
        headers["Prefer"] = "return=representation"

    req = urllib.request.Request(
        url, data=corpo, headers=headers, method=metodo,
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as resposta:
            bruto = resposta.read()
            return json.loads(bruto) if bruto else []
    except urllib.error.HTTPError as erro:
        if erro.code in (401, 403):
            raise ErroEstabelecimento(
                "A sessão expirou ou você não tem permissão. "
                "Entre com Google novamente."
            ) from erro
        if erro.code == 404:
            raise ErroEstabelecimento(
                "Cadastro indisponível. Confira a Data API no Supabase."
            ) from erro
        if erro.code == 400:
            raise ErroEstabelecimento(
                "Não foi possível salvar. Confira os campos informados."
            ) from erro
        if erro.code == 409:
            raise ErroEstabelecimento(
                "Já existe um registro com esses dados."
            ) from erro
        raise ErroEstabelecimento(
            "Não foi possível consultar o estabelecimento no momento."
        ) from erro
    except (urllib.error.URLError, TimeoutError) as erro:
        raise ErroEstabelecimento(
            "Falha de conexão. Confira sua internet e tente novamente."
        ) from erro
    except (ValueError, TypeError) as erro:
        raise ErroEstabelecimento(
            "O servidor retornou uma resposta inesperada."
        ) from erro


def obter_estabelecimento(token: str):
    """Lista somente registros do usuário autenticado, conforme RLS."""
    query = (
        "?select=id,name,business_type,phone,address,description,"
        "onboarding_step,onboarding_completed"
        "&order=created_at.asc&limit=1"
    )
    registros = _requisitar("GET", token, query)
    return registros[0] if registros else None


def salvar_primeira_etapa(token: str, formulario: dict, identificador=None):
    """Salva o negócio. A próxima etapa pendente será Horários (2/5)."""
    nome = (formulario.get("name") or "").strip()
    tipo = (formulario.get("business_type") or "").strip()
    telefone = (formulario.get("phone") or "").strip()
    endereco = (formulario.get("address") or "").strip()
    descricao = (formulario.get("description") or "").strip()
    if not 2 <= len(nome) <= 120:
        raise ErroEstabelecimento(
            "Informe o nome do estabelecimento (2 a 120 caracteres)."
        )
    if not tipo:
        raise ErroEstabelecimento("Informe a atividade do estabelecimento.")
    if any(len(texto) > limite for texto, limite in
           ((tipo, 80), (telefone, 30), (endereco, 250), (descricao, 500))):
        raise ErroEstabelecimento("Um dos campos excedeu o tamanho permitido.")

    dados = {
        "name": nome,
        "business_type": tipo,
        "phone": telefone,
        "address": endereco,
        "description": descricao,
    }
    if identificador:
        try:
            identificador = str(uuid.UUID(str(identificador)))
        except ValueError as erro:
            raise ErroEstabelecimento(
                "Identificador inválido do estabelecimento."
            ) from erro
        filtro = "?id=eq." + urllib.parse.quote(identificador, safe="-")
        resultado = _requisitar("PATCH", token, filtro, dados)
        if not resultado:
            raise ErroEstabelecimento(
                "Cadastro não encontrado ou sem permissão de edição."
            )
    else:
        dados["onboarding_step"] = 2
        dados["onboarding_completed"] = False
        resultado = _requisitar("POST", token, "", dados)
    if not isinstance(resultado, list) or not resultado:
        raise ErroEstabelecimento("O servidor não confirmou o salvamento.")
    return resultado[0]
