import traceback

import requests
from flask import Flask, render_template, jsonify
from psycopg2.extras import RealDictCursor

from database import get_connection

app = Flask(__name__)

INVERTEXTO_TOKEN = '25206|L7MAs9mOpA2RIe1FM5WX619goA39MDmR'
BASE_URL = 'https://api.invertexto.com/v1/cep/'

@app.route('/')
def index():
        return render_template('index.html')


@app.route('/api/consulta/<cep_input>')
def consulta_cep(cep_input):
    cep_formatado = ''.join(filter(str.isdigit, cep_input)) #Elimina o '-' do CEP
    if len(cep_formatado) != 8: #Verifiva a quantidade de digitos do CEP
        return jsonify({"error": "CEP inválido! Deve conter 8 digitos."}), 400
    conn = get_connection() #Verifica a conexão com o banco de dados
    if not conn:
        return jsonify({"error": "Erro de conexão com o banco de dados."}), 500
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        params = [cep_formatado]
        sql = "SELECT * FROM ceps WHERE cep = %s"
        cursor.execute(sql, params)
        cep_bd_local = cursor.fetchone()

        if cep_bd_local: #Verifica se o CEP existe no Banco de Dados local
            cursor.close()
            conn.close()
            dados = {
                "source": "local_db",
                "data": cep_bd_local
            }
            return jsonify(dados)

        #Se não existir no Banco de Dados, consulta a API externa
        response = requests.get(f"{BASE_URL}{cep_formatado}?token={INVERTEXTO_TOKEN}")
        #Se a API retornou OK, salva os dados no Banco
        if response.status_code == 200:
            dados = response.json()
            sql = "INSERT INTO ceps (cep, estado, cidade, bairro, rua, complemento, ibge) VALUES (%s, %s, %s, %s, %s, %s, %s)"
            params = [cep_formatado, dados.get('state'), dados.get('city'), dados.get('neighborhood'), dados.get('street'), dados.get('complement'), dados.get('ibge')]
            cursor.execute(sql, params)
            conn.commit()
            cursor.close()
            conn.close()
            dados_resposta = {
                "source": "api_externa",
                "data": {
                    "cep": cep_formatado,
                    "estado": dados.get('state'),
                    "cidade": dados.get('city'),
                    "bairro": dados.get('neighborhood'),
                    "rua": dados.get('street'),
                    "complemento": dados.get('complement'),
                    "ibge": dados.get('ibge')
                }
            }
            return jsonify(dados_resposta)
        elif response.status_code == 404:
            cursor.close()
            conn.close()
            return jsonify({"error": "Cep não encontrado na API"}), 404
        else:
            cursor.close()
            conn.close()
            return jsonify({"error": "Erro ao consultar API externa."}), response.status_code
    except Exception as ex:
        print("ERRO REAL:", ex)
        print(traceback.format_exc())
        if conn:
            conn.close()
        return jsonify({"error": str(ex)}), 500




if __name__ == '__main__':
    app.run(debug=True)