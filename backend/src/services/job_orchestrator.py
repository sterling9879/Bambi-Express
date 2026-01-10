"""
Orquestrador do pipeline de geração de vídeo.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Callable, Any
from pathlib import Path

from .text_processor import TextProcessor
from .audio_generator import ElevenLabsGenerator, get_audio_generator
from .audio_merger import AudioMerger
from .silence_remover import SilenceRemover
from .transcriber import AssemblyAITranscriber
from .scene_analyzer import SceneAnalyzer
from .image_generator import WaveSpeedGenerator, get_image_generator
from .music_manager import MusicManager
from .ai_music_generator import AIMusicGenerator
from .audio_mixer import AudioMixer
from .video_composer import VideoComposer
from .effects_applier import EffectsApplier
from .effects_manager import get_effects_manager
from .subtitle_burner import SubtitleBurner

from ..models.config import FullConfig
from ..models.job import JobStatus, JobStatusEnum

logger = logging.getLogger(__name__)


class JobOrchestrator:
    """
    Orquestra todo o pipeline de geração de vídeo.

    Features:
    - Execução sequencial das etapas
    - Atualização de progresso em tempo real
    - Logs detalhados em tempo real
    - Tratamento de erros com retry
    - Possibilidade de retomar de etapa específica
    """

    def __init__(
        self,
        config: FullConfig,
        temp_dir: str = "storage/temp",
        output_dir: str = "storage/outputs",
        music_library_path: str = "storage/music",
        status_callback: Optional[Callable[[JobStatus], Any]] = None
    ):
        self.config = config
        self.temp_dir = Path(temp_dir)
        self.output_dir = Path(output_dir)
        self.music_library_path = music_library_path
        self.status_callback = status_callback
        self._logs: list[str] = []

        # Ensure directories exist
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _add_log(self, message: str):
        """Adiciona uma mensagem ao log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self._logs.append(log_entry)
        logger.info(message)

    async def run(self, job_id: str, text: str) -> str:
        """
        Executa pipeline completo.

        Args:
            job_id: ID único do job
            text: Texto para gerar vídeo

        Returns:
            Path do vídeo gerado
        """
        started_at = datetime.now()
        job_temp_dir = self.temp_dir / job_id
        job_temp_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Clear logs for new job
            self._logs = []

            # 1. Processar texto
            self._add_log("Iniciando processamento de texto...")
            await self._update_status(
                job_id, JobStatusEnum.PROCESSING_TEXT, 0.05,
                "Processando texto", started_at
            )

            text_processor = TextProcessor()
            chunks = text_processor.process(text)

            self._add_log(f"Texto dividido em {len(chunks)} chunks")

            # 2. Gerar áudios
            # Determinar qual provider de áudio usar
            audio_provider_name = self.config.api.audio_provider.value if hasattr(self.config.api.audio_provider, 'value') else self.config.api.audio_provider
            provider_display = "Minimax" if audio_provider_name == "minimax" else "ElevenLabs"

            self._add_log(f"Iniciando geração de áudio com {provider_display}...")
            await self._update_status(
                job_id, JobStatusEnum.GENERATING_AUDIO, 0.10,
                "Gerando áudio", started_at,
                {"chunks_total": len(chunks), "provider": provider_display}
            )

            audio_generator = get_audio_generator(
                config=self.config,
                output_dir=str(job_temp_dir),
                log_callback=self._add_log
            )

            # Progress callback simples - sem asyncio.create_task para evitar tasks órfãs
            def audio_progress(c, t):
                try:
                    # Atualização síncrona para evitar race conditions
                    if self.status_callback:
                        from ..models.job import JobStatus
                        status = JobStatus(
                            job_id=job_id,
                            status=JobStatusEnum.GENERATING_AUDIO,
                            progress=0.10 + (c / t) * 0.15,
                            current_step=f"Gerando áudio {c}/{t}",
                            details={"chunks_completed": c, "chunks_total": t},
                            logs=self._logs.copy(),
                            started_at=started_at,
                            updated_at=datetime.now()
                        )
                        self.status_callback(status)
                except Exception as e:
                    logger.warning(f"Audio progress callback error: {e}")

            audio_chunks = await audio_generator.generate_all(
                chunks,
                progress_callback=audio_progress
            )

            # 3. Concatenar áudios
            self._add_log(f"Áudio gerado com sucesso. Concatenando {len(audio_chunks)} arquivos...")
            await self._update_status(
                job_id, JobStatusEnum.MERGING_AUDIO, 0.25,
                "Concatenando áudio", started_at
            )

            audio_merger = AudioMerger(output_dir=str(job_temp_dir))
            merged_audio = audio_merger.merge(audio_chunks)

            self._add_log(f"Áudio concatenado: {merged_audio.duration_ms}ms ({merged_audio.duration_ms / 1000:.1f}s)")

            # 3.5. Remover silêncios do áudio
            self._add_log("Detectando e removendo silêncios...")
            await self._update_status(
                job_id, JobStatusEnum.MERGING_AUDIO, 0.27,
                "Removendo silêncios", started_at
            )

            silence_remover = SilenceRemover(
                output_dir=str(job_temp_dir),
                log_callback=self._add_log
            )

            silence_result = silence_remover.remove_silences(
                audio_path=merged_audio.path,
                output_filename="audio_trimmed.mp3",
                silence_threshold_db=-40,
                min_silence_duration=0.5,
                keep_silence_ms=200
            )

            # Atualizar o caminho do áudio para usar o arquivo sem silêncios
            if silence_result.time_saved_ms > 0:
                merged_audio.path = silence_result.path
                merged_audio.duration_ms = silence_result.new_duration_ms
                self._add_log(
                    f"Silêncios removidos: {silence_result.silences_removed} trechos, "
                    f"{silence_result.time_saved_ms/1000:.1f}s economizados"
                )

            # 4. Transcrever com AssemblyAI
            self._add_log("Enviando áudio para transcrição com AssemblyAI...")
            await self._update_status(
                job_id, JobStatusEnum.TRANSCRIBING, 0.30,
                "Transcrevendo áudio", started_at
            )

            transcriber = AssemblyAITranscriber(
                api_key=self.config.api.assemblyai.api_key
            )

            # Progress callback para transcrição
            def transcribe_progress(s, p):
                try:
                    if self.status_callback:
                        from ..models.job import JobStatus
                        status = JobStatus(
                            job_id=job_id,
                            status=JobStatusEnum.TRANSCRIBING,
                            progress=0.30 + p * 0.10,
                            current_step=f"Transcrevendo: {s}",
                            details={},
                            logs=self._logs.copy(),
                            started_at=started_at,
                            updated_at=datetime.now()
                        )
                        self.status_callback(status)
                except Exception as e:
                    logger.warning(f"Transcribe progress callback error: {e}")

            transcription = await transcriber.transcribe(
                audio_path=merged_audio.path,
                language_code=self.config.api.assemblyai.language_code,
                progress_callback=transcribe_progress
            )

            self._add_log(
                f"Transcrição concluída: {len(transcription.words)} palavras, "
                f"{len(transcription.segments)} segmentos"
            )

            # 5. Analisar cenas
            self._add_log("Iniciando análise de cenas com Gemini...")
            await self._update_status(
                job_id, JobStatusEnum.ANALYZING_SCENES, 0.40,
                "Analisando cenas", started_at
            )

            scene_analyzer = SceneAnalyzer(
                api_key=self.config.api.gemini.api_key,
                model=self.config.api.gemini.model,
                image_style=self.config.api.wavespeed.image_style,
                scene_context=getattr(self.config.api.gemini, 'scene_context', ''),
                log_callback=self._add_log
            )

            scene_analysis = await scene_analyzer.analyze(
                transcription,
                min_scene_duration=self.config.ffmpeg.scene_duration.min_duration or 3.0,
                max_scene_duration=self.config.ffmpeg.scene_duration.max_duration or 6.0
            )

            self._add_log(f"Análise de cenas concluída: {len(scene_analysis.scenes)} cenas identificadas")

            # 6. Selecionar/gerar música
            self._add_log("Selecionando música de fundo...")
            await self._update_status(
                job_id, JobStatusEnum.SELECTING_MUSIC, 0.45,
                "Selecionando música", started_at
            )

            music_segments = []
            if self.config.music.mode.value == "library":
                music_manager = MusicManager(library_path=self.music_library_path)
                music_segments = music_manager.select_music(
                    scenes=scene_analysis.scenes,
                    music_cues=scene_analysis.music_cues,
                    total_duration_ms=transcription.duration_ms,
                    config=self.config.music
                )
            elif self.config.music.mode.value == "ai_generated":
                if self.config.api.suno and self.config.api.suno.api_key:
                    ai_music = AIMusicGenerator(
                        api_key=self.config.api.suno.api_key,
                        output_dir=str(job_temp_dir)
                    )
                    generated = await ai_music.generate_for_video(
                        scenes=scene_analysis.scenes,
                        total_duration_ms=transcription.duration_ms,
                        config=self.config.music
                    )
                    if generated:
                        from ..models.video import MusicSegment
                        music_segments = [MusicSegment(
                            music_path=generated[0].audio_path,
                            mood=generated[0].style,
                            start_ms=0,
                            end_ms=transcription.duration_ms,
                            fade_in_ms=self.config.music.fade_in_ms,
                            fade_out_ms=self.config.music.fade_out_ms,
                            volume=self.config.music.volume
                        )]

            # 7. Gerar imagens
            # Usar factory function para escolher entre GPU local ou WaveSpeed
            image_generator = get_image_generator(
                config=self.config,
                output_dir=str(job_temp_dir),
                log_callback=self._add_log
            )

            # Determinar qual provider está sendo usado
            is_local = self.config.gpu and self.config.gpu.enabled and self.config.gpu.provider.value == "local"
            provider_name = "GPU Local" if is_local else "WaveSpeed"

            self._add_log(f"Iniciando geração de {len(scene_analysis.scenes)} imagens com {provider_name}...")
            await self._update_status(
                job_id, JobStatusEnum.GENERATING_IMAGES, 0.50,
                "Gerando imagens", started_at,
                {"scenes_total": len(scene_analysis.scenes), "provider": provider_name}
            )

            # Progress callback para imagens - o mais crítico (121+ chamadas)
            def image_progress(c, t):
                try:
                    if self.status_callback:
                        from ..models.job import JobStatus
                        status = JobStatus(
                            job_id=job_id,
                            status=JobStatusEnum.GENERATING_IMAGES,
                            progress=0.50 + (c / t) * 0.30,
                            current_step=f"Gerando imagem {c}/{t}",
                            details={"images_completed": c, "images_total": t},
                            logs=self._logs.copy(),
                            started_at=started_at,
                            updated_at=datetime.now()
                        )
                        self.status_callback(status)
                except Exception as e:
                    logger.warning(f"Image progress callback error: {e}")

            images = await image_generator.generate_all(
                scene_analysis.scenes,
                progress_callback=image_progress
            )

            # 8. Mixar áudio
            self._add_log(f"Imagens geradas com sucesso. Mixando áudio...")
            await self._update_status(
                job_id, JobStatusEnum.MIXING_AUDIO, 0.80,
                "Mixando áudio", started_at
            )

            audio_mixer = AudioMixer(output_dir=str(job_temp_dir))
            mixed_audio = audio_mixer.mix(
                narration_path=merged_audio.path,
                music_segments=music_segments,
                config=self.config.music
            )

            # 9. Compor vídeo
            self._add_log("Áudio mixado. Iniciando composição do vídeo final...")
            await self._update_status(
                job_id, JobStatusEnum.COMPOSING_VIDEO, 0.85,
                "Montando vídeo", started_at
            )

            video_composer = VideoComposer(
                config=self.config.ffmpeg,
                output_dir=str(self.output_dir)
            )

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"{timestamp}_{job_id}.mp4"

            result = video_composer.compose(
                scenes=scene_analysis.scenes,
                images=images,
                audio_path=mixed_audio.path,
                output_filename=output_filename
            )

            # 9.5. Aplicar efeitos de overlay (se configurado)
            effects_config = getattr(self.config, 'effects', None)
            if effects_config and effects_config.enabled and effects_config.effect_id:
                self._add_log("Aplicando efeito de overlay...")
                await self._update_status(
                    job_id, JobStatusEnum.COMPOSING_VIDEO, 0.92,
                    "Aplicando efeitos", started_at
                )

                effects_manager = get_effects_manager()
                effect_path = effects_manager.get_effect_path(effects_config.effect_id)

                if effect_path:
                    effects_applier = EffectsApplier(
                        output_dir=str(self.output_dir),
                        log_callback=self._add_log
                    )

                    # Gerar nome do arquivo com efeito
                    effect_filename = f"{timestamp}_{job_id}_fx.mp4"

                    effect_result = effects_applier.apply_effect(
                        video_path=result.path,
                        effect_path=effect_path,
                        output_filename=effect_filename,
                        blend_mode=effects_config.blend_mode,
                        effect_opacity=effects_config.opacity
                    )

                    # Remover vídeo original sem efeito
                    try:
                        Path(result.path).unlink()
                    except Exception:
                        pass

                    # Atualizar resultado com o vídeo com efeito
                    result.path = effect_result.path
                    result.file_size = effect_result.file_size

                    self._add_log(f"Efeito aplicado: {effect_result.effect_applied}")
                else:
                    self._add_log("Aviso: Efeito configurado não encontrado, pulando...")

            # 9.75. Aplicar legendas (se configurado)
            subtitles_config = getattr(self.config, 'subtitles', None)
            if subtitles_config and subtitles_config.enabled:
                self._add_log("Aplicando legendas estilo filme...")
                await self._update_status(
                    job_id, JobStatusEnum.COMPOSING_VIDEO, 0.95,
                    "Aplicando legendas", started_at
                )

                subtitle_burner = SubtitleBurner(
                    output_dir=str(self.output_dir),
                    log_callback=self._add_log
                )

                # Gerar nome do arquivo com legendas
                subtitle_filename = f"{timestamp}_{job_id}_sub.mp4"

                subtitle_result = subtitle_burner.burn_subtitles(
                    video_path=result.path,
                    transcription=transcription,
                    config=subtitles_config,
                    output_filename=subtitle_filename
                )

                # Remover vídeo anterior sem legendas
                try:
                    Path(result.path).unlink()
                except Exception:
                    pass

                # Atualizar resultado com o vídeo com legendas
                result.path = subtitle_result.path
                result.file_size = subtitle_result.file_size

                self._add_log(f"Legendas aplicadas: {subtitle_result.subtitle_count} segmentos na posição {subtitles_config.position.value}")

            # 10. Finalizar
            await self._update_status(
                job_id, JobStatusEnum.COMPLETED, 1.0,
                "Concluído", started_at,
                {
                    "video_path": result.path,
                    "duration": result.duration_seconds,
                    "scenes": result.scenes_count,
                    "file_size": result.file_size
                }
            )

            self._add_log(f"Vídeo gerado com sucesso: {result.path}")
            self._add_log(f"Duração: {result.duration_seconds:.1f}s, Cenas: {result.scenes_count}, Tamanho: {result.file_size / 1024 / 1024:.1f}MB")

            # Cleanup temp files
            self._add_log("Limpando arquivos temporários...")
            self._cleanup_temp_dir(job_temp_dir)

            return result.path

        except Exception as e:
            self._add_log(f"ERRO no pipeline: {str(e)}")
            await self._update_status(
                job_id, JobStatusEnum.FAILED, 0,
                "Erro", started_at,
                error=str(e)
            )
            raise

    async def _update_status(
        self,
        job_id: str,
        status: JobStatusEnum,
        progress: float,
        current_step: str,
        started_at: datetime,
        details: dict = None,
        error: str = None
    ):
        """Atualiza status do job."""
        job_status = JobStatus(
            job_id=job_id,
            status=status,
            progress=progress,
            current_step=current_step,
            details=details or {},
            logs=self._logs.copy(),
            started_at=started_at,
            updated_at=datetime.now(),
            error=error
        )

        if self.status_callback:
            try:
                result = self.status_callback(job_status)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.warning(f"Status callback error: {e}")

        # Yield control ao event loop para permitir que outras requisições sejam processadas
        await asyncio.sleep(0)

    def _cleanup_temp_dir(self, temp_dir: Path):
        """Remove arquivos temporários após processamento."""
        try:
            import shutil
            shutil.rmtree(temp_dir)
            logger.info(f"Cleaned up temp directory: {temp_dir}")
        except Exception as e:
            logger.warning(f"Failed to cleanup temp directory: {e}")
