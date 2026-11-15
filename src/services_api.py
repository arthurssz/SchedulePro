"""Catálogo de serviços do SchedulePro via REST com JWT e RLS.

O servidor valida proprietário do estabelecimento; o cliente envia apenas
a chave publicável Supabase e o JWT autenticado do usuário atual.
"""

import json
import re
import urllib.error
import urllib.request
import uuid
from decimal import Decimal, InvalidOperation

from establishments_api import ErroEstabelecimento
from supabase_config import SUPABASE_PUBLISHABLE_KEY, SUPABASE_URL


_PRECO = re.compile(r"^\d{1,5}(?:[,.]\d{1,2})?$")


def _uuid(valor):
    try:
        return str(uuid.UUID(str(valor)))
    except (TypeError, ValueError, AttributeError) as erro:
        raise ErroEstabelecimento(
            "Identificador inválido do estabelecimento ou serviço."
        ) from erro


def valor_em_centavos(texto):
    """Aceita preço em reais: 50, 50,00 ou 50.00. Sem floats."""
    if not isinstance(texto, str):
        raise ErroEstabelecimento("Digite um preço válido em reais.")
    bruto = texto.strip().replace("R$", "").strip().replace(" ", "")
    if not _PRECO.fullmatch(bruto):
        raise ErroEstabelecimento(
            "Preço inválido. Exemplos: 50,00 ou 0,00."
        )
    try:
        centavos = int(
            (Decimal(bruto.replace(",", ".")) * 100)
            .quantize(Decimal("1"))
        )
    except (InvalidOperation, ValueError) as erro:
        raise ErroEstabelecimento("Preço inválido.") from erro
    if centavos > 10000000:
        raise ErroEstabelecimento("Preço máximo: R$ 100.000,00.")
    return centavos


def formatar_preco(centavos):
    centavos = int(centavos)
    reais, parte = divmod(centavos, 100)
    return f"R$ {reais:,}".replace(",", ".") + f",{parte:02d}"


def validar_servico(dados):
    nome = str(dados.get("name") or "").strip()
    descricao = str(dados.get("description") or "").strip()
    try:
        duracao = int(str(dados.get("duration_minutes") or "").strip())
    except (ValueError, TypeError) as erro:
        raise ErroEstabelecimento(
            "A duração deve ser informada em minutos."
        ) from erro
    if not 2 <= len(nome) <= 120:
        raise ErroEstabelecimento("Nome: informe entre 2 e 120 caracteres.")
    if not 5 <= duracao <= 480:
        raise ErroEstabelecimento(
            "A duração deve ser entre 5 e 480 minutos."
        )
    if len(descricao) > 500:
        raise ErroEstabelecimento(
            "Descrição: limite de 500 caracteres."
        )
    return {
        "name": nome,
        "duration_minutes": duracao,
        "price_cents": valor_em_centavos(
            str(dados.get("price") if dados.get("price") is not None else "")
        ),
        "description": descricao,
        "is_active": dados.get("is_active") is True,
    }


def _pedir(token, caminho, metodo="GET", corpo=None):
    if not token:
        raise ErroEstabelecimento(
            "Entre com Google para gerenciar os serviços."
        )
    headers = {
        "apikey": SUPABASE_PUBLISHABLE_KEY,
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    payload = None
    if corpo is not None:
        headers["Content-Type"] = "application/json"
        headers["Prefer"] = "return=representation"
        payload = json.dumps(
            corpo, ensure_ascii=False,
        ).encode("utf-8")
    requisicao = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/{caminho}",
        data=payload,
        headers=headers,
        method=metodo,
    )
    try:
        with urllib.request.urlopen(requisicao, timeout=25) as resposta:
            bruto = resposta.read()
            return json.loads(bruto) if bruto else []
    except urllib.error.HTTPError as erro:
        if erro.code in (401, 403):
            mensagem = "Sua sessão expirou ou você não tem permissão."
        elif erro.code == 404:
            mensagem = "Tabela de serviços indisponível no Supabase."
        elif erro.code in (400, 409, 422):
            mensagem = "Não foi possível salvar. Verifique os campos."
        else:
            mensagem = "O Supabase não conseguiu processar o pedido."
        raise ErroEstabelecimento(mensagem) from erro
    except (urllib.error.URLError, TimeoutError) as erro:
        raise ErroEstabelecimento(
            "Falha na conexão. Confira a internet."
        ) from erro
    except (TypeError, ValueError) as erro:
        raise ErroEstabelecimento(
            "Resposta inesperada do servidor."
        ) from erro


def listar_servicos(token, estabelecimento_id):
    estabelecimento_id = _uuid(estabelecimento_id)
    return _pedir(
        token,
        "services?establishment_id=eq." + estabelecimento_id
        + "&select=id,name,duration_minutes,price_cents,description,is_active"
        + "&order=created_at.asc",
    )


def salvar_servico(
    token, estabelecimento_id, formulario,
    servico_id=None, etapa_atual=3,
):
    estabelecimento_id = _uuid(estabelecimento_id)
    dados = validar_servico(formulario)
    if servico_id:
        servico_id = _uuid(servico_id)
        resultado = _pedir(
            token,
            "services?id=eq." + servico_id
            + "&establishment_id=eq." + estabelecimento_id,
            metodo="PATCH",
            corpo=dados,
        )
    else:
        resultado = _pedir(
            token, "services",
            metodo="POST",
            corpo={"establishment_id": estabelecimento_id, **dados},
        )
    if not isinstance(resultado, list) or len(resultado) != 1:
        raise ErroEstabelecimento(
            "O servidor não confirmou a gravação do serviço."
        )
    servico = resultado[0]
    servico["_etapa_avancou"] = False
    # Um serviço ativo é necessário para concluir a etapa 3/5.
    if dados["is_active"] and int(etapa_atual or 1) < 4:
        try:
            etapa = _pedir(
                token, "establishments?id=eq." + estabelecimento_id,
                metodo="PATCH",
                corpo={"onboarding_step": 4},
            )
            servico["_etapa_avancou"] = bool(etapa)
            if not etapa:
                servico["_aviso"] = (
                    "Serviço salvo, mas a etapa não avançou. Tente editar."
                )
        except ErroEstabelecimento:
            servico["_aviso"] = (
                "Serviço salvo, mas a etapa não avançou. Tente editar."
            )
    return servico


def alterar_atividade(token, estabelecimento_id, servico_id, ativo):
    estabelecimento_id, servico_id = (
        _uuid(estabelecimento_id), _uuid(servico_id)
    )
    resultado = _pedir(
        token, "services?id=eq." + servico_id
        + "&establishment_id=eq." + estabelecimento_id,
        metodo="PATCH",
        corpo={"is_active": ativo is True},
    )
    if not isinstance(resultado, list) or len(resultado) != 1:
        raise ErroEstabelecimento(
            "Serviço não encontrado ou sem permissão."
        )
    return resultado[0]
