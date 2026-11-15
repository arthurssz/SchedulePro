"""Tela de profissionais, com vínculo aos serviços reais do estabelecimento."""

import flet as ft

from services_api import formatar_preco


FUNDO = "#111111"
CARTAO = "#1D1D1D"
CINZA = "#A3A3A3"


def abrir_gerenciador_profissionais(
    page, profissionais, servicos, salvar, ao_salvar,
):
    """Formulário Android; callbacks autenticadas providas pelo main.py."""
    # Reserva área inferior extra para os botões de navegação do Android.
    altura = max(300, min(625, (page.height or 720) * 0.73))
    principal = ft.Column(expand=True, spacing=10)
    aviso = ft.Text("", size=12, color="#F3B5B5")

    def fechar(evento=None):
        page.pop_dialog()

    def botao_primario(texto, acao=None):
        return ft.Button(
            texto, bgcolor="#F0F0F0", color="#181818",
            on_click=acao,
        )

    def campo(rotulo, valor="", teclado=None):
        opcoes = dict(
            label=rotulo,
            value=str(valor or ""),
            dense=True,
            text_size=14,
            bgcolor=CARTAO,
            border_color="#3D3D3D",
            focused_border_color="#D7D7D7",
            border_radius=10,
            content_padding=ft.Padding.symmetric(
                horizontal=12, vertical=11,
            ),
        )
        if teclado is not None:
            opcoes["keyboard_type"] = teclado
        return ft.TextField(**opcoes)

    def novo_formulario(profissional=None):
        registro = profissional or {}
        editando = profissional is not None
        nome = campo("Nome do profissional *", registro.get("name"))
        especialidade = campo(
            "Especialidade ou função (opcional)",
            registro.get("specialty"),
        )
        telefone = campo(
            "Telefone com DDD (opcional)",
            registro.get("phone"),
            ft.KeyboardType.PHONE,
        )
        email = campo(
            "E-mail (opcional)",
            registro.get("email"),
            ft.KeyboardType.EMAIL,
        )
        ativo = ft.Checkbox(
            label="Profissional ativo",
            value=registro.get("is_active", True),
        )

        vinculados = set(registro.get("service_ids") or [])
        opcoes = []
        for servico in servicos:
            esta_ativo = servico.get("is_active", False) is True
            preco = formatar_preco(servico.get("price_cents") or 0)
            rotulo = (
                f"{servico['name']} · {preco} · "
                f"{servico.get('duration_minutes', 0)} min"
            )
            if not esta_ativo:
                rotulo += " (inativo)"
            opcao = ft.Checkbox(
                label=rotulo,
                value=servico["id"] in vinculados,
                data=servico["id"],
            )
            opcoes.append(opcao)

        salvar_btn = botao_primario("Salvar profissional")

        async def confirmar(evento):
            salvar_btn.disabled = True
            aviso.value = "Salvando profissional e serviços no Supabase..."
            page.update()
            formulario = {
                "name": nome.value or "",
                "specialty": especialidade.value or "",
                "phone": telefone.value or "",
                "email": email.value or "",
                "is_active": ativo.value is True,
                "service_ids": [
                    opcao.data
                    for opcao in opcoes if opcao.value is True
                ],
            }
            try:
                resultado = await salvar(
                    formulario, registro.get("id") if editando else None
                )
            except Exception as erro:
                aviso.value = str(erro)
                salvar_btn.disabled = False
                page.update()
                return
            fechar()
            ao_salvar(resultado)
            page.show_dialog(
                ft.SnackBar(
                    content=ft.Text(
                        "Profissional salvo! Próxima etapa: 5/5."
                        if resultado.get("_etapa_avancou")
                        else "Profissional salvo com sucesso."
                    )
                )
            )

        salvar_btn.on_click = confirmar
        aviso.value = ""
        itens = [
            ft.Text(
                "PROFISSIONAIS · ETAPA 4/5",
                size=11, color=CINZA,
            ),
            ft.Text(
                "Editar profissional" if editando else "Novo profissional",
                size=22, weight=ft.FontWeight.BOLD,
            ),
            nome,
            especialidade,
            telefone,
            email,
            ativo,
            ft.Text(
                "Serviços que este profissional realiza",
                size=14, weight=ft.FontWeight.BOLD,
            ),
            ft.Text(
                "Selecione um ou mais serviços para um profissional ativo.",
                size=12, color=CINZA,
            ),
        ]
        if not opcoes:
            itens.append(
                ft.Text(
                    "Cadastre e ative um serviço antes de adicionar "
                    "profissionais.",
                    color=CINZA, size=12,
                )
            )
        else:
            itens.extend(opcoes)
        principal.controls = [
            ft.Column(
                expand=True,
                scroll=ft.ScrollMode.AUTO,
                spacing=10,
                controls=itens,
            ),
            aviso,
            ft.Row(
                alignment=ft.MainAxisAlignment.END,
                spacing=8,
                controls=[
                    ft.TextButton("Voltar", on_click=mostrar_lista),
                    salvar_btn,
                ],
            ),
        ]
        page.update()

    def linha_profissional(item):
        ativo = bool(item.get("is_active"))
        id_vinculos = set(item.get("service_ids") or [])
        nomes_vinculos = [
            s.get("name") or "Serviço"
            for s in servicos if s.get("id") in id_vinculos
        ]
        descricao = ", ".join(nomes_vinculos) or "Sem serviços vinculados"
        return ft.Container(
            bgcolor=CARTAO, border_radius=12,
            padding=ft.Padding.symmetric(horizontal=14, vertical=12),
            content=ft.Column(
                tight=True, spacing=9,
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text(
                                item.get("name") or "Profissional",
                                expand=True,
                                size=15,
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Text(
                                "Ativo" if ativo else "Inativo",
                                color=CINZA, size=11,
                            ),
                        ],
                    ),
                    ft.Text(
                        item.get("specialty") or "Atendimento",
                        color=CINZA, size=12,
                    ),
                    ft.Text(
                        descricao, color=CINZA, size=12,
                    ),
                    ft.TextButton(
                        "Editar profissional",
                        on_click=lambda _, reg=item: novo_formulario(reg),
                    ),
                ],
            ),
        )

    def mostrar_lista(evento=None):
        aviso.value = ""
        lista = [linha_profissional(reg) for reg in profissionais]
        if not lista:
            lista = [
                ft.Container(
                    bgcolor=CARTAO, border_radius=12, padding=20,
                    content=ft.Column(
                        tight=True,
                        spacing=8,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Icon(
                                ft.Icons.PEOPLE_OUTLINE,
                                color="#BBBBBB", size=34,
                            ),
                            ft.Text(
                                "Nenhum profissional cadastrado",
                                weight=ft.FontWeight.BOLD,
                                size=15,
                            ),
                            ft.Text(
                                "Cadastre quem realiza os atendimentos.",
                                color=CINZA, size=12,
                                text_align=ft.TextAlign.CENTER,
                            ),
                        ],
                    ),
                )
            ]
        principal.controls = [
            ft.Text(
                "PROFISSIONAIS · ETAPA 4/5",
                color=CINZA, size=11,
            ),
            ft.Text(
                "Equipe e profissionais",
                size=23, weight=ft.FontWeight.BOLD,
            ),
            ft.Text(
                "Vincule os profissionais aos serviços oferecidos.",
                color=CINZA, size=13,
            ),
            ft.Column(
                expand=True, scroll=ft.ScrollMode.AUTO,
                spacing=9, controls=lista,
            ),
            aviso,
            ft.Row(
                alignment=ft.MainAxisAlignment.END,
                spacing=8,
                controls=[
                    ft.TextButton("Fechar", on_click=fechar),
                    botao_primario(
                        "+ Novo profissional",
                        lambda _: novo_formulario(),
                    ),
                ],
            ),
        ]
        page.update()

    page.show_dialog(
        ft.BottomSheet(
            scrollable=True, show_drag_handle=True,
            bgcolor=FUNDO,
            content=ft.Container(
                height=altura,
                padding=ft.Padding.only(
                    left=17, right=17, top=10, bottom=45,
                ),
                content=principal,
            ),
        )
    )
    mostrar_lista()
