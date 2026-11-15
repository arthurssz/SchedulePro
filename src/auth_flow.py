"""Fluxo OAuth Google/Supabase com PKCE para o teste inicial no Android.

A sessão NÃO é persistida nesta etapa. Persistência segura, refresh e logout
serão implementados antes de usar o aplicativo com dados reais.
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


def completar_google(codigo: str, verificador: str) -> str:
    """Troca o código PKCE por sessão e retorna somente o e-mail de teste."""
    payload = json.dumps(
        {"auth_code": codigo, "code_verifier": verificador}
    ).encode("utf-8")
    requisicao = urllib.request.Request(
        f"{SUPABASE_URL}/auth/v1/token?grant_type=pkce",
        data=payload,
        headers={
            "apikey": SUPABASE_PUBLISHABLE_KEY,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(requisicao, timeout=25) as resposta:
            dados = json.load(resposta)
    except urllib.error.HTTPError as erro:
        raise RuntimeError(
            "O Supabase não conseguiu validar o retorno do Google."
        ) from erro

    usuario = dados.get("user") or {}
    email = usuario.get("email")
    if not email:
        raise RuntimeError("O Google não retornou um e-mail válido.")
    # Teste inicial: não grava tokens nem sessão em disco.
    return email
