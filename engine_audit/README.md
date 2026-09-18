# Auditoria pendente antes de portar o motor

`grep -liE "davibraga|realdeal|kenosis" src/social_selling/*.py` no
`social-selling-control-plane` encontrou referências ao cliente em ~22 dos ~60
módulos — incluindo módulos que pareciam genéricos: `qualification.py` (2),
`ports.py` (1), e mais uma lista longa. Isso significa que **nenhum desses
arquivos vai direto pro `instagram-hermes-agent` sem passar por aqui primeiro**.

## Processo por arquivo, antes de copiar

1. Ler o arquivo inteiro (não só o grep) — referência ao cliente pode estar em
   exemplo de docstring, config default, nome de variável, ou lógica de
   negócio real específica do RealDeal (ex.: regras do "Método do Alívio").
2. Decidir: é (a) exemplo/docstring — troca por um genérico; (b) config
   default — vira parâmetro sem default específico; (c) regra de negócio do
   RealDeal de verdade — **não copia**, essa parte fica de fora e o
   `instagram-hermes-agent` implementa uma versão genérica própria.
3. Só depois de limpo, copiar pra `plugins/instagram_tools/` ou um pacote
   `engine/` novo, com teste próprio.

## Ordem sugerida (menor superfície primeiro)

1. `domain.py`, `ports.py` — tipos e interfaces, provavelmente a limpeza mais
   rápida.
2. `perception.py`, `rules.py`, `conduction.py` — 0 hits no grep, mas ainda
   precisam da leitura manual do passo 1.
3. `qualification.py` — 2 hits, provavelmente exemplos; confirmar antes de
   portar.
4. `governance.py`, `method.py`, `method_pack.py`, `arsenal.py` — a lógica de
   composição/guard; aqui é onde regra de negócio específica do RealDeal é
   mais provável de aparecer misturada com a genérica.

Não pular pra services/HTTP/webhook do control-plane — esses são específicos
da infra do Railway do RealDeal e não fazem sentido dentro da imagem Docker do
Hermes agent, que fala com a Meta API diretamente a partir de
`plugins/instagram_tools/`.

## Atualização: `rules.py` não é portável — decisão tomada

Lido o arquivo inteiro (2145 linhas). Não são referências pontuais ao
cliente — é um sistema de guarda inteiro construído incidente por incidente
("achado real 15/09", "caso real de 02/09") pro método de vendas de alto
ticket do Davi/RealDeal (perguntas de faturamento, "sessão de validação",
detecção de "closer", agendamento). Não vai ser portado, nem limpo — seria
reescrever do zero, e não é o trabalho certo pra esse hackathon.

**Por que isso está ok**: aquele motor precisa desse nível de guarda porque
envia sozinho, sem aprovação humana por mensagem, em escala. Este agente é
mais seguro por design — toda resposta passa pelo dono antes de sair (ver
SKILL.md). Por isso `plugins/instagram_tools/qualification.py` é uma
qualificação simples e nova (não um port), e é o tamanho certo pro que esse
agente realmente precisa.

Mesma lógica provavelmente vale pra `conduction.py`, `governance.py`,
`method.py`, `method_pack.py`, `arsenal.py` — não abrir esses esperando
portar; ler primeiro pra confirmar, mas o padrão encontrado em `rules.py`
sugere que são igualmente específicos do RealDeal.
