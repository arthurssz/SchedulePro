"""Gerenciador de serviços (cadastro, edição e ativação) do SchedulePro."""

import flet as ft

from services_api import formatar_preco


FUNDO = "#111111"
CARTAO = "#1D1D1D"
SECUNDARIO = "#A3A3A3"


def abrir_gerenciador_servicos(
    page, cadastrados, salvar, mudar_atividade, ao_alterar,
):
    """Recebe dados já filtrados por RLS; nenhuma API é chamada na prévia."""
    altura = max(310, min(700, (page.height or 720) * 0.82))
    corpo = ft.Column(expand=True, spacing=10)
    erro = ft.Text("", color="#F3B5B5", size=12)

    def fechar(evento=None):
        page.pop_dialog()

    def botao_claro(rotulo, acao):
        return ft.Button(
            rotulo,
            bgcolor="#F0F0F0",
            color="#181818",
            on_click=acao,
        )

    def campo(rotulo, valor="", teclado=None, varias_linhas=False):
        opcoes = dict(
            label=rotulo,
            value=str(valor or ""),
            dense=True,
            text_size=14,
            bgcolor=CARTAO,
            border_color="#404040",
            focused_border_color="#CFCFCF",
            border_radius=10,
            content_padding=ft.Padding.symmetric(
                horizontal=12, vertical=10,
            ),
        )
        if teclado is not None:
            opcoes["keyboard_type"] = teclado
        if varias_linhas:
            opcoes.update(multiline=True, min_lines=2, max_lines=4)
        return ft.TextField(**opcoes)

    def mostrar_formulario(servico=None):
        editar = servico is not None
        existente = servico or {}
        nome = campo("Nome do serviço *", existente.get("name"))
        duracao = campo(
            "Duração em minutos *",
            existente.get("duration_minutes", 30),
            ft.KeyboardType.NUMBER,
        )
        preco = campo(
            "Preço em reais * (ex.: 50,00)",
            ("%d,%02d" % divmod(
                int(existente.get("price_cents") or 0), 100
            )) if editar else "0,00",
            ft.KeyboardType.NUMBER,
        )
        descricao = campo(
            "Descrição (opcional)",
            existente.get("description"),
            varias_linhas=True,
        )
        ativo = ft.Checkbox(
            label="Serviço ativo",
            value=existente.get("is_active", True),
        )
        salvar_btn = botao_claro("Salvar serviço", None)

        async def confirmar(evento):
            salvar_btn.disabled = True
            erro.value = "Salvando no Supabase..."
            page.update()
            try:
                resposta = await salvar(
                    {
                        "name": nome.value or "",
                        "duration_minutes": duracao.value or "",
                        "price": preco.value or "",
                        "description": descricao.value or "",
                        "is_active": ativo.value is True,
                    },
                    existente.get("id") if editar else None,
                )
            except Exception as falha:
                erro.value = str(falha)
                salvar_btn.disabled = False
                page.update()
                return
            fechar()
            ao_alterar(resposta)
            aviso = resposta.get("_aviso")
            texto = aviso or (
                "Serviço salvo. Próxima etapa: profissionais (4/5)."
                if resposta.get("_etapa_avancou")
                else "Serviço salvo com sucesso."
            )
            page.show_dialog(
                ft.SnackBar(content=ft.Text(texto))
            )

        salvar_btn.on_click = confirmar
        erro.value = ""
        scroll_form = ft.Column(
            expand=True,
            spacing=12,
            scroll=ft.ScrollMode.AUTO,
            controls=[
                ft.Text(
                    "SERVIÇOS · ETAPA 3/5",
                    size=11,
                    color=SECUNDARIO,
                ),
                ft.Text(
                    "Editar serviço" if editar else "Novo serviço",
                    size=23,
                    weight=ft.FontWeight.BOLD,
                ),
                nome,
                duracao,
                preco,
                descricao,
                ativo,
            ],
        )
        corpo.controls = [
            scroll_form,
            erro,
            ft.Row(
                alignment=ft.MainAxisAlignment.END,
                controls=[
                    ft.TextButton("Voltar", on_click=mostrar_lista),
                    salvar_btn,
                ],
            ),
        ]
        page.update()

    async def alternar(servico):
        erro.value = "Atualizando no Supabase..."
        page.update()
        try:
            retorno = await mudar_atividade(
                servico["id"], not servico.get("is_active", True)
            )
        except Exception as falha:
            erro.value = str(falha)
            page.update()
            return
        fechar()
        ao_alterar(retorno)
        page.show_dialog(
            ft.SnackBar(
                content=ft.Text(
                    "Serviço ativado."
                    if retorno.get("is_active") else "Serviço desativado."
                )
            )
        )

    def linha_servico(servico):
        ativo = bool(servico.get("is_active"))
        titulo = servico.get("name") or "Serviço"
        preco = formatar_preco(servico.get("price_cents") or 0)
        duracao = int(servico.get("duration_minutes") or 0)
        return ft.Container(
            bgcolor=CARTAO,
            border_radius=12,
            padding=ft.Padding.symmetric(
                horizontal=12, vertical=10,
            ),
            content=ft.Column(
                tight=True,
                spacing=7,
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text(
                                titulo,
                                size=15,
                                weight=ft.FontWeight.BOLD,
                                expand=True,
                            ),
                            ft.Text(
                                "Ativo" if ativo else "Inativo",
                                size=11,
                                color=SECUNDARIO,
                            ),
                        ]
                    ),
                    ft.Text(
                        f"{preco} · {duracao} min",
                        size=12,
                        color=SECUNDARIO,
                    ),
                    ft.Row(
                        spacing=9,
                        controls=[
                            ft.TextButton(
                                "Editar",
                                on_click=lambda _, item=servico:
                                    mostrar_formulario(item),
                            ),
                            ft.TextButton(
                                "Desativar" if ativo else "Ativar",
                                on_click=lambda _, item=servico:
                                    page.run_task(alternar, item),
                            ),
                        ],
                    ),
                ],
            ),
        )

    def mostrar_lista(evento=None):
        erro.value = ""
        itens = [
            linha_servico(item) for item in cadastrados
        ]
        if not itens:
            itens = [
                ft.Container(
                    bgcolor=CARTAO,
                    border_radius=12,
                    padding=20,
                    content=ft.Column(
                        tight=True,
                        spacing=8,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Icon(
                                ft.Icons.DESIGN_SERVICES_OUTLINED,
                                size=34,
                                color="#BBBBBB",
                            ),
                            ft.Text(
                                "Nenhum serviço cadastrado",
                                size=15,
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Text(
                                "Adicione o primeiro serviço do negócio.",
                                color=SECUNDARIO,
                                size=12,
                                text_align=ft.TextAlign.CENTER,
                            ),
                        ],
                    ),
                )
            ]
        corpo.controls = [
            ft.Text(
                "SERVIÇOS · ETAPA 3/5",
                color=SECUNDARIO,
                size=11,
            ),
            ft.Text(
                "Catálogo de serviços",
                size=23,
                weight=ft.FontWeight.BOLD,
            ),
            ft.Text(
                "Defina o preço e o tempo de cada atendimento.",
                size=13,
                color=SECUNDARIO,
            ),
            ft.Column(
                expand=True,
                spacing=10,
                scroll=ft.ScrollMode.AUTO,
                controls=itens,
            ),
            erro,
            ft.Row(
                alignment=ft.MainAxisAlignment.END,
                controls=[
                    ft.TextButton("Fechar", on_click=fechar),
                    botao_claro(
                        "+ Novo serviço",
                        lambda _: mostrar_formulario(),
                    ),
                ],
            ),
        ]
        page.update()

    page.show_dialog(
        ft.BottomSheet(
            scrollable=True,
            show_drag_handle=True,
            bgcolor=FUNDO,
            content=ft.Container(
                height=altura,
                padding=ft.Padding.symmetric(
                    horizontal=18, vertical=12,
                ),
                content=corpo,
            ),
        )
    )
    mostrar_lista()
