"""SchedulePro: autenticação com Google e sessão segura no Android."""

import asyncio
from urllib.parse import parse_qs, urlsplit

import flet as ft
import flet_secure_storage as fss
from schedulepro_ui import FUNDO, TEXTO_SECUNDARIO, criar_painel
from establishments_api import (
    ErroEstabelecimento,
    obter_estabelecimento,
    salvar_primeira_etapa,
)
from establishment_form import abrir_formulario_estabelecimento
from hours_api import carregar_horarios, salvar_horarios
from hours_form import abrir_formulario_horarios
from services_api import listar_servicos, salvar_servico, alterar_atividade
from services_form import abrir_gerenciador_servicos
from professionals_api import listar_profissionais, salvar_profissional
from professionals_form import abrir_gerenciador_profissionais
from activation_api import (
    carregar_jornadas,
    salvar_jornada_profissional,
    revisar_ativacao,
    ativar_estabelecimento,
)
from activation_form import abrir_revisao_estabelecimento

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

    estado_estabelecimento = {}
    consulta_estabelecimento = {"ok": False}

    def abrir_cadastro_estabelecimento(evento=None):
        """Abre o cadastro apenas com o login autenticado no APK."""
        if not consulta_estabelecimento["ok"]:
            page.show_dialog(
                ft.SnackBar(
                    content=ft.Text(
                        "Não conseguimos verificar seus estabelecimentos. "
                        "Confira a internet e reabra o aplicativo."
                    )
                )
            )
            return

        async def salvar_dados(dados):
            token = usuario["access_token"]
            if not token:
                raise ErroEstabelecimento(
                    "Sua sessão terminou. Entre com Google novamente."
                )
            identificador = estado_estabelecimento.get("id")
            return await asyncio.to_thread(
                salvar_primeira_etapa, token, dados, identificador
            )

        def cadastro_salvo(registro):
            estado_estabelecimento.clear()
            estado_estabelecimento.update(registro)
            mostrar_painel()

        abrir_formulario_estabelecimento(
            page,
            estado_estabelecimento,
            salvar_dados,
            cadastro_salvo,
        )

    async def abrir_horarios(evento=None):
        """Abre e salva jornadas do estabelecimento com a sessão atual."""
        token = usuario["access_token"]
        identificador = estado_estabelecimento.get("id")
        if not token or not identificador or not consulta_estabelecimento["ok"]:
            page.show_dialog(
                ft.SnackBar(
                    content=ft.Text(
                        "Entre na conta e cadastre o estabelecimento primeiro."
                    )
                )
            )
            return
        try:
            cadastrados = await asyncio.to_thread(
                carregar_horarios, token, identificador
            )
        except ErroEstabelecimento as erro:
            page.show_dialog(ft.SnackBar(content=ft.Text(str(erro))))
            return

        async def gravar(semana):
            return await asyncio.to_thread(
                salvar_horarios, usuario["access_token"],
                identificador, semana,
                estado_estabelecimento.get("onboarding_step", 2),
            )

        def jornada_salva():
            etapa = int(estado_estabelecimento.get("onboarding_step") or 1)
            estado_estabelecimento["onboarding_step"] = max(etapa, 3)
            mostrar_painel()

        abrir_formulario_horarios(
            page, cadastrados, gravar, jornada_salva
        )

    async def abrir_servicos(evento=None):
        """Gerencia o catálogo real vinculado à conta Google do negócio."""
        token = usuario["access_token"]
        negocio_id = estado_estabelecimento.get("id")
        etapa = int(estado_estabelecimento.get("onboarding_step") or 1)
        if not token or not negocio_id or not consulta_estabelecimento["ok"]:
            page.show_dialog(
                ft.SnackBar(
                    content=ft.Text(
                        "Entre com Google e cadastre seu estabelecimento."
                    )
                )
            )
            return
        if etapa < 3:
            page.show_dialog(
                ft.SnackBar(
                    content=ft.Text(
                        "Configure os horários antes dos serviços."
                    )
                )
            )
            return
        try:
            itens = await asyncio.to_thread(
                listar_servicos, token, negocio_id
            )
        except ErroEstabelecimento as erro:
            page.show_dialog(ft.SnackBar(content=ft.Text(str(erro))))
            return

        async def gravar_servico(dados, identificador=None):
            return await asyncio.to_thread(
                salvar_servico,
                usuario["access_token"], negocio_id,
                dados, identificador,
                estado_estabelecimento.get("onboarding_step", 3),
            )

        async def atualizar_status(identificador, ativo):
            return await asyncio.to_thread(
                alterar_atividade,
                usuario["access_token"], negocio_id, identificador, ativo,
            )

        def servico_alterado(registro):
            if registro.get("_etapa_avancou"):
                etapa_atual = int(
                    estado_estabelecimento.get("onboarding_step") or 1
                )
                estado_estabelecimento["onboarding_step"] = max(
                    etapa_atual, 4
                )
            mostrar_painel()

        abrir_gerenciador_servicos(
            page, itens, gravar_servico, atualizar_status, servico_alterado,
        )

    async def abrir_profissionais(evento=None):
        """Abre cadastro real de profissionais e associa serviços autorizados."""
        token = usuario["access_token"]
        negocio_id = estado_estabelecimento.get("id")
        etapa = int(estado_estabelecimento.get("onboarding_step") or 1)
        if not token or not negocio_id or not consulta_estabelecimento["ok"]:
            page.show_dialog(
                ft.SnackBar(
                    content=ft.Text(
                        "Entre com Google e cadastre o estabelecimento primeiro."
                    )
                )
            )
            return
        if etapa < 4:
            page.show_dialog(
                ft.SnackBar(
                    content=ft.Text(
                        "Cadastre pelo menos um serviço ativo antes."
                    )
                )
            )
            return
        try:
            profissionais, servicos = await asyncio.gather(
                asyncio.to_thread(
                    listar_profissionais, token, negocio_id
                ),
                asyncio.to_thread(
                    listar_servicos, token, negocio_id
                ),
            )
        except ErroEstabelecimento as erro:
            page.show_dialog(ft.SnackBar(content=ft.Text(str(erro))))
            return

        async def gravar(dados, profissional_id=None):
            return await asyncio.to_thread(
                salvar_profissional,
                usuario["access_token"], negocio_id,
                dados, profissional_id,
            )

        def profissional_salvo(registro):
            if registro.get("_etapa_avancou"):
                etapa_atual = int(
                    estado_estabelecimento.get("onboarding_step") or 1
                )
                estado_estabelecimento["onboarding_step"] = max(
                    etapa_atual, 5
                )
            mostrar_painel()

        abrir_gerenciador_profissionais(
            page, profissionais, servicos, gravar, profissional_salvo,
        )

    async def configurar_jornada_profissional(profissional_id):
        """Jornada inicial individual compatível com o funcionamento."""
        token = usuario["access_token"]
        negocio_id = estado_estabelecimento.get("id")
        if not token or not negocio_id:
            page.show_dialog(
                ft.SnackBar(content=ft.Text("Entre com Google novamente."))
            )
            return
        try:
            horarios_negocio, jornadas = await asyncio.gather(
                asyncio.to_thread(carregar_horarios, token, negocio_id),
                asyncio.to_thread(carregar_jornadas, token, negocio_id),
            )
        except ErroEstabelecimento as erro:
            page.show_dialog(ft.SnackBar(content=ft.Text(str(erro))))
            return

        horarios_prof = [
            {
                "weekday": r["weekday"],
                "intervals": r.get("intervals") or [],
            }
            for r in jornadas if r.get("professional_id") == profissional_id
        ]
        # Primeira abertura: sugere a jornada real do estabelecimento,
        # mas só salva depois que o usuário confirmar.
        if not horarios_prof:
            horarios_prof = [
                {"weekday": dia["weekday"],
                 "intervals": dia.get("intervals") or []}
                for dia in horarios_negocio
            ]

        async def gravar(semana):
            return await asyncio.to_thread(
                salvar_jornada_profissional,
                usuario["access_token"],
                negocio_id,
                profissional_id,
                semana,
                horarios_negocio,
            )

        def jornada_salva():
            mostrar_painel()

        abrir_formulario_horarios(
            page, horarios_prof, gravar, jornada_salva,
            tipo="profissional",
        )

    async def abrir_revisao(evento=None):
        """Revisa requisitos no servidor e libera ativação autenticada."""
        token = usuario["access_token"]
        negocio_id = estado_estabelecimento.get("id")
        etapa = int(estado_estabelecimento.get("onboarding_step") or 1)
        if not token or not negocio_id or not consulta_estabelecimento["ok"]:
            page.show_dialog(
                ft.SnackBar(
                    content=ft.Text("Entre com Google para continuar.")
                )
            )
            return
        if etapa < 5:
            page.show_dialog(
                ft.SnackBar(
                    content=ft.Text("Cadastre um profissional ativo primeiro.")
                )
            )
            return
        try:
            resumo, profissionais, jornadas = await asyncio.gather(
                asyncio.to_thread(revisar_ativacao, token, negocio_id),
                asyncio.to_thread(
                    listar_profissionais, token, negocio_id
                ),
                asyncio.to_thread(carregar_jornadas, token, negocio_id),
            )
        except ErroEstabelecimento as erro:
            page.show_dialog(ft.SnackBar(content=ft.Text(str(erro))))
            return

        async def ativar():
            return await asyncio.to_thread(
                ativar_estabelecimento,
                usuario["access_token"],
                negocio_id,
            )

        def ativado(resposta):
            estado_estabelecimento.update(resposta)
            mostrar_painel()

        abrir_revisao_estabelecimento(
            page, resumo, profissionais, jornadas,
            configurar_jornada_profissional,
            ativar, ativado,
        )

    async def entrar_no_painel():
        """Consulta o estabelecimento com o JWT antes de mostrar o painel."""
        consulta_estabelecimento["ok"] = False
        estado_estabelecimento.clear()
        problema = None
        try:
            registro = await asyncio.to_thread(
                obter_estabelecimento, usuario["access_token"]
            )
            if registro:
                estado_estabelecimento.update(registro)
            consulta_estabelecimento["ok"] = True
        except ErroEstabelecimento as erro:
            problema = str(erro)
        mostrar_painel()
        if problema:
            page.show_dialog(ft.SnackBar(content=ft.Text(problema)))

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
            await entrar_no_painel()
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
        estado_estabelecimento.clear()
        consulta_estabelecimento["ok"] = False
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
            await entrar_no_painel()
        except Exception:
            feedback.value = "Erro ao validar login. Tente novamente."
            mostrar_login()

    async def ao_mudar_rota(evento):
        await tratar_callback(page.route or "")

    mostrar_painel = criar_painel(
        page,
        sair_da_conta,
        abrir_estabelecimento=abrir_cadastro_estabelecimento,
        dados_estabelecimento=estado_estabelecimento,
        abrir_horarios=abrir_horarios,
        abrir_servicos=abrir_servicos,
        abrir_profissionais=abrir_profissionais,
        abrir_revisao=abrir_revisao,
    )
    page.on_route_change = ao_mudar_rota
    mostrar_login()
    if (page.route or "").startswith("/callback"):
        await tratar_callback(page.route)
    else:
        await recuperar_sessao()


if __name__ == "__main__":
    ft.run(main)
