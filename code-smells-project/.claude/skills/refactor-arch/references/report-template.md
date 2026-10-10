# Template do Relatório de Auditoria (Fase 2)

O relatório é impresso para o usuário **e** salvo em Markdown (ver SKILL.md, Fase 2 passo 5).
Reproduza exatamente a estrutura abaixo. Substitua `<...>`; mantenha cabeçalhos, separadores e
rótulos dos campos literalmente (em inglês, padrão do enunciado). Texto livre (descrição,
impacto, recomendação) em português.

## Regras
1. Findings ordenados **CRITICAL → HIGH → MEDIUM → LOW**; dentro de cada nível: segurança,
   depois arquitetura, depois o resto. Numere sequencialmente (`F01`, `F02`, …).
2. `File:` deve conter localizações exatas: `caminho:linha`, `caminho:início-fim` ou várias
   separadas por `, ` — caminhos relativos à raiz do projeto. Vários arquivos → uma linha `File:` por arquivo.
3. Todo finding referencia um ID do catálogo (`AP-xx` / `AP-DEP`) e um padrão do playbook (`P-xx`).
4. *Description* cita o código/valor concreto problemático (identificador, literal, query).
5. As contagens do Summary devem bater com o número de findings listados por nível, e `Total` com a soma.
6. A seção **Deprecated APIs** é obrigatória, mesmo vazia ("None detected for …").
7. Nenhum finding sem evidência; nenhum finding duplicado.

## Template

````markdown
================================
ARCHITECTURE AUDIT REPORT
================================
Project: <nome da pasta do projeto>
Stack:   <linguagem + versão> + <framework + versão> (<banco / estilo de acesso>)
Files:   <N> analyzed | ~<LOC> lines of code
Date:    <AAAA-MM-DD>

## Summary
CRITICAL: <n> | HIGH: <n> | MEDIUM: <n> | LOW: <n>

| # | Severity | Finding | Catalog | Location |
|---|---|---|---|---|
| F01 | CRITICAL | <título> | AP-xx | <primeiro arquivo:linha> |
| ... | | | | |

## Findings

### F01 [CRITICAL] <Título>
File: <caminho:linhas>
Catalog: AP-xx — <nome no catálogo>
Description: <o que está errado, citando o código problemático>
Impact: <consequência concreta neste projeto>
Recommendation: <o que fazer> (Playbook P-xx)

### F02 [HIGH] <Título>
File: <caminho:linhas>
Catalog: AP-xx — <nome no catálogo>
Description: ...
Impact: ...
Recommendation: ... (Playbook P-xx)

<... um bloco por finding ...>

## Deprecated APIs
| Location | Deprecated usage | Modern equivalent |
|---|---|---|
| <caminho:linha> | <chamada> | <substituto> |
<ou: "None detected for <stack + versões>.">

## Architecture Notes
- Current: <rótulo da arquitetura da Fase 1> — <por quê>
- Missing layers: <config | models | controllers | views/routes | error handling | composition root>
- Proposed target: <resumo em uma linha da estrutura MVC alvo>

================================
Total: <N> findings
================================
````

## Exemplo de finding (para calibração)

```markdown
### F02 [CRITICAL] SQL Injection
File: models.py:28, 47-50, 110
Catalog: AP-02 — SQL Injection
Description: Queries montadas por concatenação: `"SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'"`.
Impact: `POST /login` com email `' OR 1=1 --` autentica sem senha; qualquer tabela pode ser lida ou apagada.
Recommendation: Usar queries parametrizadas (`?` + tupla de parâmetros) em todo acesso a dados (Playbook P-02).
```
