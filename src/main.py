"""SchedulePro: navegação inicial e teste de login Google no Android."""

import asyncio
from urllib.parse import parse_qs, urlsplit

import flet as ft

from auth_flow import completar_google, iniciar_google


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

CHAVE_PKCE = "schedulepro.auth.pkce_verifier"


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


async def main(page: ft.Page):
    page.title = "SchedulePro"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = FUNDO
    page.padding = 0

    preferencias = ft.SharedPreferences()
    navegador = ft.UrlLauncher()
    conteudo = ft.Column(expand=True, spacing=14, scroll=ft.ScrollMode.AUTO, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
    feedback = ft.Text("", size=13, color="#FCA5A5")
    usuario = {"email": None}

    def renderizar(indice: int):
        titulo = ABAS[indice][0]
        itens = [
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text("SchedulePro", size=25, weight=ft.FontWeight.BOLD),
                    ft.Text("ETAPA 02", size=11, color=TEXTO_SECUNDARIO),
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
                    cartao(
                        "Conta de teste",
                        f"Google conectado: {usuario['email']}",
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

    async def entrar_google(evento):
        feedback.value = "Abrindo o login do Google..."
        page.update()
        try:
            verificador, url = iniciar_google()
            await preferencias.set(CHAVE_PKCE, verificador)
            await navegador.launch_url(
                url, mode=ft.LaunchMode.EXTERNAL_APPLICATION
            )
        except Exception:
            feedback.value = "Não foi possível abrir o Google. Tente novamente."
            page.update()

    def mostrar_login():
        page.controls.clear()
        page.navigation_bar = None
        page.add(
            ft.SafeArea(
                expand=True,
                content=ft.Container(
                    expand=True,
                    padding=28,
                    content=ft.Column(
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                        spacing=20,
                        controls=[
                            ft.Text(
                                "SchedulePro",
                                size=34,
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Text(
                                "Organize seu negócio em um só lugar.",
                                color=TEXTO_SECUNDARIO,
                                size=16,
                            ),
                            ft.Container(height=12),
                            ft.Button(
                                "Entrar com Google",
                                on_click=entrar_google,
                            ),
                            feedback,
                            ft.Text(
                                "Versão de teste: a sessão ainda não é salva "
                                "ao fechar o aplicativo.",
                                size=12,
                                color=TEXTO_SECUNDARIO,
                            ),
                        ],
                    ),
                ),
            )
        )
        page.update()

    async def tratar_callback(rota: str):
        if not rota.startswith("/callback"):
            return
        consulta = parse_qs(urlsplit(rota).query)
        erro = consulta.get("error")
        if erro:
            feedback.value = "O Google não concluiu o login. Tente novamente."
            mostrar_login()
            return
        codigo = (consulta.get("code") or [None])[0]
        if not codigo:
            feedback.value = "Não recebemos o código de retorno do Google."
            mostrar_login()
            return
        verificador = await preferencias.get(CHAVE_PKCE)
        if not verificador:
            feedback.value = "Sessão de login expirada. Tente novamente."
            mostrar_login()
            return
        try:
            email = await asyncio.to_thread(
                completar_google, codigo, verificador
            )
            await preferencias.remove(CHAVE_PKCE)
            usuario["email"] = email
            mostrar_painel()
        except Exception:
            await preferencias.remove(CHAVE_PKCE)
            feedback.value = "Erro ao validar o login no Supabase. Tente novamente."
            mostrar_login()

    async def ao_mudar_rota(evento):
        await tratar_callback(page.route or "")

    page.on_route_change = ao_mudar_rota
    mostrar_login()
    if (page.route or "").startswith("/callback"):
        await tratar_callback(page.route)


if __name__ == "__main__":
    ft.run(main)
