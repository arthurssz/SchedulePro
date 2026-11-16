"""Novo agendamento interno no APK autenticado do SchedulePro."""

from datetime import date, datetime, time, timedelta

import flet as ft

from services_api import formatar_preco

FUNDO = "#111111"
CARTAO = "#1D1D1D"
CINZA = "#A3A3A3"


def abrir_formulario_agendamento(
    page, clientes, servicos, profissionais, salvar, ao_salvar,
    data_inicial=None,
):
    """Formulário real: seleção de cliente, serviço, profissional e horário."""
    clientes = [
        c for c in clientes if c.get("is_archived") is not True
    ]
    servicos = [
        s for s in servicos if s.get("is_active") is True
    ]
    profissionais = [
        p for p in profissionais if p.get("is_active") is True
    ]

    if not clientes or not servicos or not profissionais:
        faltando = (
            "cliente ativo" if not clientes else
            "serviço ativo" if not servicos else "profissional ativo"
        )
        page.show_dialog(
            ft.SnackBar(
                content=ft.Text(
                    f"Cadastre ao menos um {faltando} antes de agendar."
                )
            )
        )
        return

    hoje = date.today()
    data_escolhida = {
        "valor": max(hoje, data_inicial or hoje)
    }
    horario_escolhido = {"valor": time(hour=10, minute=0)}
    aviso = ft.Text("", color="#F3B5B5", size=12)

    def texto_data(dia):
        return dia.strftime("%d/%m/%Y")

    campo_cliente = ft.Dropdown(
        label="Cliente *",
        value=clientes[0]["id"],
        options=[
            ft.DropdownOption(key=c["id"], text=c.get("name") or "Cliente")
            for c in clientes
        ],
        bgcolor=CARTAO,
        border_color="#3D3D3D",
    )
    campo_servico = ft.Dropdown(
        label="Serviço *",
        value=servicos[0]["id"],
        options=[
            ft.DropdownOption(
                key=s["id"],
                text=(
                    f"{s.get('name') or 'Serviço'} · "
                    f"{s.get('duration_minutes') or 0} min · "
                    f"{formatar_preco(s.get('price_cents') or 0)}"
                ),
            )
            for s in servicos
        ],
        bgcolor=CARTAO,
        border_color="#3D3D3D",
    )
    campo_profissional = ft.Dropdown(
        label="Profissional *",
        bgcolor=CARTAO,
        border_color="#3D3D3D",
    )

    def atualizar_profissionais(evento=None):
        disponiveis = [
            p for p in profissionais
            if campo_servico.value in (p.get("service_ids") or [])
        ]
        campo_profissional.options = [
            ft.DropdownOption(key=p["id"], text=p.get("name") or "Profissional")
            for p in disponiveis
        ]
        if campo_profissional.value not in [p["id"] for p in disponiveis]:
            campo_profissional.value = (
                disponiveis[0]["id"] if disponiveis else None
            )
        if evento is not None:
            aviso.value = (
                "" if disponiveis
                else "Nenhum profissional ativo realiza este serviço."
            )
            page.update()

    campo_servico.on_select = atualizar_profissionais
    atualizar_profissionais()

    botao_data = ft.Button(
        f"Data: {texto_data(data_escolhida['valor'])}",
        icon=ft.Icons.CALENDAR_MONTH_OUTLINED,
        bgcolor=CARTAO,
        color="#EDEDED",
    )
    botao_hora = ft.Button(
        "Horário: 10:00",
        icon=ft.Icons.SCHEDULE,
        bgcolor=CARTAO,
        color="#EDEDED",
    )

    def ao_escolher_data(evento):
        if evento.control.value is None:
            return
        valor = evento.control.value
        data_escolhida["valor"] = (
            valor.date() if isinstance(valor, datetime) else valor
        )
        botao_data.content = (
            f"Data: {texto_data(data_escolhida['valor'])}"
        )
        page.update()

    def ao_escolher_hora(evento):
        valor = evento.control.value
        if valor is None:
            return
        horario_escolhido["valor"] = valor
        botao_hora.content = f"Horário: {valor.strftime('%H:%M')}"
        page.update()

    calendario = ft.DatePicker(
        first_date=datetime.combine(hoje, time.min),
        last_date=datetime.combine(hoje + timedelta(days=365), time.min),
        value=datetime.combine(data_escolhida["valor"], time.min),
        current_date=datetime.combine(data_escolhida["valor"], time.min),
        on_change=ao_escolher_data,
    )
    relogio = ft.TimePicker(
        value=horario_escolhido["valor"],
        on_change=ao_escolher_hora,
        hour_format=ft.TimePickerHourFormat.H24,
    )
    botao_data.on_click = lambda _: page.show_dialog(calendario)
    botao_hora.on_click = lambda _: page.show_dialog(relogio)

    observacoes = ft.TextField(
        label="Observações (opcional)",
        multiline=True,
        min_lines=2,
        max_lines=3,
        bgcolor=CARTAO,
        border_color="#3D3D3D",
        text_size=14,
    )
    botao_salvar = ft.Button(
        "Salvar agendamento",
        icon=ft.Icons.CHECK,
        bgcolor="#F0F0F0",
        color="#181818",
    )

    async def confirmar(evento):
        if not (
            campo_cliente.value and campo_servico.value
            and campo_profissional.value
        ):
            aviso.value = "Selecione cliente, serviço e profissional."
            page.update()
            return
        botao_salvar.disabled = True
        aviso.value = "Conferindo horários e salvando no Supabase..."
        page.update()
        try:
            registro = await salvar({
                "customer_id": campo_cliente.value,
                "service_id": campo_servico.value,
                "professional_id": campo_profissional.value,
                "local_date": data_escolhida["valor"].isoformat(),
                "local_time": horario_escolhido["valor"].strftime("%H:%M"),
                "notes": observacoes.value or "",
            })
        except Exception as erro:
            aviso.value = str(erro)
            botao_salvar.disabled = False
            page.update()
            return
        page.pop_dialog()
        ao_salvar(registro)
        page.show_dialog(ft.SnackBar(
            content=ft.Text("Agendamento confirmado no Supabase.")
        ))

    botao_salvar.on_click = confirmar
    page.show_dialog(ft.BottomSheet(
        scrollable=True,
        show_drag_handle=True,
        bgcolor=FUNDO,
        content=ft.Container(
            padding=ft.Padding.only(left=16, top=12, right=16, bottom=44),
            content=ft.Column(
                tight=True,
                spacing=14,
                controls=[
                    ft.Text("NOVO AGENDAMENTO", size=11, color=CINZA),
                    ft.Text(
                        "Agendar atendimento",
                        size=22,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Text(
                        "A disponibilidade será validada no servidor.",
                        size=12,
                        color=CINZA,
                    ),
                    campo_cliente,
                    campo_servico,
                    campo_profissional,
                    ft.Column(
                        tight=True,
                        spacing=8,
                        controls=[botao_data, botao_hora],
                    ),
                    observacoes,
                    aviso,
                    ft.Row(
                        spacing=10,
                        alignment=ft.MainAxisAlignment.END,
                        controls=[
                            ft.TextButton(
                                "Cancelar",
                                on_click=lambda _: page.pop_dialog(),
                            ),
                            botao_salvar,
                        ],
                    ),
                ],
            ),
        ),
    ))
