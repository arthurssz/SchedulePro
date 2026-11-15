"""Gerenciamento de profissionais e suas especialidades via Supabase.

A gravação do profissional e dos serviços acontece numa única transação
PostgreSQL (RPC SECURITY INVOKER sujeita à RLS, sem chave administrativa).
"""

import json
import re
import urllib.error
import urllib.request
import uuid

from establishments_api import ErroEstabelecimento
from supabase_config import SUPABASE_PUBLISHABLE_KEY, SUPABASE_URL


def _uuid(valor):
    try:
        return str(uuid.UUID(str(valor)))
    except (ValueError, TypeError, AttributeError) as erro:
        raise ErroEstabelecimento("Identificador inválido.") from erro


def _pedir(token, caminho, metodo="GET", dados=None):
    if not token:
        raise ErroEstabelecimento("Entre com Google para continuar.")
    cabecalhos = {
        "apikey": SUPABASE_PUBLISHABLE_KEY,
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    corpo = None
    if dados is not None:
        cabecalhos["Content-Type"] = "application/json"
        cabecalhos["Prefer"] = "return=representation"
        corpo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/{caminho}",
        data=corpo, headers=cabecalhos, method=metodo,
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as resposta:
            bruto = resposta.read()
            return json.loads(bruto) if bruto else []
    except urllib.error.HTTPError as erro:
        if erro.code in (401, 403):
            mensagem = "Sessão expirada ou sem permissão. Entre novamente."
        elif erro.code == 404:
            mensagem = "Cadastro de profissionais indisponível na API."
        elif erro.code in (400, 409, 422):
            mensagem = "Não foi possível salvar. Revise os dados e serviços."
        else:
            mensagem = "O Supabase não conseguiu processar o pedido."
        raise ErroEstabelecimento(mensagem) from erro
    except (urllib.error.URLError, TimeoutError) as erro:
        raise ErroEstabelecimento(
            "Falha na conexão. Confira a internet."
        ) from erro
    except (TypeError, ValueError) as erro:
        raise ErroEstabelecimento(
            "Resposta inesperada do Supabase."
        ) from erro


def validar_profissional(formulario):
    nome = str(formulario.get("name") or "").strip()
    especialidade = str(formulario.get("specialty") or "").strip()
    telefone = str(formulario.get("phone") or "").strip()
    email = str(formulario.get("email") or "").strip()
    ativo = formulario.get("is_active") is True

    if not 2 <= len(nome) <= 120:
        raise ErroEstabelecimento(
            "Informe o nome do profissional (2 a 120 caracteres)."
        )
    if len(especialidade) > 120 or len(telefone) > 30 or len(email) > 254:
        raise ErroEstabelecimento("Um campo excedeu o tamanho permitido.")
    if email and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise ErroEstabelecimento("Informe um e-mail válido ou deixe vazio.")
    if telefone:
        digitos = "".join(c for c in telefone if c.isdigit())
        if digitos.startswith("55") and len(digitos) in (12, 13):
            digitos = digitos[2:]
        if len(digitos) not in (10, 11):
            raise ErroEstabelecimento(
                "Telefone precisa ter DDD e 10 ou 11 dígitos."
            )
    ids = formulario.get("service_ids")
    if not isinstance(ids, list) or len(ids) > 100:
        raise ErroEstabelecimento("Seleção de serviços inválida.")
    ids = [_uuid(identificador) for identificador in ids]
    if len(set(ids)) != len(ids):
        raise ErroEstabelecimento("Não repita serviços.")
    if ativo and not ids:
        raise ErroEstabelecimento(
            "Selecione ao menos um serviço para o profissional ativo."
        )
    return {
        "name": nome,
        "specialty": especialidade,
        "phone": telefone,
        "email": email,
        "is_active": ativo,
        "service_ids": ids,
    }


def listar_profissionais(token, estabelecimento_id):
    negocio = _uuid(estabelecimento_id)
    lista = _pedir(
        token,
        "professionals?establishment_id=eq." + negocio
        + "&select=id,name,specialty,phone,email,is_active"
        + "&order=created_at.asc",
    )
    vinculos = _pedir(
        token,
        "professional_services?establishment_id=eq." + negocio
        + "&select=professional_id,service_id",
    )
    mapa = {item["id"]: [] for item in lista}
    for vinculo in vinculos:
        ident = vinculo.get("professional_id")
        if ident in mapa:
            mapa[ident].append(vinculo["service_id"])
    for item in lista:
        item["service_ids"] = mapa[item["id"]]
    return lista


def salvar_profissional(token, estabelecimento_id, formulario, profissional_id=None):
    negocio = _uuid(estabelecimento_id)
    dados = validar_profissional(formulario)
    resultado = _pedir(
        token,
        "rpc/save_schedulepro_professional",
        metodo="POST",
        dados={
            "p_establishment_id": negocio,
            "p_name": dados["name"],
            "p_specialty": dados["specialty"],
            "p_phone": dados["phone"],
            "p_email": dados["email"],
            "p_is_active": dados["is_active"],
            "p_service_ids": dados["service_ids"],
            "p_professional_id": (
                _uuid(profissional_id) if profissional_id else None
            ),
        },
    )
    if not isinstance(resultado, dict) or not resultado.get("id"):
        raise ErroEstabelecimento(
            "O servidor não confirmou o cadastro do profissional."
        )
    return resultado
