"""Agendamentos internos reais: Supabase JWT, horários e conflitos no servidor."""

import json
import re
import urllib.error
import urllib.request
import uuid
from datetime import date, datetime, time

from establishments_api import ErroEstabelecimento
from supabase_config import SUPABASE_PUBLISHABLE_KEY, SUPABASE_URL


def _id(valor):
    try:
        return str(uuid.UUID(str(valor)))
    except (ValueError, TypeError, AttributeError) as erro:
        raise ErroEstabelecimento("Identificador inválido no agendamento.") from erro


def validar_agendamento(dados):
    try:
        dia = date.fromisoformat(str(dados.get("local_date")))
        horario = time.fromisoformat(str(dados.get("local_time")))
    except (ValueError, TypeError) as erro:
        raise ErroEstabelecimento(
            "Informe data e horário válidos para o agendamento."
        ) from erro
    if horario.second or horario.microsecond or horario.tzinfo:
        raise ErroEstabelecimento("Informe o horário no formato HH:MM.")
    obs = str(dados.get("notes") or "").strip()
    if len(obs) > 1000:
        raise ErroEstabelecimento("Observações: máximo 1.000 caracteres.")
    return {
        "p_customer_id": _id(dados.get("customer_id")),
        "p_professional_id": _id(dados.get("professional_id")),
        "p_service_id": _id(dados.get("service_id")),
        "p_local_date": dia.isoformat(),
        "p_local_time": horario.strftime("%H:%M"),
        "p_notes": obs,
    }


def _pedir(token, caminho, dados=None):
    if not token:
        raise ErroEstabelecimento("Entre novamente com Google.")
    cabecalhos = {
        "apikey": SUPABASE_PUBLISHABLE_KEY,
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    corpo = None
    if dados is not None:
        cabecalhos["Content-Type"] = "application/json"
        corpo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
    requisicao = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/{caminho}",
        headers=cabecalhos,
        data=corpo,
        method="POST" if dados is not None else "GET",
    )
    try:
        with urllib.request.urlopen(requisicao, timeout=25) as resposta:
            conteudo = resposta.read()
            return json.loads(conteudo) if conteudo else []
    except urllib.error.HTTPError as erro:
        if erro.code in (401, 403):
            mensagem = "Sua sessão expirou ou você não tem permissão."
        elif erro.code == 404:
            mensagem = "A agenda ainda não está disponível no servidor."
        elif erro.code in (400, 409, 422):
            mensagem = "Não foi possível concluir. Verifique os dados."
            try:
                detalhe = json.loads(erro.read() or b"{}").get("message", "")
                permitidas = (
                    "Este profissional já tem agendamento nesse horário.",
                    "Horário fora do funcionamento do estabelecimento.",
                    "Horário fora da jornada do profissional.",
                    "Profissional não realiza o serviço selecionado.",
                    "Serviço indisponível.",
                    "Profissional indisponível.",
                    "Selecione um cliente ativo do seu estabelecimento.",
                    "Escolha um horário futuro.",
                    "O serviço precisa terminar no mesmo dia.",
                    "Agendamentos são aceitos até 365 dias à frente.",
                    "Estabelecimento não ativo ou sem permissão.",
                    "Agendamento não encontrado.",
                    "Este agendamento já foi finalizado e não pode ser alterado.",
                    "Somente agendamentos pendentes podem ser confirmados.",
                    "Não é possível confirmar um horário que já começou.",
                    "Aguarde o fim do horário para concluir o atendimento.",
                    "Status solicitado inválido.",
                    "Data ou horário inválido.",
                    "Não é possível reagendar um atendimento que já começou.",
                    "Escolha uma data ou horário diferente do atual.",
                )
                if detalhe in permitidas:
                    mensagem = detalhe
            except (ValueError, TypeError):
                pass
        else:
            mensagem = "O servidor não conseguiu concluir o agendamento."
        raise ErroEstabelecimento(mensagem) from erro
    except (urllib.error.URLError, TimeoutError) as erro:
        raise ErroEstabelecimento(
            "Falha de conexão. Confira a internet."
        ) from erro
    except (ValueError, TypeError) as erro:
        raise ErroEstabelecimento(
            "Resposta inesperada do servidor."
        ) from erro


def criar_agendamento(token, estabelecimento_id, dados):
    parametros = validar_agendamento(dados)
    parametros["p_establishment_id"] = _id(estabelecimento_id)
    resultado = _pedir(
        token, "rpc/schedulepro_create_internal_appointment",
        dados=parametros,
    )
    if not isinstance(resultado, dict) or not resultado.get("id"):
        raise ErroEstabelecimento(
            "O servidor não confirmou o agendamento."
        )
    return resultado


def listar_agendamentos(token, estabelecimento_id, inicio, fim):
    try:
        dia_inicio = date.fromisoformat(str(inicio))
        dia_fim = date.fromisoformat(str(fim))
    except (TypeError, ValueError) as erro:
        raise ErroEstabelecimento("Período de agenda inválido.") from erro
    if dia_fim < dia_inicio or (dia_fim - dia_inicio).days > 62:
        raise ErroEstabelecimento("O período da agenda deve ter até 63 dias.")
    caminho = (
        "appointments?establishment_id=eq." + _id(estabelecimento_id)
        + "&local_date=gte." + dia_inicio.isoformat()
        + "&local_date=lte." + dia_fim.isoformat()
        + "&select=id,local_date,local_time,starts_at,ends_at,price_cents,status,notes,"
        + "customer:customers(name),professional:professionals(id,name),"
        + "service:services(id,name,duration_minutes)"
        + "&order=local_date.asc,local_time.asc&limit=500"
    )
    registros = _pedir(token, caminho)
    if not isinstance(registros, list):
        raise ErroEstabelecimento("Lista de agendamentos inválida.")
    return registros


STATUS_EDITAVEIS = frozenset(("confirmed", "completed", "canceled"))


def alterar_status_agendamento(token, estabelecimento_id, agendamento_id, status):
    """Altera a situação via RPC segura; nunca permite PATCH direto do APK."""
    if status not in STATUS_EDITAVEIS:
        raise ErroEstabelecimento("Situação de agendamento inválida.")
    parametros = {
        "p_establishment_id": _id(estabelecimento_id),
        "p_appointment_id": _id(agendamento_id),
        "p_new_status": status,
    }
    resposta = _pedir(
        token, "rpc/schedulepro_change_appointment_status",
        dados=parametros,
    )
    if not isinstance(resposta, dict) or not resposta.get("id"):
        raise ErroEstabelecimento(
            "O servidor não confirmou a atualização do agendamento."
        )
    if resposta.get("status") != status:
        raise ErroEstabelecimento(
            "O servidor retornou uma situação diferente da solicitada."
        )
    return resposta


def reagendar_agendamento(
    token, estabelecimento_id, agendamento_id, nova_data, novo_horario,
):
    """Move um agendamento ativo de forma atômica, com auditoria no Postgres."""
    try:
        dia = date.fromisoformat(str(nova_data))
        hora = time.fromisoformat(str(novo_horario))
    except (ValueError, TypeError) as erro:
        raise ErroEstabelecimento(
            "Informe data e horário válidos para o reagendamento."
        ) from erro
    if hora.second or hora.microsecond or hora.tzinfo:
        raise ErroEstabelecimento("Informe o horário no formato HH:MM.")
    identificador = _id(agendamento_id)
    resposta = _pedir(
        token,
        "rpc/schedulepro_reschedule_internal_appointment",
        dados={
            "p_establishment_id": _id(estabelecimento_id),
            "p_appointment_id": identificador,
            "p_new_local_date": dia.isoformat(),
            "p_new_local_time": hora.strftime("%H:%M"),
        },
    )
    if (
        not isinstance(resposta, dict)
        or resposta.get("id") != identificador
        or resposta.get("status") != "scheduled"
    ):
        raise ErroEstabelecimento(
            "O servidor não confirmou o reagendamento."
        )
    return resposta


def listar_historico_reagendamentos(
    token, estabelecimento_id, agendamento_id,
):
    """Histórico visível apenas para o dono autenticado via RLS."""
    caminho = (
        "appointment_reschedule_history?"
        + "establishment_id=eq." + _id(estabelecimento_id)
        + "&appointment_id=eq." + _id(agendamento_id)
        + "&select=old_local_date,old_local_time,new_local_date,"
        + "new_local_time,old_status,changed_at"
        + "&order=changed_at.desc&limit=50"
    )
    resposta = _pedir(token, caminho)
    if not isinstance(resposta, list):
        raise ErroEstabelecimento("Histórico inválido.")
    return resposta
