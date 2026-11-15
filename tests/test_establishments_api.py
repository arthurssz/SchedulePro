"""Testes locais da integração, sem acessar contas nem o Supabase real."""

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import establishments_api as api


class RespostaFalsa:
    def __init__(self, dados):
        self.dados = json.dumps(dados).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self.dados


class TestEstabelecimentos(unittest.TestCase):
    def setUp(self):
        self.dados = {
            "name": "Estúdio Exemplo",
            "business_type": "Barbearia",
            "phone": "(11) 99999-9999",
            "address": "Endereço demonstrativo",
            "description": "",
        }
        self.registro = {
            "id": "4d76ddab-8fa1-4c74-956a-f423702ab568",
            "name": "Estúdio Exemplo",
            "onboarding_step": 2,
        }

    @patch.object(api.urllib.request, "urlopen")
    def test_criar_envia_jwt_e_nao_envia_owner_id(self, post):
        post.return_value = RespostaFalsa([self.registro])
        gravado = api.salvar_primeira_etapa("token-falso", self.dados)
        requisicao = post.call_args.args[0]
        enviado = json.loads(requisicao.data)
        self.assertEqual(requisicao.get_method(), "POST")
        self.assertEqual(enviado["onboarding_step"], 2)
        self.assertNotIn("owner_id", enviado)
        self.assertEqual(requisicao.get_header("Authorization"),
                         "Bearer token-falso")
        self.assertEqual(gravado["id"], self.registro["id"])

    @patch.object(api.urllib.request, "urlopen")
    def test_editar_usa_patch_com_id(self, post):
        post.return_value = RespostaFalsa([self.registro])
        api.salvar_primeira_etapa(
            "token-falso", self.dados, self.registro["id"]
        )
        requisicao = post.call_args.args[0]
        self.assertEqual(requisicao.get_method(), "PATCH")
        self.assertIn("id=eq.", requisicao.full_url)

    @patch.object(api.urllib.request, "urlopen")
    def test_buscar_retorna_primeiro_registro(self, get):
        get.return_value = RespostaFalsa([self.registro])
        retorno = api.obter_estabelecimento("token-falso")
        self.assertEqual(retorno["name"], "Estúdio Exemplo")
        self.assertEqual(get.call_args.args[0].get_method(), "GET")

    def test_nome_invalido_nao_chama_servidor(self):
        with self.assertRaises(api.ErroEstabelecimento):
            api.salvar_primeira_etapa(
                "token", {**self.dados, "name": "A"}
            )

    def test_sem_tipo_nao_chama_servidor(self):
        with self.assertRaises(api.ErroEstabelecimento):
            api.salvar_primeira_etapa(
                "token", {**self.dados, "business_type": ""}
            )


if __name__ == "__main__":
    unittest.main()
