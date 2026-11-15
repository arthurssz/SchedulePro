"""Testes offline para jornadas do profissional e ativação interna."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import activation_api as api
from establishments_api import ErroEstabelecimento

BUSINESS = "4d76ddab-8fa1-4c74-956a-f423702ab568"
PROFESSIONAL = "7c2a1cb7-ea1c-4088-a12f-97b48bcb48e2"


def semana():
    return [
        {"weekday": d,
         "intervals": [{"start": "09:00", "end": "18:00"}]
         if d < 5 else []}
        for d in range(7)
    ]


class TestJornadas(unittest.TestCase):
    def test_profissional_pode_herdar_horarios_da_empresa(self):
        self.assertEqual(
            api.validar_compatibilidade(semana(), semana()),
            semana(),
        )

    def test_jornada_incompativel_e_bloqueada(self):
        dias = semana()
        dias[0]["intervals"][0]["start"] = "08:00"
        with self.assertRaisesRegex(
            ErroEstabelecimento, "incompatível"
        ):
            api.validar_compatibilidade(dias, semana())

    def test_nao_atende_durante_pausa(self):
        negocio = semana()
        negocio[0]["intervals"] = [
            {"start": "09:00", "end": "12:00"},
            {"start": "13:00", "end": "18:00"},
        ]
        with self.assertRaises(ErroEstabelecimento):
            api.validar_compatibilidade(semana(), negocio)

    def test_salva_sete_dias_com_proprietario_no_servidor(self):
        with patch.object(
            api, "_pedir", return_value=[{} for _ in range(7)]
        ) as requisicao:
            api.salvar_jornada_profissional(
                "token", BUSINESS, PROFESSIONAL,
                semana(), semana(),
            )
        self.assertEqual(
            requisicao.call_args.kwargs["metodo"], "POST"
        )
        dados = requisicao.call_args.kwargs["dados"]
        self.assertEqual(len(dados), 7)
        self.assertTrue(all(
            x["establishment_id"] == BUSINESS
            and x["professional_id"] == PROFESSIONAL
            for x in dados
        ))
        self.assertNotIn("owner_id", dados[0])

    def test_activation_check_exige_login(self):
        with patch.object(
            api, "_rpc",
            return_value={"ready": False, "issues": ["Jornada pendente"]},
        ) as requisicao:
            retorno = api.revisar_ativacao("token", BUSINESS)
        self.assertFalse(retorno["ready"])
        self.assertEqual(
            requisicao.call_args.args[1],
            "rpc/schedulepro_activation_check",
        )

    def test_activation_rejects_incomplete_confirmation(self):
        with patch.object(
            api, "_rpc", return_value={"onboarding_completed": False}
        ):
            with self.assertRaises(ErroEstabelecimento):
                api.ativar_estabelecimento("token", BUSINESS)

    def test_activation_success_preserves_public_booking_off(self):
        resposta = {
            "onboarding_completed": True,
            "onboarding_step": 5,
            "public_booking_enabled": False,
        }
        with patch.object(api, "_rpc", return_value=resposta):
            resultado = api.ativar_estabelecimento("token", BUSINESS)
        self.assertFalse(resultado["public_booking_enabled"])


if __name__ == "__main__":
    unittest.main()
