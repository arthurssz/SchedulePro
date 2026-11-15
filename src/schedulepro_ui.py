"""Telas compartilhadas entre o APK e a prévia web do SchedulePro.

Manter a interface neste módulo evita dois designs divergentes.
NÃO há autenticação nem acesso a dados privados nesta camada.
"""
from datetime import date, timedelta
import flet as ft


FUNDO = "#111111"
CARTAO = "#1D1D1D"
TEXTO_SECUNDARIO = "#A3A3A3"

DIAS_SEMANA = ("Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo")
MESES = ("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro")

ABAS = [
    ("Início", ft.Icons.HOME_OUTLINED),
    ("Agenda", ft.Icons.CALENDAR_MONTH_OUTLINED),
    ("Clientes", ft.Icons.PEOPLE_OUTLINE),
    ("Mais", ft.Icons.MORE_HORIZ),
]

AREAS = [
    "Serviços",
    "Profissionais",
    "Horários e bloqueios",
    "Relatórios",
    "Equipe e permissões",
    "Preferências",
    "Minha conta",
    "Ajuda e sobre",
]


def cartao(titulo: str, descricao: str, expand: bool = False) -> ft.Container:
    return ft.Container(
        expand=expand,
        bgcolor=CARTAO,
        border_radius=16,
        padding=16,
        content=ft.Column(
            spacing=8,
            tight=True,
            controls=[
                ft.Text(titulo, size=15, weight=ft.FontWeight.BOLD),
                ft.Text(descricao, size=13, color=TEXTO_SECUNDARIO),
            ],
        ),
    )



def criar_painel(page: ft.Page, sair_da_conta):
    """Prepara a navegação e retorna a função que abre o painel."""
    conteudo = ft.Column(
        expand=True,
        spacing=14,
        scroll=ft.ScrollMode.AUTO,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
    )

    dia_visivel = {"data": date.today()}

    def cabecalho():
        return ft.Row(
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Icon(
                    ft.Icons.CALENDAR_MONTH_OUTLINED,
                    size=22,
                    color="#EBEBEB",
                ),
                ft.Text(
                    "schedulepro",
                    size=19,
                    weight=ft.FontWeight.BOLD,
                ),
                ft.Container(expand=True),
                ft.IconButton(
                    icon=ft.Icons.NOTIFICATIONS_NONE,
                    icon_size=21,
                    tooltip="Avisos (em desenvolvimento)",
                    on_click=lambda _: mostrar_aviso(
                        "A Central de Avisos estará disponível em breve."
                    ),
                ),
                ft.IconButton(
                    icon=ft.Icons.ACCOUNT_CIRCLE_OUTLINED,
                    icon_size=22,
                    tooltip="Minha conta",
                    on_click=abrir_mais,
                ),
            ],
        )

    def mostrar_aviso(mensagem: str):
        page.show_dialog(ft.SnackBar(content=ft.Text(mensagem)))

    def mudar_data(diferenca: int):
        dia_visivel["data"] += timedelta(days=diferenca)
        renderizar(0)

    def ir_para_hoje(evento):
        dia_visivel["data"] = date.today()
        renderizar(0)

    def abrir_agenda(evento):
        page.navigation_bar.selected_index = 1
        renderizar(1)

    def abrir_mais(evento):
        page.navigation_bar.selected_index = 3
        renderizar(3)

    def formatar_data(valor: date):
        return (
            f"{DIAS_SEMANA[valor.weekday()]}, {valor.day} "
            f"de {MESES[valor.month - 1]}"
        )

    def resumo(numero: str, legenda: str):
        return ft.Column(
            expand=True,
            spacing=7,
            controls=[
                ft.Text(
                    numero,
                    size=30,
                    weight=ft.FontWeight.BOLD,
                ),
                ft.Text(
                    legenda,
                    size=12,
                    color=TEXTO_SECUNDARIO,
                ),
            ],
        )

    def renderizar(indice: int):
        titulo = ABAS[indice][0]
        itens = [
            cabecalho(),
            ft.Divider(height=18, color="#2B2B2B"),
        ]

        if indice == 0:
            itens.extend(
                [
                    ft.Text(
                        "ESTABELECIMENTO NÃO CONFIGURADO",
                        size=11,
                        color=TEXTO_SECUNDARIO,
                    ),
                    ft.Text(
                        "Visão geral",
                        size=28,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Row(
                        spacing=0,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Container(
                                expand=True,
                                content=ft.Text(
                                    formatar_data(dia_visivel["data"]),
                                    size=13,
                                    color=TEXTO_SECUNDARIO,
                                ),
                            ),
                            ft.IconButton(
                                icon=ft.Icons.CHEVRON_LEFT,
                                icon_size=19,
                                tooltip="Dia anterior",
                                on_click=lambda _: mudar_data(-1),
                            ),
                            ft.Button(
                                "Hoje",
                                on_click=ir_para_hoje,
                            ),
                            ft.IconButton(
                                icon=ft.Icons.CHEVRON_RIGHT,
                                icon_size=19,
                                tooltip="Dia seguinte",
                                on_click=lambda _: mudar_data(1),
                            ),
                        ],
                    ),
                    ft.Container(
                        padding=ft.Padding.only(top=12, bottom=12),
                        content=ft.Row(
                            spacing=8,
                            controls=[
                                resumo("—", "Agendamentos"),
                                resumo("—", "A confirmar"),
                                resumo("—", "Concluídos"),
                            ],
                        ),
                    ),
                    ft.Container(
                        bgcolor="#F1F1F1",
                        border_radius=14,
                        padding=15,
                        on_click=lambda _: mostrar_aviso(
                            "Primeiro vamos cadastrar seu estabelecimento "
                            "para habilitar os agendamentos."
                        ),
                        content=ft.Row(
                            alignment=ft.MainAxisAlignment.CENTER,
                            controls=[
                                ft.Icon(
                                    ft.Icons.ADD,
                                    color="#151515",
                                    size=23,
                                ),
                                ft.Text(
                                    "Novo agendamento",
                                    color="#151515",
                                    size=16,
                                    weight=ft.FontWeight.BOLD,
                                ),
                            ],
                        ),
                    ),
                    ft.Container(height=7),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text(
                                "Agenda do dia",
                                size=21,
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Button(
                                "Todos",
                                on_click=lambda _: mostrar_aviso(
                                    "Os filtros serão liberados quando "
                                    "a agenda estiver integrada."
                                ),
                            ),
                        ],
                    ),
                    ft.Container(
                        bgcolor=CARTAO,
                        border_radius=12,
                        padding=20,
                        content=ft.Column(
                            spacing=7,
                            tight=True,
                            controls=[
                                ft.Text(
                                    "Nenhum agendamento neste dia.",
                                    size=14,
                                ),
                                ft.Text(
                                    "Os agendamentos aparecerão aqui "
                                    "após a configuração do negócio.",
                                    size=12,
                                    color=TEXTO_SECUNDARIO,
                                ),
                            ],
                        ),
                    ),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.CENTER,
                        controls=[
                            ft.TextButton(
                                "Ver agenda completa →",
                                on_click=abrir_agenda,
                            )
                        ],
                    ),
                ]
            )
        else:
            itens.append(
                ft.Text(
                    titulo,
                    size=24,
                    weight=ft.FontWeight.BOLD,
                )
            )
            if indice == 1:
                itens.append(
                    cartao(
                        "Agenda",
                        "Aqui aparecerão os horários e agendamentos "
                        "do estabelecimento.",
                    )
                )
            elif indice == 2:
                itens.append(
                    cartao(
                        "Clientes",
                        "Aqui você poderá consultar e cadastrar clientes.",
                    )
                )
            else:
                itens.append(
                    ft.Button(
                        "Sair da conta",
                        icon=ft.Icons.LOGOUT,
                        on_click=sair_da_conta,
                    )
                )
                itens.append(
                    ft.Text(
                        "Áreas previstas para as próximas etapas:",
                        color=TEXTO_SECUNDARIO,
                        size=13,
                    )
                )
                itens.extend(
                    cartao(nome, "Em desenvolvimento") for nome in AREAS
                )

        conteudo.controls = itens
        page.update()

    def mudar_aba(evento):
        renderizar(evento.control.selected_index)

    def mostrar_painel():
        page.controls.clear()
        page.navigation_bar = ft.NavigationBar(
            selected_index=0,
            bgcolor=CARTAO,
            indicator_color="#383838",
            on_change=mudar_aba,
            destinations=[
                ft.NavigationBarDestination(icon=icone, label=nome)
                for nome, icone in ABAS
            ],
        )
        page.add(
            ft.SafeArea(
                expand=True,
                content=ft.Container(
                    expand=True,
                    padding=20,
                    content=conteudo,
                ),
            )
        )
        renderizar(0)

    return mostrar_painel
