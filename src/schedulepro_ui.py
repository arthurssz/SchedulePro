"""Telas compartilhadas entre o APK e a prévia web do SchedulePro.

Manter a interface neste módulo evita dois designs divergentes.
NÃO há autenticação nem acesso a dados privados nesta camada.
"""
from datetime import date, datetime, timedelta, timezone
import calendar
import flet as ft

from appointment_filters import FILTROS_STATUS, filtrar_agenda, opcoes_agenda


FUNDO = "#111111"
CARTAO = "#1D1D1D"
TEXTO_SECUNDARIO = "#A3A3A3"

DIAS_SEMANA = ("Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo")
MESES = ("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro")
DIAS_CURTOS = ("Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom")
MESES_CURTOS = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")

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



def criar_painel(
    page: ft.Page, sair_da_conta,
    abrir_estabelecimento=None, dados_estabelecimento=None,
    abrir_horarios=None,
    abrir_servicos=None,
    abrir_profissionais=None,
    abrir_revisao=None,
    buscar_clientes=None,
    persistir_cliente=None,
    alterar_arquivo_cliente=None,
    remover_cliente_real=None,
    abrir_agendamento=None,
    buscar_agendamentos=None,
    alterar_status_agendamento=None,
    abrir_reagendamento=None,
    listar_historico_reagendamento=None,
):
    """Prepara a navegação e retorna a função que abre o painel."""
    conteudo = ft.Column(
        expand=True,
        spacing=9,
        scroll=ft.ScrollMode.AUTO,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
    )

    dia_visivel = {"data": date.today()}
    agenda_estado = {
        "data": date.today(),
        "modo": "Dia",
        "busca": "",
        "busca_rascunho": "",
        "pesquisa_aberta": False,
        "filtro_status": "todos",
        "filtro_profissional": "todos",
        "filtro_servico": "todos",
        "rotulos_profissionais": {},
        "rotulos_servicos": {},
    }

    agenda_consulta = {
        "chave": None,
        "registros": [],
        "carregando": False,
        "erro": None,
        "sequencia": 0,
    }

    def reservas_no_dia(dia):
        return [
            r for r in agenda_consulta["registros"]
            if r.get("local_date") == dia.isoformat()
        ]

    def reservas_filtradas():
        return filtrar_agenda(
            agenda_consulta["registros"],
            status=agenda_estado["filtro_status"],
            profissional_id=agenda_estado["filtro_profissional"],
            servico_id=agenda_estado["filtro_servico"],
            busca=agenda_estado["busca"],
        )

    def reservas_filtradas_no_dia(dia):
        return [
            r for r in reservas_filtradas()
            if r.get("local_date") == dia.isoformat()
        ]

    def selecionar_status_agenda(evento):
        novo_status = evento.control.value or "todos"
        if novo_status == agenda_estado["filtro_status"]:
            return
        agenda_estado["filtro_status"] = novo_status
        renderizar(1)

    def selecionar_profissional_agenda(evento):
        novo_id = evento.control.value or "todos"
        if novo_id == agenda_estado["filtro_profissional"]:
            return
        agenda_estado["filtro_profissional"] = novo_id
        renderizar(1)

    def selecionar_servico_agenda(evento):
        novo_id = evento.control.value or "todos"
        if novo_id == agenda_estado["filtro_servico"]:
            return
        agenda_estado["filtro_servico"] = novo_id
        renderizar(1)

    def opcoes_filtro_agenda(tipo):
        """Mantém a seleção mesmo quando o usuário muda de período."""
        chave = (
            "rotulos_profissionais"
            if tipo == "professional" else "rotulos_servicos"
        )
        mapa = agenda_estado[chave]
        mapa.update(opcoes_agenda(agenda_consulta["registros"], tipo))
        titulo = (
            "Todos os profissionais"
            if tipo == "professional" else "Todos os serviços"
        )
        return [
            ft.DropdownOption(key="todos", text=titulo),
            *[
                ft.DropdownOption(key=identificador, text=nome)
                for identificador, nome in sorted(
                    mapa.items(),
                    key=lambda item: (item[1].casefold(), item[0]),
                )
            ],
        ]

    def abrir_detalhes_reserva(registro):
        """Painel único para gerenciar o status real da reserva."""
        status_atual = registro.get("status") or "scheduled"
        rotulos = {
            "scheduled": "Agendado",
            "confirmed": "Confirmado",
            "completed": "Concluído",
            "canceled": "Cancelado",
            "no_show": "Não compareceu",
        }
        cliente = (registro.get("customer") or {}).get("name") or "Cliente"
        servico = (registro.get("service") or {}).get("name") or "Serviço"
        profissional = (
            (registro.get("professional") or {}).get("name") or "Profissional"
        )
        data_str = str(registro.get("local_date") or "")
        hora_str = str(registro.get("local_time") or "")[:5]
        preco = int(registro.get("price_cents") or 0)
        try:
            termino = datetime.fromisoformat(
                str(registro.get("ends_at") or "").replace("Z", "+00:00")
            )
            horario_terminou = (
                termino.tzinfo is not None
                and termino <= datetime.now(timezone.utc)
            )
        except (ValueError, TypeError):
            horario_terminou = False

        aviso = ft.Text("", size=12, color="#F3B5B5")
        botoes = []

        async def aplicar_status(novo_status):
            if alterar_status_agendamento is None:
                mostrar_aviso("Gerenciamento disponível no APK autenticado.")
                return
            for botao in botoes:
                botao.disabled = True
            aviso.value = "Atualizando o agendamento no Supabase..."
            page.update()
            try:
                await alterar_status_agendamento(registro["id"], novo_status)
            except Exception as falha:
                aviso.value = str(falha)
                for botao in botoes:
                    botao.disabled = False
                page.update()
                return
            page.pop_dialog()
            agenda_consulta["sequencia"] += 1
            agenda_consulta["chave"] = None
            aba = (
                page.navigation_bar.selected_index
                if page.navigation_bar is not None else 1
            )
            renderizar(aba)
            mensagem = {
                "confirmed": "Agendamento confirmado!",
                "completed": "Atendimento concluído!",
                "canceled": "Agendamento cancelado.",
            }
            mostrar_aviso(mensagem.get(novo_status, "Agendamento atualizado."))

        async def confirmar(evento):
            await aplicar_status("confirmed")

        async def concluir(evento):
            await aplicar_status("completed")

        async def confirmar_cancelamento(evento):
            page.pop_dialog()
            await aplicar_status("canceled")

        def pedir_cancelamento(evento):
            page.show_dialog(
                ft.AlertDialog(
                    modal=True,
                    title=ft.Text("Cancelar agendamento?"),
                    content=ft.Text(
                        "O atendimento será marcado como cancelado "
                        "e o horário ficará disponível novamente. "
                        "O registro será preservado no histórico."
                    ),
                    actions=[
                        ft.TextButton(
                            "Voltar",
                            on_click=lambda _: page.pop_dialog(),
                        ),
                        ft.Button(
                            "Sim, cancelar",
                            bgcolor="#482525",
                            color="#F5DEDE",
                            on_click=confirmar_cancelamento,
                        ),
                    ],
                )
            )

        def iniciar_reagendamento(evento):
            if abrir_reagendamento is None:
                mostrar_aviso("Reagendamento disponível no APK autenticado.")
                return
            page.pop_dialog()
            abrir_reagendamento(registro)

        async def ver_historico(evento):
            if listar_historico_reagendamento is None:
                mostrar_aviso("Histórico disponível no APK autenticado.")
                return
            aviso.value = "Carregando histórico..."
            page.update()
            try:
                mudancas = await listar_historico_reagendamento(registro["id"])
            except Exception as erro:
                aviso.value = str(erro)
                page.update()
                return
            page.pop_dialog()
            itens = [
                ft.Text(
                    "HISTÓRICO DE REAGENDAMENTOS",
                    size=11,
                    color=TEXTO_SECUNDARIO,
                ),
                ft.Text(
                    "Alterações de data e horário",
                    size=21,
                    weight=ft.FontWeight.BOLD,
                ),
            ]
            for item in mudancas:
                de_dia = str(item.get("old_local_date") or "")
                para_dia = str(item.get("new_local_date") or "")
                de_hora = str(item.get("old_local_time") or "")[:5]
                para_hora = str(item.get("new_local_time") or "")[:5]
                itens.append(
                    ft.Container(
                        bgcolor=CARTAO,
                        border_radius=12,
                        padding=14,
                        content=ft.Column(
                            tight=True,
                            spacing=8,
                            controls=[
                                ft.Text(
                                    f"De {de_dia[8:10]}/{de_dia[5:7]}/{de_dia[:4]}"
                                    f" às {de_hora}",
                                    size=13,
                                ),
                                ft.Text(
                                    f"Para {para_dia[8:10]}/{para_dia[5:7]}/{para_dia[:4]}"
                                    f" às {para_hora}",
                                    size=14,
                                    weight=ft.FontWeight.BOLD,
                                ),
                            ],
                        ),
                    )
                )
            if not mudancas:
                itens.append(
                    ft.Text(
                        "Este atendimento ainda não foi reagendado.",
                        color=TEXTO_SECUNDARIO,
                    )
                )
            itens.append(
                ft.TextButton(
                    "Fechar",
                    on_click=lambda _: page.pop_dialog(),
                )
            )
            page.show_dialog(
                ft.BottomSheet(
                    scrollable=True,
                    show_drag_handle=True,
                    bgcolor=FUNDO,
                    content=ft.Container(
                        padding=ft.Padding.only(
                            left=16,top=12,right=16,bottom=44,
                        ),
                        content=ft.Column(
                            tight=True,spacing=12,controls=itens,
                        ),
                    ),
                )
            )

        if status_atual == "scheduled":
            botoes.append(
                ft.Button(
                    "Confirmar",
                    icon=ft.Icons.CHECK_CIRCLE_OUTLINE,
                    bgcolor="#F0F0F0",
                    color="#171717",
                    on_click=confirmar,
                )
            )
        if status_atual in ("scheduled", "confirmed"):
            botoes.append(
                ft.Button(
                    "Reagendar",
                    icon=ft.Icons.EDIT,
                    bgcolor="#292929",
                    color="#F0F0F0",
                    on_click=iniciar_reagendamento,
                )
            )
            if horario_terminou:
                botoes.append(
                    ft.Button(
                        "Concluir",
                        icon=ft.Icons.DONE_ALL,
                        bgcolor="#292929",
                        color="#F0F0F0",
                        on_click=concluir,
                    )
                )
            botoes.append(
                ft.Button(
                    "Cancelar agendamento",
                    bgcolor="#292929",
                    color="#EAB5B5",
                    on_click=pedir_cancelamento,
                )
            )

        detalhes = [
            ft.Text(
                "DETALHES DO AGENDAMENTO",
                size=11,
                color=TEXTO_SECUNDARIO,
            ),
            ft.Text(
                f"{data_str[8:10]}/{data_str[5:7]}/{data_str[:4]} · {hora_str}",
                size=21,
                weight=ft.FontWeight.BOLD,
            ),
            ft.Text(
                rotulos.get(status_atual, "Agendado"),
                size=13,
                color=TEXTO_SECUNDARIO,
            ),
            ft.Container(
                bgcolor=CARTAO,
                border_radius=13,
                padding=14,
                content=ft.Column(
                    tight=True,
                    spacing=10,
                    controls=[
                        ft.Text(f"Cliente: {cliente}", size=14),
                        ft.Text(f"Serviço: {servico}", size=14),
                        ft.Text(f"Profissional: {profissional}", size=14),
                        ft.Text(
                            "Valor: R$ "
                            + f"{preco // 100:,}".replace(",", ".")
                            + f",{preco % 100:02d}",
                            size=14,
                        ),
                        ft.Text(
                            "Observações: "
                            + (registro.get("notes") or "Nenhuma"),
                            size=12,
                            color=TEXTO_SECUNDARIO,
                        ),
                    ],
                ),
            ),
        ]
        if status_atual in ("scheduled", "confirmed") and not horario_terminou:
            detalhes.append(
                ft.Text(
                    "Concluir ficará disponível após o fim do atendimento.",
                    size=12,
                    color=TEXTO_SECUNDARIO,
                )
            )
        detalhes.append(aviso)
        if listar_historico_reagendamento is not None:
            detalhes.append(
                ft.TextButton(
                    "Ver histórico de reagendamentos",
                    on_click=ver_historico,
                )
            )
        if botoes:
            detalhes.extend(botoes)
        else:
            detalhes.append(
                ft.Text(
                    "Este agendamento está finalizado.",
                    color=TEXTO_SECUNDARIO,
                    size=12,
                )
            )
        detalhes.append(
            ft.TextButton(
                "Fechar",
                on_click=lambda _: page.pop_dialog(),
            )
        )
        page.show_dialog(
            ft.BottomSheet(
                scrollable=True,
                show_drag_handle=True,
                bgcolor=FUNDO,
                content=ft.Container(
                    padding=ft.Padding.only(
                        left=16, top=12, right=16, bottom=44,
                    ),
                    content=ft.Column(
                        tight=True,
                        spacing=12,
                        controls=detalhes,
                    ),
                ),
            )
        )

    def cartao_reserva(registro):
        pessoa = (registro.get("customer") or {}).get("name") or "Cliente"
        servico = (registro.get("service") or {}).get("name") or "Serviço"
        profissional = (registro.get("professional") or {}).get("name") or "Profissional"
        horario = str(registro.get("local_time") or "")[:5]
        status = {
            "scheduled": "Agendado",
            "confirmed": "Confirmado",
            "completed": "Concluído",
            "canceled": "Cancelado",
            "no_show": "Não compareceu",
        }.get(registro.get("status"), "Agendado")
        return ft.Container(
            bgcolor=CARTAO,
            border_radius=13,
            padding=14,
            on_click=lambda _, r=registro: abrir_detalhes_reserva(r),
            content=ft.Column(
                tight=True,
                spacing=6,
                controls=[
                    ft.Row(controls=[
                        ft.Text(horario, size=18, weight=ft.FontWeight.BOLD),
                        ft.Container(expand=True),
                        ft.Text(status, size=12, color=TEXTO_SECUNDARIO),
                    ]),
                    ft.Text(pessoa, size=15, weight=ft.FontWeight.BOLD),
                    ft.Text(
                        f"{servico} · {profissional}",
                        size=12,
                        color=TEXTO_SECUNDARIO,
                    ),
                    ft.Text(
                        "Toque para gerenciar",
                        size=11,
                        color=TEXTO_SECUNDARIO,
                    ),
                ],
            ),
        )

    def mudar_modo_agenda(modo: str):
        agenda_estado["modo"] = modo
        renderizar(1)

    def mudar_periodo_agenda(deslocamento: int):
        data = agenda_estado["data"]
        modo = agenda_estado["modo"]
        if modo == "Dia":
            data += timedelta(days=deslocamento)
        elif modo == "Semana":
            data += timedelta(days=7 * deslocamento)
        else:
            mes = data.month - 1 + deslocamento
            ano = data.year + mes // 12
            novo_mes = mes % 12 + 1
            ultimo_dia = calendar.monthrange(ano, novo_mes)[1]
            data = date(ano, novo_mes, min(data.day, ultimo_dia))
        agenda_estado["data"] = data
        renderizar(1)

    def voltar_hoje_agenda(evento):
        agenda_estado["data"] = date.today()
        renderizar(1)

    def selecionar_dia_agenda(dia: int):
        data = agenda_estado["data"]
        agenda_estado["data"] = date(data.year, data.month, dia)
        agenda_estado["modo"] = "Dia"
        renderizar(1)

    def abrir_pesquisa_agenda(evento):
        agenda_estado["pesquisa_aberta"] = True
        renderizar(1)

    def registrar_busca(evento):
        agenda_estado["busca_rascunho"] = evento.control.value or ""

    def aplicar_busca_agenda(evento):
        agenda_estado["busca"] = agenda_estado["busca_rascunho"].strip()
        renderizar(1)

    def limpar_busca_agenda(evento):
        agenda_estado["busca"] = ""
        agenda_estado["busca_rascunho"] = ""
        agenda_estado["pesquisa_aberta"] = False
        renderizar(1)

    def agendamento_indisponivel(evento):
        if dados_estabelecimento and dados_estabelecimento.get(
            "onboarding_completed"
        ) and abrir_agendamento is not None:
            indice = (
                page.navigation_bar.selected_index
                if page.navigation_bar is not None else 0
            )
            dia = (
                agenda_estado["data"] if indice == 1
                else dia_visivel["data"]
            )
            page.run_task(abrir_agendamento, dia)
        elif dados_estabelecimento and dados_estabelecimento.get(
            "onboarding_completed"
        ):
            mostrar_aviso(
                "O cadastro de agendamentos estará disponível no APK."
            )
        else:
            mostrar_aviso(
                "Conclua as cinco etapas de configuração "
                "do estabelecimento para continuar."
            )

    def criar_agenda():
        """Agenda visual sem agendamentos fictícios nem dados públicos."""
        modo = agenda_estado["modo"]
        data = agenda_estado["data"]
        inicio_semana = data - timedelta(days=data.weekday())
        fim_semana = inicio_semana + timedelta(days=6)
        if modo == "Dia":
            periodo = formatar_data(data)
        elif modo == "Semana":
            periodo = (
                f"{inicio_semana.day} {MESES_CURTOS[inicio_semana.month - 1]}"
                f" – {fim_semana.day} {MESES_CURTOS[fim_semana.month - 1]}"
            )
        else:
            periodo = f"{MESES[data.month - 1].capitalize()} {data.year}"

        controles = [
            ft.Row(
                spacing=6,
                controls=[
                    ft.Text(
                        "Agenda",
                        expand=True,
                        size=26,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.SEARCH,
                        tooltip="Pesquisar",
                        on_click=abrir_pesquisa_agenda,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.TUNE,
                        tooltip="Filtros avançados",
                        on_click=lambda _: mostrar_aviso(
                            "Use os filtros de status, profissional e serviço "
                            "disponíveis abaixo."
                        ),
                    ),
                    ft.IconButton(
                        icon=ft.Icons.ADD,
                        tooltip="Novo agendamento",
                        on_click=agendamento_indisponivel,
                    ),
                ],
            ),
            ft.Row(
                spacing=5,
                controls=[
                    ft.Container(
                        expand=True,
                        content=ft.Button(
                            nome,
                            expand=True,
                            bgcolor=("#EAEAEA" if nome == modo else CARTAO),
                            color=("#161616" if nome == modo else "#C6C6C6"),
                            on_click=lambda _, selecionado=nome: mudar_modo_agenda(
                                selecionado
                            ),
                        ),
                    )
                    for nome in ("Dia", "Semana", "Mês")
                ],
            ),
            ft.Row(
                spacing=0,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(
                        expand=True,
                        content=ft.Text(
                            periodo,
                            size=14,
                            weight=ft.FontWeight.W_500,
                        ),
                    ),
                    ft.IconButton(
                        icon=ft.Icons.CHEVRON_LEFT,
                        tooltip="Período anterior",
                        on_click=lambda _: mudar_periodo_agenda(-1),
                    ),
                    ft.Button(
                        "Hoje",
                        bgcolor=CARTAO,
                        color="#EAEAEA",
                        on_click=voltar_hoje_agenda,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.CHEVRON_RIGHT,
                        tooltip="Próximo período",
                        on_click=lambda _: mudar_periodo_agenda(1),
                    ),
                ],
            ),
            ft.Row(
                spacing=12,
                controls=[
                    ft.Text("Status", size=13, color=TEXTO_SECUNDARIO),
                    ft.Dropdown(
                        expand=True,
                        value=agenda_estado["filtro_status"],
                        options=[
                            ft.DropdownOption(key=chave, text=rotulo)
                            for chave, rotulo in FILTROS_STATUS
                        ],
                        bgcolor=CARTAO,
                        border_color="#3D3D3D",
                        on_select=selecionar_status_agenda,
                    ),
                ],
            ),
            ft.Row(
                spacing=12,
                controls=[
                    ft.Text("Profissional", size=13, color=TEXTO_SECUNDARIO),
                    ft.Dropdown(
                        expand=True,
                        value=agenda_estado["filtro_profissional"],
                        options=opcoes_filtro_agenda("professional"),
                        bgcolor=CARTAO,
                        border_color="#3D3D3D",
                        on_select=selecionar_profissional_agenda,
                    ),
                ],
            ),
            ft.Row(
                spacing=12,
                controls=[
                    ft.Text("Serviço", size=13, color=TEXTO_SECUNDARIO),
                    ft.Dropdown(
                        expand=True,
                        value=agenda_estado["filtro_servico"],
                        options=opcoes_filtro_agenda("service"),
                        bgcolor=CARTAO,
                        border_color="#3D3D3D",
                        on_select=selecionar_servico_agenda,
                    ),
                ],
            ),
        ]

        if agenda_estado["pesquisa_aberta"]:
            controles.append(
                ft.Column(
                    spacing=3,
                    controls=[
                        ft.Row(
                            spacing=4,
                            controls=[
                                ft.TextField(
                                    expand=True,
                                    label="Buscar por nome do cliente",
                                    hint_text="Ex.: Maria",
                                    value=agenda_estado["busca_rascunho"],
                                    on_change=registrar_busca,
                                    on_submit=aplicar_busca_agenda,
                                    text_size=14,
                                    border_color="#3D3D3D",
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.SEARCH,
                                    tooltip="Aplicar pesquisa",
                                    on_click=aplicar_busca_agenda,
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.CLOSE,
                                    tooltip="Limpar pesquisa",
                                    on_click=limpar_busca_agenda,
                                ),
                            ],
                        ),
                        ft.Text(
                            "Digite um nome e toque na lupa ou em buscar no teclado.",
                            size=11,
                            color=TEXTO_SECUNDARIO,
                        ),
                    ],
                )
            )

        carregando = agenda_consulta["carregando"]
        erro = agenda_consulta["erro"]
        if erro and buscar_agendamentos is not None:
            controles.append(ft.Text(erro, size=12, color="#F3B5B5"))
        elif carregando and buscar_agendamentos is not None:
            controles.append(
                ft.Text(
                    "Carregando agenda do Supabase...",
                    size=12, color=TEXTO_SECUNDARIO,
                )
            )

        if modo == "Mês":
            controles.append(
                ft.Container(
                    bgcolor=CARTAO,
                    border_radius=16,
                    padding=10,
                    content=ft.Column(
                        spacing=3,
                        tight=True,
                        controls=[
                            ft.Row(
                                spacing=0,
                                controls=[
                                    ft.Container(
                                        expand=True,
                                        content=ft.Text(
                                            nome, text_align=ft.TextAlign.CENTER,
                                            size=11, color=TEXTO_SECUNDARIO,
                                        ),
                                    )
                                    for nome in DIAS_CURTOS
                                ],
                            ),
                            *[
                                ft.Row(
                                    spacing=0,
                                    controls=[
                                        ft.Container(
                                            expand=True,
                                            height=38,
                                            padding=8,
                                            border_radius=9,
                                            bgcolor=(
                                                "#3E3E3E" if numero == data.day
                                                else "transparent"
                                            ),
                                            content=ft.Text(
                                                str(numero) if numero else "",
                                                size=12,
                                                text_align=ft.TextAlign.CENTER,
                                                color="#EAEAEA" if numero else "#666666",
                                            ),
                                            on_click=(
                                                (lambda _, dia=numero:
                                                    selecionar_dia_agenda(dia))
                                                if numero else None
                                            ),
                                        )
                                        for numero in semana
                                    ],
                                )
                                for semana in calendar.monthcalendar(
                                    data.year, data.month
                                )
                            ],
                        ],
                    ),
                )
            )
            if not carregando and not erro:
                quantidade = len(reservas_filtradas())
                controles.append(ft.Text(
                    f"{quantidade} agendamento(s) neste mês. "
                    "Toque em um dia para ver detalhes.",
                    size=12, color=TEXTO_SECUNDARIO,
                ))
        elif modo == "Semana":
            for deslocamento in range(7):
                dia = inicio_semana + timedelta(days=deslocamento)
                quantidade = len(reservas_filtradas_no_dia(dia))
                controles.append(
                    ft.Container(
                        bgcolor=CARTAO,
                        border_radius=12,
                        padding=13,
                        content=ft.Row(
                            controls=[
                                ft.Text(
                                    f"{DIAS_CURTOS[dia.weekday()]}, {dia.day}",
                                    size=14, weight=ft.FontWeight.BOLD,
                                ),
                                ft.Container(expand=True),
                                ft.Text(
                                    f"{quantidade} agendamento(s)"
                                    if not carregando and not erro else "Carregando",
                                    size=12, color=TEXTO_SECUNDARIO,
                                ),
                            ],
                        ),
                        on_click=lambda _, escolhido=dia:
                            abrir_dia_agenda(escolhido),
                    )
                )
        else:
            reservas = reservas_filtradas_no_dia(data)
            if not carregando and not erro and reservas:
                controles.extend(cartao_reserva(r) for r in reservas)
            elif not carregando and not erro:
                controles.append(
                    ft.Container(
                        bgcolor=CARTAO,
                        border_radius=14,
                        padding=18,
                        content=ft.Column(
                            tight=True,
                            spacing=8,
                            controls=[
                                ft.Icon(
                                    ft.Icons.EVENT_AVAILABLE,
                                    size=22, color="#A8A8A8",
                                ),
                                ft.Text(
                                    (
                                        "Nenhum agendamento encontrado para este cliente."
                                        if agenda_estado["busca"]
                                        else "Nenhum agendamento neste dia."
                                        if all(
                                            agenda_estado[chave] == "todos"
                                            for chave in (
                                                "filtro_status",
                                                "filtro_profissional",
                                                "filtro_servico",
                                            )
                                        )
                                        else "Nenhum agendamento com estes filtros."
                                    ),
                                    size=15, weight=ft.FontWeight.BOLD,
                                ),
                                ft.Text(
                                    (
                                        "Altere o nome pesquisado ou os filtros."
                                        if agenda_estado["busca"]
                                        else "Toque em + para criar um atendimento."
                                        if all(
                                            agenda_estado[chave] == "todos"
                                            for chave in (
                                                "filtro_status",
                                                "filtro_profissional",
                                                "filtro_servico",
                                            )
                                        )
                                        else "Altere os filtros para ver outros atendimentos."
                                    ),
                                    size=12, color=TEXTO_SECUNDARIO,
                                ),
                            ],
                        ),
                    )
                )

        return controles

    def abrir_dia_agenda(dia: date):
        agenda_estado["data"] = dia
        agenda_estado["modo"] = "Dia"
        renderizar(1)


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
        # Evita quebra de linha em telas pequenas do Android.
        if (page.width or 360) < 500:
            return f"{DIAS_CURTOS[valor.weekday()]}, {valor.day} {MESES_CURTOS[valor.month - 1]}"
        return (
            f"{DIAS_SEMANA[valor.weekday()]}, {valor.day} "
            f"de {MESES[valor.month - 1]}"
        )

    def resumo(numero: str, legenda: str):
        return ft.Column(
            expand=True,
            spacing=4,
            controls=[
                ft.Text(
                    numero,
                    size=28,
                    weight=ft.FontWeight.BOLD,
                ),
                ft.Text(
                    legenda,
                    size=12,
                    color=TEXTO_SECUNDARIO,
                ),
            ],
        )

    # Dados de demonstração mantidos somente em memória nesta sessão.
    # Não são compartilhados com o Supabase ou persistidos no navegador.
    clientes = []
    clientes_estado = {
        "pesquisa": "",
        "filtro": "Ativos",
        "ordenacao": "A–Z",
        "limite": 20,
        "proximo_id": 1,
    }
    clientes_lista = {"controle": None}
    clientes_contagem = {"controle": None}
    clientes_estado["carregando"] = False
    FILTROS_CLIENTES = (
        "Ativos",
        "Arquivados",
        "Agendamento futuro",
        "Sem histórico",
    )
    ORDENACOES_CLIENTES = (
        "A–Z",
        "Z–A",
        "Cadastro recente",
        "Última atividade",
        "Mais atendimentos",
    )

    async def carregar_clientes_autenticados():
        """Atualiza somente os dados da conta autenticada (sem mock)."""
        if buscar_clientes is None or clientes_estado["carregando"]:
            return
        clientes_estado["carregando"] = True
        try:
            linhas = await buscar_clientes()
            clientes[:] = [
                {
                    "id": item["id"],
                    "nome": item.get("name") or "",
                    "telefone": item.get("phone") or "",
                    "email": item.get("email") or "",
                    "observacoes": item.get("notes") or "",
                    "arquivado": bool(item.get("is_archived")),
                    "atendimentos": 0,
                    "criado_em": item.get("created_at") or "",
                    "ultima_atividade": item.get("updated_at") or "",
                }
                for item in linhas
            ]
            atualizar_lista_clientes()
        except Exception as falha:
            clientes.clear()
            atualizar_lista_clientes()
            mostrar_aviso(str(falha))
        finally:
            clientes_estado["carregando"] = False

    def iniciais_cliente(nome: str) -> str:
        partes = nome.split()
        if not partes:
            return "?"
        if len(partes) == 1:
            return partes[0][:2].upper()
        return (partes[0][0] + partes[-1][0]).upper()

    def selecionar_filtro_cliente(nome: str):
        clientes_estado["filtro"] = nome
        clientes_estado["limite"] = 20
        renderizar(2)

    def selecionar_ordenacao_cliente(nome: str):
        clientes_estado["ordenacao"] = nome
        clientes_estado["limite"] = 20
        renderizar(2)

    def pesquisar_cliente(evento):
        clientes_estado["pesquisa"] = evento.control.value or ""
        clientes_estado["limite"] = 20
        atualizar_lista_clientes()

    def clientes_visiveis():
        termo = clientes_estado["pesquisa"].strip().casefold()
        filtro = clientes_estado["filtro"]
        encontrados = []
        for cliente in clientes:
            if filtro == "Ativos" and cliente["arquivado"]:
                continue
            if filtro == "Arquivados" and not cliente["arquivado"]:
                continue
            if filtro == "Agendamento futuro":
                continue  # Agenda real ainda não foi conectada.
            if filtro == "Sem histórico" and cliente["atendimentos"] > 0:
                continue
            campos = (
                cliente["nome"],
                cliente["telefone"],
                cliente["email"],
            )
            if termo and not any(termo in valor.casefold() for valor in campos):
                continue
            encontrados.append(cliente)
        ordem = clientes_estado["ordenacao"]
        if ordem == "A–Z":
            encontrados.sort(key=lambda c: c["nome"].casefold())
        elif ordem == "Z–A":
            encontrados.sort(key=lambda c: c["nome"].casefold(), reverse=True)
        elif ordem == "Cadastro recente":
            encontrados.sort(
                key=lambda c: str(c["criado_em"]), reverse=True
            )
        elif ordem == "Última atividade":
            encontrados.sort(key=lambda c: c["ultima_atividade"], reverse=True)
        elif ordem == "Mais atendimentos":
            encontrados.sort(key=lambda c: c["atendimentos"], reverse=True)
        return encontrados

    def estado_vazio_clientes():
        """Centraliza mensagem e ícone mesmo em telas Android estreitas."""
        tem_clientes = bool(clientes)
        titulo = (
            "Nenhum cliente encontrado"
            if tem_clientes else "Nenhum cliente cadastrado"
        )
        descricao = (
            "Tente outra busca ou ajuste os filtros."
            if tem_clientes
            else "Cadastre seu primeiro cliente para começar."
        )
        return ft.Container(
            alignment=ft.Alignment.CENTER,
            padding=ft.Padding.only(top=42, bottom=40, left=8, right=8),
            content=ft.Column(
                tight=True,
                spacing=9,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(
                        ft.Icons.PEOPLE_OUTLINE,
                        size=37,
                        color=TEXTO_SECUNDARIO,
                    ),
                    ft.Text(
                        titulo,
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        descricao,
                        size=12,
                        color=TEXTO_SECUNDARIO,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
            ),
        )

    def atualizar_lista_clientes():
        lista = clientes_lista["controle"]
        if lista is None:
            return
        encontrados = clientes_visiveis()
        exibidos = encontrados[:clientes_estado["limite"]]
        controles = []
        if not encontrados:
            controles.append(estado_vazio_clientes())
        for cliente in exibidos:
            nome = cliente["nome"]
            identificador = cliente["id"]
            subtitulo = cliente["telefone"] or cliente["email"] or "Sem contato"
            controles.append(
                ft.Container(
                    padding=ft.Padding.symmetric(vertical=10, horizontal=4),
                    on_click=lambda _, cid=identificador: abrir_detalhes_cliente(cid),
                    content=ft.Row(
                        spacing=12,
                        controls=[
                            ft.Container(
                                width=38,
                                height=38,
                                alignment=ft.Alignment.CENTER,
                                bgcolor="#272727",
                                border_radius=20,
                                content=ft.Text(
                                    iniciais_cliente(nome),
                                    size=12,
                                    weight=ft.FontWeight.BOLD,
                                ),
                            ),
                            ft.Column(
                                expand=True,
                                spacing=2,
                                tight=True,
                                controls=[
                                    ft.Text(
                                        nome,
                                        size=14,
                                        weight=ft.FontWeight.W_500,
                                    ),
                                    ft.Text(
                                        subtitulo,
                                        size=12,
                                        color=TEXTO_SECUNDARIO,
                                    ),
                                ],
                            ),
                            ft.Icon(
                                ft.Icons.CHEVRON_RIGHT,
                                size=17,
                                color=TEXTO_SECUNDARIO,
                            ),
                        ],
                    ),
                )
            )
            controles.append(ft.Divider(height=1, color="#2C2C2C"))
        if len(encontrados) > clientes_estado["limite"]:
            controles.append(
                ft.TextButton(
                    "Mostrar mais 20",
                    on_click=mostrar_mais_clientes,
                )
            )
        lista.controls = controles
        contagem = clientes_contagem["controle"]
        if contagem is not None:
            contagem.value = f"{len(encontrados)} " + (
                "cliente" if len(encontrados) == 1 else "clientes"
            )
        page.update()

    def mostrar_mais_clientes(evento):
        clientes_estado["limite"] += 20
        atualizar_lista_clientes()

    def criar_clientes_ui():
        busca = ft.TextField(
            value=clientes_estado["pesquisa"],
            hint_text="Buscar nome, telefone ou e-mail",
            prefix_icon=ft.Icons.SEARCH,
            bgcolor=CARTAO,
            border_color="#333333",
            text_size=14,
            on_change=pesquisar_cliente,
        )
        lista = ft.Column(spacing=0, tight=True)
        clientes_lista["controle"] = lista
        encontrados = clientes_visiveis()
        contagem_texto = ft.Text(
            f"{len(encontrados)} " +
            ("cliente" if len(encontrados) == 1 else "clientes"),
            size=12,
            color=TEXTO_SECUNDARIO,
        )
        clientes_contagem["controle"] = contagem_texto
        # O contêiner vazio usa a mesma centralização do filtro de busca.
        lista.controls = [estado_vazio_clientes()] if not encontrados else []
        return [
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text(
                        "Clientes",
                        size=26,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Button(
                        "Novo cliente",
                        icon=ft.Icons.ADD,
                        bgcolor="#F0F0F0",
                        color="#161616",
                        on_click=lambda _: abrir_form_cliente(),
                    ),
                ],
            ),
            busca,
            ft.Row(
                spacing=7,
                run_spacing=6,
                wrap=True,
                controls=[
                    *[
                        ft.Button(
                            titulo,
                            bgcolor=(
                                "#EAEAEA"
                                if clientes_estado["filtro"] == titulo
                                else CARTAO
                            ),
                            color=(
                                "#181818"
                                if clientes_estado["filtro"] == titulo
                                else "#D0D0D0"
                            ),
                            on_click=lambda _, filtro=titulo:
                                selecionar_filtro_cliente(filtro),
                        )
                        for titulo in ("Ativos", "Arquivados")
                    ],
                    ft.PopupMenuButton(
                        bgcolor="#242424",
                        content=ft.Container(
                            bgcolor=(
                                "#EAEAEA"
                                if clientes_estado["filtro"] not in
                                ("Ativos", "Arquivados") else CARTAO
                            ),
                            border_radius=22,
                            padding=ft.Padding.symmetric(
                                horizontal=12, vertical=10
                            ),
                            content=ft.Row(
                                spacing=3,
                                tight=True,
                                controls=[
                                    ft.Text(
                                        (
                                            clientes_estado["filtro"]
                                            if clientes_estado["filtro"] not in
                                            ("Ativos", "Arquivados")
                                            else "Mais filtros"
                                        ),
                                        size=12,
                                        color=(
                                            "#181818"
                                            if clientes_estado["filtro"] not in
                                            ("Ativos", "Arquivados")
                                            else "#D0D0D0"
                                        ),
                                    ),
                                    ft.Icon(
                                        ft.Icons.ARROW_DROP_DOWN,
                                        size=16,
                                        color="#777777",
                                    ),
                                ],
                            ),
                        ),
                        items=[
                            ft.PopupMenuItem(
                                content=titulo,
                                on_click=lambda _, filtro=titulo:
                                    selecionar_filtro_cliente(filtro),
                            )
                            for titulo in FILTROS_CLIENTES
                        ],
                    ),
                ],
            ),
            ft.Row(
                spacing=5,
                controls=[
                    ft.Text(
                        "Ordenar:",
                        size=13,
                        color=TEXTO_SECUNDARIO,
                    ),
                    ft.PopupMenuButton(
                        content=ft.Row(
                            spacing=4,
                            controls=[
                                ft.Text(
                                    clientes_estado["ordenacao"],
                                    size=13,
                                ),
                                ft.Icon(ft.Icons.ARROW_DROP_DOWN, size=19),
                            ],
                        ),
                        items=[
                            ft.PopupMenuItem(
                                content=ordenacao,
                                on_click=lambda _, escolhida=ordenacao:
                                    selecionar_ordenacao_cliente(escolhida),
                            )
                            for ordenacao in ORDENACOES_CLIENTES
                        ],
                    ),
                    ft.Container(expand=True),
                    contagem_texto,
                ],
            ),
            ft.Divider(height=2, color="#2A2A2A"),
            lista,
            ft.Text(
                "Cadastros privados armazenados no Supabase."
                if buscar_clientes is not None else
                "PRÉVIA: cadastros temporários, não salvos. "
                "Não utilize dados reais de clientes.",
                size=11,
                color=TEXTO_SECUNDARIO,
            ),
        ]

    def buscar_cliente_por_id(cid):
        return next((c for c in clientes if c["id"] == cid), None)

    def abrir_form_cliente(cliente_id=None):
        cliente = buscar_cliente_por_id(cliente_id) if cliente_id else None
        nome = ft.TextField(
            label="Nome *",
            value=cliente["nome"] if cliente else "",
            autofocus=True,
            dense=True,
            text_size=14,
            bgcolor=CARTAO,
            border_color="#393939",
            focused_border_color="#BDBDBD",
            border_radius=10,
            content_padding=ft.Padding.symmetric(horizontal=14, vertical=12),
        )
        telefone = ft.TextField(
            label="Telefone com DDD (opcional)",
            hint_text="(11) 99999-9999",
            keyboard_type=ft.KeyboardType.PHONE,
            value=cliente["telefone"] if cliente else "",
            dense=True,
            text_size=14,
            bgcolor=CARTAO,
            border_color="#393939",
            focused_border_color="#BDBDBD",
            border_radius=10,
            content_padding=ft.Padding.symmetric(horizontal=14, vertical=12),
        )
        email = ft.TextField(
            label="E-mail (opcional)",
            keyboard_type=ft.KeyboardType.EMAIL,
            value=cliente["email"] if cliente else "",
            dense=True,
            text_size=14,
            bgcolor=CARTAO,
            border_color="#393939",
            focused_border_color="#BDBDBD",
            border_radius=10,
            content_padding=ft.Padding.symmetric(horizontal=14, vertical=12),
        )
        observacoes = ft.TextField(
            label="Observações (opcional)",
            multiline=True,
            min_lines=2,
            max_lines=3,
            value=cliente["observacoes"] if cliente else "",
            dense=True,
            text_size=14,
            bgcolor=CARTAO,
            border_color="#393939",
            focused_border_color="#BDBDBD",
            border_radius=10,
            content_padding=ft.Padding.symmetric(horizontal=14, vertical=11),
        )
        erro = ft.Text("", color="#F0B5B5", size=12)

        async def salvar(evento):
            novo_nome = (nome.value or "").strip()
            novo_telefone = (telefone.value or "").strip()
            digitos = "".join(c for c in novo_telefone if c.isdigit())
            # Aceita código brasileiro +55 quando informado.
            if digitos.startswith("55") and len(digitos) in (12, 13):
                digitos = digitos[2:]
            if digitos and len(digitos) not in (10, 11):
                erro.value = "Telefone deve ter DDD e 10 ou 11 dígitos."
                page.update()
                return
            if digitos:
                ddd, numero = digitos[:2], digitos[2:]
                separador = 5 if len(numero) == 9 else 4
                novo_telefone = (
                    f"({ddd}) {numero[:separador]}-{numero[separador:]}"
                )
            else:
                novo_telefone = ""
            novo_email = (email.value or "").strip()
            if not novo_nome:
                erro.value = "Informe o nome do cliente."
                page.update()
                return
            if novo_email and (
                "@" not in novo_email or "." not in novo_email.split("@")[-1]
            ):
                erro.value = "Informe um e-mail válido."
                page.update()
                return
            duplicado = any(
                outro["id"] != cliente_id
                and (
                    outro["nome"].casefold() == novo_nome.casefold()
                    or (
                        novo_email
                        and outro["email"].casefold() == novo_email.casefold()
                    )
                    or (
                        novo_telefone
                        and outro["telefone"] == novo_telefone
                    )
                )
                for outro in clientes
            )
            if duplicado:
                erro.value = (
                    "Possível cadastro duplicado. Confira nome, "
                    "telefone ou e-mail antes de salvar."
                )
                page.update()
                return
            if persistir_cliente is not None:
                try:
                    await persistir_cliente(
                        {
                            "name": novo_nome,
                            "phone": novo_telefone,
                            "email": novo_email,
                            "notes": observacoes.value or "",
                        },
                        cliente_id,
                    )
                except Exception as falha:
                    erro.value = str(falha)
                    page.update()
                    return
                page.pop_dialog()
                await carregar_clientes_autenticados()
                mostrar_aviso("Cliente salvo no Supabase.")
                return
            if cliente:
                cliente.update(
                    nome=novo_nome,
                    telefone=novo_telefone,
                    email=novo_email,
                    observacoes=observacoes.value or "",
                    ultima_atividade=clientes_estado["proximo_id"],
                )
            else:
                identificador = clientes_estado["proximo_id"]
                clientes.append({
                    "id": identificador,
                    "nome": novo_nome,
                    "telefone": novo_telefone,
                    "email": novo_email,
                    "observacoes": observacoes.value or "",
                    "arquivado": False,
                    "atendimentos": 0,
                    "criado_em": date.today(),
                    "ultima_atividade": identificador,
                })
                clientes_estado["proximo_id"] += 1
            page.pop_dialog()
            renderizar(2)
            mostrar_aviso("Cadastro temporário salvo nesta prévia.")

        page.show_dialog(
            ft.BottomSheet(
                scrollable=True,
                show_drag_handle=True,
                bgcolor=FUNDO,
                content=ft.Container(
                    padding=16,
                    content=ft.Column(
                        tight=True,
                        spacing=10,
                        controls=[
                            ft.Text(
                                "Editar cliente" if cliente else "Novo cliente",
                                size=21,
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Text(
                                "Dados privados, salvos na sua conta."
                                if persistir_cliente is not None else
                                "Dados de demonstração: não serão enviados "
                                "ao Supabase.",
                                size=12,
                                color=TEXTO_SECUNDARIO,
                            ),
                            nome,
                            telefone,
                            email,
                            observacoes,
                            erro,
                            ft.Row(
                                alignment=ft.MainAxisAlignment.END,
                                controls=[
                                    ft.TextButton(
                                        "Cancelar",
                                        on_click=lambda _: page.pop_dialog(),
                                    ),
                                    ft.Button(
                                        "Salvar",
                                        bgcolor="#F0F0F0",
                                        color="#181818",
                                        on_click=salvar,
                                    ),
                                ],
                            ),
                        ],
                    ),
                ),
            )
        )

    def abrir_detalhes_cliente(cid):
        cliente = buscar_cliente_por_id(cid)
        if not cliente:
            return

        def acao_editar(evento):
            page.pop_dialog()
            abrir_form_cliente(cid)

        async def acao_arquivar(evento):
            if alterar_arquivo_cliente is not None:
                try:
                    await alterar_arquivo_cliente(
                        cid, not cliente["arquivado"]
                    )
                except Exception as falha:
                    mostrar_aviso(str(falha))
                    return
                page.pop_dialog()
                await carregar_clientes_autenticados()
                mostrar_aviso("Status do cliente atualizado no Supabase.")
                return
            cliente["arquivado"] = not cliente["arquivado"]
            page.pop_dialog()
            renderizar(2)
            mostrar_aviso(
                "Cliente reativado nesta prévia."
                if not cliente["arquivado"]
                else "Cliente arquivado nesta prévia."
            )

        def confirmar_exclusao(evento):
            page.pop_dialog()
            page.show_dialog(
                ft.AlertDialog(
                    modal=True,
                    title=ft.Text("Excluir cadastro de cliente?"),
                    content=ft.Text(
                        "Esta ação apaga definitivamente o cadastro. "
                        "Se houver agendamentos vinculados, "
                        "a exclusão será impedida."
                        if remover_cliente_real is not None else
                        "Esta ação apaga definitivamente este cadastro "
                        "temporário. Deseja continuar?"
                    ),
                    actions=[
                        ft.TextButton(
                            "Cancelar",
                            on_click=lambda _: page.pop_dialog(),
                        ),
                        ft.Button(
                            "Excluir",
                            bgcolor="#3D2424",
                            color="#F3DADA",
                            on_click=remover_cliente,
                        ),
                    ],
                )
            )

        async def remover_cliente(evento):
            if remover_cliente_real is not None:
                try:
                    await remover_cliente_real(cid)
                except Exception as falha:
                    mostrar_aviso(str(falha))
                    return
                page.pop_dialog()
                await carregar_clientes_autenticados()
                mostrar_aviso("Cliente excluído do Supabase.")
                return
            clientes[:] = [c for c in clientes if c["id"] != cid]
            page.pop_dialog()
            renderizar(2)
            mostrar_aviso("Cadastro de demonstração excluído.")

        def linha_contato(icone, legenda, valor):
            return ft.Row(
                spacing=11,
                controls=[
                    ft.Icon(icone, size=19, color="#AFAFAF"),
                    ft.Column(
                        tight=True,
                        expand=True,
                        spacing=2,
                        controls=[
                            ft.Text(
                                legenda,
                                size=11,
                                color=TEXTO_SECUNDARIO,
                            ),
                            ft.Text(
                                valor or "Não informado",
                                size=14,
                            ),
                        ],
                    ),
                ],
            )

        def pequeno_indicador(rotulo, valor):
            return ft.Container(
                expand=True,
                padding=12,
                bgcolor=CARTAO,
                border_radius=12,
                content=ft.Column(
                    spacing=6,
                    tight=True,
                    controls=[
                        ft.Text(
                            valor,
                            size=19,
                            weight=ft.FontWeight.BOLD,
                        ),
                        ft.Text(
                            rotulo,
                            size=11,
                            color=TEXTO_SECUNDARIO,
                        ),
                    ],
                ),
            )

        cabecalho_cliente = ft.Row(
            spacing=14,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    width=62,
                    height=62,
                    border_radius=32,
                    bgcolor="#303030",
                    alignment=ft.Alignment.CENTER,
                    content=ft.Text(
                        iniciais_cliente(cliente["nome"]),
                        size=21,
                        weight=ft.FontWeight.BOLD,
                    ),
                ),
                ft.Column(
                    expand=True,
                    spacing=5,
                    tight=True,
                    controls=[
                        ft.Text(
                            cliente["nome"],
                            size=23,
                            weight=ft.FontWeight.BOLD,
                        ),
                        ft.Text(
                            "Arquivado" if cliente["arquivado"] else "Cliente ativo",
                            size=12,
                            color=TEXTO_SECUNDARIO,
                        ),
                    ],
                ),
                ft.PopupMenuButton(
                    icon=ft.Icons.MORE_HORIZ,
                    icon_color="#D0D0D0",
                    tooltip="Mais opções",
                    items=[
                        ft.PopupMenuItem(
                            content=(
                                "Reativar"
                                if cliente["arquivado"] else "Arquivar"
                            ),
                            on_click=acao_arquivar,
                        ),
                        ft.PopupMenuItem(
                            content="Excluir",
                            on_click=confirmar_exclusao,
                        ),
                    ],
                ),
            ],
        )

        controles = [
            cabecalho_cliente,
            ft.Container(
                bgcolor=CARTAO,
                border_radius=13,
                padding=14,
                content=ft.Column(
                    tight=True,
                    spacing=14,
                    controls=[
                        linha_contato(
                            ft.Icons.PHONE_OUTLINED,
                            "Telefone",
                            cliente["telefone"],
                        ),
                        ft.Divider(height=1, color="#363636"),
                        linha_contato(
                            ft.Icons.MAIL_OUTLINE,
                            "E-mail",
                            cliente["email"],
                        ),
                    ],
                ),
            ),
            ft.Row(
                spacing=9,
                controls=[
                    pequeno_indicador(
                        "Concluídos",
                        str(cliente["atendimentos"]),
                    ),
                    pequeno_indicador("Próxima reserva", "—"),
                    pequeno_indicador("Último atendimento", "—"),
                ],
            ),
            ft.Row(
                controls=[
                    ft.Container(
                        expand=True,
                        bgcolor=CARTAO,
                        border_radius=13,
                        padding=14,
                        content=ft.Column(
                            tight=True,
                            spacing=6,
                            controls=[
                                ft.Text(
                                    "Observações",
                                    size=13,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                ft.Text(
                                    cliente["observacoes"] or "Nenhuma observação.",
                                    size=13,
                                    color=TEXTO_SECUNDARIO,
                                ),
                            ],
                        ),
                    ),
                ],
            ),
            ft.Row(
                spacing=9,
                controls=[
                    ft.Button(
                        "Novo agendamento",
                        expand=2,
                        icon=ft.Icons.ADD,
                        bgcolor="#F0F0F0",
                        color="#171717",
                        on_click=agendamento_indisponivel,
                    ),
                    ft.Button(
                        "Editar",
                        expand=1,
                        icon=ft.Icons.EDIT_OUTLINED,
                        bgcolor="#292929",
                        color="#E2E2E2",
                        on_click=acao_editar,
                    ),
                ],
            ),
            ft.TextButton(
                "Ver histórico completo",
                on_click=lambda _: mostrar_aviso(
                    "O histórico de atendimentos será exibido "
                    "quando conectarmos a agenda ao Supabase."
                ),
            ),
            ft.Text(
                "Ficha salva no Supabase."
                if buscar_clientes is not None else
                "PRÉVIA: informações de teste não são persistidas.",
                size=11,
                color=TEXTO_SECUNDARIO,
            ),
        ]
        page.show_dialog(
            ft.BottomSheet(
                scrollable=True,
                show_drag_handle=True,
                bgcolor=FUNDO,
                content=ft.Container(
                    padding=16,
                    content=ft.Column(
                        spacing=13,
                        tight=True,
                        controls=controles,
                    ),
                ),
            )
        )

    # A aba Mais agrupa as áreas aprovadas do aplicativo.
    # A prévia visual não usa credenciais ou dados do Supabase.
    mais_estado = {"pagina": None}

    MAIS_GRUPOS = (
        (
            "ATENDIMENTO E AGENDA",
            (
                ("Serviços", ft.Icons.DESIGN_SERVICES_OUTLINED,
                 "Catálogo, preços e duração"),
                ("Profissionais", ft.Icons.PEOPLE_OUTLINE,
                 "Equipe e especialidades"),
                ("Horários e bloqueios", ft.Icons.SCHEDULE,
                 "Horários, pausas e folgas"),
            ),
        ),
        (
            "GESTÃO",
            (
                ("Relatórios", ft.Icons.BAR_CHART_OUTLINED,
                 "Indicadores e desempenho"),
                ("Equipe e permissões", ft.Icons.ADMIN_PANEL_SETTINGS_OUTLINED,
                 "Acessos e permissões"),
            ),
        ),
        (
            "CONFIGURAÇÕES",
            (
                ("Preferências", ft.Icons.TUNE,
                 "Aparência e ajustes"),
                ("Minha conta", ft.Icons.ACCOUNT_CIRCLE_OUTLINED,
                 "Perfil e segurança"),
                ("Ajuda e sobre", ft.Icons.HELP_OUTLINE,
                 "Ajuda e informações do app"),
            ),
        ),
    )

    def abrir_area_mais(nome: str):
        if nome == "Profissionais" and abrir_profissionais is not None:
            page.run_task(abrir_profissionais)
            return
        if nome == "Serviços" and abrir_servicos is not None:
            page.run_task(abrir_servicos)
            return
        if nome == "Horários e bloqueios" and abrir_horarios is not None:
            if dados_estabelecimento and dados_estabelecimento.get("id"):
                page.run_task(abrir_horarios)
                return
        mais_estado["pagina"] = nome
        renderizar(3)

    def voltar_mais(evento):
        mais_estado["pagina"] = None
        renderizar(3)

    def linha_area_mais(nome: str, icone, descricao: str):
        return ft.Container(
            bgcolor=CARTAO,
            border_radius=10,
            padding=ft.Padding.symmetric(horizontal=12, vertical=10),
            on_click=lambda _, area=nome: abrir_area_mais(area),
            content=ft.Row(
                spacing=11,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(
                        width=38,
                        height=38,
                        bgcolor="#2B2B2B",
                        border_radius=12,
                        alignment=ft.Alignment.CENTER,
                        content=ft.Icon(icone, size=20, color="#E6E6E6"),
                    ),
                    ft.Column(
                        expand=True,
                        tight=True,
                        spacing=3,
                        controls=[
                            ft.Text(
                                nome,
                                size=14,
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Text(
                                descricao,
                                size=11,
                                color=TEXTO_SECUNDARIO,
                            ),
                        ],
                    ),
                    ft.Icon(
                        ft.Icons.CHEVRON_RIGHT,
                        size=20,
                        color="#8C8C8C",
                    ),
                ],
            ),
        )

    def criar_inicio_mais():
        itens = [
            ft.Text(
                "Mais",
                size=27,
                weight=ft.FontWeight.BOLD,
            ),
            ft.Text(
                "Gerencie seu estabelecimento e as configurações.",
                color=TEXTO_SECUNDARIO,
                size=13,
            ),
        ]
        for titulo, areas in MAIS_GRUPOS:
            itens.append(
                ft.Container(
                    padding=ft.Padding.only(top=10, bottom=3),
                    content=ft.Text(
                        titulo,
                        size=11,
                        weight=ft.FontWeight.W_500,
                        color=TEXTO_SECUNDARIO,
                    ),
                )
            )
            for nome, icone, descricao in areas:
                itens.append(linha_area_mais(nome, icone, descricao))
        itens.extend(
            [
                ft.Container(height=7),
                ft.Button(
                    "Sair da conta",
                    icon=ft.Icons.LOGOUT,
                    bgcolor="#292929",
                    color="#E2E2E2",
                    on_click=sair_da_conta,
                ),
                ft.Text(
                    "SchedulePro · Prévia de desenvolvimento",
                    color=TEXTO_SECUNDARIO,
                    text_align=ft.TextAlign.CENTER,
                    size=11,
                ),
            ]
        )
        return itens

    def criar_detalhe_mais(nome: str):
        descricoes = {
            "Serviços": (
                ft.Icons.DESIGN_SERVICES_OUTLINED,
                "Configure os serviços, preços e duração dos atendimentos.",
                "Nenhum serviço cadastrado",
            ),
            "Profissionais": (
                ft.Icons.PEOPLE_OUTLINE,
                "Cadastre os profissionais e vincule os serviços.",
                "Nenhum profissional cadastrado",
            ),
            "Horários e bloqueios": (
                ft.Icons.SCHEDULE,
                "Defina os horários de funcionamento, pausas e folgas.",
                "Horários ainda não configurados",
            ),
            "Relatórios": (
                ft.Icons.BAR_CHART_OUTLINED,
                "Acompanhe agendamentos, receitas e desempenho.",
                "Dados disponíveis após os primeiros agendamentos",
            ),
            "Equipe e permissões": (
                ft.Icons.ADMIN_PANEL_SETTINGS_OUTLINED,
                "Administre quem pode acessar cada função.",
                "Permissões ainda não configuradas",
            ),
            "Preferências": (
                ft.Icons.TUNE,
                "Personalize a experiência do SchedulePro.",
                "Opções de aparência e preferências em preparação",
            ),
            "Minha conta": (
                ft.Icons.ACCOUNT_CIRCLE_OUTLINED,
                "Gerencie as informações e a segurança da sua conta.",
                "Dados da conta disponíveis no aplicativo autenticado",
            ),
            "Ajuda e sobre": (
                ft.Icons.HELP_OUTLINE,
                "Encontre informações sobre o SchedulePro.",
                "Central de ajuda em preparação",
            ),
        }
        icone, descricao, estado = descricoes[nome]
        controles = [
            ft.Row(
                spacing=6,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.IconButton(
                        icon=ft.Icons.ARROW_BACK,
                        tooltip="Voltar para Mais",
                        on_click=voltar_mais,
                    ),
                    ft.Text(
                        nome,
                        size=21,
                        weight=ft.FontWeight.BOLD,
                        expand=True,
                    ),
                ],
            ),
            ft.Text(
                descricao,
                size=13,
                color=TEXTO_SECUNDARIO,
            ),
            ft.Container(
                padding=ft.Padding.symmetric(horizontal=18, vertical=29),
                bgcolor=CARTAO,
                border_radius=15,
                content=ft.Column(
                    tight=True,
                    spacing=12,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(
                            icone,
                            size=34,
                            color="#BFBFBF",
                        ),
                        ft.Text(
                            estado,
                            size=15,
                            weight=ft.FontWeight.BOLD,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Text(
                            "Esta área será conectada às funcionalidades "
                            "reais nas próximas etapas.",
                            color=TEXTO_SECUNDARIO,
                            size=12,
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ],
                ),
            ),
        ]
        if nome == "Minha conta":
            controles.append(
                ft.Button(
                    "Sair da conta",
                    icon=ft.Icons.LOGOUT,
                    bgcolor="#292929",
                    color="#E2E2E2",
                    on_click=sair_da_conta,
                )
            )
        return controles

    def criar_mais():
        pagina = mais_estado["pagina"]
        return criar_detalhe_mais(pagina) if pagina else criar_inicio_mais()

    def intervalo_consulta(indice):
        if indice == 0:
            dia = dia_visivel["data"]
            return dia, dia
        dia = agenda_estado["data"]
        if agenda_estado["modo"] == "Semana":
            inicio = dia - timedelta(days=dia.weekday())
            return inicio, inicio + timedelta(days=6)
        if agenda_estado["modo"] == "Mês":
            inicio = date(dia.year, dia.month, 1)
            fim = date(
                dia.year, dia.month,
                calendar.monthrange(dia.year, dia.month)[1],
            )
            return inicio, fim
        return dia, dia

    async def carregar_consulta(chave, sequencia):
        try:
            registros = await buscar_agendamentos(*chave)
            erro = None
        except Exception as falha:
            registros = []
            erro = str(falha)
        if sequencia != agenda_consulta["sequencia"]:
            return
        agenda_consulta["registros"] = registros
        agenda_consulta["carregando"] = False
        agenda_consulta["erro"] = erro
        if page.navigation_bar is not None:
            indice = page.navigation_bar.selected_index
            if indice in (0, 1):
                renderizar(indice)

    def garantir_consulta(indice):
        if buscar_agendamentos is None or not (
            dados_estabelecimento
            and dados_estabelecimento.get("onboarding_completed")
        ):
            return
        inicio, fim = intervalo_consulta(indice)
        chave = (inicio.isoformat(), fim.isoformat())
        if chave == agenda_consulta["chave"]:
            return
        agenda_consulta["chave"] = chave
        agenda_consulta["carregando"] = True
        agenda_consulta["erro"] = None
        agenda_consulta["registros"] = []
        agenda_consulta["sequencia"] += 1
        page.run_task(
            carregar_consulta, chave, agenda_consulta["sequencia"]
        )

    def renderizar(indice: int):
        if indice in (0, 1):
            garantir_consulta(indice)
        titulo = ABAS[indice][0]
        itens = []

        if indice == 0:
            itens.extend(
                [
                    ft.Text(
                        (
                            (dados_estabelecimento.get("name") or "").upper()
                            if dados_estabelecimento and
                            dados_estabelecimento.get("name")
                            else "ESTABELECIMENTO NÃO CONFIGURADO"
                        ),
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
                                color="#EDEDED",
                                bgcolor=CARTAO,
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
                        padding=ft.Padding.only(top=5, bottom=5),
                        content=ft.Row(
                            spacing=8,
                            controls=[
                                resumo(
                                    str(len(reservas_no_dia(dia_visivel["data"])))
                                    if not agenda_consulta["carregando"] else "—",
                                    "Agendamentos",
                                ),
                                resumo(
                                    str(sum(
                                        1 for r in reservas_no_dia(dia_visivel["data"])
                                        if r.get("status") == "scheduled"
                                    )) if not agenda_consulta["carregando"] else "—",
                                    "A confirmar",
                                ),
                                resumo(
                                    str(sum(
                                        1 for r in reservas_no_dia(dia_visivel["data"])
                                        if r.get("status") == "completed"
                                    )) if not agenda_consulta["carregando"] else "—",
                                    "Concluídos",
                                ),
                            ],
                        ),
                    ),
                    ft.Container(
                        bgcolor="#F1F1F1",
                        border_radius=14,
                        padding=13,
                        on_click=agendamento_indisponivel,
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
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text(
                                "Agenda do dia",
                                size=20,
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Button(
                                "Todos",
                                color="#D5D5D5",
                                bgcolor=CARTAO,
                                on_click=lambda _: mostrar_aviso(
                                    "Os filtros serão liberados quando "
                                    "a agenda estiver integrada."
                                ),
                            ),
                        ],
                    ),
                    *(
                        [cartao_reserva(r) for r in reservas_no_dia(dia_visivel["data"])]
                        if not agenda_consulta["carregando"]
                        and not agenda_consulta["erro"]
                        and reservas_no_dia(dia_visivel["data"])
                        else [
                            ft.Container(
                                bgcolor=CARTAO,
                                border_radius=12,
                                padding=16,
                                content=ft.Text(
                                    (
                                        agenda_consulta["erro"]
                                        or "Carregando agenda..."
                                        if agenda_consulta["carregando"]
                                        or agenda_consulta["erro"]
                                        else "Nenhum agendamento neste dia."
                                    ),
                                    size=13,
                                    color=TEXTO_SECUNDARIO,
                                ),
                            ),
                        ]
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
            if abrir_estabelecimento is not None:
                tem_negocio = bool(
                    dados_estabelecimento and dados_estabelecimento.get("id")
                )
                itens.insert(
                    2,
                    ft.Button(
                        "Editar dados do negócio" if tem_negocio
                        else "Cadastrar estabelecimento",
                        icon=ft.Icons.STOREFRONT_OUTLINED,
                        bgcolor="#292929",
                        color="#EDEDED",
                        on_click=abrir_estabelecimento,
                    ),
                )
                if tem_negocio and abrir_horarios is not None:
                    etapa_atual = int(
                        dados_estabelecimento.get("onboarding_step") or 1
                    )
                    itens.insert(
                        3,
                        ft.Button(
                            "Configurar horários · 2/5"
                            if etapa_atual <= 2 else "Editar horários",
                            icon=ft.Icons.SCHEDULE,
                            bgcolor="#292929",
                            color="#EDEDED",
                            on_click=abrir_horarios,
                        ),
                    )
                if (
                    tem_negocio and abrir_servicos is not None
                    and int(
                        dados_estabelecimento.get("onboarding_step") or 1
                    ) >= 3
                ):
                    proxima_etapa = int(
                        dados_estabelecimento.get("onboarding_step") or 1
                    )
                    itens.insert(
                        4,
                        ft.Button(
                            "Configurar serviços · 3/5"
                            if proxima_etapa == 3 else "Gerenciar serviços",
                            icon=ft.Icons.DESIGN_SERVICES_OUTLINED,
                            bgcolor="#292929",
                            color="#EDEDED",
                            on_click=abrir_servicos,
                        ),
                    )
                if (
                    tem_negocio and abrir_profissionais is not None
                    and int(
                        dados_estabelecimento.get("onboarding_step") or 1
                    ) >= 4
                ):
                    etapa_profissionais = int(
                        dados_estabelecimento.get("onboarding_step") or 1
                    )
                    itens.insert(
                        5,
                        ft.Button(
                            "Configurar profissionais · 4/5"
                            if etapa_profissionais == 4
                            else "Gerenciar profissionais",
                            icon=ft.Icons.PEOPLE_OUTLINE,
                            bgcolor="#292929",
                            color="#EDEDED",
                            on_click=abrir_profissionais,
                        ),
                    )
                if (
                    tem_negocio and abrir_revisao is not None
                    and int(
                        dados_estabelecimento.get("onboarding_step") or 1
                    ) >= 5
                ):
                    esta_ativo = bool(
                        dados_estabelecimento.get("onboarding_completed")
                    )
                    itens.insert(
                        6,
                        ft.Button(
                            "Estabelecimento ativo · Ver revisão"
                            if esta_ativo else "Revisar e ativar · 5/5",
                            icon=ft.Icons.CHECK_CIRCLE_OUTLINE,
                            bgcolor="#292929",
                            color="#EDEDED",
                            on_click=abrir_revisao,
                        ),
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
                itens.pop()
                itens.extend(criar_agenda())
            elif indice == 2:
                itens.pop()
                itens.extend(criar_clientes_ui())
            else:
                itens.pop()
                itens.extend(criar_mais())

        conteudo.controls = itens
        page.update()
        if indice == 2:
            if buscar_clientes is not None:
                page.run_task(carregar_clientes_autenticados)
            else:
                atualizar_lista_clientes()

    def mudar_aba(evento):
        if evento.control.selected_index != 3:
            mais_estado["pagina"] = None
        renderizar(evento.control.selected_index)

    def abrir_agenda_na_data(data_iso):
        try:
            agenda_estado["data"] = date.fromisoformat(str(data_iso))
        except ValueError:
            agenda_estado["data"] = date.today()
        agenda_estado["modo"] = "Dia"
        agenda_consulta["chave"] = None
        if page.navigation_bar is not None:
            page.navigation_bar.selected_index = 1
        renderizar(1)

    def mostrar_painel():
        # Não mostrar pesquisas/profissionais/serviços de uma conta anterior.
        agenda_estado["busca"] = ""
        agenda_estado["busca_rascunho"] = ""
        agenda_estado["pesquisa_aberta"] = False
        agenda_estado["filtro_status"] = "todos"
        agenda_estado["filtro_profissional"] = "todos"
        agenda_estado["filtro_servico"] = "todos"
        agenda_estado["rotulos_profissionais"].clear()
        agenda_estado["rotulos_servicos"].clear()
        agenda_consulta["sequencia"] += 1
        agenda_consulta["chave"] = None
        agenda_consulta["registros"] = []
        if buscar_clientes is not None:
            # Não manter fichas da conta anterior ao trocar o login.
            clientes.clear()
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
                    padding=ft.Padding.symmetric(horizontal=20, vertical=10),
                    content=ft.Column(
                        expand=True,
                        spacing=0,
                        controls=[
                            ft.Container(
                                padding=ft.Padding.only(bottom=6),
                                content=cabecalho(),
                            ),
                            ft.Divider(height=8, color="#2B2B2B"),
                            conteudo,
                        ],
                    ),
                ),
            )
        )
        renderizar(0)

    mostrar_painel.abrir_agenda_na_data = abrir_agenda_na_data
    return mostrar_painel
