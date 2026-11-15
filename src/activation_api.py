"""Etapa 5/5: jornadas dos profissionais e ativação segura do negócio."""

import urllib.parse

from establishments_api import ErroEstabelecimento
from hours_api import _pedir, _id_valido, validar_jornada
from professionals_api import _pedir as _rpc


def validar_compatibilidade(semana, horarios_negocio):
    """Cada intervalo do profissional deve caber em um intervalo do negócio."""
    semana = validar_jornada(semana)
    negocio = {
        int(dia["weekday"]): dia.get("intervals") or []
        for dia in horarios_negocio
    }
    for dia in semana:
        for intervalo in dia["intervals"]:
            if not any(
                horario["start"] <= intervalo["start"]
                and intervalo["end"] <= horario["end"]
                for horario in negocio.get(dia["weekday"], [])
            ):
                raise ErroEstabelecimento(
                    "Jornada incompatível com o funcionamento do negócio. "
                    "Confira dias, pausas, abertura e fechamento."
                )
    return semana


def carregar_jornadas(token, estabelecimento_id):
    estabelecimento_id = _id_valido(estabelecimento_id)
    return _pedir(
        token,
        "professional_weekly_hours?"
        "establishment_id=eq." + estabelecimento_id
        + "&select=professional_id,weekday,intervals"
        + "&order=weekday.asc",
    )


def salvar_jornada_profissional(
    token, estabelecimento_id, profissional_id, semana, horarios_negocio,
):
    estabelecimento_id = _id_valido(estabelecimento_id)
    profissional_id = _id_valido(profissional_id)
    semana = validar_compatibilidade(semana, horarios_negocio)
    dados = [
        {
            "establishment_id": estabelecimento_id,
            "professional_id": profissional_id,
            "weekday": dia["weekday"],
            "intervals": dia["intervals"],
        }
        for dia in semana
    ]
    registros = _pedir(
        token,
        "professional_weekly_hours?"
        "on_conflict=professional_id,weekday",
        metodo="POST",
        dados=dados,
        upsert=True,
    )
    if not isinstance(registros, list) or len(registros) != 7:
        raise ErroEstabelecimento(
            "O Supabase não confirmou todos os horários do profissional."
        )
    return registros


def revisar_ativacao(token, estabelecimento_id):
    negocio = _id_valido(estabelecimento_id)
    return _rpc(
        token, "rpc/schedulepro_activation_check",
        metodo="POST",
        dados={"p_establishment_id": negocio},
    )


def ativar_estabelecimento(token, estabelecimento_id):
    negocio = _id_valido(estabelecimento_id)
    resposta = _rpc(
        token, "rpc/schedulepro_activate_establishment",
        metodo="POST",
        dados={"p_establishment_id": negocio},
    )
    if not isinstance(resposta, dict) or not resposta.get(
        "onboarding_completed"
    ):
        raise ErroEstabelecimento("A ativação não foi confirmada.")
    return resposta
