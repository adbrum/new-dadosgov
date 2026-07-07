# Bloqueio de verbos HTTP (PUT/PATCH/DELETE) pelo WAF — Síntese para a equipa

## Contexto do problema

O WAF **NetScaler/Citrix ADC** que está à frente dos ambientes de pré-produção (`ppr-dadosgov.arte.gov.pt`) e de produção aplica uma regra de *HTTP Verb Tampering* que **bloqueia qualquer pedido cujo método não seja `GET` ou `POST`**.

Consequências observadas:

- Todos os pedidos `PUT`, `PATCH` e `DELETE` são rejeitados **antes** de chegarem à aplicação (backend Flask), pelo que **não aparecem nos logs da aplicação**.
- O bloqueio surge como um `HTTP 500` com página HTML do WAF (identificável pelo cookie `cookie_adc_ext` e pelo `Attack ID: 20000001`).
- Na prática, todas as operações de escrita da plataforma falham — por exemplo, a edição de perfil (`PUT /api/1/me/`) e as 43 chamadas mutantes existentes no frontend.

> Nota: este bloqueio **não** tem relação com o *hardening* de CORS do KITS24 (VULN-1496/1550). A restrição de CORS atua sobre a **origem**, não sobre os métodos. O filtro de verbos está configurado na camada do WAF, fora do repositório da aplicação.

## Opções de resolução

Existem, no essencial, **duas vias** para resolver o problema. Não são mutuamente exclusivas.

### Opção A — Ajustar a política do WAF (via de infraestrutura)

Permitir explicitamente os métodos `PUT`, `PATCH` e `DELETE` na regra de *HTTP Verb Tampering* do NetScaler ADC, para os caminhos da API (`/api/1/*` e `/api/2/*`).

- **Prós:** é a resolução "limpa" e definitiva; mantém a semântica REST original; não exige alterações na aplicação.
- **Contras:** depende da equipa de infraestrutura/segurança que gere o WAF; pode entrar em conflito com políticas de segurança corporativas; requer validação e aprovação do lado da rede.
- **Responsável:** equipa de infraestrutura/rede (gestão do NetScaler ADC).

### Opção B — Túnel dos verbos via cabeçalho `X-HTTP-Method-Override` (via aplicacional) — **já implementada**

Encaminhar os verbos mutantes dentro de um pedido `POST` que transporta o cabeçalho `X-HTTP-Method-Override: <verbo>`. O WAF deixa passar o `POST` (não inspeciona o cabeçalho) e a aplicação reescreve o método real antes do *routing*.

```
Browser ──POST + X-HTTP-Method-Override: PUT──► WAF (deixa passar) ──► Flask (reescreve para PUT) ──► handler real
```

- **Prós:** resolve o problema **sem depender de alterações no WAF**; é um padrão consagrado na indústria (Rails, Symfony, Laravel, ASP.NET Core); já está desenvolvido e testado; é *opt-in* e reversível.
- **Contras:** introduz um ponto de "verb tampering" controlado (mitigado — ver abaixo); nos logs de acesso as operações destrutivas aparecem como `POST` (é necessário correlacionar com o cabeçalho de override para auditoria).
- **Responsável:** equipa de desenvolvimento (já pronto para promoção).

## Estado atual da Opção B

A solução aplicacional **já está desenvolvida, testada e documentada**, a aguardar promoção pelos ambientes:

| Componente | Onde | Estado |
|---|---|---|
| Middleware WSGI (backend) | `backend/udata/method_override.py` + ligação em `app.py` | Em branch `feat/http-method-override` (PR draft #132 para `develop`) |
| Túnel no frontend | `frontend/src/services/api.ts` (`applyMethodOverride`) | Em branch `feat/http-method-override` (PR draft #374 para `develop`) |
| Testes | 14 testes backend + 9 testes frontend | Incluídos |
| Documentação técnica completa | `docs/http-method-override.md` | Já integrada na `main` do monorepo |

### Como se ativa

O comportamento no frontend é **opt-in** através da variável de *build*:

| Ambiente | `NEXT_PUBLIC_USE_METHOD_OVERRIDE` | Motivo |
|---|---|---|
| Desenvolvimento local | `false` (por omissão) | O backend local não tem WAF; os verbos reais funcionam e são mais fáceis de depurar. |
| Pré-produção (PPR) | `true` | O NetScaler ADC bloqueia métodos não-GET/POST. |
| Produção (PRD) | `true` | Mesma política de WAF que PPR. |

> As variáveis `NEXT_PUBLIC_*` são embebidas no *build*. Após alterar o valor, o frontend **tem de ser reconstruído (`npm run build`) e reiniciado**.

O middleware do backend está **sempre ativo** e é inofensivo quando não há cabeçalho de override presente — não precisa de *toggle* do lado do Flask.

### Garantias de segurança da Opção B

- Só pedidos `POST` podem transportar override — um `GET` com o cabeçalho é **ignorado** (evita *smuggling* por métodos cacheáveis).
- Apenas `PUT`, `PATCH` e `DELETE` são aceites como alvos de override; qualquer outro verbo é rejeitado.
- O cabeçalho é removido após consumo, para que o código a jusante veja um pedido limpo.
- O método original é preservado (`environ["udata.original_method"]`) para efeitos de auditoria.
- Sem impacto em CSRF (os blueprints da API já estão `csrf.exempt`) nem em CORS (o *preflight* espelha automaticamente o cabeçalho).
- Os *rate limits* por endpoint continuam corretos (o limitador corre depois da reescrita do método).

## Recomendação

1. **Curto prazo:** promover a **Opção B** (já pronta) pelos ambientes `develop → tst → ppr → main`, ativando `NEXT_PUBLIC_USE_METHOD_OVERRIDE=true` em PPR e PRD. Desbloqueia imediatamente todas as operações de escrita sem depender de terceiros.
2. **A avaliar com a equipa de infraestrutura:** decidir se se pretende, adicionalmente, ajustar a política do WAF (**Opção A**) para restabelecer a semântica REST original. Caso se avance com a Opção A, a Opção B pode ficar desativada (`false`) mas o middleware do backend pode permanecer no lugar sem qualquer efeito.

O ponto de *HTTP Verb Tampering (CWE-650)* introduzido pela Opção B deve ser registado para o próximo ciclo de auditoria KITS24, com a devida justificação (já contemplado na documentação técnica).

---
*Documentação técnica detalhada em `docs/http-method-override.md`.*
