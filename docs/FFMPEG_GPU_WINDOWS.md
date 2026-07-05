# Instalação do FFmpeg com Suporte a GPU no Windows

Este guia ensina como instalar o FFmpeg com aceleração por hardware (GPU) no Windows para usar com o Bambi-Express.

## Índice

1. [Verificar GPU](#1-verificar-gpu)
2. [Baixar FFmpeg](#2-baixar-ffmpeg)
3. [Instalar FFmpeg](#3-instalar-ffmpeg)
4. [Verificar Instalação](#4-verificar-instalação)
5. [Configurar no Bambi-Express](#5-configurar-no-bambi-express)
6. [Solução de Problemas](#6-solução-de-problemas)

---

## 1. Verificar GPU

### NVIDIA
```cmd
nvidia-smi
```
Se aparecer informações da GPU, você tem suporte NVIDIA.

### AMD
Abra o **Gerenciador de Dispositivos** > **Adaptadores de vídeo** e verifique se há uma GPU AMD.

### Intel
CPUs Intel com gráficos integrados (Intel UHD, Intel Iris) suportam Quick Sync.

---

## 2. Baixar FFmpeg

### Opção A: Download Direto (Recomendado)

1. Acesse: https://www.gyan.dev/ffmpeg/builds/
2. Baixe a versão **ffmpeg-git-full.7z** (inclui todos os encoders)
3. Extraia o arquivo `.7z` (use [7-Zip](https://www.7-zip.org/) se necessário)

### Opção B: Via Winget (Windows 11)
```cmd
winget install Gyan.FFmpeg
```

### Opção C: Via Chocolatey
```cmd
choco install ffmpeg-full
```

### Opção D: Via Scoop
```cmd
scoop install ffmpeg
```

---

## 3. Instalar FFmpeg

### Passo 1: Extrair arquivos

Extraia o conteúdo para uma pasta, por exemplo:
```
C:\ffmpeg
```

A estrutura deve ficar assim:
```
C:\ffmpeg\
├── bin\
│   ├── ffmpeg.exe
│   ├── ffprobe.exe
│   └── ffplay.exe
├── doc\
└── presets\
```

### Passo 2: Adicionar ao PATH

1. Pressione `Win + R`, digite `sysdm.cpl` e pressione Enter
2. Vá para a aba **Avançado**
3. Clique em **Variáveis de Ambiente**
4. Em **Variáveis do sistema**, encontre `Path` e clique em **Editar**
5. Clique em **Novo** e adicione:
   ```
   C:\ffmpeg\bin
   ```
6. Clique **OK** em todas as janelas

### Passo 3: Reiniciar o terminal

Feche e abra novamente o CMD/PowerShell para as mudanças terem efeito.

---

## 4. Verificar Instalação

### Verificar versão
```cmd
ffmpeg -version
```

### Verificar encoder NVIDIA (NVENC)
```cmd
ffmpeg -encoders | findstr nvenc
```

**Saída esperada:**
```
 V..... h264_nvenc           NVIDIA NVENC H.264 encoder (codec h264)
 V..... hevc_nvenc           NVIDIA NVENC hevc encoder (codec hevc)
```

### Verificar encoder AMD (AMF)
```cmd
ffmpeg -encoders | findstr amf
```

**Saída esperada:**
```
 V..... h264_amf             AMD AMF H.264 Encoder (codec h264)
 V..... hevc_amf             AMD AMF HEVC encoder (codec hevc)
```

### Verificar encoder Intel (Quick Sync)
```cmd
ffmpeg -encoders | findstr qsv
```

**Saída esperada:**
```
 V..... h264_qsv             H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10 (Intel Quick Sync Video acceleration) (codec h264)
```

### Teste de codificação GPU

**NVIDIA:**
```cmd
ffmpeg -f lavfi -i testsrc=duration=5:size=1280x720:rate=30 -c:v h264_nvenc -preset p4 test_nvidia.mp4
```

**AMD:**
```cmd
ffmpeg -f lavfi -i testsrc=duration=5:size=1280x720:rate=30 -c:v h264_amf -quality balanced test_amd.mp4
```

**Intel:**
```cmd
ffmpeg -f lavfi -i testsrc=duration=5:size=1280x720:rate=30 -c:v h264_qsv -preset medium test_intel.mp4
```

Se o arquivo de teste for criado sem erros, a GPU está funcionando!

---

## 5. Configurar no Bambi-Express

1. Abra o Bambi-Express no navegador
2. Vá para **Configurações** > **Configurações de Vídeo (FFMPEG)**
3. Em **Processamento de Vídeo**, selecione:
   - **GPU NVIDIA (NVENC)** - se você tem GPU NVIDIA
   - **GPU AMD (AMF)** - se você tem GPU AMD
   - **Intel Quick Sync** - se você tem Intel com iGPU
4. Clique em **Salvar**

### Comparação de Performance

| Encoder | Velocidade | Qualidade | Uso de CPU |
|---------|------------|-----------|------------|
| CPU (libx264) | 1x (referência) | Excelente | 100% |
| NVIDIA NVENC | 5-10x mais rápido | Muito boa | ~10% |
| AMD AMF | 4-8x mais rápido | Muito boa | ~10% |
| Intel QSV | 3-5x mais rápido | Boa | ~15% |

---

## 6. Solução de Problemas

### Erro: "Unknown encoder 'h264_nvenc'"

**Causa:** FFmpeg não foi compilado com suporte NVENC.

**Solução:** Baixe a versão "full" do gyan.dev conforme instruções acima.

---

### Erro: "Cannot load nvcuda.dll"

**Causa:** Driver NVIDIA não instalado ou desatualizado.

**Solução:**
1. Baixe o driver mais recente: https://www.nvidia.com/drivers
2. Instale e reinicie o computador

---

### Erro: "No capable devices found" (NVIDIA)

**Causa:** GPU muito antiga ou não suporta NVENC.

**Solução:** 
- GPUs suportadas: GTX 600 series ou mais recente
- Use CPU (libx264) como fallback

---

### Erro: "amf encoder initialization failed" (AMD)

**Causa:** Driver AMD desatualizado ou GPU não suportada.

**Solução:**
1. Atualize o driver: https://www.amd.com/support
2. Verifique se sua GPU suporta AMF (RX 400 series ou mais recente)

---

### Erro: "qsv encoder initialization failed" (Intel)

**Causa:** Intel Media SDK não instalado ou CPU sem Quick Sync.

**Solução:**
1. Verifique se seu processador suporta Quick Sync: https://ark.intel.com
2. Instale o Intel Graphics Driver mais recente

---

### Performance muito baixa com GPU

**Possíveis causas:**
1. Resolução muito alta para a GPU
2. Preset muito "lento" (slow/veryslow)

**Solução:** Use preset `fast` ou `medium` no Bambi-Express.

---

### Como voltar para CPU

Se a GPU não funcionar, simplesmente selecione **CPU (libx264)** nas configurações do Bambi-Express. É a opção mais compatível e funciona em qualquer sistema.

---

## Dicas Adicionais

### Verificar uso de GPU durante encoding

**NVIDIA:**
```cmd
nvidia-smi -l 1
```
Procure por "Video Encode" no uso de GPU.

### Manter FFmpeg atualizado

O site gyan.dev atualiza builds frequentemente. Recomenda-se atualizar a cada 2-3 meses para correções de bugs e melhorias de performance.

### Docker com GPU (Avançado)

Se você roda o Bambi-Express em Docker, use:

```dockerfile
FROM nvidia/cuda:12.0-runtime-ubuntu22.04

RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*
```

E execute com:
```bash
docker run --gpus all ...
```

---

## Links Úteis

- [FFmpeg Downloads](https://www.gyan.dev/ffmpeg/builds/)
- [NVIDIA Drivers](https://www.nvidia.com/drivers)
- [AMD Drivers](https://www.amd.com/support)
- [Intel Drivers](https://www.intel.com/content/www/us/en/download-center/home.html)
- [FFmpeg NVENC Guide](https://trac.ffmpeg.org/wiki/HWAccelIntro)
- [Lista de GPUs com suporte NVENC](https://developer.nvidia.com/video-encode-and-decode-gpu-support-matrix-new)
