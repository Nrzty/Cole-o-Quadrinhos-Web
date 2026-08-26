import os
import unittest
import httpx
from dotenv import load_dotenv

class TestGoogleBooksAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Carrega as variáveis do arquivo .env
        load_dotenv()
        cls.api_key = os.getenv("GOOGLE_BOOKS_API_KEY")
        # ISBN fornecido (já limpando os hífens)
        cls.isbn = "978-1401207526".replace("-", "")

    def test_01_api_key_configurada(self):
        """Verifica se a chave da API foi encontrada no .env"""
        self.assertIsNotNone(self.api_key, "A chave GOOGLE_BOOKS_API_KEY não foi encontrada no arquivo .env!")
        self.assertNotEqual(self.api_key, "", "A chave GOOGLE_BOOKS_API_KEY está vazia!")

    def test_02_busca_informacoes_e_capa(self):
        """Testa se a API do Google retorna dados vitais e a URL da capa para o ISBN."""
        if not self.api_key:
            self.skipTest("Sem chave de API para testar.")

        url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{self.isbn}&key={self.api_key}"
        
        with httpx.Client() as client:
            response = client.get(url, follow_redirects=True)
            
        # Verifica se não deu erro de quota ou autorização (Status 200)
        self.assertEqual(response.status_code, 200, f"A API retornou erro. Provável problema com a chave. Resposta: {response.text}")
        
        dados = response.json()
        
        # Verifica se o livro existe na base do Google
        self.assertGreater(dados.get("totalItems", 0), 0, f"O ISBN {self.isbn} não foi encontrado no Google Books.")
        
        volume_info = dados["items"][0].get("volumeInfo", {})
        
        # Verifica se encontrou as informações principais (Título)
        titulo = volume_info.get("title")
        self.assertTrue(bool(titulo), "O livro foi encontrado, mas não possui título.")
        
        # Verifica se encontrou a URL da Capa (Thumbnail)
        image_links = volume_info.get("imageLinks", {})
        capa_url = image_links.get("thumbnail")
        self.assertTrue(bool(capa_url), "O livro foi encontrado, mas o Google Books não disponibilizou a imagem da capa para ele.")

        print(f"\n[SUCESSO] Livro encontrado: '{titulo}'")
        print(f"[SUCESSO] Link da Capa: {capa_url}")

if __name__ == '__main__':
    unittest.main(verbosity=2)
