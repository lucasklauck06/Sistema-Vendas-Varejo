import sys
import json
# Importando os 4 módulos
import db_postgres
import db_neo4j
import db_mongo
import db_redis

# Configuração Neo4j
URI_NEO4J = "bolt://localhost:7687"
AUTH_NEO4J = ("neo4j", "unochapeco") 

# ==============================================================================
# LÓGICA DE INTEGRAÇÃO / CONSOLIDAÇÃO DE DADOS
# ==============================================================================
def gerar_recomendacoes_redis():
    """
    Simula a API: Consolida dados das Bases 1, 2 e 3 e grava na Base 4 (Redis).
    """
    print("\n=== GERADOR DE RECOMENDAÇÕES (CONSOLIDAÇÃO) ===")
    
    # --- MUDANÇA AQUI: LISTAR CLIENTES ANTES DE PEDIR CPF ---
    print("\n--- Clientes Disponíveis (PostgreSQL) ---")
    conn_listagem = db_postgres.conectar()
    if conn_listagem:
        try:
            cur = conn_listagem.cursor()
            cur.execute("SELECT COUNT(*) FROM Clientes;")
            total = cur.fetchone()[0]
            if not total:
                print("Nenhum cliente encontrado. Não é possível gerar recomendações.")
                conn_listagem.close()
                return
            # Se há clientes, mostra a lista (função existente)
            db_postgres.listar_clientes(conn_listagem)
        except Exception as e:
            print(f"Erro ao verificar clientes: {e}")
        finally:
            conn_listagem.close()
    else:
        print("(Não foi possível conectar ao Postgres para listar clientes)")
        return
    # --------------------------------------------------------

    cpf_alvo = input("Digite o CPF do usuário para gerar recomendações: ")
    
    # 1. Buscamos quem são os amigos desse usuário no Neo4j (Base 3)
    grafo = db_neo4j.GrafoDB(URI_NEO4J, AUTH_NEO4J)
    amigos_conectados = grafo.listar_amigos_de(cpf_alvo) # Retorna lista de dicts
    grafo.close()
    
    if not amigos_conectados:
        print("⚠️ Este usuário não tem amigos conectados no Grafo.")
        print("Dica: Faça uma compra na Opção 5 e indique um amigo primeiro.")
        return

    print(f"-> Encontrados {len(amigos_conectados)} amigos conectados.")
    
    # 2. Conectamos no Postgres para ver o que esses amigos compraram (Base 1)
    conn_pg = db_postgres.conectar()
    if not conn_pg: return

    lista_recomendacoes_produtos = []
    
    cursor = conn_pg.cursor()
    for amigo in amigos_conectados:
        cpf_amigo = amigo['amigo.cpf']
        nome_amigo = amigo['amigo.nome']
        
        # Descobre o ID desse amigo no Postgres pelo CPF
        cursor.execute("SELECT id FROM Clientes WHERE cpf = %s", (cpf_amigo,))
        res = cursor.fetchone()
        
        if res:
            id_pg_amigo = res[0]
            # Busca compras deste amigo (Usando a função nova que pedimos para adicionar)
            # Nota: Certifique-se que adicionou 'buscar_compras_por_cliente' no db_postgres.py
            if hasattr(db_postgres, 'buscar_compras_por_cliente'):
                compras = db_postgres.buscar_compras_por_cliente(conn_pg, id_pg_amigo)
                
                for c in compras:
                    lista_recomendacoes_produtos.append({
                        "indicado_por": nome_amigo,
                        "produto": c['produto'],
                        "categoria": c['tipo']
                    })
            else:
                print("❌ Erro: Função 'buscar_compras_por_cliente' não encontrada no db_postgres.py")
    
    conn_pg.close()

    # 3. Buscamos os interesses pessoais no MongoDB (Base 2)
    conn_pg = db_postgres.conectar()
    cursor = conn_pg.cursor()
    cursor.execute("SELECT id, nome FROM Clientes WHERE cpf = %s", (cpf_alvo,))
    usuario_pg = cursor.fetchone()
    conn_pg.close()

    interesses_pessoais = []
    nome_usuario = "Usuário sem compras"
    origem_captacao = None
    
    if usuario_pg:
        id_usuario, nome_usuario = usuario_pg
        dados_mongo = db_mongo.listar_interesses_cliente(id_usuario)
        if dados_mongo:
            interesses_pessoais = dados_mongo.get('interesses', [])
            origem_captacao = dados_mongo.get('origem_captacao', None)

    # 4. CONSOLIDAÇÃO FINAL (JSON)
    dados_consolidados = {
        "usuario": {
            "cpf": cpf_alvo,
            "nome": nome_usuario,
            "origem": origem_captacao
        },
        "interesses_pessoais": interesses_pessoais,
        "recomendacoes_baseadas_em_amigos": lista_recomendacoes_produtos
    }

    # 5. Salva no Redis (Base 4)
    db_redis.salvar_recomendacao(cpf_alvo, dados_consolidados)
    
    print("\n--- JSON GERADO (Salvo no Redis) ---")
    print(json.dumps(dados_consolidados, indent=4, ensure_ascii=False))


# ==============================================================================
# FLUXO DE COMPRA 
# ==============================================================================
# Substitua APENAS a função fluxo_compra_integrada no main.py

def fluxo_compra_integrada():
    print("\n=== NOVA COMPRA COM INDICAÇÃO (AUTO-CADASTRO) ===")
    conn_pg = db_postgres.conectar()
    if not conn_pg: return

    try:
        cursor = conn_pg.cursor()

        # [PASSO 1] Identificação do Cliente
        print("\n--- [1] Identificação do Cliente ---")

        # Verifica se há clientes cadastrados; se não, oferece cadastrar ou sair
        try:
            cursor.execute("SELECT COUNT(*) FROM Clientes;")
            total_clientes = cursor.fetchone()[0]
        except Exception as e:
            print(f"Erro ao verificar clientes: {e}")
            return

        id_cliente = None
        if total_clientes == 0:
            escolha = input("Nenhum cliente encontrado. Deseja cadastrar agora? (S/N): ").strip().upper()
            if escolha == 'S':
                id_cliente = db_postgres.criar_cliente(conn_pg)
                if not id_cliente: return
            else:
                print("Operação cancelada.")
                return
        else:
            db_postgres.listar_clientes(conn_pg)
            entrada_cliente = input("Digite o ID do Cliente (ou 'N' para cadastrar novo): ")

            if entrada_cliente.upper() == 'N':
                id_cliente = db_postgres.criar_cliente(conn_pg)
                if not id_cliente: return
            else:
                id_cliente = entrada_cliente
                cursor.execute("SELECT id FROM Clientes WHERE id = %s", (id_cliente,))
                if not cursor.fetchone():
                    print(f"⚠️ Cliente {id_cliente} não encontrado.")
                    if input("Cadastrar agora? (S/N): ").upper() == 'S':
                        id_cliente = db_postgres.criar_cliente(conn_pg)
                        if not id_cliente: return
                    else: return

        # Pega nome atualizado
        cursor.execute("SELECT cpf, nome FROM Clientes WHERE id = %s", (id_cliente,))
        cpf_cliente, nome_cliente = cursor.fetchone()
        print(f"✅ Cliente: {nome_cliente}")

        # [PASSO 2] Seleção do Produto
        print("\n--- [2] Seleção do Produto ---")

        compras_pendente = []  # lista de (id_produto, quantidade)

        while True:
            db_postgres.listar_produtos(conn_pg)
            entrada_prod = input("Digite o ID do Produto (ou 'N' para novo): ")

            if entrada_prod.upper() == 'N':
                id_produto = db_postgres.criar_produto(conn_pg)
                if not id_produto:
                    continue
            else:
                id_produto = entrada_prod
                cursor.execute("SELECT id FROM Produtos WHERE id = %s", (id_produto,))
                if not cursor.fetchone():
                    if input("Produto não existe. Cadastrar? (S/N): ").upper() == 'S':
                        id_produto = db_postgres.criar_produto(conn_pg)
                        if not id_produto:
                            continue
                    else:
                        return

            # Pergunta quantidade
            try:
                quantidade = int(input("Quantidade desejada: ").strip())
                if quantidade <= 0:
                    print("Quantidade deve ser maior que zero.")
                    continue
            except ValueError:
                print("Quantidade inválida.")
                continue

            # Tenta decrementar estoque (os commits serão feitos ao final)
            if not db_postgres.decrementar_estoque(conn_pg, id_produto, quantidade):
                print("Não foi possível reservar a quantidade solicitada. Tente outro produto ou ajuste a quantidade.")
                if input("Deseja tentar outro produto? (S/N): ").strip().upper() == 'S':
                    continue
                else:
                    conn_pg.rollback()
                    return

            compras_pendente.append((id_produto, quantidade))

            if input("Deseja adicionar outro produto? (S/N): ").strip().upper() != 'S':
                break

        # Grava todas as compras e commita uma vez
        try:
            for pid, qty in compras_pendente:
                for _ in range(qty):
                    cursor.execute("INSERT INTO Compras (id_cliente, id_produto) VALUES (%s, %s)", (id_cliente, pid))
            conn_pg.commit()
            print(f"✅ Estoque atualizado e Compra registrada no Postgres.")
        except Exception as e:
            print(f"❌ Erro ao registrar compra: {e}")
            conn_pg.rollback()
            return

        # =========================================================

        # [PASSO 4] INDICAÇÃO / ORIGEM
        print("\n--- [3] Indicação / Origem ---")
        entrada_indicacao = input("CPF do Amigo (ou 'N' para nenhum / 'O' para outra origem): ")
        
        origem_captacao = None 

        if entrada_indicacao.strip().upper() == 'N':
            print("ℹ️ Nenhuma indicação registrada.")
        
        elif entrada_indicacao.strip().upper() == 'O':
            origem_captacao = input("Onde o cliente viu a loja? (Anuncio, Folder, Fachada...): ")
            print(f"📝 Origem '{origem_captacao}' registrada.")
            
        else:
            cpf_amigo = entrada_indicacao
            nome_amigo = input("Nome do Amigo: ")
            
            try:
                grafo = db_neo4j.GrafoDB(URI_NEO4J, AUTH_NEO4J)
                grafo.criar_pessoa(id_cliente, cpf_cliente, nome_cliente)
                grafo.criar_pessoa(0, cpf_amigo, nome_amigo)
                grafo.adicionar_amizade(cpf_cliente, cpf_amigo)
                grafo.close()
                print("✅ Vínculo de amizade criado no Neo4j.")
            except Exception as e:
                print(f"⚠️ Erro ao conectar no Neo4j: {e}")

        # [PASSO 5] MONGODB
        print("\n--- [4] Interesses (MongoDB) ---")
        entrada_interesses = input(f"Quais os interesses de {nome_cliente}? (ex: Tech, Viagem) ou 'N' para pular: ")
        
        lista_interesses = []
        if entrada_interesses.strip().upper() == 'N':
            print("ℹ️ Cadastro de interesses pulado.")
        elif entrada_interesses.strip():
            lista_interesses = [x.strip() for x in entrada_interesses.split(',')]
            
        if lista_interesses or origem_captacao:
            db_mongo.adicionar_interesses(id_cliente, nome_cliente, lista_interesses, origem=origem_captacao)
        else:
            print("Nenhum dado extra para salvar no Mongo.")

        # [FINAL]
        db_redis.limpar_cache()
        print("\n✨ FLUXO FINALIZADO! ✨")

    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        conn_pg.rollback() # Desfaz alterações se der erro no meio
    finally:
        if conn_pg: conn_pg.close()

# ==============================================================================
# MENU E VERIFICAÇÕES
# ==============================================================================
def verificar_tudo():
    print("🔄 Verificando serviços...")
    pg = db_postgres.testar_conexao()
    print(f"{'✅' if pg else '❌'} Postgres")
    
    neo = False
    try:
        g = db_neo4j.GrafoDB(URI_NEO4J, AUTH_NEO4J)
        if g.verificar_conexao(): neo = True
        g.close()
    except: pass
    print(f"{'✅' if neo else '❌'} Neo4j")
    
    mongo = db_mongo.testar_conexao_mongo()
    print(f"{'✅' if mongo else '❌'} Mongo")
    
    red = db_redis.testar_conexao_redis()
    print(f"{'✅' if red else '❌'} Redis")
    
    return pg and neo and mongo and red

def menu():
    while True:
        print("\n=== SISTEMA 4 BASES (INTEGRAÇÃO TOTAL) ===")
        print("1. Postgres (Admin)")
        print("2. Neo4j (Visualizar)")
        print("3. Mongo (Interesses)")
        print("4. Redis (Cache/Consulta)")
        print("-" * 30)
        print("5. REALIZAR COMPRA")
        print("6. GERAR RECOMENDAÇÕES")
        print("7. Cadastrar Cliente")
        print("8. Cadastrar Produto")
        print("9. Listar Compras")
        print("10. Limpar Dados (PG, Neo4j, Mongo, Redis)")
        print("0. Sair")
        
        op = input("Opção: ")
        if op == '1':
            db_postgres.menu()
        elif op == '2':
            db_neo4j.menu_grafo()
        elif op == '3':
            db_mongo.menu_mongo()
        elif op == '4':
            db_redis.menu_redis()
        elif op == '5':
            fluxo_compra_integrada()
        elif op == '6':
            gerar_recomendacoes_redis()
        elif op == '7':
            conn = db_postgres.conectar()
            if conn:
                db_postgres.criar_cliente(conn)
                conn.close()
            else:
                print("Não foi possível conectar ao Postgres.")
        elif op == '8':
            conn = db_postgres.conectar()
            if conn:
                db_postgres.criar_produto(conn)
                conn.close()
            else:
                print("Não foi possível conectar ao Postgres.")
        elif op == '9':
            conn = db_postgres.conectar()
            if conn:
                db_postgres.listar_compras(conn)
                conn.close()
            else:
                print("Não foi possível conectar ao Postgres.")
        elif op == '10':
            confirm = input("ATENÇÃO: Isso removerá TODOS os dados das 4 bases. Continuar? (S/N): ").strip().upper()
            if confirm != 'S':
                print("Operação de limpeza cancelada.")
                continue

            # Postgres
            try:
                db_postgres.limpar_dados_postgres()
            except Exception as e:
                print(f"Erro limpando Postgres: {e}")

            # Neo4j
            try:
                db_neo4j.limpar_grafo()
            except Exception as e:
                print(f"Erro limpando Neo4j: {e}")

            # MongoDB
            try:
                db_mongo.limpar_dados_mongo()
            except Exception as e:
                print(f"Erro limpando MongoDB: {e}")

            # Redis
            try:
                db_redis.limpar_dados_redis()
            except Exception as e:
                print(f"Erro limpando Redis: {e}")

            print("\n🎯 Limpeza concluída (se as conexões estavam disponíveis).")
        elif op == '0':
            sys.exit()
        else:
            print("Inválido.")

if __name__ == "__main__":
    # A função verificar_tudo retorna True se TODOS estiverem on, 
    # e False se ALGUM estiver off.
    sistema_online = verificar_tudo()

    if sistema_online:
        # Se tudo estiver ✅, abre o menu normal
        menu()
    else:
        # Se algum estiver ❌, cai aqui e BLOQUEIA
        print("\n⛔ ERRO CRÍTICO: O sistema não pode ser iniciado.")
        print("   Motivo: Não foi possível estabelecer conexão com TODOS os 4 bancos.")
        print("   A integração exige que PostgreSQL, Neo4j, MongoDB e Redis estejam rodando.")
        
        # Pausa para o usuário ler antes de fechar
        input("\n   Pressione ENTER para encerrar o programa...")
        sys.exit() # Encerra o script