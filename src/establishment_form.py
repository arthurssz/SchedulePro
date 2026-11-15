"""Primeiro passo do cadastro de estabelecimento (exclusivo do APK).

O formulário valida entradas localmente; a persistência é feita por uma
callback autenticada, nunca pela prévia pública sem login.
"""

import flet as ft


FUNDO = "#111111"
CARTAO = "#1D1D1D"
CINZA = "#AAAAAA"


def abrir_formulario_estabelecimento(page, registro, salvar, ao_salvar):
    """Exibe o passo 1/5; salvar é uma função assíncrona autenticada."""
    inicial = registro or {}

    def campo(rotulo, valor="", tipo=None, multiline=False):
        opcoes = {
            "label": rotulo,
            "value": valor or "",
            "dense": True,
            "text_size": 14,
            "bgcolor": CARTAO,
            "border_color": "#383838",
            "focused_border_color": "#CACACA",
            "border_radius": 10,
            "content_padding": ft.Padding.symmetric(
                horizontal=14, vertical=12
            ),
        }
        if tipo is not None:
            opcoes["keyboard_type"] = tipo
        if multiline:
            opcoes.update(
                multiline=True,
                min_lines=2,
                max_lines=3,
            )
        return ft.TextField(**opcoes)

    nome = campo("Nome do estabelecimento *", inicial.get("name"))
    tipo = campo(
        "Tipo de negócio * (ex.: barbearia, salão)",
        inicial.get("business_type"),
    )
    telefone = campo(
        "Telefone com DDD (opcional)",
        inicial.get("phone"),
        tipo=ft.KeyboardType.PHONE,
    )
    endereco = campo(
        "Endereço (opcional)",
        inicial.get("address"),
    )
    descricao = campo(
        "Descrição (opcional)",
        inicial.get("description"),
        multiline=True,
    )
    erro = ft.Text("", size=12, color="#F3B5B5")
    salvar_btn = ft.Button(
        "Salvar e sair",
        bgcolor="#F0F0F0",
        color="#181818",
    )

    async def confirmar(evento):
        titulo = (nome.value or "").strip()
        atividade = (tipo.value or "").strip()
        numero = (telefone.value or "").strip()
        digitos = "".join(c for c in numero if c.isdigit())
        if digitos.startswith("55") and len(digitos) in (12, 13):
            digitos = digitos[2:]

        if len(titulo) < 2 or len(titulo) > 120:
            erro.value = "Informe um nome entre 2 e 120 caracteres."
            page.update()
            return
        if not atividade:
            erro.value = "Informe o tipo de negócio."
            page.update()
            return
        if digitos and len(digitos) not in (10, 11):
            erro.value = "Telefone precisa ter DDD e 10 ou 11 dígitos."
            page.update()
            return
        salvar_btn.disabled = True
        erro.value = "Salvando dados no Supabase..."
        page.update()
        try:
            registro_salvo = await salvar(
                {
                    "name": titulo,
                    "business_type": atividade,
                    "phone": numero,
                    "address": (endereco.value or "").strip(),
                    "description": (descricao.value or "").strip(),
                }
            )
        except Exception as falha:
            erro.value = str(falha)
            salvar_btn.disabled = False
            page.update()
            return
        page.pop_dialog()
        ao_salvar(registro_salvo)
        page.show_dialog(
            ft.SnackBar(
                content=ft.Text(
                    "Estabelecimento salvo! Próximo passo: horários (2/5)."
                )
            )
        )

    salvar_btn.on_click = confirmar
    page.show_dialog(
        ft.BottomSheet(
            scrollable=True,
            show_drag_handle=True,
            bgcolor=FUNDO,
            content=ft.Container(
                padding=18,
                content=ft.Column(
                    spacing=11,
                    tight=True,
                    controls=[
                        ft.Text(
                            "CADASTRO DO ESTABELECIMENTO · 1/5",
                            size=11,
                            color=CINZA,
                        ),
                        ft.Text(
                            "Informações do negócio",
                            size=23,
                            weight=ft.FontWeight.BOLD,
                        ),
                        ft.Text(
                            "Vamos começar com os dados básicos. "
                            "Você poderá continuar a configuração depois.",
                            size=13,
                            color=CINZA,
                        ),
                        nome,
                        tipo,
                        telefone,
                        endereco,
                        descricao,
                        erro,
                        ft.Row(
                            alignment=ft.MainAxisAlignment.END,
                            spacing=10,
                            controls=[
                                ft.TextButton(
                                    "Cancelar",
                                    on_click=lambda _: page.pop_dialog(),
                                ),
                                salvar_btn,
                            ],
                        ),
                        ft.Text(
                            "Seus dados serão salvos apenas na sua conta.",
                            size=11,
                            color=CINZA,
                        ),
                    ],
                ),
            ),
        )
    )
