"""Clientes reais do SchedulePro: API REST protegida por JWT e RLS."""

import json
import re
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone

from establishments_api import ErroEstabelecimento
from supabase_config import SUPABASE_PUBLISHABLE_KEY, SUPABASE_URL


def _uuid(valor):
    try:
        return str(uuid.UUID(str(valor)))
    except (TypeError, ValueError, AttributeError) as exc:
        raise ErroEstabelecimento("Identificador de cliente inválido.") from exc


def validar_cliente(campos):
    """Valida dados mínimos; telefone e e-mail são opcionais."""
    nome = str(campos.get("name") or "").strip()
    telefone = str(campos.get("phone") or "").strip()
    email = str(campos.get("email") or "").strip().lower()
    notas = str(campos.get("notes") or "").strip()
    if not 2 <= len(nome) <= 120:
        raise ErroEstabelecimento(
            "Informe o nome do cliente (2 a 120 caracteres)."
        )
    if telefone:
        digitos = "".join(c for c in telefone if c.isdigit())
        if digitos.startswith("55") and len(digitos) in (12, 13):
            digitos = digitos[2:]
        if len(digitos) not in (10, 11):
            raise ErroEstabelecimento(
                "Telefone deve ter DDD e 10 ou 11 dígitos."
            )
        ddd, numero = digitos[:2], digitos[2:]
        divisor = 5 if len(numero) == 9 else 4
        telefone = f"({ddd}) {numero[:divisor]}-{numero[divisor:]}"
    if email and (
        len(email) > 254
        or re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email) is None
    ):
        raise ErroEstabelecimento(
            "Informe um e-mail válido ou deixe o campo vazio."
        )
    if len(notas) > 1500:
        raise ErroEstabelecimento(
            "Observações: limite de 1.500 caracteres."
        )
    return {
        "name": nome,
        "phone": telefone,
        "email": email,
        "notes": notas,
    }


def _pedir(token, recurso, metodo="GET", dados=None):
    if not token:
        raise ErroEstabelecimento("Sua sessão terminou. Entre novamente.")
    cabecalhos = {
        "apikey": SUPABASE_PUBLISHABLE_KEY,
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    corpo = None
    if dados is not None:
        corpo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
        cabecalhos["Content-Type"] = "application/json"
        cabecalhos["Prefer"] = "return=representation"
    elif metodo == "DELETE":
        cabecalhos["Prefer"] = "return=representation"
    requisicao = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/{recurso}",
        headers=cabecalhos, data=corpo, method=metodo,
    )
    try:
        with urllib.request.urlopen(requisicao, timeout=25) as resposta:
            bruto = resposta.read()
            return json.loads(bruto) if bruto else []
    except urllib.error.HTTPError as erro:
        if erro.code in (401, 403):
            mensagem = "Sessão expirada ou sem permissão."
        elif erro.code == 404:
            mensagem = "Cadastro de clientes indisponível no servidor."
        elif erro.code == 409:
            mensagem = (
                "Já existe um cliente com esse telefone ou e-mail, "
                "ou o cliente possui agendamentos vinculados."
            )
        elif erro.code in (400, 422):
            mensagem = "Não foi possível salvar. Revise os dados do cliente."
        else:
            mensagem = "Não foi possível concluir a operação no Supabase."
        raise ErroEstabelecimento(mensagem) from erro
    except (urllib.error.URLError, TimeoutError) as erro:
        raise ErroEstabelecimento(
            "Falha de conexão. Confira a internet."
        ) from erro
    except (ValueError, TypeError) as erro:
        raise ErroEstabelecimento(
            "Resposta inesperada do servidor."
        ) from erro


def listar_clientes(token, estabelecimento_id):
    negocio = _uuid(estabelecimento_id)
    resultado = _pedir(
        token,
        "customers?establishment_id=eq." + negocio
        + "&select=id,name,phone,email,notes,is_archived,created_at,updated_at"
        + "&order=created_at.desc&limit=500",
    )
    if not isinstance(resultado, list):
        raise ErroEstabelecimento("Lista de clientes inválida.")
    return resultado


def salvar_cliente(token, estabelecimento_id, formulario, cliente_id=None):
    negocio = _uuid(estabelecimento_id)
    dados = validar_cliente(formulario)
    if cliente_id is None:
        recurso = "customers"
        metodo = "POST"
        dados["establishment_id"] = negocio
    else:
        recurso = (
            "customers?id=eq." + _uuid(cliente_id)
            + "&establishment_id=eq." + negocio
        )
        metodo = "PATCH"
        dados["updated_at"] = datetime.now(timezone.utc).isoformat()
    resposta = _pedir(token, recurso, metodo=metodo, dados=dados)
    if not isinstance(resposta, list) or len(resposta) != 1:
        raise ErroEstabelecimento(
            "O servidor não confirmou o cadastro do cliente."
        )
    return resposta[0]


def arquivar_cliente(token, estabelecimento_id, cliente_id, arquivar=True):
    negocio = _uuid(estabelecimento_id)
    resposta = _pedir(
        token,
        "customers?id=eq." + _uuid(cliente_id)
        + "&establishment_id=eq." + negocio,
        metodo="PATCH",
        dados={
            "is_archived": arquivar is True,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    if not isinstance(resposta, list) or len(resposta) != 1:
        raise ErroEstabelecimento(
            "O cliente não foi encontrado ou falta permissão."
        )
    return resposta[0]


def excluir_cliente(token, estabelecimento_id, cliente_id):
    negocio = _uuid(estabelecimento_id)
    resposta = _pedir(
        token,
        "customers?id=eq." + _uuid(cliente_id)
        + "&establishment_id=eq." + negocio,
        metodo="DELETE",
    )
    if not isinstance(resposta, list) or len(resposta) != 1:
        raise ErroEstabelecimento(
            "A exclusão não foi confirmada pelo servidor."
        )
    return resposta[0]
