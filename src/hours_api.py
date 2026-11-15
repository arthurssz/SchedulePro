"""Horários semanais do estabelecimento, isolados por RLS no Supabase."""

import json
import re
import urllib.error
import urllib.request
import uuid

from establishments_api import ErroEstabelecimento
from supabase_config import SUPABASE_PUBLISHABLE_KEY, SUPABASE_URL


NOMES_DIAS = ("Segunda", "Terça", "Quarta", "Quinta",
              "Sexta", "Sábado", "Domingo")
FORMATO_HORARIO = re.compile(r"^(?:[01][0-9]|2[0-3]):[0-5][0-9]$")


def _id_valido(value):
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, TypeError, AttributeError) as erro:
        raise ErroEstabelecimento("Estabelecimento inválido.") from erro


def _pedir(token, recurso, metodo="GET", dados=None, upsert=False):
    if not token:
        raise ErroEstabelecimento("Sua sessão terminou. Entre novamente.")
    cabecalho = {
        "apikey": SUPABASE_PUBLISHABLE_KEY,
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    corpo = None
    if dados is not None:
        corpo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
        cabecalho["Content-Type"] = "application/json"
        cabecalho["Prefer"] = (
            "resolution=merge-duplicates,return=representation"
            if upsert else "return=representation"
        )
    requisicao = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/{recurso}", data=corpo,
        headers=cabecalho, method=metodo,
    )
    try:
        with urllib.request.urlopen(requisicao, timeout=25) as resposta:
            bruto = resposta.read()
            return json.loads(bruto) if bruto else []
    except urllib.error.HTTPError as erro:
        if erro.code in (401, 403):
            mensagem = "Sessão expirada ou sem permissão. Entre novamente."
        elif erro.code == 404:
            mensagem = "Tabela de horários indisponível na API."
        elif erro.code in (400, 409, 422):
            mensagem = "Não foi possível salvar os horários. Revise os dados."
        else:
            mensagem = "O Supabase não conseguiu processar os horários."
        raise ErroEstabelecimento(mensagem) from erro
    except (urllib.error.URLError, TimeoutError) as erro:
        raise ErroEstabelecimento(
            "Falha de conexão. Confira sua internet."
        ) from erro
    except (TypeError, ValueError) as erro:
        raise ErroEstabelecimento("Resposta inesperada do Supabase.") from erro


def _minutos(texto):
    if not isinstance(texto, str) or not FORMATO_HORARIO.fullmatch(texto):
        raise ErroEstabelecimento(
            "Use horários no formato 24 horas: 09:00, 13:30."
        )
    hora, minuto = texto.split(":")
    return int(hora) * 60 + int(minuto)


def validar_jornada(semana):
    """Valida sete dias, intervalos ordenados e sem sobreposição."""
    if not isinstance(semana, list) or len(semana) != 7:
        raise ErroEstabelecimento("Configure os sete dias da semana.")
    dias = []
    for indice, registro in enumerate(semana):
        if registro.get("weekday") != indice:
            raise ErroEstabelecimento("Os dias da semana estão fora de ordem.")
        intervalos = registro.get("intervals")
        if not isinstance(intervalos, list) or len(intervalos) > 8:
            raise ErroEstabelecimento(
                f"{NOMES_DIAS[indice]}: máximo de oito intervalos."
            )
        anteriores = -1
        normalizados = []
        for intervalo in intervalos:
            inicio = intervalo.get("start", "").strip()
            fim = intervalo.get("end", "").strip()
            inicio_min, fim_min = _minutos(inicio), _minutos(fim)
            if fim_min <= inicio_min:
                raise ErroEstabelecimento(
                    f"{NOMES_DIAS[indice]}: o fim precisa ser "
                    "posterior ao início, no mesmo dia."
                )
            if inicio_min < anteriores:
                raise ErroEstabelecimento(
                    f"{NOMES_DIAS[indice]}: coloque os intervalos "
                    "em ordem, sem sobreposição."
                )
            anteriores = fim_min
            normalizados.append({"start": inicio, "end": fim})
        dias.append({"weekday": indice, "intervals": normalizados})
    if not any(dia["intervals"] for dia in dias):
        raise ErroEstabelecimento(
            "Defina pelo menos um dia de funcionamento."
        )
    return dias


def carregar_horarios(token, estabelecimento_id):
    identificador = _id_valido(estabelecimento_id)
    resultado = _pedir(
        token,
        "establishment_weekly_hours?"
        f"establishment_id=eq.{identificador}"
        "&select=weekday,intervals&order=weekday.asc",
    )
    return resultado


def salvar_horarios(token, estabelecimento_id, semana, etapa_atual=2):
    identificador = _id_valido(estabelecimento_id)
    dias = validar_jornada(semana)
    dados = [
        {"establishment_id": identificador,
         "weekday": dia["weekday"],
         "intervals": dia["intervals"]}
        for dia in dias
    ]
    retorno = _pedir(
        token,
        "establishment_weekly_hours?"
        "on_conflict=establishment_id,weekday",
        metodo="POST",
        dados=dados,
        upsert=True,
    )
    if not isinstance(retorno, list) or len(retorno) != 7:
        raise ErroEstabelecimento(
            "O Supabase não confirmou todos os dias salvos."
        )
    if int(etapa_atual or 1) < 3:
        novos = _pedir(
            token, f"establishments?id=eq.{identificador}",
            metodo="PATCH",
            dados={"onboarding_step": 3},
        )
        if not novos:
            raise ErroEstabelecimento(
                "Horários salvos, mas o avanço da etapa não foi confirmado. "
                "Tente salvar novamente."
            )
    return dias
