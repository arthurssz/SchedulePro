"""Etapa 5/5: revisão do negócio, jornadas e ativação interna."""

import flet as ft


FUNDO = "#111111"
CARTAO = "#1D1D1D"
CINZA = "#A3A3A3"


def abrir_revisao_estabelecimento(
    page, resumo, profissionais, jornadas, abrir_jornada,
    ativar, concluido,
):
    """A prévia pública não recebe estes dados; só o APK autenticado."""
    altura = max(340, min(660, (page.height or 720) * 0.77))
    pronto = resumo.get("ready") is True
    ativo = resumo.get("onboarding_completed") is True
    aviso = ft.Text("", color="#F3B5B5", size=12)
    salvar_btn = ft.Button(
        "Ativar estabelecimento",
        bgcolor="#F0F0F0",
        color="#181818",
        disabled=(not pronto or ativo),
    )

    def fechar(evento=None):
        page.pop_dialog()

    async def ativar_agora(evento):
        salvar_btn.disabled = True
        aviso.value = "Validando a configuração no Supabase..."
        page.update()
        try:
            resposta = await ativar()
        except Exception as erro:
            aviso.value = str(erro)
            salvar_btn.disabled = False
            page.update()
            return
        fechar()
        concluido(resposta)
        page.show_dialog(
            ft.SnackBar(
                content=ft.Text(
                    "Estabelecimento ativo! Agenda interna liberada. "
                    "Reservas públicas continuam desativadas."
                )
            )
        )

    salvar_btn.on_click = ativar_agora

    def linha_resumo(rotulo, valor):
        return ft.Row(
            spacing=7,
            controls=[
                ft.Text(rotulo, color=CINZA, size=12, expand=True),
                ft.Text(
                    str(valor), size=12, weight=ft.FontWeight.BOLD,
                ),
            ],
        )

    conteudo = [
        ft.Text(
            "REVISÃO E ATIVAÇÃO · ETAPA 5/5",
            color=CINZA, size=11,
        ),
        ft.Text(
            "Finalizar configuração",
            size=22, weight=ft.FontWeight.BOLD,
        ),
        ft.Text(
            "Confira as informações antes de liberar a agenda.",
            color=CINZA, size=13,
        ),
        ft.Container(
            bgcolor=CARTAO, border_radius=13, padding=15,
            content=ft.Column(
                spacing=9, tight=True,
                controls=[
                    linha_resumo(
                        "Estabelecimento", resumo.get("name") or "—",
                    ),
                    linha_resumo(
                        "Fuso", resumo.get("timezone") or "—",
                    ),
                    linha_resumo(
                        "Dias configurados",
                        resumo.get("business_hours_days", 0),
                    ),
                    linha_resumo(
                        "Serviços ativos", resumo.get("active_services", 0),
                    ),
                    linha_resumo(
                        "Profissionais ativos",
                        resumo.get("active_professionals", 0),
                    ),
                ],
            ),
        ),
        ft.Text(
            "Jornadas dos profissionais",
            size=15, weight=ft.FontWeight.BOLD,
        ),
        ft.Text(
            "Defina quando cada profissional atende. Inicialmente, "
            "você poderá usar os horários do estabelecimento e ajustá-los.",
            color=CINZA, size=12,
        ),
    ]

    dias_por_profissional = {}
    for registro in jornadas:
        ident = registro.get("professional_id")
        dias_por_profissional[ident] = (
            dias_por_profissional.get(ident, 0) + 1
        )
    for profissional in profissionais:
        if not profissional.get("is_active"):
            continue
        identificador = profissional.get("id")
        dias = dias_por_profissional.get(identificador, 0)
        conteudo.append(
            ft.Container(
                bgcolor=CARTAO, border_radius=12,
                padding=ft.Padding.symmetric(
                    horizontal=12, vertical=10,
                ),
                content=ft.Row(
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Column(
                            expand=True, spacing=3, tight=True,
                            controls=[
                                ft.Text(
                                    profissional.get("name") or "Profissional",
                                    size=14, weight=ft.FontWeight.BOLD,
                                ),
                                ft.Text(
                                    "Jornada configurada"
                                    if dias == 7
                                    else "Jornada pendente",
                                    color=CINZA, size=11,
                                ),
                            ],
                        ),
                        ft.TextButton(
                            "Editar" if dias == 7 else "Definir",
                            on_click=lambda _, pid=identificador: (
                                fechar(),
                                page.run_task(abrir_jornada, pid),
                            ),
                        ),
                    ],
                ),
            )
        )

    if resumo.get("issues"):
        conteudo.append(
            ft.Text(
                "Pendências para ativação",
                size=15, weight=ft.FontWeight.BOLD,
            )
        )
        for pendencia in resumo["issues"]:
            conteudo.append(
                ft.Text(
                    "• " + pendencia,
                    size=12, color="#F2B4B4",
                )
            )
    elif ativo:
        conteudo.append(
            ft.Text(
                "O estabelecimento já está ativo.",
                size=13, color="#E7E7E7",
            )
        )
    else:
        conteudo.append(
            ft.Text(
                "Tudo pronto para ativação.",
                size=13, color="#E7E7E7",
            )
        )
    conteudo.append(
        ft.Text(
            "A ativação libera apenas a agenda interna. "
            "O portal de reservas públicas permanece desligado.",
            size=12, color=CINZA,
        )
    )

    page.show_dialog(
        ft.BottomSheet(
            scrollable=True,
            show_drag_handle=True,
            bgcolor=FUNDO,
            content=ft.Container(
                height=altura,
                padding=ft.Padding.only(
                    left=17, right=17, top=10, bottom=45,
                ),
                content=ft.Column(
                    expand=True,
                    spacing=11,
                    controls=[
                        ft.Column(
                            expand=True, scroll=ft.ScrollMode.AUTO,
                            spacing=12, controls=conteudo,
                        ),
                        aviso,
                        ft.Row(
                            alignment=ft.MainAxisAlignment.END,
                            spacing=9,
                            controls=[
                                ft.TextButton("Voltar", on_click=fechar),
                                salvar_btn,
                            ],
                        ),
                    ],
                ),
            ),
        )
    )
