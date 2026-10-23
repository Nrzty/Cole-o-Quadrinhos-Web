document.addEventListener('alpine:init', () => {
    Alpine.data('quadrinhosApp', () => ({
        quadrinhos: [],
        novoIsbn: '',
        novoTipo: 'Quadrinho', // Quadrinho ou Mangá
        filtro: 'Todos', // Todos, Quadrinho, Mangá
        termoBusca: '', // Filtro por título
        carregando: false,
        mensagemErro: '',
        mensagemSucesso: '',
        scannerAtivo: false,
        html5QrcodeScanner: null,
        
        modalManual: false,
        formManual: {
            titulo: '', autor: '', editora: '', ano: '', isbn: '', capa_url: '', tipo: 'Quadrinho'
        },

        init() {
            this.carregarQuadrinhos();
        },

        get quadrinhosFiltrados() {
            let lista = this.quadrinhos;
            if (this.filtro !== 'Todos') {
                lista = lista.filter(q => q.tipo === this.filtro);
            }
            if (this.termoBusca.trim() !== '') {
                const termo = this.termoBusca.toLowerCase();
                lista = lista.filter(q => q.titulo.toLowerCase().includes(termo));
            }
            return lista;
        },

        async carregarQuadrinhos() {
            try {
                const res = await fetch('/api/quadrinhos/');
                this.quadrinhos = await res.json();
            } catch (error) {
                console.error("Erro ao carregar quadrinhos", error);
            }
        },

        toggleScanner() {
            if (this.scannerAtivo) {
                this.pararScanner();
            } else {
                this.iniciarScanner();
            }
        },

        iniciarScanner() {
            this.scannerAtivo = true;
            this.mensagemErro = '';
            this.mensagemSucesso = '';
            
            setTimeout(() => {
                this.html5QrcodeScanner = new Html5Qrcode("reader");
                const config = { fps: 10, qrbox: { width: 200, height: 100 } };
                
                this.html5QrcodeScanner.start(
                    { facingMode: "environment" },
                    config,
                    (decodedText, decodedResult) => {
                        this.novoIsbn = decodedText;
                        this.pararScanner();
                        this.adicionar();
                    },
                    (errorMessage) => {
                        // Silencioso
                    }
                ).catch((err) => {
                    this.mensagemErro = "Erro ao acessar câmera.";
                    this.scannerAtivo = false;
                });
            }, 200);
        },

        pararScanner() {
            if (this.html5QrcodeScanner) {
                this.html5QrcodeScanner.stop().then(() => {
                    this.html5QrcodeScanner.clear();
                    this.scannerAtivo = false;
                }).catch(err => console.error("Erro ao parar scanner:", err));
            } else {
                this.scannerAtivo = false;
            }
        },

        async adicionar() {
            if (!this.novoIsbn) return;
            
            this.carregando = true;
            this.mensagemErro = '';
            this.mensagemSucesso = '';
            
            try {
                const isbnLimpo = this.novoIsbn.replace(/[^0-9X-]/gi, '');
                
                const res = await fetch('/api/quadrinhos/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ isbn: isbnLimpo, tipo: this.novoTipo })
                });
                
                if (!res.ok) {
                    const err = await res.json();
                    throw new Error(err.detail || 'Erro ao adicionar o quadrinho.');
                }
                
                const json = await res.json();
                this.novoIsbn = '';
                this.mensagemSucesso = `"${json.titulo}" salvo!`;
                await this.carregarQuadrinhos();
                
                setTimeout(() => { this.mensagemSucesso = ''; }, 3000);
            } catch (error) {
                this.mensagemErro = error.message;
            } finally {
                this.carregando = false;
            }
        },

        async salvarManual() {
            if (!this.formManual.titulo) { alert("O título é obrigatório!"); return; }
            this.carregando = true;
            try {
                const res = await fetch('/api/quadrinhos/manual', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(this.formManual)
                });
                
                if (!res.ok) throw new Error((await res.json()).detail || "Erro ao adicionar.");
                
                this.modalManual = false;
                this.formManual = {titulo: '', autor: '', editora: '', ano: '', isbn: '', capa_url: '', tipo: 'Quadrinho'};
                this.mensagemSucesso = "Cadastrado com sucesso!";
                await this.carregarQuadrinhos();
                setTimeout(() => { this.mensagemSucesso = ''; }, 3000);
            } catch (error) {
                alert(error.message);
            } finally {
                this.carregando = false;
            }
        },

        async remover(id) {
            if(!confirm("Remover da coleção?")) return;
            try {
                const res = await fetch(`/api/quadrinhos/${id}`, { method: 'DELETE' });
                if(res.ok) {
                    await this.carregarQuadrinhos();
                }
            } catch (error) {
                console.error("Erro ao remover", error);
            }
        },

        async editarCapa(id) {
            const url = prompt("Cole aqui o link da imagem da capa (ex: site da Amazon, Panini, etc):");
            if (!url) return;
            
            try {
                const res = await fetch(`/api/quadrinhos/${id}/capa`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ capa_url: url })
                });
                if (res.ok) {
                    await this.carregarQuadrinhos();
                } else {
                    alert("Erro ao atualizar a capa.");
                }
            } catch (error) {
                console.error("Erro ao editar capa", error);
            }
        }
    }))
})
