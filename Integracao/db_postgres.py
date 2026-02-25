import psycopg2
from psycopg2 import Error

# --- CONFIGURAÇÃO DA CONEXÃO ---
DB_HOST = "localhost"
DB_NAME = "TrabalhoFinalBancoII" 
DB_USER = "postgres"
DB_PASS = "postgres"
DB_PORT = "5432"

# --- FUNÇÃO QUE FALTAVA (O ERRO ESTAVA AQUI) ---
def testar_conexao():
    """Tenta conectar e desconectar apenas para verificar se o banco está ON."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            port=DB_PORT,
            connect_timeout=3
        )
        conn.close()
        return True
    except Error:
        return False
# ------------------------------------------------

def conectar():
    """Estabelece a conexão com o banco de dados."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            port=DB_PORT
        )
        return conn
    except Error as e:
        print(f"Erro ao conectar ao PostgreSQL: {e}")
        return None

# ==========================================
# FUNÇÕES DE CLIENTES
# ==========================================
def criar_cliente(conn):
    print("\n--- Novo Cliente ---")
    cpf = input("CPF (apenas números): ")
    nome = input("Nome Completo: ")
    endereco = input("Endereço: ")
    cidade = input("Cidade: ")
    uf = input("UF (2 letras): ")
    email = input("E-mail: ")

    try:
        cursor = conn.cursor()
        sql = """INSERT INTO Clientes (cpf, nome, endereco, cidade, uf, email) 
                 VALUES (%s, %s, %s, %s, %s, %s) RETURNING id;"""
        cursor.execute(sql, (cpf, nome, endereco, cidade, uf, email))
        id_gerado = cursor.fetchone()[0]
        conn.commit()
        print(f"✅ Cliente cadastrado com sucesso! ID: {id_gerado}")
        return id_gerado  # <--- ADICIONADO: Retorna o ID para o main.py usar
    except Error as e:
        print(f"❌ Erro ao inserir: {e}")
        return None

def listar_clientes(conn):
    print("\n--- Lista de Clientes ---")
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, cpf, nome, email FROM Clientes ORDER BY id;")
        registros = cursor.fetchall()
        
        if not registros:
            print("Nenhum cliente encontrado.")
        else:
            print(f"{'ID':<5} {'CPF':<15} {'NOME':<30} {'EMAIL'}")
            print("-" * 70)
            for row in registros:
                print(f"{row[0]:<5} {row[1]:<15} {row[2]:<30} {row[3]}")
    except Error as e:
        print(f"❌ Erro ao ler dados: {e}")

def atualizar_cliente(conn):
    listar_clientes(conn)
    id_cliente = input("\nDigite o ID do cliente para atualizar: ")
    novo_nome = input("Novo Nome: ")
    novo_email = input("Novo E-mail: ")

    try:
        cursor = conn.cursor()
        sql = "UPDATE Clientes SET nome = %s, email = %s WHERE id = %s;"
        cursor.execute(sql, (novo_nome, novo_email, id_cliente))
        conn.commit()
        if cursor.rowcount > 0:
            print("✅ Cliente atualizado!")
        else:
            print("⚠️ Cliente não encontrado.")
    except Error as e:
        print(f"❌ Erro ao atualizar: {e}")

def deletar_cliente(conn):
    listar_clientes(conn)
    id_cliente = input("\nDigite o ID do cliente para excluir: ")
    
    try:
        cursor = conn.cursor()
        sql = "DELETE FROM Clientes WHERE id = %s;"
        cursor.execute(sql, (id_cliente,))
        conn.commit()
        if cursor.rowcount > 0:
            print("✅ Cliente excluído!")
        else:
            print("⚠️ Cliente não encontrado.")
    except Error as e:
        print(f"❌ Erro ao excluir (verifique se há compras vinculadas): {e}")

# ==========================================
# FUNÇÕES DE PRODUTOS
# ==========================================
def criar_produto(conn):
    print("\n--- Novo Produto ---")
    produto = input("Nome do Produto: ")
    try:
        valor = float(input("Valor (ex: 10.50): "))
        quantidade = int(input("Quantidade em estoque: "))
    except ValueError:
        print("Erro: Valor ou Quantidade devem ser números.")
        return None
        
    tipo = input("Tipo/Categoria: ")

    try:
        cursor = conn.cursor()
        sql = """INSERT INTO Produtos (produto, valor, quantidade, tipo) 
                 VALUES (%s, %s, %s, %s) RETURNING id;"""
        cursor.execute(sql, (produto, valor, quantidade, tipo))
        id_gerado = cursor.fetchone()[0]
        conn.commit()
        print("✅ Produto cadastrado com sucesso!")
        return id_gerado # <--- ADICIONADO: Retorna o ID
    except Error as e:
        print(f"❌ Erro ao inserir produto: {e}")
        return None

def listar_produtos(conn):
    print("\n--- Estoque de Produtos ---")
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, produto, valor, quantidade FROM Produtos ORDER BY id;")
        registros = cursor.fetchall()
        print(f"{'ID':<5} {'PRODUTO':<30} {'VALOR':<10} {'QTD'}")
        print("-" * 60)
        for row in registros:
            print(f"{row[0]:<5} {row[1]:<30} R${row[2]:<10} {row[3]}")
    except Error as e:
        print(f"❌ Erro: {e}")

# ==========================================
# FUNÇÕES DE COMPRAS (Relacionamento)
# ==========================================
def realizar_compra(conn):
    print("\n--- Nova Compra ---")
    # Verifica se há clientes na base; se não houver, oferece cadastrar na hora
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM Clientes;")
        total_clientes = cursor.fetchone()[0]
    except Error as e:
        print(f"❌ Erro ao verificar clientes: {e}")
        return

    id_cliente = None
    if total_clientes == 0:
        escolha = input("Nenhum cliente encontrado. Deseja cadastrar agora? (S/N): ").strip().upper()
        if escolha == 'S':
            id_cliente = criar_cliente(conn)
            if not id_cliente:
                return
        else:
            print("Operação cancelada.")
            return
    else:
        # Mostra a lista somente se houver clientes (evita mensagem duplicada)
        listar_clientes(conn)
        entrada = input("Digite o ID do Cliente (ou 'N' para cadastrar novo): ")
        if entrada.strip().upper() == 'N':
            id_cliente = criar_cliente(conn)
            if not id_cliente: return
        else:
            id_cliente = entrada
            try:
                cursor.execute("SELECT id FROM Clientes WHERE id = %s", (id_cliente,))
                if not cursor.fetchone():
                    print(f"⚠️ Cliente {id_cliente} não encontrado.")
                    if input("Cadastrar agora? (S/N): ").strip().upper() == 'S':
                        id_cliente = criar_cliente(conn)
                        if not id_cliente: return
                    else:
                        return
            except Error as e:
                print(f"❌ Erro ao verificar cliente: {e}")
                return

    # Permite adicionar múltiplos produtos com quantidade
    compras_realizadas = []  # lista de (id_produto, quantidade)

    while True:
        listar_produtos(conn)
        entrada_prod = input("Digite o ID do Produto (ou 'N' para novo): ")
        if entrada_prod.strip().upper() == 'N':
            id_produto = criar_produto(conn)
            if not id_produto:
                # se falhou cadastro, volta ao início
                continue
        else:
            id_produto = entrada_prod

        try:
            quantidade = int(input("Quantidade desejada: ").strip())
            if quantidade <= 0:
                print("Quantidade deve ser maior que zero.")
                continue
        except ValueError:
            print("Quantidade inválida.")
            continue

        # Tenta decrementar estoque (não comita ainda)
        if not decrementar_estoque(conn, id_produto, quantidade):
            print("Não foi possível reservar o produto. Tente outro ou verifique o estoque.")
            if input("Deseja tentar outro produto? (S/N): ").strip().upper() == 'S':
                continue
            else:
                try:
                    conn.rollback()
                except: pass
                print("Operação cancelada.")
                return

        compras_realizadas.append((id_produto, quantidade))

        mais = input("Deseja adicionar outro produto? (S/N): ").strip().upper()
        if mais != 'S':
            break

    # Inserir registros de compra e commitar uma vez
    try:
        cursor = conn.cursor()
        sql = "INSERT INTO Compras (id_cliente, id_produto) VALUES (%s, %s);"
        for pid, qty in compras_realizadas:
            for _ in range(qty):
                cursor.execute(sql, (id_cliente, pid))
        conn.commit()
        print("✅ Compra registrada com sucesso!")
    except Error as e:
        print(f"❌ Erro ao registrar compra: {e}")
        try:
            conn.rollback()
        except: pass

def listar_compras(conn):
    print("\n--- Relatório de Compras ---")
    try:
        cursor = conn.cursor()
        # Join para mostrar nomes em vez de apenas IDs
        sql = """
        SELECT c.id, cli.nome, p.produto, c.data 
        FROM Compras c
        JOIN Clientes cli ON c.id_cliente = cli.id
        JOIN Produtos p ON c.id_produto = p.id
        ORDER BY c.data DESC;
        """
        cursor.execute(sql)
        registros = cursor.fetchall()
        print(f"{'ID':<5} {'CLIENTE':<20} {'PRODUTO':<20} {'DATA'}")
        print("-" * 70)
        for row in registros:
            print(f"{row[0]:<5} {row[1]:<20} {row[2]:<20} {row[3]}")
    except Error as e:
        print(f"❌ Erro: {e}")


# para ajudar na integração do Redis
def buscar_compras_por_cliente(conn, id_cliente):
    """Retorna lista de produtos comprados por um ID específico (Para integração)."""
    try:
        cursor = conn.cursor()
        sql = """
        SELECT p.produto, p.tipo 
        FROM Compras c
        JOIN Produtos p ON c.id_produto = p.id
        WHERE c.id_cliente = %s
        """
        cursor.execute(sql, (id_cliente,))
        # Retorna lista de dicionários simples
        return [{"produto": row[0], "tipo": row[1]} for row in cursor.fetchall()]
    except Error:
        return []
    

def decrementar_estoque(conn, id_produto, quantidade=1):
    """
    Verifica se há estoque suficiente e decrementa `quantidade` unidades.
    Retorna True se conseguiu, False caso contrário.
    """
    try:
        cursor = conn.cursor()

        # 1. Verifica a quantidade atual
        cursor.execute("SELECT quantidade FROM Produtos WHERE id = %s", (id_produto,))
        resultado = cursor.fetchone()

        if not resultado:
            print("⚠️ ERRO: Produto não existe.")
            return False

        qtd_atual = resultado[0]

        if qtd_atual >= quantidade and quantidade > 0:
            # 2. Atualiza o banco (Decrementa em lote)
            sql_update = "UPDATE Produtos SET quantidade = quantidade - %s WHERE id = %s"
            cursor.execute(sql_update, (quantidade, id_produto))
            # Nota: O commit será feito pelo chamador para garantir integridade
            return True
        else:
            print(f"⚠️ ERRO: Estoque insuficiente. Disponível: {qtd_atual}, solicitado: {quantidade}.")
            return False

    except Error as e:
        print(f"❌ Erro ao atualizar estoque: {e}")
        return False

# ==========================================
# MENU PRINCIPAL
# ==========================================
def menu():
    conn = conectar()
    if not conn:
        return

    while True:
        print("\n=== GESTÃO BASE 1 (POSTGRESQL) ===")
        print("1. Cadastrar Cliente")
        print("2. Listar Clientes")
        print("3. Atualizar Cliente")
        print("4. Excluir Cliente")
        print("----------------")
        print("5. Cadastrar Produto")
        print("6. Listar Produtos")
        print("----------------")
        print("7. Registrar Compra")
        print("8. Listar Compras")
        print("----------------")
        print("0. Sair")
        
        opcao = input("Escolha uma opção: ")

        if opcao == '1': criar_cliente(conn)
        elif opcao == '2': listar_clientes(conn)
        elif opcao == '3': atualizar_cliente(conn)
        elif opcao == '4': deletar_cliente(conn)
        elif opcao == '5': criar_produto(conn)
        elif opcao == '6': listar_produtos(conn)
        elif opcao == '7': realizar_compra(conn)
        elif opcao == '8': listar_compras(conn)
        elif opcao == '0': 
            print("Saindo...")
            break
        else:
            print("Opção inválida!")

    conn.close()


def limpar_dados_postgres():
    """Limpa dados das tabelas Clientes, Produtos e Compras (não apaga o banco)."""
    conn = conectar()
    if not conn:
        print("❌ Não foi possível conectar ao Postgres para limpar dados.")
        return

    try:
        cursor = conn.cursor()
        # TRUNCATE com RESTART IDENTITY para zerar sequências
        cursor.execute("TRUNCATE TABLE Compras, Produtos, Clientes RESTART IDENTITY CASCADE;")
        conn.commit()
        print("✅ Dados do Postgres limpos (Clientes, Produtos, Compras).")
    except Error as e:
        print(f"❌ Erro ao limpar dados do Postgres: {e}")
        try:
            conn.rollback()
        except: pass
    finally:
        conn.close()

if __name__ == "__main__":
    menu()