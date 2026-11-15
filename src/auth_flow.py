"""Google OAuth com PKCE e renovação de sessões do Supabase.

Nenhum segredo de servidor é incluído no app. A chave publicável do
Supabase é segura para clientes, desde que as tabelas usem RLS.
"""

import base64
import hashlib
import json
import secrets
import urllib.error
import urllib.parse
import urllib.request

from supabase_config import (
    ANDROID_AUTH_REDIRECT,
    SUPABASE_PUBLISHABLE_KEY,
    SUPABASE_URL,
)


class SessaoInvalida(Exception):
    """A credencial local não pode mais ser renovada."""


def iniciar_google():
    """Retorna (verificador PKCE, URL para abrir no navegador)."""
    verificador = secrets.token_urlsafe(48)
    digest = hashlib.sha256(verificador.encode("ascii")).digest()
    desafio = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    parametros = urllib.parse.urlencode(
        {
            "provider": "google",
            "redirect_to": ANDROID_AUTH_REDIRECT,
            "flow_type": "pkce",
            "code_challenge": desafio,
            "code_challenge_method": "s256",
        }
    )
    return verificador, f"{SUPABASE_URL}/auth/v1/authorize?{parametros}"


def _receber_sessao(grant_type: str, dados: dict):
    """Obtém tokens e usuário usando a API pública de Auth do Supabase."""
    requisicao = urllib.request.Request(
        f"{SUPABASE_URL}/auth/v1/token?grant_type={grant_type}",
        data=json.dumps(dados).encode("utf-8"),
        headers={
            "apikey": SUPABASE_PUBLISHABLE_KEY,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(requisicao, timeout=25) as resposta:
            sessao = json.load(resposta)
    except urllib.error.HTTPError as erro:
        if grant_type == "refresh_token" and erro.code in (400, 401, 403):
            raise SessaoInvalida("Sessão expirada ou revogada.") from erro
        raise RuntimeError("Não foi possível validar a sessão.") from erro
    except (urllib.error.URLError, TimeoutError) as erro:
        raise ConnectionError("Não foi possível acessar o Supabase.") from erro

    usuario = sessao.get("user") or {}
    email = usuario.get("email")
    access_token = sessao.get("access_token")
    refresh_token = sessao.get("refresh_token")
    if not (email and access_token and refresh_token):
        raise RuntimeError("Resposta de autenticação incompleta.")
    return {
        "email": email,
        "access_token": access_token,
        "refresh_token": refresh_token,
    }


def completar_google(codigo: str, verificador: str):
    """Troca o código PKCE por uma sessão autenticada."""
    return _receber_sessao(
        "pkce", {"auth_code": codigo, "code_verifier": verificador}
    )


def renovar_sessao(refresh_token: str):
    """Renova a sessão; o Supabase rotaciona o token de renovação."""
    return _receber_sessao("refresh_token", {"refresh_token": refresh_token})


def encerrar_sessao(access_token: str):
    """Revoga a sessão deste dispositivo, sem sair dos outros aparelhos."""
    requisicao = urllib.request.Request(
        f"{SUPABASE_URL}/auth/v1/logout?scope=local",
        headers={
            "apikey": SUPABASE_PUBLISHABLE_KEY,
            "Authorization": f"Bearer {access_token}",
        },
        method="POST",
    )
    with urllib.request.urlopen(requisicao, timeout=15):
        pass
