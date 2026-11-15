"""Testes offline da etapa de horários, sem tokens nem rede reais."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import hours_api as api
from establishments_api import ErroEstabelecimento


ID = "4d76ddab-8fa1-4c74-956a-f423702ab568"


def semana_teste():
    return [
        {"weekday": i, "intervals": []}
        for i in range(7)
    ]


class TestJornadaSemanal(unittest.TestCase):
    def test_salvar_multiplos_intervalos_e_pausa(self):
        semana = semana_teste()
        semana[0]["intervals"] = [
            {"start": "09:00", "end": "12:00"},
            {"start": "13:00", "end": "18:00"},
        ]
        self.assertEqual(api.validar_jornada(semana), semana)

    def test_intervalos_sobrepostos_sao_rejeitados(self):
        semana = semana_teste()
        semana[0]["intervals"] = [
            {"start": "09:00", "end": "13:00"},
            {"start": "12:30", "end": "18:00"},
        ]
        with self.assertRaisesRegex(ErroEstabelecimento, "sobreposição"):
            api.validar_jornada(semana)

    def test_virar_meia_noite_e_rejeitado(self):
        semana = semana_teste()
        semana[5]["intervals"] = [
            {"start": "23:00", "end": "01:00"}
        ]
        with self.assertRaisesRegex(ErroEstabelecimento, "mesmo dia"):
            api.validar_jornada(semana)

    def test_todos_os_dias_fechados_sao_rejeitados(self):
        with self.assertRaisesRegex(ErroEstabelecimento, "pelo menos um"):
            api.validar_jornada(semana_teste())

    def test_todas_as_sete_linhas_sao_enviadas(self):
        semana = semana_teste()
        semana[2]["intervals"] = [
            {"start": "08:00", "end": "17:00"}
        ]
        resposta = [{"weekday": i} for i in range(7)]
        with patch.object(api, "_pedir", side_effect=[resposta, [{"onboarding_step": 3}]]) as pedido:
            api.salvar_horarios("token-teste", ID, semana, 2)
        self.assertEqual(pedido.call_count, 2)
        chamada = pedido.call_args_list[0]
        self.assertIn("on_conflict=establishment_id,weekday", chamada.args[1])
        dados = chamada.kwargs["dados"]
        self.assertEqual(len(dados), 7)
        self.assertTrue(all("owner_id" not in linha for linha in dados))
        proxima = pedido.call_args_list[1]
        self.assertEqual(proxima.kwargs["dados"], {"onboarding_step": 3})

    def test_editar_horarios_nao_retrocede_etapa(self):
        semana = semana_teste()
        semana[0]["intervals"] = [{"start": "09:00", "end": "18:00"}]
        with patch.object(
            api, "_pedir", return_value=[{"weekday": i} for i in range(7)]
        ) as pedido:
            api.salvar_horarios("token-teste", ID, semana, 4)
        self.assertEqual(pedido.call_count, 1)


if __name__ == "__main__":
    unittest.main()
