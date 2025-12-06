# 🔴 Zero Vermelhos

Contador de dias desde a última expulsão do Benfica na Primeira Liga.

**Site:** [www.zerovermelhos.live](https://www.zerovermelhos.live)

## Actualização Automática

Este repositório inclui um script que actualiza automaticamente os dados todas as **terças-feiras às 11:00 (hora de Lisboa)**.

### Configuração (uma única vez)

1. **Criar conta gratuita na API-Football**
   - Vai a [rapidapi.com/api-sports/api/api-football](https://rapidapi.com/api-sports/api/api-football)
   - Cria conta gratuita (100 requests/dia - mais que suficiente!)
   - Copia a tua API Key

2. **Adicionar API Key ao GitHub**
   - Vai a Settings → Secrets and variables → Actions
   - Clica "New repository secret"
   - Nome: `RAPIDAPI_KEY`
   - Valor: (cola a tua API key)
   - Clica "Add secret"

3. **Pronto!** O GitHub Actions vai:
   - Correr todas as terças-feiras automaticamente
   - Verificar a API por novos cartões vermelhos
   - Actualizar o site se houver mudanças

### Trigger Manual

Podes também correr a actualização manualmente:
1. Vai a Actions → "Update Red Cards Data"
2. Clica "Run workflow"

## Actualização Manual (sem API)

Se preferires não usar a API, podes actualizar manualmente:

1. Edita `scripts/update_red_cards.py`
2. Modifica a secção `MANUAL_DATA`:

```python
MANUAL_DATA = {
    "enabled": True,  # Muda para True
    "date": "2025-08-31",
    "player": "Nome do Jogador",
    "match": "Equipa A 1 - 2 Equipa B",
    "minute": "70'",
    "card_type": "Second Yellow",  # ou "Red Card"
    "sporting_reds": 0,
    "porto_reds": 0,
}
```

3. Corre localmente:
```bash
python scripts/update_red_cards.py --manual
```

4. Faz commit e push

## Estrutura do Projecto

```
zerovermelhos/
├── index.html              # Página principal
├── CNAME                   # Domínio personalizado
├── requirements.txt        # Dependências Python
├── README.md               # Este ficheiro
├── scripts/
│   └── update_red_cards.py # Script de actualização
└── .github/
    └── workflows/
        └── update-red-cards.yml  # GitHub Action
```

## Correr Localmente

```bash
# Instalar dependências
pip install -r requirements.txt

# Verificar estado actual
python scripts/update_red_cards.py --check

# Actualizar via API (requer RAPIDAPI_KEY)
export RAPIDAPI_KEY="tua-chave-aqui"
python scripts/update_red_cards.py --api

# Actualizar manualmente
python scripts/update_red_cards.py --manual
```

## Dados Actualizados

O script actualiza automaticamente:
- ✅ Data da última expulsão do Benfica
- ✅ Nome do jogador expulso
- ✅ Jogo onde aconteceu
- ✅ Minuto da expulsão
- ✅ Tipo de cartão (vermelho directo ou segundo amarelo)
- ✅ Vermelhos do Sporting no mesmo período
- ✅ Vermelhos do Porto no mesmo período

---

**Nota:** A tabela de "streaks" históricos é mantida manualmente.

