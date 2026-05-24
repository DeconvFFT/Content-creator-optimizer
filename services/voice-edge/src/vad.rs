use crate::contracts::{VadBackend, VoiceEdgeConfig};
use silero::{SampleRate, Session, StreamState};
use std::collections::hash_map::DefaultHasher;
use std::collections::{BTreeMap, VecDeque};
use std::hash::{Hash, Hasher};
use std::path::Path;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::{Arc, Mutex, OnceLock};

const MAX_SILERO_FILE_SESSION_POOLS: usize = 8;
const MAX_SILERO_POOL_SIZE: usize = 16;
const MAX_SILERO_STREAM_STATES_PER_SLOT: usize = 4096;

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct VadDecision {
    pub is_speech: bool,
    pub rms: f64,
    pub speech_probability: f64,
}

#[derive(Debug, Clone, PartialEq)]
pub struct VadAnalysis {
    pub decision: VadDecision,
    pub requested_backend: VadBackend,
    pub effective_backend: &'static str,
    pub target_model: String,
    pub model_path_configured: bool,
    pub fallback_reason: Option<&'static str>,
}

static SILERO_SESSION_CACHE: OnceLock<Mutex<SileroSessionCache>> = OnceLock::new();
static SILERO_SESSION_LOAD_COUNT: AtomicUsize = AtomicUsize::new(0);
static SILERO_ONE_SHOT_SLOT_COUNTER: AtomicUsize = AtomicUsize::new(0);

pub fn analyze_pcm_s16le(samples: &[i16], config: &VoiceEdgeConfig) -> VadDecision {
    analyze_voice_activity(samples, config).decision
}

pub fn analyze_voice_activity(samples: &[i16], config: &VoiceEdgeConfig) -> VadAnalysis {
    analyze_voice_activity_for_stream(samples, config, None)
}

pub fn analyze_voice_activity_for_stream(
    samples: &[i16],
    config: &VoiceEdgeConfig,
    stream_key: Option<&str>,
) -> VadAnalysis {
    match config.vad_backend {
        VadBackend::DeterministicEnergy => VadAnalysis {
            decision: deterministic_energy_gate(samples, config),
            requested_backend: VadBackend::DeterministicEnergy,
            effective_backend: "deterministic_energy_gate",
            target_model: config.target_vad_model.clone(),
            model_path_configured: config.vad_model_path.is_some(),
            fallback_reason: None,
        },
        VadBackend::SileroOnnx => analyze_silero_or_fallback(samples, config, stream_key),
    }
}

fn analyze_silero_or_fallback(
    samples: &[i16],
    config: &VoiceEdgeConfig,
    stream_key: Option<&str>,
) -> VadAnalysis {
    match silero_onnx_gate(samples, config, stream_key) {
        Ok(decision) => VadAnalysis {
            decision,
            requested_backend: VadBackend::SileroOnnx,
            effective_backend: "silero_onnx",
            target_model: config.target_vad_model.clone(),
            model_path_configured: config.vad_model_path.is_some(),
            fallback_reason: None,
        },
        Err(_) if config.allow_vad_fallback => VadAnalysis {
            decision: deterministic_energy_gate(samples, config),
            requested_backend: VadBackend::SileroOnnx,
            effective_backend: "deterministic_energy_gate",
            target_model: config.target_vad_model.clone(),
            model_path_configured: config.vad_model_path.is_some(),
            fallback_reason: Some("silero_onnx_inference_failed"),
        },
        Err(_) => VadAnalysis {
            decision: VadDecision {
                is_speech: false,
                rms: deterministic_energy_gate(samples, config).rms,
                speech_probability: 0.0,
            },
            requested_backend: VadBackend::SileroOnnx,
            effective_backend: "unavailable",
            target_model: config.target_vad_model.clone(),
            model_path_configured: config.vad_model_path.is_some(),
            fallback_reason: Some("silero_onnx_inference_failed_no_fallback"),
        },
    }
}

fn silero_onnx_gate(
    samples: &[i16],
    config: &VoiceEdgeConfig,
    stream_key: Option<&str>,
) -> Result<VadDecision, String> {
    let rms = deterministic_energy_gate(samples, config).rms;
    if samples.is_empty() {
        return Ok(VadDecision {
            is_speech: false,
            rms,
            speech_probability: 0.0,
        });
    }

    let sample_rate = SampleRate::from_hz(config.sample_rate).map_err(|error| error.to_string())?;
    let audio = samples
        .iter()
        .map(|sample| f32::from(*sample) / 32768.0)
        .collect::<Vec<f32>>();
    let probabilities =
        process_with_cached_silero_session(config, sample_rate, &audio, stream_key)?;
    let speech_probability = probabilities
        .iter()
        .copied()
        .fold(0.0_f32, f32::max)
        .clamp(0.0, 1.0);
    let threshold = config.vad_probability_threshold.clamp(0.0, 1.0) as f32;

    Ok(VadDecision {
        is_speech: speech_probability >= threshold,
        rms,
        speech_probability: f64::from(speech_probability),
    })
}

fn process_with_cached_silero_session(
    config: &VoiceEdgeConfig,
    sample_rate: SampleRate,
    audio: &[f32],
    stream_key: Option<&str>,
) -> Result<Vec<f32>, String> {
    let pool = {
        let cache = SILERO_SESSION_CACHE.get_or_init(|| Mutex::new(SileroSessionCache::default()));
        let mut cache = cache
            .lock()
            .map_err(|_| "silero_session_cache_poisoned".to_string())?;
        cache.pool(config)?
    };
    pool.process(sample_rate, audio, stream_key)
}

#[derive(Debug, Clone)]
enum SileroModelSource {
    Bundled,
    File(String),
}

struct SileroSessionPool {
    source: SileroModelSource,
    stream_state_cache_size: usize,
    slots: Vec<Mutex<SileroSessionSlot>>,
}

impl SileroSessionPool {
    fn new(source: SileroModelSource, size: usize, stream_state_cache_size: usize) -> Self {
        let size = size.clamp(1, MAX_SILERO_POOL_SIZE);
        let stream_state_cache_size =
            stream_state_cache_size.clamp(1, MAX_SILERO_STREAM_STATES_PER_SLOT);
        let slots = (0..size)
            .map(|_| Mutex::new(SileroSessionSlot::default()))
            .collect();
        Self {
            source,
            stream_state_cache_size,
            slots,
        }
    }

    fn process(
        &self,
        sample_rate: SampleRate,
        audio: &[f32],
        stream_key: Option<&str>,
    ) -> Result<Vec<f32>, String> {
        let stream_key = normalize_stream_key(stream_key);
        let index = session_slot_index(stream_key, self.slots.len());
        let mut slot = self.slots[index]
            .lock()
            .map_err(|_| "silero_session_slot_poisoned".to_string())?;
        if slot.session.is_none() {
            slot.session = Some(self.load_session()?);
            SILERO_SESSION_LOAD_COUNT.fetch_add(1, Ordering::Relaxed);
        }
        let Some(raw_stream_key) = stream_key else {
            let session = slot
                .session
                .as_mut()
                .ok_or_else(|| "silero_session_slot_empty".to_string())?;
            let mut stream = StreamState::new(sample_rate);
            return session
                .process_stream(&mut stream, audio)
                .map(|probabilities| probabilities.to_vec())
                .map_err(|error| error.to_string());
        };

        let stream_key = stream_state_key(raw_stream_key, sample_rate);
        let cache_size = self.stream_state_cache_size;
        slot.ensure_stream_state(&stream_key, sample_rate, cache_size);
        let mut stream = slot
            .streams
            .remove(&stream_key)
            .ok_or_else(|| "silero_stream_state_missing".to_string())?;
        let session = slot
            .session
            .as_mut()
            .ok_or_else(|| "silero_session_slot_empty".to_string())?;
        match session.process_stream(&mut stream, audio) {
            Ok(probabilities) => {
                let probabilities = probabilities.to_vec();
                slot.streams.insert(stream_key, stream);
                Ok(probabilities)
            }
            Err(error) => Err(error.to_string()),
        }
    }

    fn load_session(&self) -> Result<Session, String> {
        match &self.source {
            SileroModelSource::Bundled => Session::bundled().map_err(|error| error.to_string()),
            SileroModelSource::File(path) => {
                Session::from_file(path).map_err(|error| error.to_string())
            }
        }
    }

    fn size(&self) -> usize {
        self.slots.len()
    }

    fn stream_state_cache_size(&self) -> usize {
        self.stream_state_cache_size
    }
}

#[derive(Default)]
struct SileroSessionSlot {
    session: Option<Session>,
    streams: BTreeMap<String, StreamState>,
    stream_lru: VecDeque<String>,
}

impl SileroSessionSlot {
    fn ensure_stream_state(&mut self, key: &str, sample_rate: SampleRate, cache_size: usize) {
        if let Some(stream) = self.streams.get_mut(key) {
            stream.set_sample_rate(sample_rate);
            self.touch_stream_key(key);
            return;
        }
        while self.streams.len() >= cache_size {
            if let Some(oldest_key) = self.stream_lru.pop_front() {
                self.streams.remove(&oldest_key);
            } else {
                break;
            }
        }
        self.streams
            .insert(key.to_string(), StreamState::new(sample_rate));
        self.stream_lru.push_back(key.to_string());
    }

    fn touch_stream_key(&mut self, key: &str) {
        self.stream_lru.retain(|candidate| candidate != key);
        self.stream_lru.push_back(key.to_string());
    }
}

#[derive(Default)]
struct SileroSessionCache {
    bundled: Option<Arc<SileroSessionPool>>,
    file_sessions: BTreeMap<String, Arc<SileroSessionPool>>,
    file_session_lru: VecDeque<String>,
}

impl SileroSessionCache {
    fn pool(&mut self, config: &VoiceEdgeConfig) -> Result<Arc<SileroSessionPool>, String> {
        let size = config.vad_session_pool_size.clamp(1, MAX_SILERO_POOL_SIZE);
        let stream_state_cache_size = config
            .vad_stream_state_cache_size
            .clamp(1, MAX_SILERO_STREAM_STATES_PER_SLOT);
        if let Some(path) = config.vad_model_path.as_deref() {
            let key = silero_file_session_key(path, size, stream_state_cache_size);
            if let Some(pool) = self.file_sessions.get(&key).map(Arc::clone) {
                self.touch_file_session_key(&key);
                return Ok(pool);
            }
            if self.file_sessions.len() >= MAX_SILERO_FILE_SESSION_POOLS {
                if let Some(oldest_key) = self.file_session_lru.pop_front() {
                    self.file_sessions.remove(&oldest_key);
                }
            }
            let pool = Arc::new(SileroSessionPool::new(
                SileroModelSource::File(path.to_string()),
                size,
                stream_state_cache_size,
            ));
            self.file_sessions.insert(key.clone(), Arc::clone(&pool));
            self.file_session_lru.push_back(key);
            return Ok(pool);
        }
        if self.bundled.as_ref().is_none_or(|pool| {
            pool.size() != size || pool.stream_state_cache_size() != stream_state_cache_size
        }) {
            self.bundled = Some(Arc::new(SileroSessionPool::new(
                SileroModelSource::Bundled,
                size,
                stream_state_cache_size,
            )));
        }
        self.bundled
            .as_ref()
            .map(Arc::clone)
            .ok_or_else(|| "silero_bundled_session_pool_missing".to_string())
    }

    fn touch_file_session_key(&mut self, key: &str) {
        self.file_session_lru.retain(|candidate| candidate != key);
        self.file_session_lru.push_back(key.to_string());
    }
}

fn silero_file_session_key(path: &str, pool_size: usize, stream_cache_size: usize) -> String {
    let normalized = Path::new(path)
        .canonicalize()
        .ok()
        .map(|path| path.to_string_lossy().into_owned())
        .unwrap_or_else(|| path.to_string());
    format!("pool={pool_size};stream_cache={stream_cache_size};path={normalized}")
}

fn stream_state_key(stream_key: &str, sample_rate: SampleRate) -> String {
    format!("sr={};stream={}", sample_rate.hz(), stream_key)
}

fn normalize_stream_key(stream_key: Option<&str>) -> Option<&str> {
    stream_key.map(str::trim).filter(|key| !key.is_empty())
}

fn session_slot_index(stream_key: Option<&str>, slot_count: usize) -> usize {
    if slot_count <= 1 {
        return 0;
    }
    let Some(stream_key) = stream_key else {
        return SILERO_ONE_SHOT_SLOT_COUNTER.fetch_add(1, Ordering::Relaxed) % slot_count;
    };
    let mut hasher = DefaultHasher::new();
    stream_key.hash(&mut hasher);
    (hasher.finish() as usize) % slot_count
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::BTreeSet;

    #[test]
    fn bundled_session_cache_reuses_slot_for_same_stream_key() {
        let pool = SileroSessionPool::new(SileroModelSource::Bundled, 4, 512);
        let samples = vec![0_i16; SampleRate::Rate16k.chunk_samples()];
        let audio = samples
            .iter()
            .map(|sample| f32::from(*sample) / 32768.0)
            .collect::<Vec<f32>>();

        let first = pool
            .process(SampleRate::Rate16k, &audio, Some("session-a"))
            .expect("first infer");
        assert_eq!(first.len(), 1);
        let stream_count_after_first = pool.slots[session_slot_index(Some("session-a"), 4)]
            .lock()
            .expect("slot")
            .streams
            .len();

        let second = pool
            .process(SampleRate::Rate16k, &audio, Some("session-a"))
            .expect("second infer");
        assert_eq!(second.len(), 1);
        let stream_count_after_second = pool.slots[session_slot_index(Some("session-a"), 4)]
            .lock()
            .expect("slot")
            .streams
            .len();

        assert_eq!(stream_count_after_first, 1);
        assert_eq!(stream_count_after_second, 1);
    }

    #[test]
    fn custom_file_session_pools_are_bounded_lru_without_loading() {
        let mut cache = SileroSessionCache::default();
        for index in 0..(MAX_SILERO_FILE_SESSION_POOLS + 2) {
            let config = VoiceEdgeConfig {
                vad_backend: VadBackend::SileroOnnx,
                vad_model_path: Some(format!("/tmp/silero-{index}.onnx")),
                vad_session_pool_size: 2,
                ..VoiceEdgeConfig::default()
            };
            cache.pool(&config).expect("pool create");
        }

        assert_eq!(cache.file_sessions.len(), MAX_SILERO_FILE_SESSION_POOLS);
    }

    #[test]
    fn custom_file_session_pool_access_refreshes_lru() {
        let mut cache = SileroSessionCache::default();
        let hot_path = "/tmp/silero-hot.onnx";
        let hot_config = VoiceEdgeConfig {
            vad_backend: VadBackend::SileroOnnx,
            vad_model_path: Some(hot_path.to_string()),
            vad_session_pool_size: 2,
            ..VoiceEdgeConfig::default()
        };
        cache.pool(&hot_config).expect("hot pool create");
        for index in 0..MAX_SILERO_FILE_SESSION_POOLS {
            let config = VoiceEdgeConfig {
                vad_backend: VadBackend::SileroOnnx,
                vad_model_path: Some(format!("/tmp/silero-lru-{index}.onnx")),
                vad_session_pool_size: 2,
                ..VoiceEdgeConfig::default()
            };
            cache.pool(&config).expect("pool create");
        }
        cache.pool(&hot_config).expect("hot pool touch");
        let overflow_config = VoiceEdgeConfig {
            vad_backend: VadBackend::SileroOnnx,
            vad_model_path: Some("/tmp/silero-overflow.onnx".to_string()),
            vad_session_pool_size: 2,
            ..VoiceEdgeConfig::default()
        };
        cache.pool(&overflow_config).expect("overflow pool create");

        assert_eq!(cache.file_sessions.len(), MAX_SILERO_FILE_SESSION_POOLS);
        assert!(cache
            .file_sessions
            .contains_key(&silero_file_session_key(hot_path, 2, 512)));
    }

    #[test]
    fn bundled_pool_rebuilds_when_requested_size_changes() {
        let mut cache = SileroSessionCache::default();
        let small_config = VoiceEdgeConfig {
            vad_backend: VadBackend::SileroOnnx,
            vad_session_pool_size: 1,
            ..VoiceEdgeConfig::default()
        };
        let large_config = VoiceEdgeConfig {
            vad_backend: VadBackend::SileroOnnx,
            vad_session_pool_size: 3,
            ..VoiceEdgeConfig::default()
        };

        let small = cache.pool(&small_config).expect("small pool");
        let large = cache.pool(&large_config).expect("large pool");

        assert_eq!(small.size(), 1);
        assert_eq!(large.size(), 3);
    }

    #[test]
    fn bundled_pool_rebuilds_when_stream_state_cache_size_changes() {
        let mut cache = SileroSessionCache::default();
        let small_config = VoiceEdgeConfig {
            vad_backend: VadBackend::SileroOnnx,
            vad_stream_state_cache_size: 2,
            ..VoiceEdgeConfig::default()
        };
        let large_config = VoiceEdgeConfig {
            vad_backend: VadBackend::SileroOnnx,
            vad_stream_state_cache_size: 5,
            ..VoiceEdgeConfig::default()
        };

        let small = cache.pool(&small_config).expect("small stream cache pool");
        let large = cache.pool(&large_config).expect("large stream cache pool");

        assert_eq!(small.stream_state_cache_size(), 2);
        assert_eq!(large.stream_state_cache_size(), 5);
    }

    #[test]
    fn slot_preserves_stream_state_pending_across_calls() {
        let pool = SileroSessionPool::new(SileroModelSource::Bundled, 1, 4);
        let half_chunk = vec![0.0_f32; SampleRate::Rate16k.chunk_samples() / 2];

        let first = pool
            .process(SampleRate::Rate16k, &half_chunk, Some("stream-a"))
            .expect("first partial");
        let second = pool
            .process(SampleRate::Rate16k, &half_chunk, Some("stream-a"))
            .expect("second partial");

        assert!(first.is_empty());
        assert_eq!(second.len(), 1);
    }

    #[test]
    fn missing_or_empty_stream_key_uses_one_shot_state_without_cache_collision() {
        let pool = SileroSessionPool::new(SileroModelSource::Bundled, 1, 4);
        let half_chunk = vec![0.0_f32; SampleRate::Rate16k.chunk_samples() / 2];

        for stream_key in [None, Some(""), Some("   ")] {
            let first = pool
                .process(SampleRate::Rate16k, &half_chunk, stream_key)
                .expect("first one-shot partial");
            let second = pool
                .process(SampleRate::Rate16k, &half_chunk, stream_key)
                .expect("second one-shot partial");

            assert!(first.is_empty());
            assert!(second.is_empty());
        }
        let cached_streams = pool.slots[0].lock().expect("slot").streams.len();

        assert_eq!(cached_streams, 0);
    }

    #[test]
    fn one_shot_streams_are_spread_across_pool_slots() {
        let seen_slots = (0..(MAX_SILERO_POOL_SIZE * 2))
            .map(|_| session_slot_index(None, MAX_SILERO_POOL_SIZE))
            .collect::<BTreeSet<usize>>();

        assert!(seen_slots.len() > 1);
    }

    #[test]
    fn stream_states_are_bounded_lru_per_slot() {
        let mut slot = SileroSessionSlot::default();
        slot.ensure_stream_state("stream-hot", SampleRate::Rate16k, 2);
        slot.ensure_stream_state("stream-cold", SampleRate::Rate16k, 2);
        slot.ensure_stream_state("stream-hot", SampleRate::Rate16k, 2);
        slot.ensure_stream_state("stream-new", SampleRate::Rate16k, 2);

        assert!(slot.streams.contains_key("stream-hot"));
        assert!(slot.streams.contains_key("stream-new"));
        assert!(!slot.streams.contains_key("stream-cold"));
    }
}

fn deterministic_energy_gate(samples: &[i16], config: &VoiceEdgeConfig) -> VadDecision {
    if samples.is_empty() {
        return VadDecision {
            is_speech: false,
            rms: 0.0,
            speech_probability: 0.0,
        };
    }

    let mean_square = samples
        .iter()
        .map(|sample| {
            let normalized = f64::from(*sample) / 32768.0;
            normalized * normalized
        })
        .sum::<f64>()
        / samples.len() as f64;
    let rms = mean_square.sqrt();
    let speech_probability = (rms / config.vad_threshold).clamp(0.0, 1.0);

    VadDecision {
        is_speech: rms >= config.vad_threshold,
        rms,
        speech_probability,
    }
}
