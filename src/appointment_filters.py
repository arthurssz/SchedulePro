"""Filtros locais da Agenda sobre os registros já autorizados pelo Supabase."""

FILTROS_STATUS = (
    ("todos", "Todos os status"),
    ("scheduled", "A confirmar"),
    ("confirmed", "Confirmados"),
    ("completed", "Concluídos"),
    ("canceled", "Cancelados"),
    ("no_show", "Não compareceu"),
)
STATUS_VALIDOS = frozenset(chave for chave, _ in FILTROS_STATUS)


def filtrar_status_agenda(registros, status="todos"):
    """Aplica filtro visual, sem mudar regras de ocupação nem registros."""
    if status not in STATUS_VALIDOS:
        raise ValueError("Filtro de status inválido.")
    if status == "todos":
        return list(registros)
    return [registro for registro in registros if registro.get("status") == status]
