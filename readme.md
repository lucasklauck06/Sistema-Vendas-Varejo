## Sistema de Vendas — Integração de 4 Bancos de Dados

Este repositório contém o trabalho final de integração de quatro bancos de dados distintos em um único sistema de vendas para loja: PostgreSQL (relacional), Neo4j (grafo), MongoDB (documentos) e Redis (cache). O objetivo foi projetar um fluxo realista onde cada tecnologia contribui com uma responsabilidade específica e os dados são consolidados entre as bases.

Principais pontos do projeto:
- Arquitetura integrada: cada base desempenha um papel claro — clientes, produtos e compras no `Postgres`; relacionamentos sociais (indicações/amigos) no `Neo4j`; interesses e origem de captura no `MongoDB`; cache de recomendações no `Redis`.
- Fluxo de compra completo: registra compras, atualiza estoque, registra indicações no grafo e guarda interesses no MongoDB.
- Motor de recomendações: consolida compras de amigos + interesses pessoais e salva um JSON no `Redis` como cache.
- Ferramentas administrativas: menus separados para testar cada base, listar e cadastrar dados, e uma opção para limpar apenas os dados (sem dropar bancos).

Onde está a integração:
- Veja o código principal em `Integracao/main.py` — ele orquestra as operações entre as quatro bases.

Pré-requisitos rápidos:
- Ter os quatro serviços rodando localmente: PostgreSQL, Neo4j, MongoDB e Redis.
- Python 3.8+ com as dependências: `psycopg2`, `neo4j`, `pymongo`, `redis`.

Como executar (exemplo rápido):
1. Inicie os serviços (Postgres, Neo4j, MongoDB, Redis).
2. Configure credenciais/hosts nos arquivos dentro de `Integracao/` se necessário.
3. Execute:

```bash
python Integracao/main.py
```


**Contribuições**
- **Lucas Sehn Klauck (@lucasklauck06)**: Autor principal — responsável pelo projeto, implementação e orquestração da integração entre PostgreSQL, Neo4j, MongoDB e Redis; desenvolvimento do `Integracao/main.py` e principais módulos.

Este trabalho demonstra como combinar tecnologias de bancos de dados distintas para construir um sistema coerente de vendas com recomendações e histórico — uma ótima vitrine de integração para aplicações reais.

Sinta-se à vontade para pedir um walkthrough, testes automatizados ou adicionar instruções de deploy.


