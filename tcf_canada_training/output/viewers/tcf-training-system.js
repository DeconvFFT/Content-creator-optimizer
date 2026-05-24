(() => {
  "use strict";

  const STORE_KEY = "tcfCanadaTrainingState.v1";

  const DATA = {
    tracks: {
      A2: {
        label: "A2 or below",
        startWeek: 1,
        lengthWeeks: 24,
        load: "18-22 h/week",
        interpretation: "Full build through B1 and B2 before score maximization."
      },
      B1: {
        label: "B1 range",
        startWeek: 5,
        lengthWeeks: 20,
        load: "16-18 h/week",
        interpretation: "Compress foundations but keep heavy B2-building work."
      },
      LOW_B2: {
        label: "Low B2 / unstable NCLC 7",
        startWeek: 9,
        lengthWeeks: 16,
        load: "14-16 h/week",
        interpretation: "Near threshold; needs stability across all four skills."
      },
      B2_C1: {
        label: "Stable B2 or low C1",
        startWeek: 13,
        lengthWeeks: 12,
        load: "12-15 h/week",
        interpretation: "Mostly timing, precision, mocks, and weak-skill repair."
      }
    },
    weeklyBlocks: [
      ["1-4", "Core systems", "Sound system, articles, gender, present tense, questions, numbers, basic messages."],
      ["5-8", "B1 transaction and narration", "Past narration, comparisons, pronouns, service interactions, complaints."],
      ["9-12", "Bridge to B2", "Register shifts, conditionnel, y/en, subjonctive triggers, first Task 3 comparisons."],
      ["13-16", "B2 consolidation", "Passive/impersonal structures, discourse markers, paraphrase, full threshold check."],
      ["17-20", "C1 safety buffer", "Precision, complex connectors, formal style, stamina, booking decision point."],
      ["21-24", "Mocks and taper", "Weak-skill bootcamp, strict dress rehearsals, final checklist, go/no-go decision."]
    ],
    dailyPlans: [
      {
        day: "Sunday",
        focus: "Review and reset",
        blocks: ["Review dashboard", "Rebuild flashcards", "Light immersion", "30 min weak-skill repair"]
      },
      {
        day: "Monday",
        focus: "Listening and systems",
        blocks: ["45 min one-pass listening", "45 min grammar", "30 min vocabulary/SRS", "20 min pronunciation"]
      },
      {
        day: "Tuesday",
        focus: "Reading and writing",
        blocks: ["60 min reading", "45 min grammar/vocab consolidation", "45 min Writing Task 1 or 2"]
      },
      {
        day: "Wednesday",
        focus: "Speaking day",
        blocks: ["45 min listening", "30 min solo speaking", "45 min live or recorded speaking", "20 min error log"]
      },
      {
        day: "Thursday",
        focus: "Reading and reformulation",
        blocks: ["60 min reading", "60 min Writing Task 2 or 3", "20 min reformulation drill"]
      },
      {
        day: "Friday",
        focus: "Mixed production",
        blocks: ["45 min listening", "45 min Speaking Task 2 or 3", "30 min grammar repair", "20 min pronunciation"]
      },
      {
        day: "Saturday",
        focus: "Timed block",
        blocks: ["Mini-mock or full block", "Review mistakes", "Update remediation map"]
      }
    ],
    mockMilestones: [
      [1, "Diagnostic baseline", "Ev@lang plus shortened TCF-style sample."],
      [4, "Mini-mock A", "Early timing and word-count control."],
      [8, "Full Mock 1", "First estimated NCLC forecast."],
      [12, "Full Mock 2", "Progress delta and serious gap analysis."],
      [16, "Full Mock 3", "All four skills should approach estimated NCLC 7."],
      [20, "Full Mock 4", "Real-test booking decision point."],
      [22, "Full Mock 5", "Stability check, not peak-score luck."],
      [24, "Final dress rehearsal", "Final readiness decision."]
    ],
    listeningItems: [
      {
        id: "L01",
        band: "A2",
        topic: "transport",
        trap: "number_confusion",
        title: "Train departure",
        script: "Bonjour. Le train pour Ottawa partira aujourd'hui à quinze heures dix, voie numéro quatre. Les passagers doivent arriver au moins vingt minutes avant le départ.",
        question: "À quelle heure part le train pour Ottawa ?",
        options: ["14 h 10", "15 h 10", "15 h 20", "16 h 10"],
        answer: 1,
        rationale: "The announcement says quinze heures dix, not quatorze heures dix or quinze heures vingt.",
        remediation: "numbers_time_drill"
      },
      {
        id: "L02",
        band: "B1",
        topic: "housing",
        trap: "detail_miss",
        title: "Apartment visit",
        script: "Bonjour, je vous appelle pour l'appartement rue Bernard. Il est disponible à partir du premier juin. Le loyer est de mille deux cents dollars, chauffage compris, mais l'électricité n'est pas incluse.",
        question: "Qu'est-ce qui est inclus dans le loyer ?",
        options: ["L'électricité", "Le chauffage", "Internet", "Le stationnement"],
        answer: 1,
        rationale: "The speaker says chauffage compris but electricity is not included.",
        remediation: "housing_ads_set"
      },
      {
        id: "L03",
        band: "B1",
        topic: "health",
        trap: "date_miss",
        title: "Medical appointment",
        script: "Votre rendez-vous avec le docteur Martin est confirmé pour jeudi matin à neuf heures trente. Si vous avez de la fièvre, appelez la clinique avant de venir.",
        question: "Quand est le rendez-vous ?",
        options: ["Jeudi à 9 h 30", "Jeudi à 19 h 30", "Mardi à 9 h 30", "Vendredi à 9 h"],
        answer: 0,
        rationale: "The appointment is Thursday morning at 9:30.",
        remediation: "dates_appointments"
      },
      {
        id: "L04",
        band: "B2",
        topic: "work",
        trap: "inference_miss",
        title: "Schedule change",
        script: "Comme la réunion avec le client est avancée à mardi, l'équipe devra envoyer le rapport lundi soir au plus tard. Ceux qui travaillent à distance doivent rester joignables toute la matinée.",
        question: "Pourquoi faut-il envoyer le rapport lundi soir ?",
        options: ["Le client a annulé la réunion", "La réunion aura lieu plus tôt que prévu", "L'équipe part en congé", "Le rapport doit être traduit"],
        answer: 1,
        rationale: "The meeting has been moved earlier to Tuesday, so the report is needed Monday evening.",
        remediation: "work_inference"
      },
      {
        id: "L05",
        band: "B2",
        topic: "consumer",
        trap: "negation_miss",
        title: "Phone bill",
        script: "Je ne conteste pas le prix de l'abonnement mensuel. En revanche, je ne comprends pas les frais supplémentaires de cinquante dollars pour des données que je n'ai jamais utilisées.",
        question: "Que conteste la personne ?",
        options: ["Le prix de l'abonnement", "Les frais de données supplémentaires", "La durée du contrat", "La qualité du téléphone"],
        answer: 1,
        rationale: "The speaker explicitly does not dispute the monthly subscription, but disputes extra data charges.",
        remediation: "negation_contrast"
      },
      {
        id: "L06",
        band: "B2",
        topic: "education_family",
        trap: "register_miss",
        title: "Daycare inquiry",
        script: "Pour inscrire votre enfant, il faut remplir le formulaire en ligne, fournir une preuve de résidence et participer à une courte rencontre avec la directrice. Les places à temps plein sont limitées.",
        question: "Quelle démarche est nécessaire ?",
        options: ["Envoyer uniquement un courriel", "Participer à une rencontre", "Payer immédiatement l'année complète", "Présenter un permis de conduire étranger"],
        answer: 1,
        rationale: "The speaker says a short meeting with the director is required.",
        remediation: "admin_steps"
      },
      {
        id: "L07",
        band: "C1",
        topic: "civic_life",
        trap: "stance_miss",
        title: "Community volunteering",
        script: "À mon avis, le bénévolat ne devrait pas être obligatoire. Cela dit, les municipalités pourraient mieux informer les nouveaux arrivants, car beaucoup aimeraient participer mais ne savent pas par où commencer.",
        question: "Quelle est la position de la personne ?",
        options: ["Rendre le bénévolat obligatoire", "Remplacer les services municipaux par des bénévoles", "Mieux informer sans imposer", "Limiter le bénévolat aux étudiants"],
        answer: 2,
        rationale: "The speaker rejects obligation but supports better municipal information.",
        remediation: "stance_markers"
      },
      {
        id: "L08",
        band: "C1",
        topic: "technology",
        trap: "counterpoint_miss",
        title: "Remote work nuance",
        script: "Le télétravail a clairement réduit les temps de déplacement. Pourtant, plusieurs employés disent qu'ils perdent les échanges spontanés qui les aidaient à résoudre rapidement les problèmes.",
        question: "Quel problème est mentionné ?",
        options: ["Des trajets plus longs", "Moins d'échanges spontanés", "Une baisse automatique du salaire", "L'impossibilité de travailler chez soi"],
        answer: 1,
        rationale: "The contrast marker pourtant introduces the drawback: fewer spontaneous exchanges.",
        remediation: "contrast_markers"
      }
    ],
    readingItems: [
      {
        id: "R01",
        band: "A2",
        topic: "admin",
        trap: "detail_miss",
        title: "Library card",
        passage: "Pour obtenir une carte de bibliothèque, présentez une pièce d'identité et une preuve d'adresse récente. L'inscription est gratuite pour les résidents de la ville. La carte est prête immédiatement.",
        question: "Qui peut s'inscrire gratuitement ?",
        options: ["Tous les visiteurs", "Les résidents de la ville", "Les étudiants seulement", "Les personnes âgées seulement"],
        answer: 1,
        rationale: "The notice says registration is free for city residents.",
        remediation: "admin_documents"
      },
      {
        id: "R02",
        band: "B1",
        topic: "housing",
        trap: "vocabulary_miss",
        title: "Apartment ad",
        passage: "Appartement non meublé, lumineux, près du métro. Loyer: 1 450 dollars par mois. Charges non comprises. Animaux acceptés après accord écrit du propriétaire.",
        question: "Que signifie l'annonce au sujet des charges ?",
        options: ["Elles sont incluses", "Elles ne sont pas incluses", "Elles sont interdites", "Elles remplacent le loyer"],
        answer: 1,
        rationale: "Non comprises means not included.",
        remediation: "housing_vocabulary"
      },
      {
        id: "R03",
        band: "B1",
        topic: "work",
        trap: "purpose_miss",
        title: "Internal note",
        passage: "Afin de mieux accueillir les nouveaux employés, le service des ressources humaines organise une séance d'information vendredi à 10 h. Les responsables d'équipe doivent confirmer le nombre de participants avant mercredi midi.",
        question: "Pourquoi la séance est-elle organisée ?",
        options: ["Pour accueillir les nouveaux employés", "Pour modifier les salaires", "Pour fermer le bureau vendredi", "Pour choisir les responsables d'équipe"],
        answer: 0,
        rationale: "The purpose is to welcome new employees better.",
        remediation: "purpose_markers"
      },
      {
        id: "R04",
        band: "B2",
        topic: "consumer",
        trap: "condition_miss",
        title: "Refund policy",
        passage: "Les remboursements sont possibles dans les trente jours suivant l'achat, à condition que le produit soit inutilisé et accompagné du reçu original. Les articles soldés ne sont ni repris ni échangés.",
        question: "Quel article peut être remboursé ?",
        options: ["Un article soldé sans reçu", "Un produit utilisé avec reçu", "Un produit inutilisé avec reçu dans les trente jours", "Tout achat après deux mois"],
        answer: 2,
        rationale: "The policy requires unused product, original receipt, and within thirty days.",
        remediation: "conditions_exceptions"
      },
      {
        id: "R05",
        band: "B2",
        topic: "health",
        trap: "inference_miss",
        title: "Healthy eating opinion",
        passage: "Certaines personnes affirment que manger sainement coûte trop cher. Pourtant, plusieurs nutritionnistes rappellent que les légumes secs, les oeufs et les produits de saison restent abordables si l'on planifie ses repas.",
        question: "Quelle idée nuance l'opinion initiale ?",
        options: ["Tous les aliments sains sont chers", "La planification peut rendre une alimentation saine abordable", "Les nutritionnistes déconseillent les produits de saison", "Les repas faits maison sont impossibles"],
        answer: 1,
        rationale: "The second sentence qualifies the cost argument by naming affordable options and planning.",
        remediation: "opinion_nuance"
      },
      {
        id: "R06",
        band: "B2",
        topic: "transport",
        trap: "cause_consequence",
        title: "Transit delay",
        passage: "En raison de travaux sur la ligne verte, les trains circuleront toutes les quinze minutes ce week-end. Les usagers sont invités à prévoir un temps de trajet plus long ou à utiliser les lignes d'autobus temporaires.",
        question: "Quelle conséquence les usagers doivent-ils prévoir ?",
        options: ["Un trajet potentiellement plus long", "La fermeture définitive de la ligne", "Des trains toutes les cinq minutes", "La suppression des autobus"],
        answer: 0,
        rationale: "The notice asks users to plan for longer travel time.",
        remediation: "cause_consequence"
      },
      {
        id: "R07",
        band: "C1",
        topic: "technology",
        trap: "stance_miss",
        title: "Digital literacy",
        passage: "Introduire l'éducation aux médias dès le collège ne signifie pas transformer chaque cours en leçon d'informatique. Il s'agit plutôt d'apprendre aux élèves à identifier une source fiable, à distinguer opinion et information, et à comprendre les effets des algorithmes.",
        question: "Que défend le texte ?",
        options: ["Remplacer les cours par l'informatique", "Interdire les algorithmes", "Former les élèves à l'esprit critique numérique", "Supprimer les opinions des médias"],
        answer: 2,
        rationale: "The text supports media literacy and source evaluation, not replacing all courses.",
        remediation: "abstract_argument"
      },
      {
        id: "R08",
        band: "C1",
        topic: "civic_life",
        trap: "comparison_miss",
        title: "Urban mobility",
        passage: "Limiter les voitures au centre-ville peut sembler contraignant pour certains commerces. Cependant, les villes qui ont développé des zones piétonnes observent souvent une hausse de la fréquentation, car les clients restent plus longtemps dans des espaces plus agréables.",
        question: "Quel argument soutient les zones piétonnes ?",
        options: ["Elles rendent tous les commerces moins accessibles", "Elles peuvent augmenter la fréquentation", "Elles suppriment les transports publics", "Elles obligent les clients à partir plus vite"],
        answer: 1,
        rationale: "The text contrasts perceived constraint with increased foot traffic.",
        remediation: "counterargument"
      }
    ],
    writingPrompts: [
      {
        id: "W1A",
        task: "Task 1",
        title: "Lost baggage message",
        limit: [60, 120],
        timeMinutes: 18,
        prompt: "Vous avez perdu votre valise pendant un voyage. Écrivez un message au service des bagages. Décrivez la valise, expliquez la situation et demandez ce que vous devez faire."
      },
      {
        id: "W1B",
        task: "Task 1",
        title: "Schedule change",
        limit: [60, 120],
        timeMinutes: 18,
        prompt: "Vous ne pouvez pas assister à une réunion prévue demain. Écrivez un message à votre responsable. Expliquez la raison, proposez une solution et présentez vos excuses."
      },
      {
        id: "W2A",
        task: "Task 2",
        title: "Advice to a friend",
        limit: [120, 150],
        timeMinutes: 20,
        prompt: "Un ami va déménager dans une nouvelle ville. Écrivez-lui un courriel pour raconter votre propre expérience de déménagement et lui donner des conseils pratiques."
      },
      {
        id: "W2B",
        task: "Task 2",
        title: "Complaint about a bill",
        limit: [120, 150],
        timeMinutes: 20,
        prompt: "Vous avez reçu une facture incorrecte. Écrivez au service client pour expliquer le problème, raconter vos démarches précédentes et demander une correction."
      },
      {
        id: "W3A",
        task: "Task 3",
        title: "Remote work",
        limit: [120, 180],
        timeMinutes: 22,
        prompt: "Document 1: Le télétravail améliore la qualité de vie car il réduit les déplacements. Document 2: Le télétravail isole les employés et rend la collaboration plus difficile. Comparez les deux points de vue et donnez votre opinion."
      },
      {
        id: "W3B",
        task: "Task 3",
        title: "Healthy eating",
        limit: [120, 180],
        timeMinutes: 22,
        prompt: "Document 1: Les écoles devraient enseigner la nutrition pour prévenir les problèmes de santé. Document 2: L'alimentation relève surtout de la responsabilité des familles. Comparez les deux points de vue et donnez votre opinion."
      }
    ],
    speakingPrompts: [
      {
        id: "S1A",
        task: "Task 1",
        title: "Self-presentation",
        prepSeconds: 0,
        responseSeconds: 120,
        prompt: "Présentez-vous à l'examinateur. Parlez de votre travail ou de vos études, de vos habitudes quotidiennes, de vos objectifs et d'un projet important pour vous."
      },
      {
        id: "S1B",
        task: "Task 1",
        title: "Professional background",
        prepSeconds: 0,
        responseSeconds: 120,
        prompt: "Répondez aux questions de l'examinateur sur votre parcours professionnel, vos compétences, votre emploi actuel et vos projets pour les prochaines années."
      },
      {
        id: "S2A",
        task: "Task 2",
        title: "Rent an apartment",
        prepSeconds: 120,
        responseSeconds: 330,
        prompt: "Vous cherchez un appartement. Appelez une agence immobilière. Demandez le prix, la taille, les charges, les transports, les documents nécessaires et les possibilités de visite."
      },
      {
        id: "S2B",
        task: "Task 2",
        title: "Open a bank account",
        prepSeconds: 120,
        responseSeconds: 330,
        prompt: "Vous voulez ouvrir un compte bancaire. Posez des questions sur les frais, la carte, les virements, les documents demandés et les services en ligne."
      },
      {
        id: "S3A",
        task: "Task 3",
        title: "Remote work opinion",
        prepSeconds: 0,
        responseSeconds: 270,
        prompt: "Selon vous, le télétravail est-il une bonne solution pour la majorité des employés ? Présentez votre opinion avec des avantages, des limites et une conclusion claire."
      },
      {
        id: "S3B",
        task: "Task 3",
        title: "Public transport opinion",
        prepSeconds: 0,
        responseSeconds: 270,
        prompt: "Les villes devraient-elles rendre les transports publics moins chers que la voiture ? Donnez votre avis avec des exemples et une réponse à un argument opposé."
      }
    ],
    remediation: {
      numbers_time_drill: "10 minutes daily: numbers, dates, prices, train times, appointment times.",
      housing_ads_set: "Read housing ads and mark loyer, charges, caution, meublé, disponible, quartier.",
      dates_appointments: "Drill days, times, and appointment phrases with one-pass dictation.",
      work_inference: "Underline cause, deadline, and consequence in workplace messages.",
      negation_contrast: "Drill ne...pas, ne...jamais, en revanche, pourtant, cependant.",
      admin_steps: "Build a checklist from documents and required actions in notices.",
      stance_markers: "Identify à mon avis, cela dit, pourtant, en revanche, il me semble que.",
      contrast_markers: "Practice two-sentence summaries with advantage plus drawback.",
      admin_documents: "Create an admin vocabulary deck: justificatif, formulaire, attestation, pièce d'identité.",
      housing_vocabulary: "Contrast inclus/compris, non compris, meublé/non meublé, charges/caution.",
      purpose_markers: "Scan for afin de, pour, dans le but de, permettre de.",
      conditions_exceptions: "Mark à condition que, sauf, uniquement, ne...ni...ni.",
      opinion_nuance: "Find the initial claim, the nuance marker, and the author's final position.",
      cause_consequence: "Map cause to consequence with en raison de, donc, par conséquent.",
      abstract_argument: "Summarize abstract claims as claim, reason, example.",
      counterargument: "Write both sides before selecting the author's stronger argument."
    }
  };

  const PRODUCTION_CRITERIA = {
    writing: [
      "Task completion, register, word count",
      "Coherence and cohesion",
      "Vocabulary range and precision",
      "Grammar and orthography",
      "Comparison / argument / reformulation"
    ],
    speaking: [
      "Task completion and interaction management",
      "Discourse organization and argument structure",
      "Vocabulary range and precision",
      "Grammar control",
      "Pronunciation, fluency, sociolinguistic fit"
    ]
  };

  const app = {
    tab: "dashboard",
    listeningIndex: 0,
    listeningPlayed: false,
    listeningAnswer: null,
    readingIndex: 0,
    readingAnswer: null,
    timer: null,
    timerDisplayId: null,
    mediaRecorder: null,
    audioChunks: [],
    currentAudioUrl: null
  };

  const state = loadState();

  function defaultState() {
    const firstWriting = DATA.writingPrompts[0].id;
    const firstSpeaking = DATA.speakingPrompts[0].id;
    return {
      profile: {
        name: "",
        startDate: todayIso(),
        baseline: "LOW_B2",
        target: "NCLC 9 buffer",
        examDate: ""
      },
      daily: {},
      selectedWritingId: firstWriting,
      selectedSpeakingId: firstSpeaking,
      writingDrafts: {},
      writingRubric: blankRubric("writing"),
      speakingRubric: blankRubric("speaking"),
      writingAttempts: [],
      speakingAttempts: [],
      listeningAttempts: [],
      readingAttempts: [],
      mocks: []
    };
  }

  function blankRubric(kind) {
    return Object.fromEntries(PRODUCTION_CRITERIA[kind].map((criterion) => [criterion, 0]));
  }

  function loadState() {
    try {
      const raw = localStorage.getItem(STORE_KEY);
      if (!raw) return defaultState();
      const parsed = JSON.parse(raw);
      return { ...defaultState(), ...parsed };
    } catch {
      return defaultState();
    }
  }

  function saveState() {
    localStorage.setItem(STORE_KEY, JSON.stringify(state));
    renderStatus();
  }

  function todayIso() {
    return new Date().toISOString().slice(0, 10);
  }

  function h(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function activeTrack() {
    return DATA.tracks[state.profile.baseline] || DATA.tracks.LOW_B2;
  }

  function currentWeek() {
    const track = activeTrack();
    const start = new Date(`${state.profile.startDate || todayIso()}T00:00:00`);
    const now = new Date(`${todayIso()}T00:00:00`);
    const elapsedWeeks = Math.max(0, Math.floor((now - start) / (7 * 24 * 60 * 60 * 1000)));
    return Math.min(24, track.startWeek + elapsedWeeks);
  }

  function countWords(text) {
    const matches = String(text || "").trim().match(/[A-Za-zÀ-ÖØ-öø-ÿ0-9']+/g);
    return matches ? matches.length : 0;
  }

  function productionBand(score) {
    const n = Number(score);
    if (n >= 16) return "estimated NCLC 10+";
    if (n >= 14) return "estimated NCLC 9";
    if (n >= 12) return "estimated NCLC 8";
    if (n >= 10) return "estimated NCLC 7";
    if (n >= 7) return "estimated NCLC 6";
    if (n >= 6) return "estimated NCLC 5";
    if (n >= 4) return "estimated NCLC 4";
    return "below NCLC 4";
  }

  function comprehensionBand(percent) {
    const n = Number(percent);
    if (!Number.isFinite(n)) return "not set";
    if (n >= 88) return "NCLC 9+ readiness";
    if (n >= 80) return "NCLC 8 readiness";
    if (n >= 72) return "NCLC 7 readiness";
    if (n >= 62) return "borderline";
    return "below target";
  }

  function setTab(tab) {
    app.tab = tab;
    document.querySelectorAll(".tabbar button").forEach((button) => {
      button.classList.toggle("active", button.dataset.tab === tab);
    });
    document.querySelectorAll(".view").forEach((view) => {
      view.classList.toggle("active", view.id === tab);
    });
    renderCurrentView();
  }

  function renderStatus() {
    const track = activeTrack();
    const week = currentWeek();
    const logs = Object.keys(state.daily).length;
    const mocks = state.mocks.length;
    document.getElementById("statusStrip").innerHTML = `
      <span class="pill green">Week ${week}</span>
      <span class="pill blue">${h(track.label)}</span>
      <span class="pill gold">${h(state.profile.target)}</span>
      <span class="pill">${logs} daily logs</span>
      <span class="pill">${mocks} mocks</span>
    `;
  }

  function renderCurrentView() {
    const renderers = {
      dashboard: renderDashboard,
      today: renderToday,
      listening: renderListening,
      reading: renderReading,
      writing: renderWriting,
      speaking: renderSpeaking,
      mocks: renderMocks,
      vault: renderVault
    };
    renderers[app.tab]();
  }

  function renderDashboard() {
    const track = activeTrack();
    const week = currentWeek();
    const lastMock = state.mocks.at(-1);
    const weakSkill = inferWeakSkill();
    document.getElementById("dashboard").innerHTML = `
      <div class="section-band">
        <div class="section-head">
          <div>
            <h2>Training Profile</h2>
            <p>Set the baseline after Ev@lang and a TCF-style diagnostic.</p>
          </div>
          <button class="primary" type="button" onclick="App.saveProfile()">Save Profile</button>
        </div>
        <div class="form-grid">
          <label>Name
            <input id="profileName" value="${h(state.profile.name)}" placeholder="Optional" />
          </label>
          <label>Start date
            <input id="profileStart" type="date" value="${h(state.profile.startDate)}" />
          </label>
          <label>Baseline
            <select id="profileBaseline">
              ${Object.entries(DATA.tracks).map(([key, item]) => `<option value="${key}" ${key === state.profile.baseline ? "selected" : ""}>${h(item.label)}</option>`).join("")}
            </select>
          </label>
          <label>Target
            <select id="profileTarget">
              ${["NCLC 7 minimum", "NCLC 8 buffer", "NCLC 9 buffer", "NCLC 10+ stretch"].map((target) => `<option ${target === state.profile.target ? "selected" : ""}>${target}</option>`).join("")}
            </select>
          </label>
        </div>
      </div>

      <div class="grid four">
        <div class="metric">
          <div class="label">Current week</div>
          <div class="value">${week}</div>
          <div class="note">Track starts at week ${track.startWeek}; ${h(track.lengthWeeks)} week calendar.</div>
        </div>
        <div class="metric">
          <div class="label">Weekly load</div>
          <div class="value">${h(track.load)}</div>
          <div class="note">${h(track.interpretation)}</div>
        </div>
        <div class="metric">
          <div class="label">Latest mock</div>
          <div class="value">${lastMock ? h(lastMock.date) : "pending"}</div>
          <div class="note">${lastMock ? h(mockSummary(lastMock)) : "Run baseline before choosing a booking window."}</div>
        </div>
        <div class="metric">
          <div class="label">Weak-skill watch</div>
          <div class="value">${h(weakSkill.label)}</div>
          <div class="note">${h(weakSkill.note)}</div>
        </div>
      </div>

      <div class="section-band">
        <div class="section-head">
          <div>
            <h3>Curriculum Blocks</h3>
            <p>The app keeps all four skills active every week.</p>
          </div>
        </div>
        <div class="table-wrap">
          <table>
            <thead><tr><th>Weeks</th><th>Block</th><th>Focus</th></tr></thead>
            <tbody>
              ${DATA.weeklyBlocks.map(([weeks, block, focus]) => `<tr><td>${weeks}</td><td>${h(block)}</td><td>${h(focus)}</td></tr>`).join("")}
            </tbody>
          </table>
        </div>
      </div>

      <div class="section-band">
        <div class="section-head">
          <div>
            <h3>Mock Milestones</h3>
            <p>Use repeated full-mock evidence. Do not book from one lucky score.</p>
          </div>
        </div>
        <div class="table-wrap">
          <table>
            <thead><tr><th>Week</th><th>Mock</th><th>Output</th></tr></thead>
            <tbody>
              ${DATA.mockMilestones.map(([w, mock, output]) => `<tr><td>${w}</td><td>${h(mock)}</td><td>${h(output)}</td></tr>`).join("")}
            </tbody>
          </table>
        </div>
      </div>

      <div class="notice">
        This app uses official format constraints, but listening and reading readiness bands are training estimates. FEI does not publish a simple raw-correct to official-score conversion.
      </div>
    `;
  }

  function saveProfile() {
    state.profile.name = document.getElementById("profileName").value.trim();
    state.profile.startDate = document.getElementById("profileStart").value || todayIso();
    state.profile.baseline = document.getElementById("profileBaseline").value;
    state.profile.target = document.getElementById("profileTarget").value;
    saveState();
    renderDashboard();
  }

  function getDailyEntry() {
    const key = todayIso();
    if (!state.daily[key]) {
      state.daily[key] = { checks: {}, minutes: "", weakSkill: "", notes: "" };
    }
    return state.daily[key];
  }

  function renderToday() {
    const plan = DATA.dailyPlans[new Date().getDay()];
    const entry = getDailyEntry();
    document.getElementById("today").innerHTML = `
      <div class="section-band">
        <div class="section-head">
          <div>
            <h2>${h(plan.day)} - ${h(plan.focus)}</h2>
            <p>${todayIso()} practice checklist.</p>
          </div>
          <button class="primary" type="button" onclick="App.saveDailyEntry()">Save Daily Log</button>
        </div>
        <div class="grid two">
          <div class="stack">
            ${plan.blocks.map((block, index) => `
              <label class="choice">
                <input type="checkbox" ${entry.checks[index] ? "checked" : ""} onchange="App.toggleDailyCheck(${index})" />
                <span>${h(block)}</span>
              </label>
            `).join("")}
          </div>
          <div class="stack">
            <label>Total minutes
              <input id="dailyMinutes" type="number" min="0" step="5" value="${h(entry.minutes)}" />
            </label>
            <label>Weakest skill today
              <select id="dailyWeakSkill">
                ${["", "Listening", "Reading", "Writing", "Speaking", "Vocabulary", "Grammar", "Pronunciation"].map((skill) => `<option ${skill === entry.weakSkill ? "selected" : ""}>${skill}</option>`).join("")}
              </select>
            </label>
            <label>Notes / error pattern
              <textarea id="dailyNotes" placeholder="What broke today? What is the next fix?">${h(entry.notes)}</textarea>
            </label>
          </div>
        </div>
      </div>
      <div class="section-band">
        <div class="section-head">
          <div>
            <h3>Fast Actions</h3>
            <p>Jump directly into the practice mode that matches today's weak skill.</p>
          </div>
        </div>
        <div class="row">
          <button type="button" onclick="App.setTab('listening')">Listening drill</button>
          <button type="button" onclick="App.setTab('reading')">Reading drill</button>
          <button type="button" onclick="App.setTab('writing')">Timed writing</button>
          <button type="button" onclick="App.setTab('speaking')">Speaking simulator</button>
          <button type="button" onclick="App.setTab('mocks')">Mock tracker</button>
        </div>
      </div>
    `;
  }

  function toggleDailyCheck(index) {
    const entry = getDailyEntry();
    entry.checks[index] = !entry.checks[index];
    saveState();
  }

  function saveDailyEntry() {
    const entry = getDailyEntry();
    entry.minutes = document.getElementById("dailyMinutes").value;
    entry.weakSkill = document.getElementById("dailyWeakSkill").value;
    entry.notes = document.getElementById("dailyNotes").value.trim();
    saveState();
    renderToday();
  }

  function renderListening() {
    const item = DATA.listeningItems[app.listeningIndex];
    const answered = app.listeningAnswer !== null;
    document.getElementById("listening").innerHTML = `
      <div class="section-band">
        <div class="section-head">
          <div>
            <h2>Listening Drill</h2>
            <p>${h(item.id)} · ${h(item.band)} · ${h(item.topic)} · trap: ${h(item.trap)}</p>
          </div>
          <div class="row">
            <button type="button" class="icon" title="Previous item" onclick="App.prevListening()">‹</button>
            <button type="button" class="icon" title="Next item" onclick="App.nextListening()">›</button>
          </div>
        </div>
        <div class="prompt-box">
          <h4>${h(item.title)}</h4>
          <p class="small">Play once, then answer. Transcript appears only after submission.</p>
          <div class="row">
            <button type="button" class="primary" onclick="App.playListening()" ${app.listeningPlayed ? "disabled" : ""} title="Play French audio once">▶ Play once</button>
            <span class="pill ${app.listeningPlayed ? "gold" : ""}">${app.listeningPlayed ? "played" : "not played"}</span>
          </div>
        </div>
        <h3>${h(item.question)}</h3>
        <div class="choice-list">
          ${item.options.map((option, index) => {
            const klass = answered ? (index === item.answer ? "correct" : index === app.listeningAnswer ? "incorrect" : "") : "";
            return `<button type="button" class="choice ${klass}" onclick="App.answerListening(${index})"><strong>${String.fromCharCode(65 + index)}</strong><span>${h(option)}</span></button>`;
          }).join("")}
        </div>
        ${answered ? `
          <div class="notice ${app.listeningAnswer === item.answer ? "good" : "risk"}">
            <strong>${app.listeningAnswer === item.answer ? "Correct." : "Missed."}</strong> ${h(item.rationale)}
            <br /><span class="small">Transcript: ${h(item.script)}</span>
            <br /><span class="small">Remediation: ${h(DATA.remediation[item.remediation])}</span>
          </div>
        ` : ""}
      </div>
    `;
  }

  function playListening() {
    const item = DATA.listeningItems[app.listeningIndex];
    app.listeningPlayed = true;
    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(item.script);
      utterance.lang = "fr-FR";
      utterance.rate = 0.92;
      window.speechSynthesis.speak(utterance);
    } else {
      alert("This browser does not expose speech synthesis. Read the transcript once after submitting, or open in a browser with Web Speech support.");
    }
    renderListening();
  }

  function answerListening(index) {
    const item = DATA.listeningItems[app.listeningIndex];
    app.listeningAnswer = index;
    state.listeningAttempts.push({
      date: todayIso(),
      itemId: item.id,
      band: item.band,
      topic: item.topic,
      correct: index === item.answer,
      trap: item.trap,
      remediation: item.remediation
    });
    saveState();
    renderListening();
  }

  function moveListening(delta) {
    app.listeningIndex = (app.listeningIndex + delta + DATA.listeningItems.length) % DATA.listeningItems.length;
    app.listeningPlayed = false;
    app.listeningAnswer = null;
    renderListening();
  }

  function renderReading() {
    const item = DATA.readingItems[app.readingIndex];
    const answered = app.readingAnswer !== null;
    document.getElementById("reading").innerHTML = `
      <div class="section-band">
        <div class="section-head">
          <div>
            <h2>Reading Drill</h2>
            <p>${h(item.id)} · ${h(item.band)} · ${h(item.topic)} · trap: ${h(item.trap)}</p>
          </div>
          <div class="row">
            <button type="button" class="icon" title="Previous item" onclick="App.prevReading()">‹</button>
            <button type="button" class="icon" title="Next item" onclick="App.nextReading()">›</button>
          </div>
        </div>
        <div class="prompt-box">
          <h4>${h(item.title)}</h4>
          <p>${h(item.passage)}</p>
        </div>
        <h3>${h(item.question)}</h3>
        <div class="choice-list">
          ${item.options.map((option, index) => {
            const klass = answered ? (index === item.answer ? "correct" : index === app.readingAnswer ? "incorrect" : "") : "";
            return `<button type="button" class="choice ${klass}" onclick="App.answerReading(${index})"><strong>${String.fromCharCode(65 + index)}</strong><span>${h(option)}</span></button>`;
          }).join("")}
        </div>
        ${answered ? `
          <div class="notice ${app.readingAnswer === item.answer ? "good" : "risk"}">
            <strong>${app.readingAnswer === item.answer ? "Correct." : "Missed."}</strong> ${h(item.rationale)}
            <br /><span class="small">Remediation: ${h(DATA.remediation[item.remediation])}</span>
          </div>
        ` : ""}
      </div>
    `;
  }

  function answerReading(index) {
    const item = DATA.readingItems[app.readingIndex];
    app.readingAnswer = index;
    state.readingAttempts.push({
      date: todayIso(),
      itemId: item.id,
      band: item.band,
      topic: item.topic,
      correct: index === item.answer,
      trap: item.trap,
      remediation: item.remediation
    });
    saveState();
    renderReading();
  }

  function moveReading(delta) {
    app.readingIndex = (app.readingIndex + delta + DATA.readingItems.length) % DATA.readingItems.length;
    app.readingAnswer = null;
    renderReading();
  }

  function renderWriting() {
    const prompt = DATA.writingPrompts.find((item) => item.id === state.selectedWritingId) || DATA.writingPrompts[0];
    const draft = state.writingDrafts[prompt.id] || "";
    const words = countWords(draft);
    const inLimit = words >= prompt.limit[0] && words <= prompt.limit[1];
    const score = rubricScore("writing");
    document.getElementById("writing").innerHTML = `
      <div class="section-band">
        <div class="section-head">
          <div>
            <h2>Writing Practice</h2>
            <p>Official-style word-count discipline with a 20-point training rubric.</p>
          </div>
          <button class="primary" type="button" onclick="App.saveWritingAttempt()">Save Attempt</button>
        </div>
        <div class="grid two">
          <div class="stack">
            <label>Prompt
              <select id="writingPrompt" onchange="App.selectWritingPrompt()">
                ${DATA.writingPrompts.map((item) => `<option value="${item.id}" ${item.id === prompt.id ? "selected" : ""}>${h(item.task)} · ${h(item.title)}</option>`).join("")}
              </select>
            </label>
            <div class="prompt-box">
              <h4>${h(prompt.task)} - ${h(prompt.title)}</h4>
              <p>${h(prompt.prompt)}</p>
              <p class="small">Target: ${prompt.limit[0]}-${prompt.limit[1]} words · suggested timer: ${prompt.timeMinutes} min.</p>
            </div>
            <div class="row">
              <button type="button" onclick="App.startTimer(${prompt.timeMinutes * 60}, 'writingTimer')">Start ${prompt.timeMinutes}:00</button>
              <button type="button" onclick="App.pauseTimer()">Pause</button>
              <button type="button" onclick="App.resetTimer('writingTimer')">Reset</button>
              <span id="writingTimer" class="timer">00:00</span>
            </div>
          </div>
          <div class="stack">
            <label>Draft
              <textarea id="writingDraft" oninput="App.updateWritingDraft()" placeholder="Write in French here.">${h(draft)}</textarea>
            </label>
            <div class="row">
              <span class="score-badge">${score}/20</span>
              <span>${h(productionBand(score))}</span>
              <span class="word-count ${inLimit ? "ok" : "bad"}">${words} words (${prompt.limit[0]}-${prompt.limit[1]})</span>
            </div>
          </div>
        </div>
      </div>
      <div class="section-band">
        <div class="section-head">
          <div>
            <h3>Writing Rubric</h3>
            <p>Use this as a training proxy, then rewrite using only three fixes.</p>
          </div>
        </div>
        ${renderRubric("writing")}
      </div>
    `;
  }

  function selectWritingPrompt() {
    state.selectedWritingId = document.getElementById("writingPrompt").value;
    saveState();
    renderWriting();
  }

  function updateWritingDraft() {
    const prompt = DATA.writingPrompts.find((item) => item.id === state.selectedWritingId) || DATA.writingPrompts[0];
    state.writingDrafts[prompt.id] = document.getElementById("writingDraft").value;
    saveState();
    renderWritingSummaryOnly(prompt);
  }

  function renderWritingSummaryOnly(prompt) {
    const draft = state.writingDrafts[prompt.id] || "";
    const words = countWords(draft);
    const inLimit = words >= prompt.limit[0] && words <= prompt.limit[1];
    const summary = document.querySelector("#writing .row .word-count");
    if (summary) {
      summary.className = `word-count ${inLimit ? "ok" : "bad"}`;
      summary.textContent = `${words} words (${prompt.limit[0]}-${prompt.limit[1]})`;
    }
  }

  function renderRubric(kind) {
    const rubric = kind === "writing" ? state.writingRubric : state.speakingRubric;
    return `
      <div class="rubric">
        ${PRODUCTION_CRITERIA[kind].map((criterion) => `
          <div class="rubric-row">
            <label>${h(criterion)}</label>
            <input type="range" min="0" max="4" value="${Number(rubric[criterion] || 0)}" oninput="App.updateRubric('${kind}', '${h(criterion)}', this.value)" />
            <strong>${Number(rubric[criterion] || 0)}/4</strong>
          </div>
        `).join("")}
      </div>
    `;
  }

  function updateRubric(kind, criterion, value) {
    const target = kind === "writing" ? state.writingRubric : state.speakingRubric;
    target[criterion] = Number(value);
    saveState();
    if (kind === "writing") renderWriting();
    if (kind === "speaking") renderSpeaking();
  }

  function rubricScore(kind) {
    const rubric = kind === "writing" ? state.writingRubric : state.speakingRubric;
    return Object.values(rubric).reduce((sum, value) => sum + Number(value || 0), 0);
  }

  function saveWritingAttempt() {
    const prompt = DATA.writingPrompts.find((item) => item.id === state.selectedWritingId) || DATA.writingPrompts[0];
    const draft = state.writingDrafts[prompt.id] || "";
    const score = rubricScore("writing");
    state.writingAttempts.push({
      date: todayIso(),
      promptId: prompt.id,
      task: prompt.task,
      title: prompt.title,
      words: countWords(draft),
      score,
      band: productionBand(score),
      draft,
      rubric: { ...state.writingRubric }
    });
    saveState();
    alert("Writing attempt saved.");
    renderWriting();
  }

  function renderSpeaking() {
    const prompt = DATA.speakingPrompts.find((item) => item.id === state.selectedSpeakingId) || DATA.speakingPrompts[0];
    const score = rubricScore("speaking");
    document.getElementById("speaking").innerHTML = `
      <div class="section-band">
        <div class="section-head">
          <div>
            <h2>Speaking Simulator</h2>
            <p>Use official-style timing. Record when your browser allows microphone access.</p>
          </div>
          <button class="primary" type="button" onclick="App.saveSpeakingAttempt()">Save Attempt</button>
        </div>
        <div class="grid two">
          <div class="stack">
            <label>Prompt
              <select id="speakingPrompt" onchange="App.selectSpeakingPrompt()">
                ${DATA.speakingPrompts.map((item) => `<option value="${item.id}" ${item.id === prompt.id ? "selected" : ""}>${h(item.task)} · ${h(item.title)}</option>`).join("")}
              </select>
            </label>
            <div class="prompt-box">
              <h4>${h(prompt.task)} - ${h(prompt.title)}</h4>
              <p>${h(prompt.prompt)}</p>
              <p class="small">Prep: ${formatTime(prompt.prepSeconds)} · response: ${formatTime(prompt.responseSeconds)}</p>
            </div>
            <div class="row">
              ${prompt.prepSeconds ? `<button type="button" onclick="App.startTimer(${prompt.prepSeconds}, 'speakingTimer')">Prep ${formatTime(prompt.prepSeconds)}</button>` : ""}
              <button type="button" onclick="App.startTimer(${prompt.responseSeconds}, 'speakingTimer')">Response ${formatTime(prompt.responseSeconds)}</button>
              <button type="button" onclick="App.pauseTimer()">Pause</button>
              <button type="button" onclick="App.resetTimer('speakingTimer')">Reset</button>
            </div>
            <div id="speakingTimer" class="timer">00:00</div>
          </div>
          <div class="stack">
            <div class="row">
              <button type="button" onclick="App.startRecording()">● Record</button>
              <button type="button" onclick="App.stopRecording()">■ Stop</button>
              <span class="score-badge">${score}/20</span>
              <span>${h(productionBand(score))}</span>
            </div>
            <div id="recordingPanel" class="prompt-box">
              ${app.currentAudioUrl ? `<audio controls src="${h(app.currentAudioUrl)}"></audio>` : `<p class="small">No recording in this browser session yet.</p>`}
            </div>
            <label>Self-review / rater notes
              <textarea id="speakingNotes" placeholder="Hesitations, missing connectors, pronunciation flags, interaction breakdowns."></textarea>
            </label>
          </div>
        </div>
      </div>
      <div class="section-band">
        <div class="section-head">
          <div>
            <h3>Speaking Rubric</h3>
            <p>For real readiness, get a second rater when possible.</p>
          </div>
        </div>
        ${renderRubric("speaking")}
      </div>
    `;
  }

  function selectSpeakingPrompt() {
    state.selectedSpeakingId = document.getElementById("speakingPrompt").value;
    saveState();
    renderSpeaking();
  }

  async function startRecording() {
    if (!navigator.mediaDevices || !window.MediaRecorder) {
      alert("Recording is not available in this browser context. Use the timer and store notes instead.");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      app.audioChunks = [];
      app.mediaRecorder = new MediaRecorder(stream);
      app.mediaRecorder.addEventListener("dataavailable", (event) => {
        if (event.data.size > 0) app.audioChunks.push(event.data);
      });
      app.mediaRecorder.addEventListener("stop", () => {
        const blob = new Blob(app.audioChunks, { type: "audio/webm" });
        if (app.currentAudioUrl) URL.revokeObjectURL(app.currentAudioUrl);
        app.currentAudioUrl = URL.createObjectURL(blob);
        stream.getTracks().forEach((track) => track.stop());
        renderSpeaking();
      });
      app.mediaRecorder.start();
    } catch (error) {
      alert(`Could not start recording: ${error.message}`);
    }
  }

  function stopRecording() {
    if (app.mediaRecorder && app.mediaRecorder.state !== "inactive") {
      app.mediaRecorder.stop();
    }
  }

  function saveSpeakingAttempt() {
    const prompt = DATA.speakingPrompts.find((item) => item.id === state.selectedSpeakingId) || DATA.speakingPrompts[0];
    const score = rubricScore("speaking");
    const notes = document.getElementById("speakingNotes")?.value.trim() || "";
    state.speakingAttempts.push({
      date: todayIso(),
      promptId: prompt.id,
      task: prompt.task,
      title: prompt.title,
      score,
      band: productionBand(score),
      notes,
      recordingCapturedInSession: Boolean(app.currentAudioUrl),
      rubric: { ...state.speakingRubric }
    });
    saveState();
    alert("Speaking attempt saved.");
    renderSpeaking();
  }

  function renderMocks() {
    const lastThree = state.mocks.slice(-3);
    const stable = readinessStable(lastThree);
    document.getElementById("mocks").innerHTML = `
      <div class="section-band">
        <div class="section-head">
          <div>
            <h2>Mock Tracker</h2>
            <p>Record full official-format mocks. Comprehension bands are readiness estimates.</p>
          </div>
          <button class="primary" type="button" onclick="App.saveMock()">Save Mock</button>
        </div>
        <div class="form-grid">
          <label>Date
            <input id="mockDate" type="date" value="${todayIso()}" />
          </label>
          <label>Listening correct /39
            <input id="mockListening" type="number" min="0" max="39" />
          </label>
          <label>Reading correct /39
            <input id="mockReading" type="number" min="0" max="39" />
          </label>
          <label>Writing /20
            <input id="mockWriting" type="number" min="0" max="20" />
          </label>
          <label>Speaking /20
            <input id="mockSpeaking" type="number" min="0" max="20" />
          </label>
          <label>Weakest skill
            <select id="mockWeakSkill">
              ${["Listening", "Reading", "Writing", "Speaking"].map((skill) => `<option>${skill}</option>`).join("")}
            </select>
          </label>
          <label>Mock type
            <select id="mockType">
              ${["Diagnostic", "Mini-mock", "Full mock", "Dress rehearsal"].map((type) => `<option>${type}</option>`).join("")}
            </select>
          </label>
          <label>Notes
            <input id="mockNotes" placeholder="Main failure mode" />
          </label>
        </div>
      </div>
      <div class="section-band">
        <div class="section-head">
          <div>
            <h3>Readiness Signal</h3>
            <p>Stable performance matters more than a single high day.</p>
          </div>
        </div>
        <div class="notice ${stable.ready ? "good" : "risk"}">${h(stable.message)}</div>
      </div>
      <div class="section-band">
        <div class="section-head">
          <div>
            <h3>Mock History</h3>
            <p>${state.mocks.length} record(s).</p>
          </div>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr><th>Date</th><th>Type</th><th>Listening</th><th>Reading</th><th>Writing</th><th>Speaking</th><th>Weak</th><th>Notes</th></tr>
            </thead>
            <tbody>
              ${state.mocks.slice().reverse().map((mock) => `
                <tr>
                  <td>${h(mock.date)}</td>
                  <td>${h(mock.type)}</td>
                  <td>${mock.listening}/39 · ${h(comprehensionBand((mock.listening / 39) * 100))}</td>
                  <td>${mock.reading}/39 · ${h(comprehensionBand((mock.reading / 39) * 100))}</td>
                  <td>${mock.writing}/20 · ${h(productionBand(mock.writing))}</td>
                  <td>${mock.speaking}/20 · ${h(productionBand(mock.speaking))}</td>
                  <td>${h(mock.weakSkill)}</td>
                  <td>${h(mock.notes)}</td>
                </tr>
              `).join("") || `<tr><td colspan="8">No mocks recorded yet.</td></tr>`}
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

  function saveMock() {
    const mock = {
      date: document.getElementById("mockDate").value || todayIso(),
      listening: clampNumber(document.getElementById("mockListening").value, 0, 39),
      reading: clampNumber(document.getElementById("mockReading").value, 0, 39),
      writing: clampNumber(document.getElementById("mockWriting").value, 0, 20),
      speaking: clampNumber(document.getElementById("mockSpeaking").value, 0, 20),
      weakSkill: document.getElementById("mockWeakSkill").value,
      type: document.getElementById("mockType").value,
      notes: document.getElementById("mockNotes").value.trim()
    };
    state.mocks.push(mock);
    saveState();
    renderMocks();
  }

  function clampNumber(value, min, max) {
    const n = Number(value);
    if (!Number.isFinite(n)) return min;
    return Math.max(min, Math.min(max, n));
  }

  function readinessStable(records) {
    if (records.length < 3) {
      return { ready: false, message: "Need at least 3 recent mock records before a stable booking signal." };
    }
    const failures = [];
    records.forEach((mock) => {
      if ((mock.listening / 39) * 100 < 72) failures.push(`${mock.date} listening`);
      if ((mock.reading / 39) * 100 < 72) failures.push(`${mock.date} reading`);
      if (mock.writing < 10) failures.push(`${mock.date} writing`);
      if (mock.speaking < 10) failures.push(`${mock.date} speaking`);
    });
    if (failures.length) {
      return { ready: false, message: `Not ready yet. Below-threshold signals: ${failures.join(", ")}.` };
    }
    return { ready: true, message: "Stable minimum signal across the last 3 mocks. Prefer NCLC 9 buffer before booking if timeline allows." };
  }

  function mockSummary(mock) {
    return `L ${mock.listening}/39, R ${mock.reading}/39, W ${mock.writing}/20, S ${mock.speaking}/20`;
  }

  function inferWeakSkill() {
    const latest = state.mocks.at(-1);
    if (latest?.weakSkill) return { label: latest.weakSkill, note: latest.notes || "Latest mock weak-skill field." };
    const dailyWeak = Object.values(state.daily).map((entry) => entry.weakSkill).filter(Boolean).at(-1);
    if (dailyWeak) return { label: dailyWeak, note: "From latest daily log." };
    return { label: "pending", note: "Run a baseline to identify it." };
  }

  function renderVault() {
    const markdown = buildMarkdownExport();
    document.getElementById("vault").innerHTML = `
      <div class="section-band">
        <div class="section-head">
          <div>
            <h2>Vault Export</h2>
            <p>Generate a Markdown practice note that fits the raw/session-notes layer.</p>
          </div>
          <div class="row">
            <button class="primary" type="button" onclick="App.copyMarkdown()">Copy Markdown</button>
            <button type="button" onclick="App.exportState()">Export State JSON</button>
            <button class="danger" type="button" onclick="App.resetState()">Reset Local State</button>
          </div>
        </div>
        <textarea id="markdownOutput" class="markdown-output">${h(markdown)}</textarea>
      </div>
      <div class="section-band">
        <div class="section-head">
          <div>
            <h3>Import State</h3>
            <p>Paste a previously exported JSON state to restore browser practice history.</p>
          </div>
          <button type="button" onclick="App.importState()">Import JSON</button>
        </div>
        <textarea id="stateImport" class="markdown-output" placeholder="Paste exported JSON here."></textarea>
      </div>
    `;
  }

  function buildMarkdownExport() {
    const date = todayIso();
    const daily = state.daily[date] || {};
    const latestWriting = state.writingAttempts.at(-1);
    const latestSpeaking = state.speakingAttempts.at(-1);
    const latestMock = state.mocks.at(-1);
    return `---
type: practice-session
project: tcf-canada-training
date: ${date}
---

# Practice Session - ${date}

## Daily Log

- Minutes: ${daily.minutes || ""}
- Weakest skill: ${daily.weakSkill || ""}
- Notes: ${daily.notes || ""}

## Latest Writing

${latestWriting ? `- Prompt: ${latestWriting.task} - ${latestWriting.title}
- Words: ${latestWriting.words}
- Score: ${latestWriting.score}/20 (${latestWriting.band})` : "- No saved writing attempt yet."}

## Latest Speaking

${latestSpeaking ? `- Prompt: ${latestSpeaking.task} - ${latestSpeaking.title}
- Score: ${latestSpeaking.score}/20 (${latestSpeaking.band})
- Notes: ${latestSpeaking.notes || ""}` : "- No saved speaking attempt yet."}

## Latest Mock

${latestMock ? `- Date: ${latestMock.date}
- Type: ${latestMock.type}
- Listening: ${latestMock.listening}/39 (${comprehensionBand((latestMock.listening / 39) * 100)})
- Reading: ${latestMock.reading}/39 (${comprehensionBand((latestMock.reading / 39) * 100)})
- Writing: ${latestMock.writing}/20 (${productionBand(latestMock.writing)})
- Speaking: ${latestMock.speaking}/20 (${productionBand(latestMock.speaking)})
- Weakest skill: ${latestMock.weakSkill}
- Notes: ${latestMock.notes || ""}` : "- No mock recorded yet."}

## Next Three Fixes

1. 
2. 
3. 
`;
  }

  async function copyMarkdown() {
    const output = document.getElementById("markdownOutput");
    output.focus();
    output.select();
    try {
      await navigator.clipboard.writeText(output.value);
      alert("Markdown copied.");
    } catch {
      document.execCommand("copy");
      alert("Markdown selected/copied with browser fallback.");
    }
  }

  function exportState() {
    const output = document.getElementById("markdownOutput");
    output.value = JSON.stringify(state, null, 2);
  }

  function importState() {
    const raw = document.getElementById("stateImport").value.trim();
    if (!raw) return;
    try {
      const parsed = JSON.parse(raw);
      Object.keys(state).forEach((key) => delete state[key]);
      Object.assign(state, { ...defaultState(), ...parsed });
      saveState();
      alert("State imported.");
      renderCurrentView();
    } catch (error) {
      alert(`Invalid JSON: ${error.message}`);
    }
  }

  function resetState() {
    if (!confirm("Reset local practice history in this browser?")) return;
    localStorage.removeItem(STORE_KEY);
    Object.keys(state).forEach((key) => delete state[key]);
    Object.assign(state, defaultState());
    saveState();
    renderCurrentView();
  }

  function startTimer(seconds, displayId) {
    pauseTimer();
    app.timerDisplayId = displayId;
    app.timer = {
      remaining: Number(seconds),
      startedAt: Date.now()
    };
    updateTimerDisplay();
    app.timer.interval = window.setInterval(() => {
      app.timer.remaining -= 1;
      updateTimerDisplay();
      if (app.timer.remaining <= 0) {
        pauseTimer();
      }
    }, 1000);
  }

  function pauseTimer() {
    if (app.timer?.interval) {
      window.clearInterval(app.timer.interval);
    }
    if (app.timer) app.timer.interval = null;
  }

  function resetTimer(displayId) {
    pauseTimer();
    app.timer = null;
    const display = document.getElementById(displayId);
    if (display) display.textContent = "00:00";
  }

  function updateTimerDisplay() {
    const display = document.getElementById(app.timerDisplayId);
    if (!display || !app.timer) return;
    display.textContent = formatTime(Math.max(0, app.timer.remaining));
  }

  function formatTime(seconds) {
    const total = Math.max(0, Number(seconds) || 0);
    const minutes = Math.floor(total / 60);
    const rest = total % 60;
    return `${String(minutes).padStart(2, "0")}:${String(rest).padStart(2, "0")}`;
  }

  function init() {
    document.querySelectorAll(".tabbar button").forEach((button) => {
      button.addEventListener("click", () => setTab(button.dataset.tab));
    });
    renderStatus();
    renderCurrentView();
  }

  window.App = {
    setTab,
    saveProfile,
    toggleDailyCheck,
    saveDailyEntry,
    playListening,
    answerListening,
    prevListening: () => moveListening(-1),
    nextListening: () => moveListening(1),
    answerReading,
    prevReading: () => moveReading(-1),
    nextReading: () => moveReading(1),
    selectWritingPrompt,
    updateWritingDraft,
    updateRubric,
    saveWritingAttempt,
    selectSpeakingPrompt,
    startRecording,
    stopRecording,
    saveSpeakingAttempt,
    saveMock,
    copyMarkdown,
    exportState,
    importState,
    resetState,
    startTimer,
    pauseTimer,
    resetTimer
  };

  document.addEventListener("DOMContentLoaded", init);
})();
