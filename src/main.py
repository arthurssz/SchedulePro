"""SchedulePro: autenticação com Google e sessão segura no Android."""

import asyncio
from urllib.parse import parse_qs, urlsplit

import flet as ft
import flet_secure_storage as fss
from schedulepro_ui import FUNDO, TEXTO_SECUNDARIO, criar_painel

from auth_flow import (
    SessaoInvalida,
    completar_google,
    encerrar_sessao,
    iniciar_google,
    renovar_sessao,
)


CHAVE_PKCE = "schedulepro.auth.pkce_verifier"
CHAVE_SESSAO = "schedulepro.auth.refresh_token"


async def main(page: ft.Page):
    page.title = "SchedulePro"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = FUNDO
    page.padding = 0

    # Android Keystore protege o token, que não fica em SharedPreferences.
    armazenamento = fss.SecureStorage(
        android_options=fss.AndroidOptions(reset_on_error=True)
    )
    navegador = ft.UrlLauncher()
    feedback = ft.Text("", size=13, color="#FCA5A5")
    usuario = {"email": None, "access_token": None}
    interface = {"pode_reconectar": False}

    async def entrar_google(evento):
        feedback.value = "Abrindo o login do Google..."
        page.update()
        try:
            verificador, url = iniciar_google()
            await armazenamento.set(CHAVE_PKCE, verificador)
            await navegador.launch_url(
                url, mode=ft.LaunchMode.EXTERNAL_APPLICATION
            )
        except Exception:
            feedback.value = "Não foi possível abrir o Google. Tente novamente."
            page.update()

    def mostrar_login():
        page.controls.clear()
        page.navigation_bar = None
        controles = [
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
            ft.Button("Entrar com Google", on_click=entrar_google),
            feedback,
        ]
        if interface["pode_reconectar"]:
            controles.append(
                ft.Button(
                    "Tentar recuperar a sessão",
                    on_click=recuperar_sessao,
                )
            )
        controles.append(
            ft.Text(
                "Seu login ficará salvo com proteção do Android.",
                size=12,
                color=TEXTO_SECUNDARIO,
            )
        )
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
                        controls=controles,
                    ),
                ),
            )
        )
        page.update()

    async def recuperar_sessao(evento=None):
        """Restaura o usuário ao abrir o app, renovando a credencial."""
        try:
            token = await armazenamento.get(CHAVE_SESSAO)
            if not token:
                interface["pode_reconectar"] = False
                mostrar_login()
                return
            sessao = await asyncio.to_thread(renovar_sessao, token)
            await armazenamento.set(CHAVE_SESSAO, sessao["refresh_token"])
            usuario["email"] = sessao["email"]
            usuario["access_token"] = sessao["access_token"]
            interface["pode_reconectar"] = False
            mostrar_painel()
        except SessaoInvalida:
            await armazenamento.remove(CHAVE_SESSAO)
            feedback.value = "Sua sessão terminou. Entre com Google novamente."
            interface["pode_reconectar"] = False
            mostrar_login()
        except Exception:
            # Não descarta o token se houver falha temporária de rede.
            feedback.value = (
                "Não foi possível verificar sua sessão. Confira a internet."
            )
            interface["pode_reconectar"] = True
            mostrar_login()

    async def sair_da_conta(evento):
        """Sai deste dispositivo, sem encerrar sessões dos outros aparelhos."""
        token = usuario["access_token"]
        try:
            await armazenamento.remove(CHAVE_SESSAO)
            await armazenamento.remove(CHAVE_PKCE)
        except Exception:
            page.show_dialog(
                ft.SnackBar(
                    content=ft.Text("Não foi possível remover a sessão salva.")
                )
            )
            return

        usuario["email"] = None
        usuario["access_token"] = None
        interface["pode_reconectar"] = False
        feedback.value = "Você saiu da conta neste aparelho."
        mostrar_login()
        if token:
            try:
                await asyncio.to_thread(encerrar_sessao, token)
            except Exception:
                feedback.value = (
                    "Você saiu deste aparelho, mas a sessão remota não foi "
                    "encerrada. Tente novamente mais tarde."
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
        try:
            verificador = await armazenamento.get(CHAVE_PKCE)
            if not verificador:
                feedback.value = "Sessão de login expirada. Tente novamente."
                mostrar_login()
                return
            sessao = await asyncio.to_thread(
                completar_google, codigo, verificador
            )
            await armazenamento.set(CHAVE_SESSAO, sessao["refresh_token"])
            await armazenamento.remove(CHAVE_PKCE)
            usuario["email"] = sessao["email"]
            usuario["access_token"] = sessao["access_token"]
            interface["pode_reconectar"] = False
            mostrar_painel()
        except Exception:
            feedback.value = "Erro ao validar login. Tente novamente."
            mostrar_login()

    async def ao_mudar_rota(evento):
        await tratar_callback(page.route or "")

    mostrar_painel = criar_painel(page, sair_da_conta)
    page.on_route_change = ao_mudar_rota
    mostrar_login()
    if (page.route or "").startswith("/callback"):
        await tratar_callback(page.route)
    else:
        await recuperar_sessao()


if __name__ == "__main__":
    ft.run(main)
