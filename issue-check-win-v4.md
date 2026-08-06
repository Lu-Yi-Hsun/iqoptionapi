# Issue Proposal: Add `check_win_v4` compatibility for OB-CC result polling

## Title
`iqoptionapi`: adicionar `check_win_v4` compatível com `OB-CC`

## Environment / Context
- Repositório: `iqoptionapi` (branch `master`, commit `e2a198f`)
- Branch local de trabalho: `improve-obcc-checkwin-v4`
- Integração afetada: `OB-CC` (`python/obcc/api/iq_option.py` -> `get_result()` chama `check_win_v4`)
- Objetivo funcional do OB-CC: execução de ordens e análise/decisão de gráfico em tempo de execução.

## Problem statement
No source local da `iqoptionapi` (6.8.9.1), não existe o método:
- `IQ_Option.check_win_v4`

Isso quebra o fluxo de resultado de ordens no OB-CC em ambientes que importam esta versão do código-fonte local (ou versões sem `check_win_v4`), gerando falha de atributo em runtime na etapa de resolução de resultado.

## Repro steps
1. Rodar OB-CC com broker real/configuração ativa.
2. Chegar em um ciclo que chama `ResultEngine._check_internal()` após `ExecutionEngine`.
3. `IQOptionAdapter.get_result()` chama `IQOptionAPI.get_result()` (wrapper de `iqoptionapi`) -> `self._api.check_win_v4(order_id)`.
4. Sem `check_win_v4` disponível, ocorre:
   - `AttributeError: ... object has no attribute 'check_win_v4'`

## Expected behavior
`check_win_v4` deve existir e retornar estado/premio de forma não bloqueante para uso em polling externo do OB-CC.

## Actual behavior
`AttributeError` em versões da `iqoptionapi` sem `check_win_v4`, interrompendo resolução de ordens e o fluxo de operação.

## Proposed fix
Adicionar método compatível no `iqoptionapi/iqoptionapi/stable_api.py`:
- `check_win_v4(id_number, timeout=0)` com polling de `self.api.socket_option_closed`.
- Retornar:
  - `(True, 0.0)` para `win == "equal"`.
  - `(True, -(sum))` para `win == "loose"`.
  - `(True, win_amount - sum)` para vitória.
  - `(False, None)` quando `timeout` expira sem fechamento.

Sem quebrar comportamentos existentes de outros métodos.

## Validation
- Patch local aplicado em branch `improve-obcc-checkwin-v4` (commit `f876a20`).
- Teste unitário isolado adicionado em `tests/test_check_win_v4.py` cobrindo:
  - retorno de resultado resolvido (`equal`, `win`, `loose`);
  - timeout com retorno pendente.
- Resultado: `2 passed` no novo teste (`python3 -m pytest -q tests/test_check_win_v4.py`).

## Impact
- Restaura/garante a resolução de resultado de ordens no OB-CC sem depender de variações de versão onde `check_win_v4` já existe no site-packages.
