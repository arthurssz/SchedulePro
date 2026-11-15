"""Telas compartilhadas entre o APK e a prévia web do SchedulePro.

Manter a interface neste módulo evita dois designs divergentes.
NÃO há autenticação nem acesso a dados privados nesta camada.
"""
from datetime import date, timedelta
import calendar
import flet as ft


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



def criar_painel(page: ft.Page, sair_da_conta):
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
    }

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

    def registrar_busca(evento):
        agenda_estado["busca"] = evento.control.value or ""

    def agendamento_indisponivel(evento):
        mostrar_aviso(
            "Antes de criar agendamentos, precisamos cadastrar "
            "o estabelecimento, os serviços e os profissionais."
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
                        on_click=lambda _: mostrar_aviso(
                            "A pesquisa será conectada aos agendamentos "
                            "depois dos cadastros."
                        ),
                    ),
                    ft.IconButton(
                        icon=ft.Icons.TUNE,
                        tooltip="Filtros avançados",
                        on_click=lambda _: mostrar_aviso(
                            "Os filtros por profissional, serviço e status "
                            "serão ativados com os cadastros."
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
                controls=[
                    ft.Text("Profissional", size=13, color=TEXTO_SECUNDARIO),
                    ft.Button(
                        "Todos",
                        bgcolor=CARTAO,
                        color="#ECECEC",
                        on_click=lambda _: mostrar_aviso(
                            "Ainda não há profissionais cadastrados."
                        ),
                    ),
                ],
            ),
        ]

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
                                            nome,
                                            text_align=ft.TextAlign.CENTER,
                                            size=11,
                                            color=TEXTO_SECUNDARIO,
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
                                                "#3E3E3E"
                                                if numero == data.day
                                                else "transparent"
                                            ),
                                            content=ft.Text(
                                                str(numero) if numero else "",
                                                size=12,
                                                text_align=ft.TextAlign.CENTER,
                                                color=(
                                                    "#EAEAEA"
                                                    if numero else "#666666"
                                                ),
                                            ),
                                            on_click=(
                                                (lambda _, dia=numero: selecionar_dia_agenda(dia))
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
            controles.append(
                ft.Text(
                    "Toque em um dia para abrir a agenda. "
                    "Não há reservas cadastradas.",
                    size=12,
                    color=TEXTO_SECUNDARIO,
                )
            )
        elif modo == "Semana":
            for deslocamento in range(7):
                dia = inicio_semana + timedelta(days=deslocamento)
                controles.append(
                    ft.Container(
                        bgcolor=CARTAO,
                        border_radius=12,
                        padding=13,
                        content=ft.Row(
                            controls=[
                                ft.Text(
                                    f"{DIAS_CURTOS[dia.weekday()]}, {dia.day}",
                                    size=14,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                ft.Container(expand=True),
                                ft.Text(
                                    "Sem agendamentos",
                                    size=12,
                                    color=TEXTO_SECUNDARIO,
                                ),
                            ],
                        ),
                        on_click=lambda _, escolhido=dia: abrir_dia_agenda(
                            escolhido
                        ),
                    )
                )
        else:
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
                                size=22,
                                color="#A8A8A8",
                            ),
                            ft.Text(
                                "Nenhum agendamento neste dia.",
                                size=15,
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Text(
                                "Assim que você cadastrar o estabelecimento "
                                "e começar a agendar clientes, os horários "
                                "aparecerão aqui.",
                                size=12,
                                color=TEXTO_SECUNDARIO,
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

    def renderizar(indice: int):
        titulo = ABAS[indice][0]
        itens = [
            cabecalho(),
            ft.Divider(height=8, color="#2B2B2B"),
        ]

        if indice == 0:
            itens.extend(
                [
                    ft.Text(
                        "ESTABELECIMENTO NÃO CONFIGURADO",
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
                                resumo("—", "Agendamentos"),
                                resumo("—", "A confirmar"),
                                resumo("—", "Concluídos"),
                            ],
                        ),
                    ),
                    ft.Container(
                        bgcolor="#F1F1F1",
                        border_radius=14,
                        padding=13,
                        on_click=lambda _: mostrar_aviso(
                            "Primeiro vamos cadastrar seu estabelecimento "
                            "para habilitar os agendamentos."
                        ),
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
                    ft.Container(
                        bgcolor=CARTAO,
                        border_radius=12,
                        padding=16,
                        content=ft.Column(
                            spacing=7,
                            tight=True,
                            controls=[
                                ft.Text(
                                    "Nenhum agendamento neste dia.",
                                    size=14,
                                ),
                                ft.Text(
                                    "Os agendamentos aparecerão aqui "
                                    "após a configuração do negócio.",
                                    size=12,
                                    color=TEXTO_SECUNDARIO,
                                ),
                            ],
                        ),
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
                itens.append(
                    cartao(
                        "Clientes",
                        "Aqui você poderá consultar e cadastrar clientes.",
                    )
                )
            else:
                itens.append(
                    ft.Button(
                        "Sair da conta",
                        icon=ft.Icons.LOGOUT,
                        on_click=sair_da_conta,
                    )
                )
                itens.append(
                    ft.Text(
                        "Áreas previstas para as próximas etapas:",
                        color=TEXTO_SECUNDARIO,
                        size=13,
                    )
                )
                itens.extend(
                    cartao(nome, "Em desenvolvimento") for nome in AREAS
                )

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

    return mostrar_painel
