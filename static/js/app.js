document.addEventListener('alpine:init', () => Alpine.data('quadrinhosApp', () => ({
 urlOfertas: 'https://panini.com.br/black-friday-panini', ofertasPanini: [], consultandoOfertas: false,
 avisoOfertas: '', erroOfertas: false, pararConsulta: null, paginasLidas: 0, produtosLidos: 0, limiteOfertas: 24,
 moeda(valor) { return Number(valor).toLocaleString('pt-BR', {style:'currency', currency:'BRL'}); },
 colarOferta(evento) {
   const texto = evento.clipboardData?.getData('text')?.trim();
   if (!texto || !/^https?:\/\//i.test(texto)) return;
   evento.preventDefault();
   this.urlOfertas = texto;
   this.buscarOfertas();
 },
 async buscarOfertas() {
   if (this.consultandoOfertas) return;
   this.consultandoOfertas = true;
   this.erroOfertas = false;
   this.ofertasPanini = [];
   this.paginasLidas = this.produtosLidos = 0;
   this.limiteOfertas = 24;
   this.avisoOfertas = 'Conectando à Panini…';
   const fila = [{url:this.urlOfertas.trim(), nome:'Panini'}];
   const paginas = new Set(), listagens = new Set(), produtos = new Set(), ranking = new Map(), falhas = [];
   const controle = new AbortController();
   this.pararConsulta = () => controle.abort();
   try {
     while (fila.length && !controle.signal.aborted) {
       const {url, nome} = fila.shift();
       if (paginas.has(url)) continue;
       paginas.add(url);
       this.avisoOfertas = nome + ' · Lendo ofertas e comparando com sua coleção…';
       const pedido = new AbortController();
       const cancelarPedido = () => pedido.abort();
       controle.signal.addEventListener('abort', cancelarPedido, {once:true});
       const prazo = setTimeout(cancelarPedido, 55000);
       try {
         const resposta = await fetch('/api/ofertas/ranking', {
           ...this.json('POST', {url}), signal: pedido.signal
         });
         const dados = await resposta.json().catch(() => ({}));
         if (!resposta.ok) throw Error(typeof dados.detail === 'string' ? dados.detail : 'Falha ao consultar a página (HTTP ' + resposta.status + ').');
         this.paginasLidas++;
         dados.produtos.forEach(link => produtos.add(link));
         this.produtosLidos = produtos.size;
         for (const item of dados.ranking) if (!ranking.has(item.url)) ranking.set(item.url, item);
         this.ofertasPanini = [...ranking.values()].sort((a,b) => b.score-a.score || a.preco-b.preco || a.titulo.localeCompare(b.titulo,'pt-BR') || a.url.localeCompare(b.url));
         for (const [editoria, link] of Object.entries(dados.editorias || {})) fila.push({url:link,nome:editoria});
         const assinatura = JSON.stringify([nome, ...dados.produtos]);
         if (dados.proxima && (paginas.has(dados.proxima) || listagens.has(assinatura))) {
           throw Error('A Panini repetiu a listagem.');
         }
         listagens.add(assinatura);
         if (dados.proxima) fila.push({url:dados.proxima,nome});
       } catch (erro) {
         if (controle.signal.aborted) break;
         falhas.push(nome + ' — ' + (pedido.signal.aborted ? 'A consulta demorou demais. Tente novamente.' : erro.message));
       } finally {
         clearTimeout(prazo);
         controle.signal.removeEventListener('abort', cancelarPedido);
       }
     }
     this.erroOfertas = falhas.length > 0;
     if (controle.signal.aborted) this.avisoOfertas = 'Busca interrompida. Os resultados já encontrados estão abaixo.';
     else if (falhas.length) this.avisoOfertas = (this.paginasLidas ? 'Resultado parcial. ' : '') + falhas.join(' / ');
     else this.avisoOfertas = ranking.size ? 'Busca concluída. Recomendações em ordem de prioridade.' : 'Busca concluída. Nenhuma oferta atingiu os critérios para sua coleção.';
   } finally {
     this.pararConsulta = null;
     this.consultandoOfertas = false;
   }
 },
 adicionarAberto: false, pagina: 1, porPagina: 24, aba: 'estante', desejos: [], requisicoesAtivas: 0, paginaDesejos: 1, destinoManual: 'estante', desejoEditando: null, ocupados: {},
 quadrinhos: [], novoIsbn: '', novoTipo: 'Quadrinho', filtro: 'Todos', colecao: 'Todas', termoBusca: '', ordem: 'titulo', carregando: false, carregandoLista: true, mensagemErro: '', mensagemSucesso: '', progresso: '', buscandoCapas: false, scannerAtivo: false, scanner: null, modalManual: false,
 formManual: {titulo:'', autor:'', editora:'', ano:'', isbn:'', capa_url:'', tipo:'Quadrinho', colecao:''},
 init() { this.carregarQuadrinhos(); this.carregarDesejos(); for(const campo of ['filtro','colecao','termoBusca','ordem','porPagina']) this.$watch(campo,()=>{this.pagina=1;}); this.$watch('quadrinhos',()=>{this.pagina=Math.min(this.pagina,this.totalPaginas);}); this.$watch('desejos',()=>{this.paginaDesejos=Math.min(this.paginaDesejos,this.totalPaginasDesejos);}); },
 get totalPaginas(){return Math.max(1,Math.ceil(this.quadrinhosFiltrados.length/Number(this.porPagina)));},
 get quadrinhosPagina(){return this.quadrinhosFiltrados.slice((this.pagina-1)*Number(this.porPagina),this.pagina*Number(this.porPagina));},
 get totalPaginasDesejos(){return Math.max(1,Math.ceil(this.desejos.length/12));},
 get desejosPagina(){return this.desejos.slice((this.paginaDesejos-1)*12,this.paginaDesejos*12);},
 async aquisicoes(url,options={}) {
   this.requisicoesAtivas++;
   try {
     const resposta = await fetch('/api/'+url, options);
     const dados = await resposta.json().catch(() => ({}));
     if (!resposta.ok) throw Error(Array.isArray(dados.detail) ? dados.detail.map(e=>e.msg).join('; ') : dados.detail || 'Falha na solicitação (HTTP '+resposta.status+').');
     return dados;
   } finally { this.requisicoesAtivas--; }
 },
 async carregarDesejos(){try{this.desejos=await this.aquisicoes('desejos');}catch(e){this.mensagemErro=e.message;}},
 abrirCadastro(destino='estante',q=null){this.destinoManual=destino;this.desejoEditando=q?.id||null;this.formManual={titulo:'',autor:'',editora:'',ano:'',isbn:'',capa_url:'',tipo:'Quadrinho',colecao:'',prioridade:2,notas:'',...(q||{})};this.mensagemErro='';this.modalManual=true;},
 async desejar(q){const chave=q.chave||q.isbn;if(this.ocupados[chave])return;this.ocupados[chave]=true;try{await this.aquisicoes('desejos',this.json('POST',{titulo:q.titulo,isbn:q.isbn,autor:q.autor,editora:q.editora,ano:q.ano,tipo:q.tipo,capa_url:q.capa_url,colecao:q.colecao==='Outras coleções'?null:q.colecao}));await this.carregarDesejos();this.mensagemSucesso='Edição adicionada à lista de desejos.';}catch(e){this.mensagemErro=e.message;}finally{delete this.ocupados[chave];}},
 async adquirir(q){if(!confirm('Adicionar esta edição à sua estante e retirar da lista de desejos?'))return;if(this.ocupados[q.id])return;this.ocupados[q.id]=true;try{await this.aquisicoes('desejos/'+q.id+'/adquirir',{method:'POST'});await Promise.all([this.carregarQuadrinhos(),this.carregarDesejos()]);this.mensagemSucesso='Edição adicionada à estante.';}catch(e){this.mensagemErro=e.message;}finally{delete this.ocupados[q.id];}},
 async removerDesejo(q){if(!confirm('Remover esta edição da lista de desejos?'))return;try{await this.aquisicoes('desejos/'+q.id,{method:'DELETE'});await this.carregarDesejos();}catch(e){this.mensagemErro=e.message;}},
 normalizar(s) { return (s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase(); },
 get colecoes() { const counts = {}; this.quadrinhos.forEach(q => counts[q.colecao] = (counts[q.colecao] || 0)+1); return Object.entries(counts).sort((a,b)=>a[0].localeCompare(b[0],'pt-BR')); },
 get quadrinhosFiltrados() { const term = this.normalizar(this.termoBusca.trim()); return this.quadrinhos.filter(q => (this.filtro==='Todos'||q.tipo===this.filtro) && (this.colecao==='Todas'||q.colecao===this.colecao) && this.normalizar([q.titulo,q.autor,q.editora,q.isbn,q.colecao].join(' ')).includes(term)).sort((a,b)=>this.ordem==='recentes'?b.id-a.id:this.ordem==='ano'?(b.ano||0)-(a.ano||0):a.titulo.localeCompare(b.titulo,'pt-BR',{numeric:true})); },
 get semCapa() { return this.quadrinhos.filter(q=>!q.capa_url).length; },
 async api(url, options={}) { return this.aquisicoes('quadrinhos'+url, options); },
 json(method, data) { return {method,headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}; },
 async carregarQuadrinhos() { this.carregandoLista=true; try { const lista=[]; for(let skip=0;;skip+=500) { const lote=await this.api('/?skip='+skip+'&limit=500'); lista.push(...lote); if(lote.length<500)break; } this.quadrinhos=lista; } catch(e){this.mensagemErro=e.message;} finally{this.carregandoLista=false;} },
 async adicionar() { if(this.carregando)return; this.carregando=true; this.mensagemErro=''; try{await this.api('/',this.json('POST',{isbn:this.novoIsbn,tipo:this.novoTipo}));this.novoIsbn='';this.mensagemSucesso='Quadrinho adicionado à coleção.';await this.carregarQuadrinhos();}catch(e){this.mensagemErro=e.message;}finally{this.carregando=false;} },
 async salvarManual(){if(this.carregando)return;this.carregando=true;this.mensagemErro='';try{const dados={...this.formManual,ano:this.formManual.ano===''?null:Number(this.formManual.ano)};if(this.destinoManual==='desejos'){await this.aquisicoes('desejos'+(this.desejoEditando?'/'+this.desejoEditando:''),this.json(this.desejoEditando?'PUT':'POST',dados));await this.carregarDesejos();}else{await this.api('/manual',this.json('POST',dados));await this.carregarQuadrinhos();}this.modalManual=false;this.mensagemSucesso='Cadastro salvo.';}catch(e){this.mensagemErro=e.message;}finally{this.carregando=false;} },
 async completarCapas() { if(this.buscandoCapas)return;this.buscandoCapas=true;let encontradas=0,falhas=0;const itens=this.quadrinhos.filter(q=>!q.capa_url&&q.isbn);try{for(let i=0;i<itens.length;i++){this.progresso=`Buscando capa ${i+1} de ${itens.length}…`;try{const q=await this.api('/'+itens[i].id+'/buscar-capa',{method:'POST'});if(q.capa_url)encontradas++;this.quadrinhos=this.quadrinhos.map(x=>x.id===q.id?q:x);}catch(e){falhas++;}}this.mensagemSucesso=`${encontradas} capas adicionadas. ${itens.length-encontradas-falhas} sem resultado; ${falhas} falhas. Itens sem ISBN precisam de um link manual.`;}finally{this.buscandoCapas=false;this.progresso='';} },
 async editarColecao(q) { const valor=prompt('Nome da coleção. Deixe vazio para usar a identificação automática.',q.colecao_manual?q.colecao:'');if(valor===null)return;try{await this.api('/'+q.id+'/colecao',this.json('PATCH',{colecao:valor}));await this.carregarQuadrinhos();}catch(e){this.mensagemErro=e.message;} },
 async editarCapa(id) { const url=prompt('Cole o link da capa. Deixe vazio para remover e permitir nova busca.');if(url===null)return;try{await this.api('/'+id+'/capa',this.json('PATCH',{capa_url:url.trim()}));await this.carregarQuadrinhos();}catch(e){this.mensagemErro=e.message;} },
 async remover(id){if(!confirm('Remover este quadrinho da coleção?'))return;try{await this.api('/'+id,{method:'DELETE'});await this.carregarQuadrinhos();}catch(e){this.mensagemErro=e.message;}},
 async toggleScanner(){if(this.scannerAtivo){await this.pararScanner();return;}this.scannerAtivo=true;await this.$nextTick();try{this.scanner=new Html5Qrcode('reader');await this.scanner.start({facingMode:'environment'},{fps:10,qrbox:{width:240,height:120}},async text=>{if(this.carregando)return;this.novoIsbn=text;await this.pararScanner();await this.adicionar();},()=>{});}catch(e){this.mensagemErro='Não foi possível abrir a câmera. Verifique a permissão e use HTTPS ou localhost.';this.scannerAtivo=false;}},
 async pararScanner(){try{if(this.scanner){await this.scanner.stop();this.scanner.clear();}}catch(e){}finally{this.scanner=null;this.scannerAtivo=false;}}
})));
