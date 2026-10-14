"""Imita o osv-scanner: devolve a fixture com o caminho da pasta e sai com 1 (achou vuln)."""
import pathlib
import sys

pasta = sys.argv[-1]
texto = (pathlib.Path(__file__).with_name("osv-saida.json")).read_text(encoding="utf-8")
sys.stdout.write(texto.replace("{PASTA}", pasta))
sys.exit(1)
