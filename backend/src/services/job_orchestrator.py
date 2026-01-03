"""
Orquestrador do pipeline de geração de vídeo.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Callable, Any
from pathlib import Path

from .text_processor import TextProcessor
from .audio_generator import ElevenLabsGenerator
from .audio_merger import AudioMerger
from .transcriber import AssemblyAITranscriber
from .scene_analyzer import SceneAnalyzer
from .image_generator import WaveSpeedGenerator
from .music_manager import MusicManager
from .ai_music_generator import AIMusicGenerator
from .audio_mixer import AudioMixer
from .video_composer import VideoComposer

from ..models.config import FullConfig
from ..models.job import JobStatus, JobStatusEnum

logger = logging.getLogger(__name__)


class JobOrchestrator:
    """
    Orquestra todo o pipeline de geração de vídeo.

    Features:
    - Execução sequencial das etapas
    - Atualização de progresso em tempo real
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

        # Ensure directories exist
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

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
            # 1. Processar texto
            await self._update_status(
                job_id, JobStatusEnum.PROCESSING_TEXT, 0.05,
                "Processando texto", started_at
            )

            text_processor = TextProcessor()
            chunks = text_processor.process(text)

            logger.info(f"Texto dividido em {len(chunks)} chunks")

            # 2. Gerar áudios
            await self._update_status(
                job_id, JobStatusEnum.GENERATING_AUDIO, 0.10,
                "Gerando áudio", started_at,
                {"chunks_total": len(chunks)}
            )

            audio_generator = ElevenLabsGenerator(
                api_key=self.config.api.elevenlabs.api_key,
                voice_id=self.config.api.elevenlabs.voice_id,
                model_id=self.config.api.elevenlabs.model_id,
                output_dir=str(job_temp_dir)
            )

            audio_chunks = await audio_generator.generate_all(
                chunks,
                progress_callback=lambda c, t: asyncio.create_task(
                    self._update_status(
                        job_id,
                        JobStatusEnum.GENERATING_AUDIO,
                        0.10 + (c / t) * 0.15,
                        f"Gerando áudio {c}/{t}",
                        started_at,
                        {"chunks_completed": c, "chunks_total": t}
                    )
                )
            )

            # 3. Concatenar áudios
            await self._update_status(
                job_id, JobStatusEnum.MERGING_AUDIO, 0.25,
                "Concatenando áudio", started_at
            )

            audio_merger = AudioMerger(output_dir=str(job_temp_dir))
            merged_audio = audio_merger.merge(audio_chunks)

            logger.info(f"Áudio concatenado: {merged_audio.duration_ms}ms")

            # 4. Transcrever com AssemblyAI
            await self._update_status(
                job_id, JobStatusEnum.TRANSCRIBING, 0.30,
                "Transcrevendo áudio", started_at
            )

            transcriber = AssemblyAITranscriber(
                api_key=self.config.api.assemblyai.api_key
            )

            transcription = await transcriber.transcribe(
                audio_path=merged_audio.path,
                language_code=self.config.api.assemblyai.language_code,
                progress_callback=lambda s, p: asyncio.create_task(
                    self._update_status(
                        job_id,
                        JobStatusEnum.TRANSCRIBING,
                        0.30 + p * 0.10,
                        f"Transcrevendo: {s}",
                        started_at
                    )
                )
            )

            logger.info(
                f"Transcrição: {len(transcription.words)} palavras, "
                f"{len(transcription.segments)} segmentos"
            )

            # 5. Analisar cenas
            await self._update_status(
                job_id, JobStatusEnum.ANALYZING_SCENES, 0.40,
                "Analisando cenas", started_at
            )

            scene_analyzer = SceneAnalyzer(
                api_key=self.config.api.gemini.api_key,
                model=self.config.api.gemini.model,
                image_style=self.config.api.wavespeed.image_style
            )

            scene_analysis = await scene_analyzer.analyze(
                transcription,
                min_scene_duration=self.config.ffmpeg.scene_duration.min_duration or 3.0,
                max_scene_duration=self.config.ffmpeg.scene_duration.max_duration or 6.0
            )

            logger.info(f"Cenas analisadas: {len(scene_analysis.scenes)}")

            # 6. Selecionar/gerar música
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
            await self._update_status(
                job_id, JobStatusEnum.GENERATING_IMAGES, 0.50,
                "Gerando imagens", started_at,
                {"scenes_total": len(scene_analysis.scenes)}
            )

            image_generator = WaveSpeedGenerator(
                api_key=self.config.api.wavespeed.api_key,
                model=self.config.api.wavespeed.model,
                resolution=self.config.api.wavespeed.resolution,
                output_dir=str(job_temp_dir)
            )

            images = await image_generator.generate_all(
                scene_analysis.scenes,
                progress_callback=lambda c, t: asyncio.create_task(
                    self._update_status(
                        job_id,
                        JobStatusEnum.GENERATING_IMAGES,
                        0.50 + (c / t) * 0.30,
                        f"Gerando imagem {c}/{t}",
                        started_at,
                        {"images_completed": c, "images_total": t}
                    )
                )
            )

            # 8. Mixar áudio
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

            logger.info(f"Vídeo gerado: {result.path}")

            # Cleanup temp files
            self._cleanup_temp_dir(job_temp_dir)

            return result.path

        except Exception as e:
            logger.error(f"Erro no pipeline: {e}", exc_info=True)
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

    def _cleanup_temp_dir(self, temp_dir: Path):
        """Remove arquivos temporários após processamento."""
        try:
            import shutil
            shutil.rmtree(temp_dir)
            logger.info(f"Cleaned up temp directory: {temp_dir}")
        except Exception as e:
            logger.warning(f"Failed to cleanup temp directory: {e}")
