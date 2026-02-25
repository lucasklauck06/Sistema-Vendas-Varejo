from pymongo import MongoClient, errors
import db_postgres

# --- CONFIGURAÇÕES ---
URI_MONGO = "mongodb://localhost:27017/"
DB_NAME_MONGO = "TrabalhoFinalBancoII"
COLLECTION_NAME = "Banco de Dados II"

# --- FUNÇÃO DE TESTE DE CONEXÃO ---
def testar_conexao_mongo():
    """Verifica se o MongoDB está acessível (Ping)."""
    try:
        client = MongoClient(URI_MONGO, serverSelectionTimeoutMS=2000)
        client.admin.command('ping')
        client.close()
        return True
    except Exception:
        return False

def conectar_mongo():
    """Retorna a coleção específica para manipulação."""
    try:
        client = MongoClient(URI_MONGO, serverSelectionTimeoutMS=3000)
        db = client[DB_NAME_MONGO]
        return db[COLLECTION_NAME], client
    except errors.ServerSelectionTimeoutError as e:
        print(f"Erro ao conectar MongoDB: {e}")
        return None, None

# --- FUNÇÕES DE INTERESSES (BASE 2) ---
def adicionar_interesses(id_sql, nome, lista_interesses, origem=None):
    """
    Cria ou atualiza os interesses.
    CORREÇÃO: Agora usa $addToSet para adicionar sem apagar os anteriores.
    """
    colecao, client = conectar_mongo()
    
    if colecao is None:
        return

    # 1. Campos que serão SUBSTITUÍDOS ou CRIADOS (Nome, Origem)
    campos_set = { "nome": nome }
    if origem:
        campos_set["origem_captacao"] = origem

    # 2. Campos que serão INCREMENTADOS (Interesses)
    # $addToSet garante que não haverá duplicatas (ex: não add "Futebol" se já tiver)
    # $each permite adicionar uma lista de uma vez só
    operacao_update = {
        "$set": campos_set,
        "$addToSet": { 
            "interesses": { "$each": lista_interesses } 
        }
    }

    try:
        colecao.update_one(
            {"id_sql": int(id_sql)}, 
            operacao_update, 
            upsert=True
        )
        print(f"✅ Interesses ADICIONADOS ao perfil no MongoDB!")
    except Exception as e:
        print(f"❌ Erro ao salvar no Mongo: {e}")
    finally:
        if client: client.close()

def listar_interesses_cliente(id_sql):
    colecao, client = conectar_mongo()
    
    if colecao is None: 
        return None

    try:
        resultado = colecao.find_one({"id_sql": int(id_sql)})
        return resultado
    except Exception as e:
        print(f"Erro ao buscar: {e}")
        return None
    finally:
        if client: client.close()

# --- MENU DE TESTE ---
def menu_mongo():
    while True:
        print(f"\n=== BASE 2: MONGODB ({DB_NAME_MONGO}) ===")
        print("1. Adicionar/Atualizar Interesses de Cliente")
        print("2. Consultar Interesses por ID")
        print("0. Sair")
        
        opcao = input("Opção: ")
        
        if opcao == '1':
            print("\n--- Clientes Disponíveis (PostgreSQL) ---")
            conn = db_postgres.conectar()
            if conn:
                db_postgres.listar_clientes(conn)
                conn.close()
            else:
                print("(Não foi possível listar clientes do Postgres)")

            try:
                id_sql = input("ID do Cliente: ")
                nome = input("Nome do Cliente: ")
                interesses_str = input("Interesses (separe por virgula): ")
                lista = [x.strip() for x in interesses_str.split(',')]
                adicionar_interesses(id_sql, nome, lista)
            except ValueError:
                print("Erro: ID deve ser número.")

        elif opcao == '2':
            print("\n--- Clientes Disponíveis (PostgreSQL) ---")
            conn = db_postgres.conectar()
            if conn:
                db_postgres.listar_clientes(conn)
                conn.close()
            else:
                print("(Não foi possível listar clientes do Postgres)")

            id_sql = input("Digite o ID do Cliente para ver Interesses: ")
            
            doc = listar_interesses_cliente(id_sql)
            if doc:
                print("-" * 40)
                print(f"Cliente: {doc.get('nome')}")
                print(f"Interesses: {doc.get('interesses')}")
                if 'origem_captacao' in doc:
                    print(f"Origem: {doc['origem_captacao']}")
                print("-" * 40)
            else:
                print("⚠️ Cliente não encontrado no MongoDB.")

        elif opcao == '0':
            break
        else:
            print("Opção inválida.")

if __name__ == "__main__":
    if testar_conexao_mongo():
        menu_mongo()
    else:
        print("❌ Não foi possível conectar ao MongoDB.")


def limpar_dados_mongo():
    """Remove todos os documentos da coleção usada pelo projeto (não apaga o DB)."""
    colecao, client = conectar_mongo()
    if colecao is None:
        print("❌ Não foi possível conectar ao Mongo para limpar dados.")
        return

    try:
        colecao.delete_many({})
        print("✅ Coleção do MongoDB limpa (todos os documentos removidos).")
    except Exception as e:
        print(f"❌ Erro ao limpar MongoDB: {e}")
    finally:
        if client: client.close()