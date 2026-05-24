import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { Mic, PauseCircle, Send, Sparkles, Type, Wand2 } from "lucide-react";
import clsx from "clsx";

export type ComposerSubmit = {
  transcript: string;
  modality: "text" | "voice";
  topic: string;
  targetFormats: string[];
};

type SpeechRecognitionLike = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start: () => void;
  stop: () => void;
  abort: () => void;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: (() => void) | null;
  onend: (() => void) | null;
};

type SpeechRecognitionEventLike = {
  resultIndex: number;
  results: {
    length: number;
    [index: number]: {
      isFinal: boolean;
      [index: number]: { transcript: string };
    };
  };
};

type SpeechWindow = Window & {
  SpeechRecognition?: new () => SpeechRecognitionLike;
  webkitSpeechRecognition?: new () => SpeechRecognitionLike;
};

const FORMAT_OPTIONS = [
  { id: "post", label: "Post" },
  { id: "reel", label: "Reel" },
  { id: "substack", label: "Substack" }
];

const PROMPT_SEEDS = [
  {
    label: "Current explainer",
    topic: "AI agents that turn research into social content",
    transcript:
      "Create a source-backed explanation for a non-technical audience. Make the short-form version ELI5 and make the long-form version detailed but still easy to follow."
  },
  {
    label: "Myth breaker",
    topic: "Misconceptions about autonomous agents",
    transcript:
      "Find real sources and turn them into a myth-versus-reality post, a tight reel script, and a Substack section with simple examples."
  },
  {
    label: "Founder angle",
    topic: "Practical AI workflows for busy teams",
    transcript:
      "Explain the workflow like I am five, but include concrete implementation details and audience hooks for founders and builders."
  }
];

type ComposerProps = {
  busy: boolean;
  onSubmit: (input: ComposerSubmit) => Promise<void>;
};

export function Composer({ busy, onSubmit }: ComposerProps) {
  const [modality, setModality] = useState<"text" | "voice">("text");
  const [transcript, setTranscript] = useState("");
  const [topic, setTopic] = useState("");
  const [targetFormats, setTargetFormats] = useState(["post", "reel", "substack"]);
  const [listening, setListening] = useState(false);
  const [voiceSupported, setVoiceSupported] = useState(false);
  const [voiceError, setVoiceError] = useState("");
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const finalTranscriptRef = useRef("");

  const charCount = transcript.trim().length;
  const canSubmit = charCount > 0 && targetFormats.length > 0 && !busy;
  const submitLabel = useMemo(() => {
    if (busy) {
      return "Working";
    }
    return modality === "voice" ? "Send dictated turn" : "Generate";
  }, [busy, modality]);

  useEffect(() => {
    const speechWindow = window as SpeechWindow;
    setVoiceSupported(Boolean(speechWindow.SpeechRecognition || speechWindow.webkitSpeechRecognition));
    return () => recognitionRef.current?.abort();
  }, []);

  function toggleFormat(format: string) {
    setTargetFormats((current) =>
      current.includes(format)
        ? current.filter((item) => item !== format)
        : [...current, format]
    );
  }

  function applySeed(seed: (typeof PROMPT_SEEDS)[number]) {
    setTopic(seed.topic);
    setTranscript(seed.transcript);
    setModality("text");
  }

  function toggleVoiceCapture() {
    if (listening) {
      recognitionRef.current?.stop();
      setListening(false);
      return;
    }

    const speechWindow = window as SpeechWindow;
    const Recognition = speechWindow.SpeechRecognition ?? speechWindow.webkitSpeechRecognition;
    if (!Recognition) {
      setModality("voice");
      setVoiceError("Browser speech capture is unavailable here. Paste a transcript or spoken note.");
      return;
    }

    const recognition = new Recognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-US";
    finalTranscriptRef.current = transcript.trim() ? `${transcript.trim()} ` : "";
    recognition.onresult = (event) => {
      let interim = "";
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const result = event.results[index];
        const text = result[0].transcript;
        if (result.isFinal) {
          finalTranscriptRef.current += `${text.trim()} `;
        } else {
          interim += text;
        }
      }
      setTranscript(`${finalTranscriptRef.current}${interim}`.trim());
    };
    recognition.onerror = () => {
      setVoiceError("Voice capture stopped. You can keep typing or try capture again.");
      setListening(false);
    };
    recognition.onend = () => setListening(false);
    recognition.start();
    recognitionRef.current = recognition;
    setModality("voice");
    setVoiceError("");
    setListening(true);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit) {
      return;
    }
    recognitionRef.current?.stop();
    setListening(false);
    await onSubmit({
      transcript: transcript.trim(),
      modality,
      topic: topic.trim(),
      targetFormats
    });
  }

  return (
    <form className="composer" onSubmit={handleSubmit}>
      <div className="composer-topline">
        <div>
          <p className="eyebrow">Creator Input</p>
          <h2>Tell the agents what to make</h2>
        </div>
        <span className={clsx("live-dot", listening && "active")} aria-live="polite">
          {listening ? "Listening" : "Ready"}
        </span>
      </div>

      <div className="composer-toolbar">
        <div className="segmented" aria-label="Input mode">
          <button
            className={clsx(modality === "text" && "active")}
            type="button"
            onClick={() => setModality("text")}
            aria-pressed={modality === "text"}
          >
            <Type size={16} aria-hidden="true" />
            Text
          </button>
          <button
            className={clsx(modality === "voice" && "active")}
            type="button"
            onClick={() => setModality("voice")}
            aria-pressed={modality === "voice"}
          >
            <Mic size={16} aria-hidden="true" />
            Dictate
          </button>
        </div>
        <input
          className="topic-input"
          value={topic}
          onChange={(event) => setTopic(event.target.value)}
          placeholder="Topic or angle"
          aria-label="Topic or angle"
        />
      </div>

      <div className="prompt-seeds" aria-label="Prompt starters">
        {PROMPT_SEEDS.map((seed) => (
          <button key={seed.label} type="button" onClick={() => applySeed(seed)}>
            <Sparkles size={14} aria-hidden="true" />
            {seed.label}
          </button>
        ))}
      </div>

      <div className="voice-strip">
        <button
          className={clsx("voice-button", listening && "recording")}
          type="button"
          onClick={toggleVoiceCapture}
          disabled={!voiceSupported && listening}
        >
          {listening ? <PauseCircle size={18} aria-hidden="true" /> : <Mic size={18} aria-hidden="true" />}
          {listening ? "Stop capture" : voiceSupported ? "Capture voice" : "Voice transcript"}
        </button>
        <span>
          {voiceSupported
            ? "Browser dictation only creates an editable transcript. Use Live Voice below for provider-backed speech-to-speech."
            : "Paste a transcript or spoken note. This control is not a provider-backed realtime audio session."}
        </span>
      </div>
      {voiceError && (
        <p className="voice-message" aria-live="polite">
          {voiceError}
        </p>
      )}

      <textarea
        value={transcript}
        onChange={(event) => setTranscript(event.target.value)}
        placeholder={
          modality === "voice"
            ? "Dictate, paste, or edit a transcript. For live back-and-forth speech, start Live Voice below."
            : "Describe the post, reel, or Substack piece you want generated..."
        }
        aria-label="Composer input"
      />

      <div className="composer-footer">
        <div className="format-toggles" aria-label="Target formats">
          {FORMAT_OPTIONS.map((format) => (
            <label key={format.id} className={clsx(targetFormats.includes(format.id) && "checked")}>
              <input
                type="checkbox"
                checked={targetFormats.includes(format.id)}
                onChange={() => toggleFormat(format.id)}
              />
              <span>{format.label}</span>
            </label>
          ))}
        </div>
        <div className="submit-cluster">
          <span>{charCount} chars</span>
          <button className="primary-button" disabled={!canSubmit} type="submit">
            {modality === "voice" ? <Mic size={18} aria-hidden="true" /> : <Wand2 size={18} aria-hidden="true" />}
            {submitLabel}
            <Send size={16} aria-hidden="true" />
          </button>
        </div>
      </div>
    </form>
  );
}
