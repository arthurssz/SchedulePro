"""Testes offline do catálogo de serviços, sem conectar ao Supabase."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import services_api as api
from establishments_api import ErroEstabelecimento


NEGOCIO = "4d76ddab-8fa1-4c74-956a-f423702ab568"
SERVICO = "6c58ae91-5afa-4b7b-a138-a19886603ba4"


class TestPrecosEValidacao(unittest.TestCase):
    def test_formato_brasileiro(self):
        self.assertEqual(api.valor_em_centavos("50,00"), 5000)
        self.assertEqual(api.valor_em_centavos("R$ 75,90"), 7590)
        self.assertEqual(api.valor_em_centavos("0,00"), 0)
        self.assertEqual(api.valor_em_centavos("59.99"), 5999)
        self.assertEqual(api.formatar_preco(7590), "R$ 75,90")

    def test_preco_ambiguo_ou_negativo_bloqueado(self):
        for valor in ("-20", "1.234,56", "abc", "20,999"):
            with self.subTest(valor=valor):
                with self.assertRaises(ErroEstabelecimento):
                    api.valor_em_centavos(valor)

    def test_nome_duracao_e_descricao_validados(self):
        base = {
            "name": "Corte de cabelo", "duration_minutes": "30",
            "price": "40,00", "description": "",
            "is_active": True,
        }
        self.assertEqual(
            api.validar_servico(base)["duration_minutes"], 30
        )
        for invalido in (
            {"name": "A"},
            {"duration_minutes": "2"},
            {"duration_minutes": "cinco"},
            {"description": "x" * 501},
        ):
            with self.subTest(invalido=invalido):
                with self.assertRaises(ErroEstabelecimento):
                    api.validar_servico({**base, **invalido})


class TestRequisicoes(unittest.TestCase):
    def setUp(self):
        self.form = {
            "name": "Corte simples", "duration_minutes": "30",
            "price": "35,00", "description": "Teste",
            "is_active": True,
        }
        self.item = {
            "id": SERVICO,
            "name": "Corte simples",
            "duration_minutes": 30,
            "price_cents": 3500,
            "is_active": True,
        }

    def test_novo_servico_avanca_etapa_3_para_4(self):
        with patch.object(
            api, "_pedir",
            side_effect=[[dict(self.item)], [{"onboarding_step": 4}]],
        ) as pedir:
            retorno = api.salvar_servico(
                "token-teste", NEGOCIO, self.form, etapa_atual=3
            )
        self.assertTrue(retorno["_etapa_avancou"])
        self.assertEqual(pedir.call_count, 2)
        chamada = pedir.call_args_list[0]
        self.assertEqual(chamada.kwargs["metodo"], "POST")
        dados = chamada.kwargs["corpo"]
        self.assertEqual(dados["establishment_id"], NEGOCIO)
        self.assertEqual(dados["price_cents"], 3500)
        self.assertNotIn("owner_id", dados)

    def test_editar_nao_regride_progresso(self):
        with patch.object(
            api, "_pedir", return_value=[dict(self.item)]
        ) as pedir:
            retorno = api.salvar_servico(
                "token-teste", NEGOCIO, self.form,
                servico_id=SERVICO, etapa_atual=5,
            )
        self.assertFalse(retorno["_etapa_avancou"])
        self.assertEqual(pedir.call_count, 1)
        self.assertEqual(pedir.call_args.kwargs["metodo"], "PATCH")
        self.assertIn("id=eq.", pedir.call_args.args[1])
        self.assertIn("establishment_id=eq.", pedir.call_args.args[1])

    def test_servico_inativo_nao_avanca(self):
        with patch.object(
            api, "_pedir", return_value=[dict(self.item)]
        ) as pedir:
            api.salvar_servico(
                "token-teste", NEGOCIO,
                {**self.form, "is_active": False},
                etapa_atual=3,
            )
        self.assertEqual(pedir.call_count, 1)

    def test_alternar_atividade_so_atualiza_servico_filtrado(self):
        with patch.object(
            api, "_pedir",
            return_value=[{**self.item, "is_active": False}],
        ) as pedir:
            retorno = api.alterar_atividade(
                "token-teste", NEGOCIO, SERVICO, False
            )
        self.assertFalse(retorno["is_active"])
        self.assertEqual(
            pedir.call_args.kwargs["corpo"],
            {"is_active": False},
        )

    def test_id_invalido_nao_faz_requisicao(self):
        with patch.object(api, "_pedir") as pedir:
            with self.assertRaises(ErroEstabelecimento):
                api.listar_servicos("token-teste", "qualquer-id")
            pedir.assert_not_called()


if __name__ == "__main__":
    unittest.main()
