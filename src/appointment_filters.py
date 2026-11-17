"""Filtros locais da Agenda sobre os registros já autorizados pelo Supabase."""

import unicodedata

FILTROS_STATUS = (
    ("todos", "Todos os status"),
    ("scheduled", "A confirmar"),
    ("confirmed", "Confirmados"),
    ("completed", "Concluídos"),
    ("canceled", "Cancelados"),
    ("no_show", "Não compareceu"),
)
STATUS_VALIDOS = frozenset(chave for chave, _ in FILTROS_STATUS)


def _normalizar_busca(texto):
    """Comparação simples, sem distinção de acentos e maiúsculas."""
    normalizado = unicodedata.normalize("NFD", str(texto or "").casefold())
    return "".join(letra for letra in normalizado if not unicodedata.combining(letra)).strip()


def filtrar_agenda(
    registros, status="todos", profissional_id="todos", servico_id="todos",
    busca="",
):
    """Filtra sem alterar registros nem ocupar/liberar horários no servidor."""
    if status not in STATUS_VALIDOS:
        raise ValueError("Filtro de status inválido.")
    termo = _normalizar_busca(busca)
    resultado = []
    for registro in registros:
        if status != "todos" and registro.get("status") != status:
            continue
        profissional = registro.get("professional") or {}
        servico = registro.get("service") or {}
        if (
            profissional_id != "todos"
            and profissional.get("id") != profissional_id
        ):
            continue
        if servico_id != "todos" and servico.get("id") != servico_id:
            continue
        if termo:
            cliente = (registro.get("customer") or {}).get("name") or ""
            if termo not in _normalizar_busca(cliente):
                continue
        resultado.append(registro)
    return resultado


def opcoes_agenda(registros, vinculo):
    """Lista IDs e nomes únicos presentes no período carregado do Supabase."""
    if vinculo not in ("professional", "service"):
        raise ValueError("Vínculo inválido para o filtro.")
    opcoes = {}
    for registro in registros:
        item = registro.get(vinculo) or {}
        identificador = item.get("id")
        if identificador:
            opcoes[identificador] = item.get("name") or "Sem nome"
    return sorted(opcoes.items(), key=lambda item: (item[1].casefold(), item[0]))


def filtrar_status_agenda(registros, status="todos"):
    """Compatibilidade com chamadas anteriores do filtro de status."""
    return filtrar_agenda(registros, status=status)
