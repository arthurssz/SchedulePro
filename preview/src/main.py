"""Prévia visual gratuita. Não acessa Supabase, Google ou dados de clientes."""

import flet as ft

from schedulepro_ui import FUNDO, criar_painel


def main(page: ft.Page):
    page.title = "SchedulePro | Prévia visual"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = FUNDO
    page.padding = 0

    def sair_demo(evento):
        page.show_dialog(
            ft.SnackBar(
                content=ft.Text(
                    "Esta é uma prévia visual pública. "
                    "Login e dados reais são testados somente no APK."
                )
            )
        )

    mostrar_painel = criar_painel(page, sair_demo)
    mostrar_painel()


if __name__ == "__main__":
    ft.run(main)
