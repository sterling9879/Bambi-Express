# 🦌 Guia de Instalação do Bambi Express (para Iniciantes)

Este guia foi escrito para **qualquer pessoa**, mesmo quem **nunca instalou um programa técnico** no computador. Vamos com calma, um passo de cada vez. Não pule etapas e leia com atenção. Se algo der errado, respire fundo — no final tem uma seção de **"Deu Problema?"** para te ajudar. 😊

> **O que é o Bambi Express?**
> É um programa que **transforma texto em vídeo** automaticamente. Você escreve um texto, e ele cria a narração (voz), imagens, música e junta tudo em um vídeo pronto, usando Inteligência Artificial.

---

## 📋 Antes de começar (leia isto!)

O Bambi Express roda no seu computador, mas usa **serviços de IA pela internet** para funcionar. Então você vai precisar de:

1. Um computador com **Windows 10 ou Windows 11**.
2. **Conexão com a internet** (durante a instalação e o uso).
3. Cerca de **1 hora de paciência** na primeira vez (depois é rápido).
4. Espaço livre no disco: pelo menos **5 GB**.

Este guia é dividido em **partes numeradas**. Faça uma parte de cada vez, **na ordem**.

> 💡 **Dica de ouro:** Sempre que este guia disser "abra o Prompt de Comando" ou "digite tal coisa", faça **exatamente** como está escrito. Um espaço ou uma letra errada pode fazer o programa não funcionar.

---

## 🧩 Visão geral (o que vamos fazer)

Para o Bambi Express funcionar, precisamos instalar **4 programas de apoio** primeiro. Pense neles como "ingredientes" de uma receita:

| # | Programa | Para que serve |
|---|----------|----------------|
| 1 | **Git** | Serve para **baixar** o Bambi Express da internet e atualizá-lo depois |
| 2 | **Python** | É o "motor" que roda a parte de trás do programa |
| 3 | **Node.js** | É o "motor" que roda a tela (a parte visual) do programa |
| 4 | **FFmpeg** | É o programa que **monta o vídeo** juntando áudio e imagem |

Depois de instalar esses 4, a gente **baixa o Bambi Express** e roda um **instalador automático**. Simples assim. Vamos lá!

---

## Parte 1 — Instalar o Git

O **Git** vai baixar o Bambi Express da internet para o seu computador.

### Passo a passo

1. Abra seu navegador (Chrome, Edge, etc.).
2. Acesse este site: **https://git-scm.com/download/win**
3. O download do instalador vai começar **sozinho** em alguns segundos. Se não começar, clique em **"64-bit Git for Windows Setup"**.
4. Quando o download terminar, **abra o arquivo** que você baixou (o nome é parecido com `Git-2.xx.x-64-bit.exe`).
5. Vai abrir uma janela de instalação. **Você não precisa entender as opções.** Apenas clique em **"Next" (Próximo)** várias vezes, até aparecer o botão **"Install" (Instalar)**.
6. Clique em **"Install"** e aguarde.
7. No final, clique em **"Finish" (Concluir)**. Pode **desmarcar** a caixinha que diz "View Release Notes".

✅ **Pronto! O Git está instalado.**

> 💡 Existe também um atalho: dentro da pasta do projeto há um arquivo chamado `install-git.bat` que instala o Git sozinho. Mas como ainda **não baixamos o projeto**, faça a instalação manual acima nesta primeira vez.

---

## Parte 2 — Instalar o Python

O **Python** é o motor principal do Bambi Express.

### Passo a passo

1. Acesse: **https://www.python.org/downloads/**
2. Clique no botão amarelo grande escrito **"Download Python 3.xx.x"** (a versão pode variar, tudo bem).
3. Abra o arquivo baixado.
4. ⚠️ **ATENÇÃO — ESTE PASSO É O MAIS IMPORTANTE DE TODOS:**
   Na primeira tela do instalador, **marque a caixinha embaixo** que diz:
   > ☑️ **"Add python.exe to PATH"** (Adicionar Python ao PATH)

   **Se você esquecer de marcar isso, o programa não vai funcionar!** Veja a imagem mental: a caixinha fica na parte de baixo da janela. Marque ela antes de continuar.
5. Agora clique em **"Install Now" (Instalar Agora)**.
6. Aguarde a instalação terminar e clique em **"Close" (Fechar)**.

✅ **Pronto! O Python está instalado.**

---

## Parte 3 — Instalar o Node.js

O **Node.js** faz a **tela do programa** funcionar (o site que você vai abrir no navegador).

### Passo a passo

1. Acesse: **https://nodejs.org/**
2. Clique no botão que diz **"LTS"** (é a versão estável e recomendada). O download começa.
3. Abra o arquivo baixado.
4. Clique em **"Next" (Próximo)** em todas as telas. Aceite os termos quando pedir e mantenha tudo como está.
5. Clique em **"Install"** e aguarde.
6. Clique em **"Finish"** no final.

✅ **Pronto! O Node.js está instalado.**

---

## Parte 4 — Instalar o FFmpeg

O **FFmpeg** é o programa que **monta o vídeo final**. Sem ele, o Bambi Express não consegue gerar o vídeo.

Esta parte é a **mais "técnica"**, mas vou te guiar com muito cuidado. Existem duas formas — escolha a **Forma A** (mais fácil).

### Forma A — A mais fácil (recomendada)

1. Aperte a tecla **Windows** (⊞) no seu teclado para abrir o menu Iniciar.
2. Digite: **`powershell`**
3. Vai aparecer **"Windows PowerShell"**. Clique com o **botão direito** do mouse nele e escolha **"Executar como administrador"**.
4. Se aparecer uma janela perguntando "Deseja permitir?", clique em **"Sim"**.
5. Vai abrir uma tela **azul ou preta** com textos. **Copie a linha abaixo**, cole lá dentro (clique com o botão direito para colar) e aperte **Enter**:

   ```powershell
   winget install --id Gyan.FFmpeg -e
   ```

6. Se perguntar algo sobre "aceitar os termos", digite **`Y`** e aperte Enter.
7. Aguarde baixar e instalar. Quando voltar a aparecer o cursor piscando, terminou.
8. **Feche essa janela do PowerShell** e abra uma nova (repita os passos 1 a 3, mas sem precisar de administrador).
9. Para testar se funcionou, digite:

   ```powershell
   ffmpeg -version
   ```

   Se aparecerem várias linhas de texto começando com `ffmpeg version...`, **deu certo!** 🎉

### Forma B — Se a Forma A não funcionou

1. Acesse: **https://www.gyan.dev/ffmpeg/builds/**
2. Baixe o arquivo **"ffmpeg-release-full.7z"** (ou o `.zip`).
3. Descompacte o arquivo (clique com o botão direito → "Extrair tudo").
4. Renomeie a pasta descompactada para apenas **`ffmpeg`** e mova ela para dentro do disco `C:`. O caminho final deve ficar assim: `C:\ffmpeg`.
5. Dentro dela existe uma pasta chamada `bin`. Guarde este caminho: `C:\ffmpeg\bin`.
6. Agora precisamos avisar o Windows onde o FFmpeg está:
   - Aperte a tecla **Windows** e digite **"variáveis de ambiente"**.
   - Clique em **"Editar as variáveis de ambiente do sistema"**.
   - Clique no botão **"Variáveis de Ambiente..."**.
   - Na lista de baixo, ache a linha **"Path"**, clique nela e depois em **"Editar..."**.
   - Clique em **"Novo"** e cole: `C:\ffmpeg\bin`
   - Clique em **"OK"** em todas as janelas para fechar.
7. **Feche e abra** o PowerShell de novo e teste com `ffmpeg -version`.

> ℹ️ Se você tem uma **placa de vídeo NVIDIA** e quer que os vídeos sejam montados **mais rápido**, existe um guia avançado extra em `docs/FFMPEG_GPU_WINDOWS.md`. Mas isso é **opcional** — pule por enquanto.

---

## Parte 5 — Baixar o Bambi Express

Agora que os "ingredientes" estão prontos, vamos **baixar o programa** em si.

1. Decida em **qual pasta** você quer guardar o programa. Uma boa escolha é a **Área de Trabalho (Desktop)** ou a pasta **Documentos**.
2. Abra essa pasta no Explorador de Arquivos.
3. Dentro dela, clique com o **botão direito** em um espaço vazio e escolha **"Abrir no Terminal"** ou **"Git Bash Here"**.
   - Se não aparecer nenhuma dessas opções, faça assim: aperte **Windows**, digite `cmd`, aperte Enter, e depois digite `cd ` (com espaço), arraste a pasta para dentro da janela e aperte Enter.
4. Na janela que abriu, **cole a linha abaixo** e aperte Enter:

   ```bash
   git clone https://github.com/sterling9879/bambi-express.git
   ```

5. Aguarde o download terminar. Vai aparecer uma pasta nova chamada **`bambi-express`** (ou parecido).

✅ **Pronto! O programa está no seu computador.**

---

## Parte 6 — Rodar o instalador automático

Agora vem a parte fácil! O Bambi Express tem um **instalador automático** que faz quase tudo sozinho.

1. Abra a pasta do Bambi Express que você acabou de baixar.
2. Procure o arquivo chamado **`install.bat`**.
3. Dê **dois cliques** nele.
4. Vai abrir uma janela preta que faz várias coisas sozinha (verifica o Python, o Node.js, instala peças internas, cria pastas...). **Isso pode demorar de 5 a 20 minutos.** É normal! Vá tomar um café. ☕
5. Quando aparecer a mensagem **"INSTALACAO CONCLUIDA!"**, está tudo pronto.
6. Aperte qualquer tecla para fechar.

> ⚠️ **Se aparecer "Python nao encontrado" ou "Node.js nao encontrado":** significa que a instalação da Parte 2 ou 3 não deu certo (provavelmente você esqueceu de marcar a caixinha "Add to PATH" do Python). **Reinstale o programa que faltou, marcando a caixinha certa, e rode o `install.bat` de novo.**

---

## Parte 7 — Iniciar o Bambi Express

Chegou a hora de usar! 🎬

1. Na pasta do Bambi Express, procure o arquivo **`start.bat`** (ele foi criado automaticamente na Parte 6).
2. Dê **dois cliques** nele.
3. Vão abrir **duas janelas pretas** — **não feche elas!** Elas são o "motor" rodando. Deixe-as abertas enquanto usar o programa.
4. Depois de alguns segundos, seu navegador vai **abrir sozinho** no endereço:

   **http://localhost:3000**

   Se não abrir sozinho, abra o navegador e digite esse endereço na barra de cima.

✅ **Parabéns! O Bambi Express está funcionando!** 🎉

---

## Parte 8 — Configurar as APIs (guia completo)

Esta é a parte que **mais dá dúvida**, então vamos com muita calma. Ao final, seu Bambi Express estará 100% pronto para gerar vídeos. 💪

### 8.1 — O que é uma "chave de API"? (entenda antes)

O Bambi Express, sozinho, **não sabe** criar voz, imagem ou música. Ele **pede ajuda** para empresas especializadas em IA pela internet. Cada uma dessas empresas exige uma **"chave de API"** para saber que é você usando o serviço.

> 🔑 Pense na chave de API como uma **senha secreta e única** que a empresa te dá. Quando o Bambi Express mostra essa senha, a empresa responde: *"Ah, é você! Pode usar."*

**Regras de ouro sobre as chaves:**

- ⚠️ **Nunca compartilhe** suas chaves com ninguém, nem poste em prints/vídeos. Quem tiver sua chave pode gastar seus créditos.
- Uma chave costuma ser um texto grande e embaralhado, tipo: `sk_a1b2c3d4e5f6...`
- Sempre **copie e cole** a chave (nunca digite à mão) para não errar nenhuma letra.

### 8.2 — Quais APIs você precisa

| Serviço | Para que serve | Obrigatório? | Custo típico |
|---------|----------------|--------------|--------------|
| **ElevenLabs** ou **Minimax** | Cria a narração (a voz) | ✅ Sim (uma das duas) | Tem plano grátis limitado / pago |
| **AssemblyAI** | Sincroniza a legenda com a fala (timestamps) | ✅ Sim | Tem cota grátis |
| **Google Gemini** | Lê o texto e divide em cenas | ✅ Sim | Grátis (com limites) |
| **WaveSpeed** | Gera as imagens das cenas | ✅ Sim | Pago (por crédito/$) |
| **Suno** | Cria música de fundo com IA | ❌ Opcional | Pago |

> 💡 **Sobre a voz:** você pode escolher entre **ElevenLabs** (vozes muito naturais) **OU** **Minimax** (que usa a mesma chave do WaveSpeed e tem controle de emoção). Você **não precisa das duas** — escolha uma. Se estiver na dúvida, comece com a **ElevenLabs**.

### 8.3 — Abrindo a tela de configuração

1. Com o Bambi Express aberto no navegador (**http://localhost:3000**), procure e clique em **"Configurações"** (pode aparecer como *Config* ou um ícone de engrenagem ⚙️).
2. Clique na aba **"Configuração de APIs"**.
3. Você verá vários blocos: *Provedor de Áudio*, *ElevenLabs*, *Minimax*, *AssemblyAI*, *Google Gemini* e *WaveSpeed*.

> 👁️ Ao lado de cada campo de chave há um **ícone de olho**. Clique nele para **mostrar ou esconder** o que você digitou — útil para conferir se colou certo.

Agora vamos pegar cada chave, uma de cada vez. Deixe a aba de configuração aberta e vá abrindo os sites em outra aba do navegador.

---

### 8.4 — Google Gemini (comece por aqui, é grátis) 🟢

Serve para o programa **entender seu texto e dividir em cenas**.

1. Acesse: **https://aistudio.google.com/apikey**
2. Faça login com sua **conta Google** (a mesma do Gmail).
3. Clique no botão **"Create API key" / "Criar chave de API"**.
4. Pode aparecer para escolher um projeto — se aparecer, escolha qualquer um ou crie um novo, e confirme.
5. Vai aparecer sua chave. Clique no botão de **copiar** 📋.
6. Volte ao Bambi Express → bloco **"Google Gemini"** → cole no campo **"API Key"**.
7. No campo **"Modelo"**, deixe **"Gemini 2.0 Flash"** (é o recomendado).
8. Clique em **"Testar conexão"** logo abaixo. Se aparecer **"Conectado"** em verde, deu certo! ✅

---

### 8.5 — AssemblyAI (grátis para começar) 🟢

Serve para **sincronizar a legenda com a fala** (saber a hora exata de cada palavra).

1. Acesse: **https://www.assemblyai.com/** e clique em **"Sign up" / Criar conta**.
2. Confirme seu e-mail, se pedir.
3. Ao entrar no painel (*Dashboard*), sua **API Key** aparece logo na tela inicial, num campo escrito **"Your API Key"**. Clique para **copiar**.
4. Volte ao Bambi Express → bloco **"AssemblyAI (Transcrição)"** → cole no campo **"API Key"**.
5. No campo **"Idioma"**, escolha o idioma do seu texto (ex.: **Português (BR)**). Se o texto puder ser em vários idiomas, escolha **"Auto-detectar"**.
6. Clique em **"Testar conexão"**. Espere o **"Conectado"** verde. ✅

---

### 8.6 — WaveSpeed (gera as imagens — precisa de créditos) 💳

Serve para **criar as imagens** de cada cena. É um serviço **pago** (você coloca créditos e vai gastando).

1. Acesse: **https://wavespeed.ai/** e crie sua conta (**Sign up**).
2. Procure no painel a seção de **"API Keys"** (Chaves de API), geralmente dentro de *Settings* / *Account* / *Dashboard*.
3. Clique em **"Create / Generate API Key"**, dê um nome qualquer (ex.: `bambi`) e **copie** a chave gerada.
4. Volte ao Bambi Express → bloco **"WaveSpeed Flux"** → cole no campo **"API Key"**.
5. Configurações recomendadas neste bloco:
   - **Modelo:** *Flux Dev Ultra Fast* (bom equilíbrio entre velocidade e qualidade).
   - **Resolução:** *1920x1080* para vídeo normal (deitado), ou *1080x1920* para vídeo vertical (Reels/TikTok/Shorts).
   - **Formato:** *PNG* (mais qualidade) ou *JPEG* (arquivo menor).
   - **Estilo Visual:** pode deixar o texto que já vem preenchido, ou trocar por um estilo seu (ex.: `cinematic, dramatic lighting, 8k`).
6. Clique em **"Testar conexão"** e espere o **"Conectado"** verde. ✅

> 💰 Para gerar imagens de verdade, você precisa **adicionar créditos** (dinheiro) na sua conta WaveSpeed. Quando conectado, o Bambi Express mostra o **saldo em $** no topo desse bloco.

---

### 8.7 — A voz: escolha ElevenLabs OU Minimax 🎙️

No topo da tela há o bloco **"Provedor de Áudio"** com dois botões: **ElevenLabs** e **Minimax**. Clique no que você vai usar. **Escolha só um.**

#### Opção A — ElevenLabs (recomendada para iniciantes)

1. Acesse: **https://elevenlabs.io/** e crie uma conta (**Sign up**).
2. Depois de logado, clique na sua **foto/inicial** no canto e vá em **"Profile"** ou **"API Keys"**.
   - O caminho costuma ser: ícone do perfil → **"API Keys"** → **"Create API Key"**.
3. **Copie** a chave gerada.
4. Volte ao Bambi Express → bloco **"ElevenLabs"** → cole no campo **"API Key"**.
5. Clique em **"Testar conexão"**. Quando conectar, a listinha **"Voice ID"** vai **carregar as vozes disponíveis**.
6. Abra o **"Voice ID"** e **escolha uma voz** da lista (experimente algumas depois para ver qual gosta mais). ✅

#### Opção B — Minimax (usa a mesma chave do WaveSpeed)

> Só faça isto se você **não** for usar a ElevenLabs.

1. No bloco **"Provedor de Áudio"**, clique em **"Minimax"** (vai aparecer a etiqueta **"Ativo"**).
2. **Não precisa de chave nova!** O Minimax usa a **mesma API Key do WaveSpeed** que você já colocou na Parte 8.6.
3. No bloco **"Minimax Audio"**, ajuste:
   - **Voz:** escolha uma da lista.
   - **Emoção:** *neutral* costuma ser a mais segura para começar.
   - **Velocidade / Pitch / Volume:** pode deixar no padrão.
4. Clique em **"Testar conexão"** e espere o **"Conectado"** verde. ✅

---

### 8.8 — Suno (música por IA — opcional, pode pular) 🎵

Isto é **totalmente opcional**. O programa já pode usar músicas da biblioteca interna sem precisar do Suno. Só configure se quiser que a **música de fundo seja criada por IA**.

- A chave do Suno **não fica** na aba "Configuração de APIs". Ela é usada na aba de **Música**: escolha o modo **"Gerar com IA (Suno)"** e informe a chave lá.
- Como o Suno **não tem uma API oficial pública fácil**, isso é considerado um recurso **avançado**. Se você é iniciante, **pule esta etapa** por enquanto.

---

### 8.9 — Salvar e testar tudo (passo final!) 💾

**Muito importante:** de nada adianta preencher as chaves e não salvar!

1. Role a tela até o final da aba de configuração.
2. Clique no botão **"Testar Todas"** — o programa vai checar todas as APIs de uma vez. O ideal é que todas as obrigatórias mostrem **"Conectado"** em verde.
3. Clique no botão azul **"Salvar"**. Vai aparecer a mensagem **"Configurações salvas!"**.

✅ **Pronto! Agora é só escrever seu texto e mandar gerar o vídeo.** 🚀

---

### 8.10 — Resumo das APIs (cola rápida)

| Serviço | Onde pegar a chave | Onde colar no Bambi |
|---------|--------------------|---------------------|
| **Google Gemini** | https://aistudio.google.com/apikey | Bloco "Google Gemini" → API Key |
| **AssemblyAI** | https://www.assemblyai.com/ (Dashboard) | Bloco "AssemblyAI" → API Key |
| **WaveSpeed** | https://wavespeed.ai/ (API Keys) | Bloco "WaveSpeed Flux" → API Key |
| **ElevenLabs** | https://elevenlabs.io/ (Profile → API Keys) | Bloco "ElevenLabs" → API Key |
| **Minimax** | (usa a chave do WaveSpeed) | Só escolher a voz no bloco "Minimax" |
| **Suno** (opcional) | Recurso avançado | Aba "Música" → modo "Gerar com IA" |

> 💡 **Dica de custo:** Gemini e AssemblyAI têm uso gratuito para começar. **WaveSpeed é pago** (você precisa de créditos para gerar imagens) e a **ElevenLabs** tem um plano grátis limitado. Confira os planos no site de cada um antes de usar bastante.

---

## 🔄 Como atualizar o Bambi Express depois

Quando sair uma versão nova, você **não precisa reinstalar tudo**. Basta:

1. Abrir a pasta do Bambi Express.
2. Dar dois cliques no arquivo **`update.bat`**.
3. Aguardar. Se ele avisar que houve mudanças nas peças internas, rode o **`install.bat`** de novo.

---

## 🆘 Deu Problema? (soluções comuns)

**❌ "Python nao encontrado" ou "Node.js nao encontrado" ao rodar o install.bat**
→ Você provavelmente esqueceu de marcar **"Add python.exe to PATH"** na Parte 2. Reinstale o Python marcando essa caixinha e rode o `install.bat` de novo. Sempre **feche e reabra** as janelas depois de instalar algo.

**❌ A janela preta abre e fecha muito rápido, sem dar para ler**
→ Não dê dois cliques direto. Em vez disso: abra o Prompt de Comando na pasta do programa e digite `install.bat` (ou `start.bat`) e aperte Enter. Assim a janela fica aberta e você consegue ler a mensagem de erro.

**❌ O navegador abre mas aparece "Não é possível acessar esse site" ou fica carregando eternamente**
→ Espere mais um pouco (o primeiro carregamento demora). Confirme que as **duas janelas pretas** do `start.bat` ainda estão abertas. Se você fechou alguma, rode o `start.bat` de novo.

**❌ O vídeo não é gerado / dá erro ao montar o vídeo**
→ Provavelmente o **FFmpeg** não foi instalado corretamente (Parte 4). Abra o PowerShell e teste com `ffmpeg -version`. Se não funcionar, refaça a Parte 4.

**❌ Dá erro dizendo que faltou uma chave de API**
→ Você precisa preencher as chaves na Parte 8. Confira se colou todas as chaves **obrigatórias** e se não sobrou espaço em branco. **Não esqueça de clicar em "Salvar"!**

**❌ A conexão da API deu "Falha" (vermelho) no botão "Testar conexão"**
→ Quase sempre é a chave colada errada. Clique no **ícone de olho** 👁️ para ver o que foi digitado e confira se não faltou um pedaço ou sobrou espaço no começo/fim. Gere a chave de novo no site se precisar. Confira também se você está com **internet** funcionando.

**❌ As imagens não são geradas / erro de "créditos" no WaveSpeed**
→ O WaveSpeed é **pago**. Você precisa **adicionar créditos** na sua conta no site do WaveSpeed. Quando conectado, o saldo em **$** aparece no topo do bloco WaveSpeed.

**❌ A voz não é gerada**
→ Confira se você escolheu um **"Provedor de Áudio"** (ElevenLabs ou Minimax) no topo. Se usa ElevenLabs, confirme que também selecionou uma voz na lista **"Voice ID"**. Se usa Minimax, lembre que ele depende da chave do **WaveSpeed** estar preenchida.

**❌ "git não é reconhecido como comando"**
→ O Git não foi instalado ou você não reabriu a janela. Feche todas as janelas de terminal, abra uma nova e tente de novo. Se persistir, refaça a Parte 1.

---

## 📌 Resumo rápido (cola)

Para quem já leu tudo e só quer lembrar a ordem:

1. Instalar **Git** → https://git-scm.com/download/win
2. Instalar **Python** (⚠️ marcar "Add to PATH") → https://www.python.org/downloads/
3. Instalar **Node.js** (versão LTS) → https://nodejs.org/
4. Instalar **FFmpeg** → `winget install --id Gyan.FFmpeg -e`
5. Baixar o projeto → `git clone https://github.com/sterling9879/bambi-express.git`
6. Rodar **`install.bat`** (dois cliques)
7. Rodar **`start.bat`** (dois cliques) → abre em http://localhost:3000
8. Colocar as **chaves de API** em Configurações → "Configuração de APIs" (Gemini, AssemblyAI, WaveSpeed e a voz ElevenLabs/Minimax), **testar** e clicar em **"Salvar"**

---

Feito com carinho para quem está começando. Qualquer dúvida, releia o passo com calma — você consegue! 💛
