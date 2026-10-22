# src/

Ödevin `src/` klasörü bu repoda Python paketi olarak [`../noncentra/`](../noncentra/) altındadır
(`pip install -e .` ile kurulur; paket adı ile klasör adı aynı olmalı).

| Katman | Yer |
|---|---|
| Hesap motoru (tek motor) | `noncentra/core/` (dağılımlar, çözücü), `noncentra/catalog/` (test modelleri) |
| CLI (`gpower-clone`) | `noncentra/contract.py` (ince adaptör) + `noncentra/contract_cli.py` |
| MCP sunucusu (`gpower-clone-mcp`) | `noncentra/mcp_contract.py` |
| AI ajanı (`noncentra-agent`) | `noncentra/agent/` |

CLI, MCP ve ajan hesap yapmaz; hepsi `noncentra.contract.run()` üzerinden motoru çağırır.
