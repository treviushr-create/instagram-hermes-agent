# Instagram Social Selling — Hermes agent

Um [Hermes agent](https://github.com/plow-pbc/plow-hermes-agent) que ajuda o
dono de um Instagram comercial a nunca perder um lead no Direct: percebe DM e
comentário, qualifica, rascunha uma resposta, manda pro dono aprovar por
mensagem, e só envia depois de aprovado. Ver o loop completo em
[`skills/instagram-social-selling/SKILL.md`](skills/instagram-social-selling/SKILL.md).

Feito pro [Hermes Hackathon](https://luma.com/3uftu95w) (AI Worth Using / Plow).
Licença MIT.

## Estado atual

**Esqueleto, não funcional ainda.** O que existe:

- Persona (`runtime/persona.md`) e skill (`skills/instagram-social-selling/`)
  já escritos.
- Dockerfile no formato de variant image real da Plow, com o reporter de uso
  do Agent Index já cabeado (`image/s6-overlay/s6-rc.d/agent-index/`), pinado
  em `vendor/client.pin`.
- `compose.yml` pronto pro fluxo local do `plow-agents`.
- `plugins/instagram_tools/__init__.py` — **stub**. As três funções
  (`fetch_new_signals`, `qualify`, `send_reply`) lançam `NotImplementedError`
  de propósito: a integração real com a Meta API e com o motor de decisão do
  `social-selling-control-plane` ainda não foi portada. Ver
  [`engine_audit/README.md`](engine_audit/README.md) pro porquê e pra ordem
  certa de fazer isso — o motor original tem referências ao cliente
  (RealDeal/Davi) espalhadas até em módulos que pareciam genéricos, então
  nada vai ser copiado sem passar por uma limpeza arquivo a arquivo antes.

## O que falta pra rodar (nessa ordem)

1. **Trocar `FROM public.ecr.aws/e1h7x4a2/plow-cloud-agents:base-<sha>` no
   Dockerfile** pela tag `base-<sha>` atual publicada em
   [plow-pbc/plow-hermes-agent](https://github.com/plow-pbc/plow-hermes-agent).
2. **Instalar Docker Desktop** — não tinha nessa máquina quando este esqueleto
   foi criado.
3. **`plow-agents login`** (clonar
   [plow-pbc/plow-agents](https://github.com/plow-pbc/plow-agents), ativar por
   SMS no seu celular) e `plow-agents lines` pra pegar uma linha livre.
4. **Auditar e portar o motor** — seguir `engine_audit/README.md`, preencher
   `plugins/instagram_tools/__init__.py` de verdade.
5. **Registrar o agente no Agent Index** antes do primeiro build real:
   ```sh
   curl -O https://raw.githubusercontent.com/plow-pbc/agent-index-client/f900ff144076f0a766584b6ec4d0993600779b16/standalone/agent_index_client.py
   set -a; . ./plow-credentials; set +a
   python3 agent_index_client.py --register --agent "instagram-social-selling" --name "Instagram Social Selling" --blurb "Draft-and-approve Instagram DM replies for a seller"
   ```
   Confirmar que o `AGENT_ID` em `compose.yml` bate com o id registrado aqui.
6. **Build + rodar local** (depois dos passos acima):
   ```sh
   plow-agents deploy --local --line ln_xxx
   docker compose logs -f
   ```
7. **Meta app novo** (Instagram Business Login, separado do app do
   RealDeal/Davi) — abrir o processo de **App Review** o quanto antes: é o
   único gargalo aqui que não depende de código, e é o que decide se outras
   pessoas conseguem de fato conectar a própria conta e virar "install" de
   verdade no ranking do hackathon.

## Por que não é o `trevius-selling`

Um Hermes agent é uma imagem Docker com persona/skills em markdown, amarrada a
uma linha de telefone da Plow — instala mandando SMS, não abrindo uma URL. Não
é o formato certo pra um dashboard web multi-tenant. O `trevius-selling`
(Next.js) pode voltar depois como painel complementar, mas o que o hackathon
julga é isto aqui.
