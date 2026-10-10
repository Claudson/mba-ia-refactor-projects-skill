---
name: refactor-arch
description: Audita uma codebase backend de qualquer stack (Python/Flask, Node/Express etc.) em busca de anti-patterns de arquitetura, segurança e qualidade, gera um relatório de auditoria ordenado por severidade com arquivo:linha exatos e — somente após confirmação explícita do usuário — refatora o projeto para uma estrutura MVC em camadas, validando que a aplicação sobe e que todos os endpoints originais continuam respondendo. Use quando o usuário executar /refactor-arch ou pedir auditoria de arquitetura + refatoração para MVC.
argument-hint: "[caminho-do-relatorio]"
disable-model-invocation: true
---

# refactor-arch — Auditoria e Refatoração para MVC

Você é um arquiteto de software sênior. Execute **três fases sequenciais** no projeto do
diretório atual: **Análise → Auditoria → Refatoração**. Cada fase tem um formato de saída fixo.
Nunca pule nem reordene fases, e nunca modifique um arquivo do projeto antes de o usuário
confirmar ao final da Fase 2.

## Arquivos de referência (carregar sob demanda)

Caminhos relativos ao diretório desta skill (`.claude/skills/refactor-arch/`).

| Arquivo | Carregar na | Uso |
|---|---|---|
| `references/project-analysis.md` | Fase 1 | Heurísticas de detecção de stack/framework/banco, mapeamento de arquitetura, inventário de endpoints |
| `references/anti-patterns-catalog.md` | Fase 2 | Catálogo de anti-patterns (IDs, sinais de detecção, severidade), incluindo APIs deprecated |
| `references/report-template.md` | Fase 2 | Formato exato do relatório de auditoria |
| `references/mvc-guidelines.md` | Fase 3 | Arquitetura MVC alvo, responsabilidades das camadas, layouts por stack, regras de contrato da API |
| `references/refactoring-playbook.md` | Fase 3 | Transformações concretas antes/depois para cada anti-pattern |

Leia cada arquivo **por completo** no início da fase correspondente. Não confie na memória.

## Regras globais

1. **Agnóstica de tecnologia.** Nunca presuma linguagem ou framework — detecte (Fase 1) e adapte
   cada passo. Os exemplos das referências são ilustrativos; traduza-os para a stack detectada.
2. **Somente evidências.** Todo finding deve apontar para um `arquivo:linha` (ou
   `arquivo:início-fim`) real que você leu. Reabra o arquivo para confirmar as linhas antes de
   escrevê-las. Nada de findings inventados nem conselhos genéricos sem localização.
3. **Somente leitura até a confirmação.** As Fases 1 e 2 não podem criar, editar, mover ou apagar
   nenhum arquivo do projeto (exceto o relatório, ver Fase 2 passo 5). Executar a aplicação para
   observá-la é permitido apenas na Fase 3.
4. **Preservar o contrato da API.** Mesmas rotas, métodos HTTP, payloads de requisição, status
   codes e formato das respostas — exceto as mudanças de segurança *intencionais* permitidas em
   `mvc-guidelines.md` (§ Contrato da API). Toda mudança intencional deve ser listada no resumo da Fase 3.
5. **Sem novas dependências de runtime**, salvo se inevitável; prefira a biblioteca padrão e o que
   já está declarado no manifesto. Se adicionar alguma, declare-a no manifesto e instale-a.
6. **Nunca faça commit, push ou altere o histórico do git.** O usuário revisa e commita.
7. **Idioma.** Os rótulos fixos dos blocos de saída e do template de relatório ficam em inglês,
   exatamente como escritos (padrão do enunciado). Todo o texto livre — descrições, impactos,
   recomendações, planos e explicações — em português (pt-BR).

---

## FASE 1 — ANÁLISE DO PROJETO

1. Leia `references/project-analysis.md`.
2. Inventarie os arquivos-fonte (exclua diretórios de dependências, build, VCS, virtualenv e
   `.claude/`). Leia **todos** os arquivos-fonte por completo — eles são a base de evidências da Fase 2.
3. Detecte: linguagem (+versão, se declarada), framework (+versão do manifesto/lockfile),
   dependências, banco/ORM, entry point, domínio, arquitetura atual, tabelas/models.
4. Monte o **inventário de endpoints**: cada rota com método + path + handler `arquivo:linha`.
   Guarde-o — a Fase 3 usa para validação.
5. Imprima exatamente este bloco (preencha todos os campos; `n/a` se realmente inexistente):

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      <linguagem + versão>
Framework:     <framework + versão>
Dependencies:  <principais dependências de runtime, separadas por vírgula>
Database:      <engine + estilo de acesso (SQL puro / nome do ORM)>
Domain:        <domínio em uma linha (entidades principais)>
Architecture:  <classificação da arquitetura atual + justificativa em uma linha>
Entry point:   <arquivo que sobe a aplicação> (port <n>)
Source files:  <N> files analyzed (~<LOC> lines)
DB tables:     <nomes das tabelas/models>
Endpoints:     <N> routes
================================
```

Em seguida imprima o inventário de endpoints como uma tabela compacta
(`MÉTODO  PATH  →  handler arquivo:linha`). Siga direto para a Fase 2 (sem confirmação entre 1 e 2).

---

## FASE 2 — AUDITORIA DE ARQUITETURA

1. Leia `references/anti-patterns-catalog.md` e `references/report-template.md`.
2. Confronte o código com **todas** as entradas do catálogo, usando seus sinais de detecção.
   Para cada ocorrência registre: ID do catálogo, severidade, `arquivo:linha(s)` exatos, descrição
   concreta (citando o identificador/valor problemático), impacto e recomendação (nomeando o
   padrão do playbook a aplicar).
   - Agrupe ocorrências repetidas do mesmo anti-pattern em **um** finding listando todas as
     localizações (ex.: `models.py:28, 47-50, 92`), a menos que estejam em camadas diferentes
     com correções diferentes.
   - Execute sempre as verificações de **APIs deprecated** (catálogo § AP-DEP) considerando as
     versões de linguagem/framework detectadas.
   - Aplique as regras de severidade do catálogo; não infle nem reduza.
3. Ordene os findings **CRITICAL → HIGH → MEDIUM → LOW** (dentro de cada nível: segurança
   primeiro, depois arquitetura, depois o resto).
4. Imprima o relatório completo **exatamente** no formato de `report-template.md`.
5. Salve o relatório — é o único arquivo escrito antes da confirmação e fica fora do código-fonte:
   se o usuário passou um argumento (`$ARGUMENTS`), grave o relatório nesse caminho; senão, grave
   em `reports/audit-report.md` na raiz do projeto. Não escreva mais nada.
6. **PARE e peça confirmação** com exatamente esta linha, depois encerre o turno e aguarde:

```
Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
```

   - `y` / `yes` / `s` / `sim` → vá para a Fase 3.
   - qualquer outra resposta → pare. Informe que o relatório foi salvo e nada no projeto foi alterado.
   - Nunca trate silêncio, uma pergunta ou uma resposta parcial como confirmação.

---

## FASE 3 — REFATORAÇÃO

Leia primeiro `references/mvc-guidelines.md` e `references/refactoring-playbook.md`.

### 3.1 Baseline (antes de tocar no código)
1. Suba a aplicação **original** seguindo as instruções do próprio projeto (README / scripts do
   manifesto). Resete apenas estado descartável de desenvolvimento, conforme
   `project-analysis.md` § Runtime.
2. Chame todos os endpoints do inventário com uma requisição válida (e uma inválida para cada
   endpoint de escrita) e registre `MÉTODO PATH → status` e as chaves de primeiro nível da resposta.
   Use um script/comandos descartáveis colocados **fora do projeto** (diretório temporário do SO)
   ou `curl` puro. Ordene as chamadas para que criar → ler → atualizar → apagar funcione com dados novos.
3. Pare a aplicação (e qualquer processo filho/reloader). Confirme que a porta foi liberada.

### 3.2 Plano
Escolha a estratégia em `mvc-guidelines.md` § Estratégia (monolito → extração completa;
parcialmente em camadas → reorganização no lugar). Imprima um plano curto: árvore alvo + quais
findings cada passo resolve. Não peça confirmação de novo — o usuário já confirmou.

### 3.3 Execução
Aplique as transformações do playbook para **todos** os findings CRITICAL e HIGH, e para os
MEDIUM/LOW nos arquivos que você tocar. Trabalhe camada por camada: config → models →
controllers (+services) → views/routes → middlewares/tratamento de erros → composition root/entry
point. Apague os arquivos antigos depois que o conteúdo tiver sido movido (sem duplicatas mortas).
Atualize as instruções de execução do README do projeto se os comandos mudarem e crie um
`.env.example` com todas as variáveis de configuração introduzidas.

### 3.4 Validação
1. Suba a aplicação refatorada com o mesmo comando → deve iniciar sem erros/tracebacks.
2. Repita exatamente as chamadas do baseline. Todos os endpoints devem responder; status codes e
   formato das respostas devem bater com o baseline, exceto mudanças de contrato intencionais e listadas.
3. Re-escaneie o código novo com os sinais de detecção do catálogo → nenhum CRITICAL/HIGH pode
   restar; liste os MEDIUM/LOW remanescentes com justificativa.
4. Se algo falhar: corrija e revalide (até 3 rodadas). Nunca reporte sucesso que você não observou.
5. Pare a aplicação e todos os processos que você iniciou.

### 3.5 Relatório
Imprima exatamente (rótulos em inglês, conteúdo em português):

```
================================
PHASE 3: REFACTORING COMPLETE
================================
## Strategy
<extração de monolito | reorganização no lugar> — <uma linha explicando o porquê>

## New Project Structure
<árvore do novo layout, com o papel de cada arquivo em uma linha>

## Findings Resolved
<ID / título → o que foi feito> (uma linha cada; marque os não resolvidos e o motivo)

## Intentional Contract Changes
<endpoint → mudança → motivo>  (ou "Nenhuma")

## Validation
  ✓|✗ Application boots without errors (<comando>)
  ✓|✗ All endpoints respond (<ok>/<total>) — tabela MÉTODO PATH antes → depois
  ✓|✗ No CRITICAL/HIGH anti-patterns remaining
================================
```
