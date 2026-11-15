"""SchedulePro: estrutura visual inicial do aplicativo."""

import flet as ft

FUNDO = "#111111"
CARTAO = "#1D1D1D"
TEXTO_SECUNDARIO = "#A3A3A3"

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


def main(page: ft.Page):
    page.title = "SchedulePro"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = FUNDO
    page.padding = 0

    conteudo = ft.Column(expand=True, spacing=14, scroll=ft.ScrollMode.AUTO)

    def renderizar(indice: int):
        titulo = ABAS[indice][0]
        itens = [
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text("SchedulePro", size=25, weight=ft.FontWeight.BOLD),
                    ft.Text("ETAPA 01", size=11, color=TEXTO_SECUNDARIO),
                ],
            ),
            ft.Text(titulo, size=21, weight=ft.FontWeight.BOLD),
        ]

        if indice == 0:
            itens.extend(
                [
                    ft.Text(
                        "Seu negócio em um só lugar.",
                        size=14,
                        color=TEXTO_SECUNDARIO,
                    ),
                    ft.Row(
                        spacing=12,
                        controls=[
                            cartao("Agendamentos hoje", "—", expand=True),
                            cartao("Clientes", "—", expand=True),
                        ],
                    ),
                    cartao(
                        "Próximos agendamentos",
                        "Nenhum agendamento cadastrado.",
                    ),
                    cartao(
                        "Resumo financeiro",
                        "Os indicadores aparecerão quando conectarmos os dados.",
                    ),
                ]
            )
        elif indice == 1:
            itens.append(
                cartao(
                    "Agenda",
                    "Aqui aparecerão os horários e agendamentos do estabelecimento.",
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
                ft.Text(
                    "Áreas previstas para as próximas etapas:",
                    color=TEXTO_SECUNDARIO,
                    size=13,
                )
            )
            itens.extend(cartao(nome, "Em desenvolvimento") for nome in AREAS)

        conteudo.controls = itens
        page.update()

    def mudar_aba(evento):
        renderizar(evento.control.selected_index)

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


if __name__ == "__main__":
    ft.run(main)
