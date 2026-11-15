"""Testes offline da etapa 4/5: profissionais e serviços associados."""

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import professionals_api as api
from establishments_api import ErroEstabelecimento


ESTABELECIMENTO = "4d76ddab-8fa1-4c74-956a-f423702ab568"
SERVICO_1 = "6c58ae91-5afa-4b7b-a138-a19886603ba4"
SERVICO_2 = "5c2a1cb7-ea1c-4088-a12f-97b48bcb48e2"
PROFISSIONAL = "7c2a1cb7-ea1c-4088-a12f-97b48bcb48e2"


class RespostaFalsa:
    def __init__(self, conteudo):
        self.data = json.dumps(conteudo).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self.data


def exemplo():
    return {
        "name": "Profissional Exemplo",
        "specialty": "Cabeleireiro",
        "phone": "(11) 99999-9999",
        "email": "teste@example.com",
        "is_active": True,
        "service_ids": [SERVICO_1, SERVICO_2],
    }


class TestValidacao(unittest.TestCase):
    def test_selecao_multipla_e_campos(self):
        saida = api.validar_profissional(exemplo())
        self.assertEqual(saida["name"], "Profissional Exemplo")
        self.assertEqual(len(saida["service_ids"]), 2)

    def test_ativo_precisa_servico(self):
        with self.assertRaisesRegex(ErroEstabelecimento, "serviço"):
            api.validar_profissional({
                **exemplo(), "service_ids": []
            })

    def test_profissional_inativo_sem_servico_e_permitido(self):
        saida = api.validar_profissional({
            **exemplo(), "service_ids": [], "is_active": False
        })
        self.assertFalse(saida["is_active"])

    def test_rejeita_ids_repetidos_e_email_ruim(self):
        with self.assertRaises(ErroEstabelecimento):
            api.validar_profissional({
                **exemplo(), "service_ids": [SERVICO_1, SERVICO_1]
            })
        with self.assertRaises(ErroEstabelecimento):
            api.validar_profissional({
                **exemplo(), "email": "invalido"
            })

    def test_nao_aceita_id_falso(self):
        with self.assertRaises(ErroEstabelecimento):
            api.validar_profissional({
                **exemplo(), "service_ids": ["outro-estabelecimento"]
            })


class TestRequisicoes(unittest.TestCase):
    @patch.object(api.urllib.request, "urlopen")
    def test_criar_via_rpc_atomica_e_token_publicavel(self, req):
        req.return_value = RespostaFalsa({
            "id": PROFISSIONAL, "_etapa_avancou": True,
        })
        resposta = api.salvar_profissional(
            "token-teste", ESTABELECIMENTO, exemplo()
        )
        chamada = req.call_args.args[0]
        dados = json.loads(chamada.data)
        self.assertEqual(chamada.get_method(), "POST")
        self.assertTrue(chamada.full_url.endswith(
            "/rest/v1/rpc/save_schedulepro_professional"
        ))
        self.assertEqual(
            chamada.get_header("Authorization"), "Bearer token-teste"
        )
        self.assertEqual(
            dados["p_service_ids"], [SERVICO_1, SERVICO_2]
        )
        self.assertIsNone(dados["p_professional_id"])
        self.assertNotIn("owner_id", dados)
        self.assertTrue(resposta["_etapa_avancou"])

    @patch.object(api.urllib.request, "urlopen")
    def test_editar_envia_mesmo_id(self, req):
        req.return_value = RespostaFalsa({
            "id": PROFISSIONAL, "_etapa_avancou": False,
        })
        api.salvar_profissional(
            "token-teste", ESTABELECIMENTO, exemplo(), PROFISSIONAL
        )
        enviado = json.loads(req.call_args.args[0].data)
        self.assertEqual(enviado["p_professional_id"], PROFISSIONAL)

    @patch.object(api.urllib.request, "urlopen")
    def test_listar_profissionais_com_seus_servicos(self, req):
        req.side_effect = [
            RespostaFalsa([{
                "id": PROFISSIONAL, "name": "Exemplo",
                "is_active": True,
            }]),
            RespostaFalsa([
                {"professional_id": PROFISSIONAL, "service_id": SERVICO_1},
                {"professional_id": PROFISSIONAL, "service_id": SERVICO_2},
            ]),
        ]
        saida = api.listar_profissionais(
            "token-teste", ESTABELECIMENTO
        )
        self.assertEqual(
            saida[0]["service_ids"], [SERVICO_1, SERVICO_2]
        )
        self.assertIn(
            "professional_services?",
            req.call_args_list[1].args[0].full_url
        )


if __name__ == "__main__":
    unittest.main()
