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

## Parte 8 — Configurar as chaves de API (importante!)

O Bambi Express usa serviços de IA de outras empresas para criar voz, imagem e transcrição. Para isso, você precisa das **"chaves de API"** — pense nelas como **senhas** que liberam esses serviços.

Você vai precisar criar uma conta e pegar a chave em cada um destes sites:

| Serviço | Para que serve | Obrigatório? |
|---------|----------------|--------------|
| **ElevenLabs** | Cria a narração (voz) | ✅ Sim |
| **AssemblyAI** | Sincroniza a legenda com a voz | ✅ Sim |
| **Google Gemini** | Divide o texto em cenas | ✅ Sim |
| **WaveSpeed** | Gera as imagens | ✅ Sim |
| **Suno** | Cria músicas de fundo | ❌ Opcional |

**Como colocar as chaves no programa:**

1. Com o Bambi Express aberto no navegador (http://localhost:3000), procure a seção de **"Configurações"** (Config / Settings).
2. Cole cada chave no campo correspondente.
3. Salve.

Pronto! Agora é só escrever seu texto e mandar gerar o vídeo. 🚀

> 💡 Cada um desses serviços pode ter **custos** ou **limites gratuitos**. Confira os planos no site de cada um antes de usar bastante.

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
→ Você precisa preencher as chaves na Parte 8. Confira se colou todas as chaves **obrigatórias** e se não sobrou espaço em branco.

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
8. Colocar as **chaves de API** nas Configurações

---

Feito com carinho para quem está começando. Qualquer dúvida, releia o passo com calma — você consegue! 💛
