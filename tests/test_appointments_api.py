"""Testes offline da agenda interna; as regras de conflito ficam no Postgres."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import appointments_api as api
from establishments_api import ErroEstabelecimento


BUSINESS = "a5010cbc-f84a-4086-b182-aee5372fb182"
CLIENT = "93516dde-1135-4b2c-8e9f-a0859a3972b9"
PRO = "8fd9921a-4af4-4fc0-9861-19f4c73073a9"
SERVICE = "4893df53-f5c2-4a80-8cc9-a92f8b1fa3ed"


def booking(**alteracoes):
    return {
        "customer_id": CLIENT,
        "professional_id": PRO,
        "service_id": SERVICE,
        "local_date": "2026-11-23",
        "local_time": "10:00",
        "notes": "",
        **alteracoes,
    }


class TestAppointments(unittest.TestCase):
    def test_valida_booking_e_limite(self):
        self.assertEqual(
            api.validar_agendamento(booking())["p_local_time"], "10:00"
        )
        for dados in (
            booking(local_date="23/11/2026"),
            booking(local_time="25:00"),
            booking(local_time="10:02:10"),
            booking(customer_id="id-invalido"),
            booking(notes="x" * 1001),
        ):
            with self.subTest(dados=dados):
                with self.assertRaises(ErroEstabelecimento):
                    api.validar_agendamento(dados)

    def test_rpc_recebe_owner_token_e_dados_validados(self):
        with patch.object(
            api, "_pedir", return_value={"id": CLIENT}
        ) as pedir:
            resultado = api.criar_agendamento(
                "jwt-do-usuario", BUSINESS, booking()
            )
            self.assertEqual(resultado["id"], CLIENT)
            self.assertEqual(
                pedir.call_args.args[1],
                "rpc/schedulepro_create_internal_appointment",
            )
            self.assertEqual(
                pedir.call_args.kwargs["dados"]["p_establishment_id"],
                BUSINESS,
            )
            self.assertNotIn(
                "owner_id", pedir.call_args.kwargs["dados"]
            )

    def test_rpc_exige_confirmacao_do_servidor(self):
        with patch.object(api, "_pedir", return_value=[]):
            with self.assertRaises(ErroEstabelecimento):
                api.criar_agendamento(
                    "jwt-do-usuario", BUSINESS, booking()
                )

    def test_listagem_restrita_ao_estabelecimento(self):
        with patch.object(
            api, "_pedir", return_value=[]
        ) as pedir:
            self.assertEqual(
                api.listar_agendamentos(
                    "jwt-do-usuario", BUSINESS,
                    "2026-11-23", "2026-11-29",
                ), []
            )
            caminho = pedir.call_args.args[1]
            self.assertIn("establishment_id=eq." + BUSINESS, caminho)
            self.assertIn("local_date=gte.2026-11-23", caminho)
            self.assertIn("local_date=lte.2026-11-29", caminho)

    def test_status_valido_usa_rpc_autenticada(self):
        with patch.object(
            api, "_pedir",
            return_value={"id": CLIENT, "status": "confirmed"},
        ) as pedido:
            resultado = api.alterar_status_agendamento(
                "jwt-do-usuario", BUSINESS, CLIENT, "confirmed"
            )
        self.assertEqual(resultado["status"], "confirmed")
        self.assertEqual(
            pedido.call_args.args[1],
            "rpc/schedulepro_change_appointment_status",
        )
        self.assertEqual(
            pedido.call_args.kwargs["dados"]["p_establishment_id"],
            BUSINESS,
        )
        self.assertEqual(
            pedido.call_args.kwargs["dados"]["p_appointment_id"],
            CLIENT,
        )

    def test_nao_permite_status_fora_do_fluxo(self):
        with patch.object(api, "_pedir") as pedido:
            for status in (
                "scheduled", "no_show", "inventado", "", None,
            ):
                with self.subTest(status=status):
                    with self.assertRaises(ErroEstabelecimento):
                        api.alterar_status_agendamento(
                            "jwt-do-usuario", BUSINESS, CLIENT, status
                        )
            pedido.assert_not_called()

    def test_status_exige_confirmacao_remota(self):
        with patch.object(
            api, "_pedir",
            return_value={"id": CLIENT, "status": "canceled"},
        ):
            with self.assertRaises(ErroEstabelecimento):
                api.alterar_status_agendamento(
                    "jwt-do-usuario", BUSINESS, CLIENT, "confirmed"
                )

    def test_filtro_tem_periodo_limitado(self):
        with patch.object(api, "_pedir") as pedir:
            with self.assertRaises(ErroEstabelecimento):
                api.listar_agendamentos(
                    "jwt-do-usuario", BUSINESS,
                    "2026-01-01", "2026-12-31",
                )
            pedir.assert_not_called()


if __name__ == "__main__":
    unittest.main()
