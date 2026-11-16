"""Testes offline do cadastro real de clientes no SchedulePro."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import customers_api as api
from establishments_api import ErroEstabelecimento


ESTABELECIMENTO = "4d76ddab-8fa1-4c74-956a-f423702ab568"
CLIENTE = "6c58ae91-5afa-4b7b-a138-a19886603ba4"


class TestarValidacao(unittest.TestCase):
    def test_formatacao_de_telefone(self):
        dados = api.validar_cliente({
            "name": "Cliente Teste",
            "phone": "11999999999",
            "email": "Cliente@Exemplo.com",
            "notes": "",
        })
        self.assertEqual(dados["phone"], "(11) 99999-9999")
        self.assertEqual(dados["email"], "cliente@exemplo.com")

    def test_sem_contato_aceito(self):
        dados = api.validar_cliente({
            "name": "Cliente Teste",
            "phone": "", "email": "", "notes": "",
        })
        self.assertEqual(dados["phone"], "")

    def test_telefone_e_email_invalidos(self):
        for caso in (
            {"phone": "123"},
            {"email": "email_invalido"},
            {"notes": "A" * 1501},
            {"name": "X"},
        ):
            with self.subTest(caso=caso):
                with self.assertRaises(ErroEstabelecimento):
                    api.validar_cliente({
                        "name": "Cliente Exemplo",
                        "phone": "", "email": "", "notes": "",
                        **caso,
                    })


class TestarRequisicoes(unittest.TestCase):
    def setUp(self):
        self.cliente = {
            "name": "Teste de cliente",
            "phone": "", "email": "", "notes": "",
        }
        self.retorno = {
            "id": CLIENTE, "name": "Teste de cliente",
        }

    def test_insercao_proprietario_via_rls(self):
        with patch.object(
            api, "_pedir", return_value=[dict(self.retorno)]
        ) as pedir:
            api.salvar_cliente(
                "token-teste", ESTABELECIMENTO, self.cliente
            )
        args = pedir.call_args
        self.assertEqual(args.kwargs["metodo"], "POST")
        self.assertEqual(args.args[1], "customers")
        self.assertEqual(
            args.kwargs["dados"]["establishment_id"], ESTABELECIMENTO
        )
        self.assertNotIn("owner_id", args.kwargs["dados"])

    def test_edicao_fica_restrita_ao_estabelecimento(self):
        with patch.object(
            api, "_pedir", return_value=[dict(self.retorno)]
        ) as pedir:
            api.salvar_cliente(
                "token-teste", ESTABELECIMENTO, self.cliente, CLIENTE
            )
        self.assertEqual(pedir.call_args.kwargs["metodo"], "PATCH")
        self.assertIn(
            "establishment_id=eq.",
            pedir.call_args.args[1],
        )
        self.assertIn("id=eq.", pedir.call_args.args[1])

    def test_arquivar_fica_restrito_ao_estabelecimento(self):
        with patch.object(
            api, "_pedir", return_value=[dict(self.retorno)]
        ) as pedir:
            api.arquivar_cliente(
                "token-teste", ESTABELECIMENTO, CLIENTE
            )
        self.assertTrue(pedir.call_args.kwargs["dados"]["is_archived"])
        self.assertEqual(pedir.call_args.kwargs["metodo"], "PATCH")

    def test_excluir_nao_retorna_sem_confirmacao(self):
        with patch.object(api, "_pedir", return_value=[]):
            with self.assertRaisesRegex(ErroEstabelecimento, "exclusão"):
                api.excluir_cliente(
                    "token-teste", ESTABELECIMENTO, CLIENTE
                )

    def test_listagem_do_negocio(self):
        with patch.object(
            api, "_pedir", return_value=[dict(self.retorno)]
        ) as pedir:
            resultado = api.listar_clientes(
                "token-teste", ESTABELECIMENTO
            )
        self.assertEqual(len(resultado), 1)
        self.assertIn(
            "establishment_id=eq.",
            pedir.call_args.args[1],
        )

    def test_identificador_invalido_nao_requisita(self):
        with patch.object(api, "_pedir") as pedir:
            with self.assertRaises(ErroEstabelecimento):
                api.listar_clientes("token-teste", "negocio-invalido")
            pedir.assert_not_called()


if __name__ == "__main__":
    unittest.main()
