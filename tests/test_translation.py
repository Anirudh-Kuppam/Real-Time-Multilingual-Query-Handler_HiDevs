from backend.translation_engine import translate_local


def test_translate_local_identity():
    s = "Bonjour, j'ai un problème avec ma commande"
    out = translate_local(s)
    assert isinstance(out, str)