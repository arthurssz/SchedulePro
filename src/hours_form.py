"""Formulário de jornadas semanais, etapa 2/5 do SchedulePro."""

import flet as ft

from hours_api import NOMES_DIAS


FUNDO = "#111111"
CARTAO = "#1D1D1D"
SECUNDARIO = "#A3A3A3"


def abrir_formulario_horarios(page, cadastrados, salvar, concluido):
    """Jornadas do estabelecimento: dias, múltiplos intervalos e pausas."""
    existentes = {
        int(registro["weekday"]): registro.get("intervals") or []
        for registro in cadastrados
    }
    controles = []
    estado = {}
    erro = ft.Text("", size=12, color="#F3B5B5")

    def criar_campo(rotulo, valor):
        return ft.TextField(
            label=rotulo,
            value=valor,
            hint_text="09:00",
            dense=True,
            text_size=14,
            bgcolor="#272727",
            border_color="#424242",
            focused_border_color="#D8D8D8",
            border_radius=10,
            content_padding=ft.Padding.symmetric(
                horizontal=10, vertical=10,
            ),
            expand=True,
        )

    def adicionar_intervalo(indice, inicio="09:00", fim="18:00"):
        if len(estado[indice]["intervalos"]) >= 8:
            erro.value = "Máximo de oito intervalos por dia."
            page.update()
            return
        estado[indice]["intervalos"].append(
            (criar_campo("Início", inicio), criar_campo("Fim", fim))
        )
        atualizar_dia(indice)

    def excluir_intervalo(indice, posicao):
        estado[indice]["intervalos"].pop(posicao)
        if not estado[indice]["intervalos"]:
            estado[indice]["ativo"].value = False
        atualizar_dia(indice)

    def alternar_dia(indice, evento):
        if evento.control.value and not estado[indice]["intervalos"]:
            adicionar_intervalo(indice)
        elif not evento.control.value:
            estado[indice]["intervalos"].clear()
            atualizar_dia(indice)

    def atualizar_dia(indice):
        dia = estado[indice]
        linhas = []
        for posicao, (inicio, fim) in enumerate(dia["intervalos"]):
            linhas.append(
                ft.Row(
                    spacing=7,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        inicio,
                        fim,
                        ft.IconButton(
                            icon=ft.Icons.CLOSE,
                            icon_size=18,
                            tooltip="Remover intervalo",
                            on_click=lambda _, d=indice, p=posicao:
                                excluir_intervalo(d, p),
                        ),
                    ],
                )
            )
        if dia["ativo"].value:
            linhas.append(
                ft.TextButton(
                    "+ Adicionar intervalo",
                    on_click=lambda _, d=indice: adicionar_intervalo(d),
                )
            )
        else:
            linhas.append(
                ft.Text(
                    "Fechado",
                    size=12,
                    color=SECUNDARIO,
                )
            )
        dia["corpo"].controls = linhas
        page.update()

    for indice, nome in enumerate(NOMES_DIAS):
        intervalos = []
        for periodo in existentes.get(indice, []):
            intervalos.append(
                (criar_campo("Início", periodo["start"]),
                 criar_campo("Fim", periodo["end"]))
            )
        ativo = ft.Checkbox(
            label=nome,
            value=bool(intervalos),
            on_change=lambda evento, d=indice: alternar_dia(d, evento),
        )
        corpo = ft.Column(spacing=6, tight=True)
        estado[indice] = {
            "ativo": ativo,
            "corpo": corpo,
            "intervalos": intervalos,
        }
        controles.append(
            ft.Container(
                bgcolor=CARTAO,
                border_radius=12,
                padding=ft.Padding.symmetric(horizontal=12, vertical=9),
                content=ft.Column(
                    spacing=4,
                    tight=True,
                    controls=[ativo, corpo],
                ),
            )
        )

    botao_salvar = ft.Button(
        "Salvar horários",
        bgcolor="#F0F0F0",
        color="#181818",
    )

    async def confirmar(evento):
        semana = []
        for indice in range(7):
            periodos = [
                {"start": campo_inicio.value or "",
                 "end": campo_fim.value or ""}
                for campo_inicio, campo_fim in estado[indice]["intervalos"]
            ]
            semana.append({"weekday": indice, "intervals": periodos})
        botao_salvar.disabled = True
        erro.value = "Salvando horários no Supabase..."
        page.update()
        try:
            await salvar(semana)
        except Exception as falha:
            erro.value = str(falha)
            botao_salvar.disabled = False
            page.update()
            return
        page.pop_dialog()
        concluido()
        page.show_dialog(
            ft.SnackBar(
                content=ft.Text(
                    "Horários salvos! A configuração avançou para a etapa 3/5."
                ),
            )
        )

    botao_salvar.on_click = confirmar
    pagina = ft.Column(
        spacing=11,
        tight=True,
        controls=[
            ft.Text(
                "HORÁRIOS DE FUNCIONAMENTO · 2/5",
                size=11,
                color=SECUNDARIO,
            ),
            ft.Text(
                "Jornada semanal",
                size=23,
                weight=ft.FontWeight.BOLD,
            ),
            ft.Text(
                "Ative os dias em que o estabelecimento funciona. "
                "Use mais de um intervalo para incluir pausas, como almoço.",
                size=13,
                color=SECUNDARIO,
            ),
            *controles,
            erro,
            ft.Row(
                alignment=ft.MainAxisAlignment.END,
                spacing=10,
                controls=[
                    ft.TextButton(
                        "Cancelar",
                        on_click=lambda _: page.pop_dialog(),
                    ),
                    botao_salvar,
                ],
            ),
            ft.Text(
                "Não é possível sobrepor horários ou atravessar a meia-noite. "
                "Folgas e bloqueios excepcionais serão configurados depois.",
                size=11,
                color=SECUNDARIO,
            ),
        ],
    )

    page.show_dialog(
        ft.BottomSheet(
            scrollable=True,
            show_drag_handle=True,
            bgcolor=FUNDO,
            content=ft.Container(
                padding=18,
                content=pagina,
            ),
        )
    )
    for indice in range(7):
        atualizar_dia(indice)
