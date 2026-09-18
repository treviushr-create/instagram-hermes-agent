# Instagram Social Selling — Hermes agent

Um [Hermes agent](https://github.com/plow-pbc/plow-hermes-agent) que ajuda o
dono de um Instagram comercial a nunca perder um lead no Direct: percebe DM e
comentário, qualifica, rascunha uma resposta, manda pro dono aprovar por
mensagem, e só envia depois de aprovado. Ver o loop completo em
[`skills/instagram-social-selling/SKILL.md`](skills/instagram-social-selling/SKILL.md).

Feito pro [Hermes Hackathon](https://luma.com/3uftu95w) (AI Worth Using / Plow).
Licença MIT.

## Estado atual

- Persona (`runtime/persona.md`) e skill (`skills/instagram-social-selling/`)
  escritos.
- Dockerfile no formato de variant image real da Plow, com o reporter de uso
  do Agent Index já cabeado (`image/s6-overlay/s6-rc.d/agent-index/`), pinado
  em `vendor/client.pin`. Builda limpo local e via `plow-agents image build`.
- `compose.yml` pronto pro fluxo local do `plow-agents`.
- `plugins/instagram_tools/` — `qualify` é real e testado
  (`qualification.py`; `python3 demo_local.py` mostra funcionando).
  `fetch_new_signals`/`send_reply` já chamam a API do Instagram de verdade
  (`graph_api.py`), faltando as credenciais reais da conta.
- Imagem publicada em `ghcr.io/treviushr-create/instagram-hermes-agent`.
- Deploy na nuvem da Plow pedido, ainda falhando com
  `failed(provider_unreachable)` — não é a nossa imagem (isso daria
  `image_pull_timeout` ou `setup_failed`); é o gateway do lado da Plow não
  alcançando o provedor de IA deles. Acompanhando no Discord do hackathon.

## O que falta pra rodar (nessa ordem)

1. **Meta app** (Instagram Business Login, conta própria, sem CNPJ — modo
   Tester cobre os primeiros usuários reais sem precisar de App Review):
   `INSTAGRAM_ACCESS_TOKEN` e `INSTAGRAM_BUSINESS_ACCOUNT_ID`.
2. **Resolver o `provider_unreachable`** no deploy cloud (ou testar local via
   `docker compose up --build`, sabendo que emulação amd64 em Mac Apple
   Silicon pode causar um segfault não-fatal num script de setup).
3. **Registrar o agente no Agent Index** antes do build final:
   ```sh
   curl -O https://raw.githubusercontent.com/plow-pbc/agent-index-client/f900ff144076f0a766584b6ec4d0993600779b16/standalone/agent_index_client.py
   set -a; . ./plow-credentials; set +a
   python3 agent_index_client.py --register --agent "instagram-social-selling" --name "Instagram Social Selling" --blurb "Draft-and-approve Instagram DM replies for a seller"
   ```
   Confirmar que o `AGENT_ID` em `compose.yml` bate com o id registrado aqui.

## Por que é um Hermes agent, não um dashboard web

Um Hermes agent é uma imagem Docker com persona/skills em markdown, amarrada a
uma linha de telefone da Plow — instala mandando SMS, não abrindo uma URL.
Não é o formato certo pra um dashboard web multi-tenant, que é um produto
diferente e pode existir separadamente depois — mas o que o hackathon julga
é isto aqui.
