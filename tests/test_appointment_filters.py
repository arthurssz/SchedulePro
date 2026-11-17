"""Testes dos filtros visuais de status da Agenda."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from appointment_filters import (
    FILTROS_STATUS, filtrar_status_agenda, filtrar_agenda, opcoes_agenda,
)


class TestFiltrosAgenda(unittest.TestCase):
    def setUp(self):
        self.registros = [
            {"id": "1", "status": "scheduled", "local_date": "2026-11-23"},
            {"id": "2", "status": "confirmed", "local_date": "2026-11-23"},
            {"id": "3", "status": "canceled", "local_date": "2026-11-23"},
            {"id": "4", "status": "completed", "local_date": "2026-11-24"},
            {"id": "5", "status": "no_show", "local_date": "2026-11-24"},
        ]

    def test_todos_mantem_registros_sem_modificar_original(self):
        filtrados = filtrar_status_agenda(self.registros, "todos")
        self.assertEqual(filtrados, self.registros)
        self.assertIsNot(filtrados, self.registros)

    def test_cada_opcao_retorna_apenas_o_status_solicitado(self):
        for status, _ in FILTROS_STATUS:
            with self.subTest(status=status):
                filtrados = filtrar_status_agenda(self.registros, status)
                if status == "todos":
                    self.assertEqual(len(filtrados), 5)
                else:
                    self.assertEqual(len(filtrados), 1)
                    self.assertEqual(filtrados[0]["status"], status)

    def test_status_sem_resultados_retorna_lista_vazia(self):
        self.assertEqual(filtrar_status_agenda([], "confirmed"), [])


    def test_filtros_combinados_usam_ids_e_nao_nomes(self):
        registros = [
            {
                "status": "confirmed",
                "professional": {"id": "p1", "name": "João"},
                "service": {"id": "s1", "name": "Corte"},
            },
            {
                "status": "scheduled",
                "professional": {"id": "p2", "name": "João"},
                "service": {"id": "s1", "name": "Corte"},
            },
            {
                "status": "canceled",
                "professional": {"id": "p2", "name": "João"},
                "service": {"id": "s2", "name": "Corte"},
            },
        ]
        self.assertEqual(
            filtrar_agenda(
                registros, status="scheduled",
                profissional_id="p2", servico_id="s1",
            ),
            [registros[1]],
        )
        self.assertEqual(
            filtrar_agenda(
                registros, status="confirmed",
                profissional_id="p2", servico_id="s1",
            ), [],
        )
        self.assertEqual(len(filtrar_agenda(registros, servico_id="s1")), 2)
        self.assertEqual(len(filtrar_agenda(registros, profissional_id="p2")), 2)

    def test_opcoes_unicas_ordenadas_por_nome_sem_perder_id(self):
        registros = [
            {"professional": {"id": "p2", "name": "Zélia"},
             "service": {"id": "s2", "name": "Barba"}},
            {"professional": {"id": "p1", "name": "Ana"},
             "service": {"id": "s1", "name": "Corte"}},
            {"professional": {"id": "p1", "name": "Ana"},
             "service": {"id": "s1", "name": "Corte"}},
            {"professional": None, "service": None},
        ]
        self.assertEqual(
            opcoes_agenda(registros, "professional"),
            [("p1", "Ana"), ("p2", "Zélia")],
        )
        self.assertEqual(
            opcoes_agenda(registros, "service"),
            [("s2", "Barba"), ("s1", "Corte")],
        )
        with self.assertRaises(ValueError):
            opcoes_agenda(registros, "customer")

    def test_filtros_combinados_nao_alteram_o_registro_original(self):
        registros = [
            {
                "status": "canceled",
                "professional": {"id": "p1", "name": "João"},
                "service": {"id": "s1", "name": "Corte"},
            }
        ]
        self.assertEqual(
            filtrar_agenda(registros, "scheduled", "p1", "s1"), [],
        )
        self.assertEqual(registros[0]["status"], "canceled")

    def test_filtro_invalido_rejeitado(self):
        with self.assertRaises(ValueError):
            filtrar_status_agenda(self.registros, "indefinido")

    def test_filtro_nao_altera_ocupacao_ou_status_dos_registros(self):
        antes = [dict(registro) for registro in self.registros]
        filtrar_status_agenda(self.registros, "canceled")
        self.assertEqual(self.registros, antes)


if __name__ == "__main__":
    unittest.main()
