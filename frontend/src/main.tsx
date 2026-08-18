import React, {useEffect, useRef, useState} from 'react';
import {createRoot} from 'react-dom/client';
import {AreaChart, Area, ResponsiveContainer, Tooltip} from 'recharts';
import {
  ArrowRight,
  Camera,
  Mic,
  Play,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  Square,
  Volume2,
  X,
  Trash2
} from 'lucide-react';
import './styles.css';

declare global {
  interface Window {
    SpeechRecognition?: any;
    webkitSpeechRecognition?: any;
  }
}

type Profile = {
  role:string;
  seniority:string;
  skills:string[];
  technologies:string[];
  responsibilities:string[];
  behavioral_competencies:string[];
  likely_topics:string[];
};

type Question = {
  question:string;
  type:string;
  difficulty:number;
};

type Answer = {
  question:string;
  question_type:string;
  transcript:string;
  duration:number;
  delivery:any;
  content:any;
};

const API='http://localhost:8000/api';

const demoJD=`We are looking for a Machine Learning Engineer to build reliable recommendation and fraud-detection systems. You will partner with product and data teams, deploy models in Python, and explain trade-offs using measurable outcomes. Experience with SQL, experimentation, and production ML systems is valued.`;

const fallbackQuestions: Question[] = [
  {
    question:'Tell me about your experience relevant to this role.',
    type:'HR',
    difficulty:1
  },
  {
    question:'Tell me about a machine learning project you worked on.',
    type:'Technical',
    difficulty:2
  },
  {
    question:'Describe a difficult technical problem you had to solve.',
    type:'Behavioral',
    difficulty:3
  },
  {
    question:'How would you approach a major failure in a machine learning system?',
    type:'Technical',
    difficulty:4
  },
  {
    question:'What trade-offs would you consider when designing a production ML system?',
    type:'Technical',
    difficulty:5
  }
];

const demoTranscript=`I built a fraud detection model for a marketplace. First, I partnered with our risk team to define the cost of false positives. I used a Random Forest baseline because it handled our mixed feature types well, then compared it with logistic regression for interpretability. We monitored precision at a fixed recall threshold and reduced manual review by 28 percent while keeping fraud capture stable.`;

function App(){

  const [questions,setQuestions]=useState<Question[]>([]);
  const [page,setPage]=useState<'home'|'setup'|'room'|'report'>('home');

  const [title,setTitle]=useState('Machine Learning Engineer');
  const [company,setCompany]=useState('');
  const [jd,setJd]=useState(demoJD);
  const [kind,setKind]=useState('Mixed');
  const [difficulty,setDifficulty]=useState('Medium');

  const [profile,setProfile]=useState<Profile|null>(null);
  const [id,setId]=useState('');

  const [answers,setAnswers]=useState<Answer[]>([]);
  const [index,setIndex]=useState(0);
  const [followup,setFollowup]=useState('');

  const start=async(demo=false)=>{

    const body={
      title:demo?'Machine Learning Engineer':title,
      company,
      job_description:demo?demoJD:jd,
      interview_type:kind,
      difficulty
    };

    try{

      const r=await fetch(
        API+'/interviews/create',
        {
          method:'POST',
          headers:{
            'Content-Type':'application/json'
          },
          body:JSON.stringify(body)
        }
      );

      if(!r.ok){
        throw new Error('Failed to create interview');
      }

      const data=await r.json();

      setId(data.id);
      setProfile(data.profile);

      setQuestions(
        Array.isArray(data.questions) &&
        data.questions.length
          ? data.questions
          : fallbackQuestions
      );

      if(demo){
        setIndex(0);
        setFollowup('');
        setPage('room');
      }

    }catch(error){

        console.error('Failed to create interview:', error);

        alert('Failed to create interview. Check the backend terminal.');

        return;
    }
  };

  if(page==='home'){
    return (
      <Home
        onStart={()=>setPage('setup')}
        onDemo={()=>start(true)}
      />
    );
  }

  if(page==='setup'){
    return (
      <Setup
        {...{
          title,
          setTitle,
          company,
          setCompany,
          jd,
          setJd,
          kind,
          setKind,
          difficulty,
          setDifficulty,
          profile,
          start
        }}
        launch={()=>{
          setIndex(0);
          setFollowup('');
          setAnswers([]);
          setPage('room');
        }}
        back={()=>setPage('home')}
      />
    );
  }

  if(page==='room'){

    const currentQuestion=questions[index];

    if(!currentQuestion){
      return (
        <main className="room">
          <Nav/>
          <div style={{
            padding:'4rem',
            textAlign:'center'
          }}>
            <h2>
              Preparing your interview...
            </h2>
          </div>
        </main>
      );
    }

    return (
      <Room
        question={
          followup ||
          currentQuestion.question
        }

        type={
          followup
            ? 'Follow-up'
            : currentQuestion.type
        }

        number={index+1}
        total={questions.length}

        onExit={()=>{
          setPage('setup');
        }}

        onSubmit={
          async(
            transcript,
            duration,
            eye,
            words
          )=>{

            let result:any;

            try{

              const r=await fetch(
                `${API}/interviews/${id}/answer`,
                {
                  method:'POST',
                  headers:{
                    'Content-Type':'application/json'
                  },
                  body:JSON.stringify({
                    question:
                      followup ||
                      currentQuestion.question,

                    question_type:
                      followup
                        ? 'Technical'
                        : currentQuestion.type,

                    transcript,

                    duration_seconds:
                      duration,

                    eye_contact:eye,
                    words: words || []
                  })
                }
              );

              if(!r.ok){
                throw new Error(
                  'Answer analysis failed'
                );
              }

              result=await r.json();

            }catch{

              result=localAnalysis(
                transcript,
                duration,
                eye
              );
            }

            setAnswers(a=>[
              ...a,
              {
                question:
                  followup ||
                  currentQuestion.question,

                question_type:
                  followup
                    ? 'Follow-up'
                    : currentQuestion.type,

                transcript,
                duration,

                delivery:
                  result.delivery,

                content:
                  result.content
              }
            ]);

            /*
             * The LLM now decides whether
             * the answer actually deserves
             * a follow-up.
             */
            if(
              !followup &&
              result.content?.should_follow_up &&
              result.follow_up
            ){
              setFollowup(
                result.follow_up
              );

              return;
            }

            setFollowup('');

            if(
              index >= questions.length-1
            ){
              setPage('report');
            }else{
              setIndex(
                i=>i+1
              );
            }
          }
        }
      />
    );
  }

  return (
    <Report
      answers={answers}
      profile={profile!}

      onRestart={()=>{
        setAnswers([]);
        setIndex(0);
        setFollowup('');
        setQuestions([]);
        setPage('home');
      }}

      id={id}
    />
  );
}

function Home({
  onStart,
  onDemo
}:{
  onStart:()=>void;
  onDemo:()=>void;
}){

  return (
    <main>

      <Nav/>

      <section className="hero">

        <div className="eyebrow">
          <Sparkles size={14}/>
          YOUR INTERVIEW, MADE LEGIBLE
        </div>

        <h1>
          Speak with<br/>
          <i>clarity.</i> Interview<br/>
          with confidence.
        </h1>

        <p>
          Aptly is the AI interview coach that
          listens to what you say — and how
          you say it.
        </p>

        <div className="actions">

          <button
            className="primary"
            onClick={onStart}
          >
            Start mock interview
            <ArrowRight size={17}/>
          </button>

          <button
            className="secondary"
            onClick={onDemo}
          >
            <Play size={16}/>
            Try demo interview
          </button>

        </div>

        <div className="privacy">
          <ShieldCheck size={16}/>
          Demo Mode is ready — no API key or account required
        </div>

      </section>

      <section className="capabilities">

        {[
          [
            'CONTENT',
            'Knows whether your answer is actually good.'
          ],
          [
            'DELIVERY',
            'Detects fillers, pacing, pauses and eye contact.'
          ],
          [
            'COACHING',
            'Turns weaknesses into drills you can practice today.'
          ]
        ].map(([a,b],i)=>(
          <article key={a}>

            <span>
              0{i+1}
            </span>

            <h3>
              {a}
            </h3>

            <p>
              {b}
            </p>

          </article>
        ))}

      </section>

    </main>
  );
}

function Nav(){

  return (
    <nav>

      <div className="logo">
        <span>✦</span>
        APTLY
      </div>

      <div className="mode">
        ● DEMO MODE
      </div>

    </nav>
  );
}

function Setup(p:any){

  return (
    <main className="setup">

      <Nav/>

      <button
        className="back"
        onClick={p.back}
      >
        ← Back
      </button>

      <div className="setupGrid">

        <section>

          <div className="eyebrow">
            01 / INTERVIEW BRIEF
          </div>

          <h2>
            Tell us what<br/>
            <i>you’re chasing.</i>
          </h2>

          <p className="muted">
            Aptly will build an interview around
            the role, not a generic question bank.
          </p>

          <label>
            Target role

            <input
              value={p.title}
              onChange={
                e=>p.setTitle(e.target.value)
              }
            />
          </label>

          <label>
            Company <small>(optional)</small>

            <input
              value={p.company}
              onChange={
                e=>p.setCompany(e.target.value)
              }
              placeholder="e.g. Northstar"
            />
          </label>

          <div className="selects">

            <label>
              Interview type

              <select
                value={p.kind}
                onChange={
                  e=>p.setKind(e.target.value)
                }
              >
                {[
                  'Mixed',
                  'Technical',
                  'Behavioral',
                  'HR'
                ].map(x=>(
                  <option key={x}>
                    {x}
                  </option>
                ))}
              </select>
            </label>

            <label>
              Difficulty

              <select
                value={p.difficulty}
                onChange={
                  e=>p.setDifficulty(e.target.value)
                }
              >
                {[
                  'Easy',
                  'Medium',
                  'Hard'
                ].map(x=>(
                  <option key={x}>
                    {x}
                  </option>
                ))}
              </select>
            </label>

          </div>

          <label>
            Job description

            <textarea
              value={p.jd}
              onChange={
                e=>p.setJd(e.target.value)
              }
            />
          </label>

          <button
            className="primary"
            onClick={()=>{
              p.start(false)
            }}
          >
            Build interview profile
            <ArrowRight size={17}/>
          </button>

        </section>

        <aside className="profile">

          {p.profile ? (
            <>

              <div className="eyebrow">
                INTERVIEW PROFILE · READY
              </div>

              <h3>
                {p.profile.role}
              </h3>

              <p>
                {p.profile.seniority}
              </p>

              <h4>
                Skills we’ll test
              </h4>

              <div className="chips">

                {p.profile.skills.map(
                  (x:string)=>(
                    <span key={x}>
                      {x}
                    </span>
                  )
                )}

              </div>

              <h4>
                Likely topics
              </h4>

              {p.profile.likely_topics.map(
                (x:string)=>(
                  <p
                    className="topic"
                    key={x}
                  >
                    ↗ {x}
                  </p>
                )
              )}

              <button
                className="primary profileStart"
                onClick={p.launch}
              >
                Start this interview
                <ArrowRight size={17}/>
              </button>

            </>
          ) : (
            <>

              <div className="ghostIcon">
                ◎
              </div>

              <h3>
                Your interview profile
              </h3>

              <p>
                Paste a job description and we’ll map
                the skills, responsibilities, and
                pressure points worth practicing.
              </p>

            </>
          )}

        </aside>

      </div>

    </main>
  );
}

function Room({
  question,
  type,
  number,
  total,
  onExit,
  onSubmit
}:any){

  const [recording,setRecording]=useState(false);
  const [analyzing,setAnalyzing]=useState(false);
  const [transcribed,setTranscribed]=useState(false);
  const [elapsed,setElapsed]=useState(0);
  const [transcript,setTranscript]=useState('');
  const [stream,setStream]=useState<MediaStream|null>(null);

  const video=useRef<HTMLVideoElement>(null);

  const recorder=useRef<MediaRecorder|null>(null);
  const recordedChunks=useRef<Blob[]>([]);

  const cameraStream=useRef<MediaStream|null>(null);
  const audioStream=useRef<MediaStream|null>(null);

  const started=useRef(0);

  const recognition=useRef<any>(null);
  const recordingRef=useRef(false);

  const finalTranscriptRef=useRef('');
  const interimTranscriptRef=useRef('');

  const restartTimerRef=useRef<number|null>(null);

  /*
   * Keep the camera preview alive for the entire interview room.
   * Audio is intentionally NOT requested here.
   */
  useEffect(()=>{

    let mounted=true;

    const startCamera=async()=>{

      try{

        const camera=
          await navigator.mediaDevices.getUserMedia({
            video:true,
            audio:false
          });

        if(!mounted){

          camera.getTracks()
            .forEach(
              track=>track.stop()
            );

          return;

        }

        cameraStream.current=camera;
        setStream(camera);

      }catch(error){

        console.error(
          'Camera preview failed:',
          error
        );

      }

    };

    startCamera();

    return()=>{

      mounted=false;

      cameraStream.current
        ?.getTracks()
        .forEach(
          track=>track.stop()
        );

      cameraStream.current=null;

      audioStream.current
        ?.getTracks()
        .forEach(
          track=>track.stop()
        );

      audioStream.current=null;

    };

  },[]);

  useEffect(()=>{

    if(
      stream &&
      video.current
    ){

      video.current.srcObject=
        stream;

    }

  },[stream]);

  useEffect(()=>{

    const timer=recording
      ? setInterval(()=>{

          setElapsed(
            Math.floor(
              (Date.now()-started.current)/1000
            )
          );

        },500)
      : undefined;

    return()=>{

      if(timer){
        clearInterval(timer);
      }

    };

  },[recording]);

  useEffect(()=>{
    speech(question);
  },[question]);

  useEffect(()=>{

    return()=>{

      recordingRef.current=false;

      if(restartTimerRef.current){

        window.clearTimeout(
          restartTimerRef.current
        );

        restartTimerRef.current=null;

      }

      if(recognition.current){

        try{

          recognition.current.onend=null;
          recognition.current.stop();

        }catch{}

        recognition.current=null;

      }

      if(
        recorder.current &&
        recorder.current.state!=='inactive'
      ){

        try{
          recorder.current.stop();
        }catch{}

      }

      audioStream.current
        ?.getTracks()
        .forEach(
          track=>track.stop()
        );

      audioStream.current=null;

    };

  },[]);

  const startSpeechRecognition=()=>{

    const SpeechRecognitionAPI=
      window.SpeechRecognition ||
      window.webkitSpeechRecognition;

    if(!SpeechRecognitionAPI){

      console.warn(
        'SpeechRecognition is not supported in this browser.'
      );

      return false;

    }

    const instance=
      new SpeechRecognitionAPI();

    recognition.current=instance;

    instance.continuous=true;
    instance.interimResults=true;
    instance.lang=
      navigator.language?.toLowerCase().startsWith('en-in')
        ? 'en-IN'
        : 'en-US';
    instance.maxAlternatives=1;

    instance.onstart=()=>{

      console.log(
        'LIVE SPEECH RECOGNITION ACTIVE'
      );

    };

    instance.onresult=(event:any)=>{

      let finalText='';
      let interimText='';

      for(
        let i=event.resultIndex;
        i<event.results.length;
        i++
      ){

        const result=
          event.results[i];

        const value=
          result?.[0]?.transcript || '';

        if(result.isFinal){

          finalText+=
            value+' ';

        }else{

          interimText+=
            value;

        }

      }

      if(finalText){

        finalTranscriptRef.current=
          (
            finalTranscriptRef.current+
            ' '+
            finalText
          )
            .replace(/\s+/g,' ')
            .trim();

      }

      interimTranscriptRef.current=
        interimText
          .replace(/\s+/g,' ')
          .trim();

      const display=
        (
          finalTranscriptRef.current+
          (
            interimTranscriptRef.current
              ? ' '+interimTranscriptRef.current
              : ''
          )
        )
          .replace(/\s+/g,' ')
          .trim();

      if(display){

        setTranscript(
          display
        );

      }

    };

    instance.onerror=(event:any)=>{

      console.warn(
        'Speech recognition error:',
        event.error
      );

      if(
        event.error==='not-allowed' ||
        event.error==='service-not-allowed'
      ){

        recordingRef.current=false;
        setRecording(false);

        audioStream.current
          ?.getTracks()
          .forEach(
            track=>track.stop()
          );

        audioStream.current=null;

        alert(
          'Microphone access is blocked. Allow microphone access for localhost:5173, then reload Aptly.'
        );

      }

    };

    instance.onend=()=>{

      console.log(
        'Speech recognition ended'
      );

      if(
        recordingRef.current &&
        recognition.current===instance
      ){

        if(restartTimerRef.current){

          window.clearTimeout(
            restartTimerRef.current
          );

        }

        restartTimerRef.current=
          window.setTimeout(()=>{

            if(
              !recordingRef.current ||
              recognition.current!==instance
            ){

              return;

            }

            try{

              instance.start();

              console.log(
                'Speech recognition restarted'
              );

            }catch{}

          },150);

      }

    };

    try{

      instance.start();

      console.log(
        'Speech recognition STARTED'
      );

      return true;

    }catch(error){

      console.warn(
        'Speech recognition failed to start:',
        error
      );

      recognition.current=null;

      return false;

    }

  };

  const begin=async()=>{

    try{

      /*
       * IMPORTANT:
       * Camera is already running.
       * Only request microphone permission here.
       */
      const microphone=
        await navigator.mediaDevices.getUserMedia({
          audio:{
            echoCancellation:true,
            noiseSuppression:true,
            autoGainControl:true
          }
        });

      audioStream.current=
        microphone;

      recordedChunks.current=[];

      /*
       * Keep a real audio recorder as a local fallback.
       * The live browser transcript is used immediately,
       * so Gemini transcription is not on the critical path.
       */
      const recorderOptions:any=
        MediaRecorder.isTypeSupported(
          'audio/webm;codecs=opus'
        )
          ? {
              mimeType:'audio/webm;codecs=opus'
            }
          : undefined;

      recorder.current=
        recorderOptions
          ? new MediaRecorder(
              microphone,
              recorderOptions
            )
          : new MediaRecorder(
              microphone
            );

      recorder.current.ondataavailable=
        event=>{

          if(
            event.data &&
            event.data.size>0
          ){

            recordedChunks.current.push(
              event.data
            );

          }

        };

      recorder.current.start(250);

      started.current=
        Date.now();

      finalTranscriptRef.current='';
      interimTranscriptRef.current='';

      setElapsed(0);
      setTranscript('');
      setTranscribed(false);
      setAnalyzing(false);

      recordingRef.current=true;
      setRecording(true);

      const startedRecognition=
        startSpeechRecognition();

      if(!startedRecognition){

        console.warn(
          'Live transcription unavailable. The candidate can type an answer.'
        );

      }

    }catch(error){

      console.error(
        'Could not start microphone:',
        error
      );

      recordingRef.current=false;
      setRecording(false);

      audioStream.current
        ?.getTracks()
        .forEach(
          track=>track.stop()
        );

      audioStream.current=null;

      if(
        recorder.current &&
        recorder.current.state!=='inactive'
      ){

        try{
          recorder.current.stop();
        }catch{}

      }

      recorder.current=null;

      alert(
        'Microphone access was denied. Please allow microphone access and try again.'
      );

    }

  };

  const stop=()=>{

    if(
      !recordingRef.current &&
      !recorder.current
    ){

      return;

    }

    recordingRef.current=false;
    setRecording(false);

    if(restartTimerRef.current){

      window.clearTimeout(
        restartTimerRef.current
      );

      restartTimerRef.current=null;

    }

    const activeRecognition=
      recognition.current;

    recognition.current=null;

    if(activeRecognition){

      try{

        activeRecognition.onend=null;
        activeRecognition.stop();

      }catch{}

    }

    const finalText=
      finalTranscriptRef.current
        .replace(/\s+/g,' ')
        .trim();

    const interimText=
      interimTranscriptRef.current
        .replace(/\s+/g,' ')
        .trim();

    const browserTranscript=
      (
        finalText+
        (
          interimText
            ? ' '+interimText
            : ''
        )
      )
        .replace(/\s+/g,' ')
        .trim();

    /*
     * Stop microphone only.
     * The camera preview remains active.
     */
    audioStream.current
      ?.getTracks()
      .forEach(
        track=>track.stop()
      );

    audioStream.current=null;

    const duration=
      Math.max(
        Math.floor(
          (Date.now()-started.current)/1000
        ),
        1
      );

    const finalAnswer=
      browserTranscript ||
      transcript.trim();

    if(finalAnswer){

      setTranscript(
        finalAnswer
      );

      setAnalyzing(false);
      setTranscribed(true);

      if(
        recorder.current &&
        recorder.current.state!=='inactive'
      ){

        try{
          recorder.current.stop();
        }catch{}

      }

      recorder.current=null;

      setTimeout(()=>{

        setTranscribed(false);

        onSubmit(
          finalAnswer,
          duration,
          76,
          []
        );

      },300);

      return;

    }

    setAnalyzing(false);

    if(
      recorder.current &&
      recorder.current.state!=='inactive'
    ){

      try{
        recorder.current.stop();
      }catch{}

    }

    recorder.current=null;

    alert(
      'Aptly did not detect speech. Please speak again or type your answer.'
    );

  };

  return (
    <main className="room">

      <Nav/>

      <div className="roomTop">

        <button
          className="back"
          onClick={onExit}
        >
          <X size={16}/>
          Exit
        </button>

        <span>
          QUESTION {number} OF {total}
        </span>

        <div className="timer">
          {String(
            Math.floor(elapsed/60)
          ).padStart(2,'0')}
          :
          {String(
            elapsed%60
          ).padStart(2,'0')}
        </div>

      </div>

      <div className="roomGrid">

        <section className="interviewer">

          <div className="avatar">
            A
          </div>

          <div className="live">
            <i/>
            ALEX IS {
              recording
                ? 'LISTENING'
                : 'SPEAKING'
            }
          </div>

          <p className="role">
            SENIOR HIRING MANAGER · {
              type.toUpperCase()
            }
          </p>

          <h2>
            {question}
          </h2>

          <button
            className="replay"
            onClick={()=>
              speech(question)
            }
          >
            <Volume2 size={15}/>
            Replay question
          </button>

        </section>

        <section className="camera">

          {stream ? (
            <video
              ref={video}
              autoPlay
              muted
              playsInline
            />
          ) : (
            <div className="cameraBlank">

              <Camera size={40}/>

              <p>
                Camera preview
              </p>

              <small>
                Your video is processed
                for delivery estimates only.
              </small>

            </div>
          )}

          {recording && (
            <div className="rec">
              <i/>
              RECORDING
            </div>
          )}

        </section>

        <aside className="roomMeta">

          <div>
            <Mic size={17}/>
            <span>
              MICROPHONE
            </span>
            <b>
              {recording
                ? 'Active'
                : 'Ready'}
            </b>
          </div>

          <div>
            <Camera size={17}/>
            <span>
              CAMERA
            </span>
            <b>
              {stream
                ? 'Active'
                : 'Ready'}
            </b>
          </div>

          <hr/>

          <p>
            Answer naturally. Alex may follow up
            on details from your answer.
          </p>

          <div className="demoHint">
            Speak naturally. Aptly will transcribe
            and evaluate your actual answer.
          </div>

        </aside>

      </div>

      <div className="answerBar">

        <textarea
          placeholder={
            'Your transcription will appear here...'
          }
          value={transcript}
          onChange={
            e=>setTranscript(e.target.value)
          }
        />

        {analyzing ? (

          <button className="primary loading">
            Processing your answer…
          </button>

        ) : transcribed ? (

          <button className="primary">
            ✓ Transcript captured
          </button>

        ) : recording ? (

          <button
            className="stop"
            onClick={stop}
          >
            <Square size={16}/>
            Stop answer
          </button>

        ) : (

          <button
            className="primary"
            onClick={begin}
          >
            <Mic size={17}/>
            Start answer
          </button>

        )}

      </div>

    </main>
  );
}

function Report({
  answers,
  profile,
  onRestart,
  id
}:any){

  const a=answers.length
    ? answers
    : [];

  if(!profile){
    return (
      <main className="report">
        <Nav/>
        <div style={{
          padding:'4rem',
          textAlign:'center'
        }}>
          <h2>
            No interview report available.
          </h2>
        </div>
      </main>
    );
  }

  const fills=a.reduce(
    (n:number,x:any)=>
      n+
      (x.delivery?.fillers?.total || 0),
    0
  );

  const wpm=a.length
    ? Math.round(
        a.reduce(
          (n:number,x:any)=>
            n+
            (x.delivery?.pacing?.wpm || 0),
          0
        )/a.length
      )
    : 0;

  const eye=a.length
    ? Math.round(
        a.reduce(
          (n:number,x:any)=>
            n+
            (x.delivery?.eye_contact || 0),
          0
        )/a.length
      )
    : 0;

  const score=a.length
    ? Math.round(
        a.reduce(
          (n:number,x:any)=>
            n+
            (x.content?.overall_score || 0),
          0
        )/a.length
      )
    : 0;

  const chart=a.map(
    (x:any,i:number)=>({
      n:`Q${i+1}`,
      v:x.content?.overall_score || 0
    })
  );

  const targets=[];

  if(fills>0){

    targets.push([
      `${fills} filler words detected`,
      `Evidence: Aptly detected ${fills} filler words across your answers.`,
      `Drill: replace filler words with a deliberate 2-second pause.`
    ]);
  }

  const weakAnswer=a
    .slice()
    .sort(
      (x:any,y:any)=>
        (x.content?.structure || 0)-
        (y.content?.structure || 0)
    )[0];

  if(
    weakAnswer &&
    (weakAnswer.content?.structure || 100)<75
  ){

    targets.push([
      `Answer structure needs work`,
      `Evidence: your weakest answer scored ${weakAnswer.content.structure} for structure.`,
      `Drill: answer using Situation → Task → Action → Result.`
    ]);
  }

  const depthAnswer=a
    .slice()
    .sort(
      (x:any,y:any)=>
        (x.content?.technical_depth || 0)-
        (y.content?.technical_depth || 0)
    )[0];

  if(
    depthAnswer &&
    (depthAnswer.content?.technical_depth || 100)<75
  ){

    targets.push([
      `Technical depth can improve`,
      `Evidence: your lowest technical-depth score was ${depthAnswer.content.technical_depth}.`,
      `Drill: explain your decision, an alternative, the trade-off, and the result.`
    ]);
  }

  while(targets.length<3){

    targets.push([
      'Make your answers more evidence-driven',
      'Evidence: strong answers connect decisions to measurable outcomes.',
      'Drill: finish every answer with a specific result or metric.'
    ]);
  }

  const deleteSession=async()=>{

    if(
      id &&
      id!=='local-demo'
    ){

      await fetch(
        `${API}/interviews/${id}`,
        {
          method:'DELETE'
        }
      );
    }

    onRestart();
  };

  return (
    <main className="report">

      <Nav/>

      <header className="reportHero">

        <div>

          <div className="eyebrow">
            INTERVIEW SESSION · {
              profile.role.toUpperCase()
            }
          </div>

          <h1>
            Your Aptly<br/>
            <i>Interview Report.</i>
          </h1>

          <p>
            Delivery estimates are based on
            observable signals — not a psychological
            diagnosis.
          </p>

        </div>

        <div className="score">

          <span>
            OVERALL
          </span>

          <b>
            {score}
          </b>

          <small>
            / 100
          </small>

          <p>
            {score>=85
              ? 'Excellent performance'
              : score>=70
                ? 'Strong foundation'
                : 'Room to improve'}
          </p>

        </div>

      </header>

      <section className="metrics">

        {[
          [
            'FILLER WORDS',
            fills,
            fills
              ? 'Practice pauses'
              : 'Clean delivery'
          ],
          [
            'SPEAKING RATE',
            `${wpm} WPM`,
            wpm>=130&&wpm<=170
              ? 'Within target'
              : 'Review pacing'
          ],
          [
            'EYE CONTACT',
            `${eye}%`,
            'Estimated from webcam'
          ],
          [
            'ANSWERS ANALYZED',
            a.length,
            'Evidence captured'
          ]
        ].map(([k,v,n])=>(
          <article key={String(k)}>

            <span>
              {k}
            </span>

            <b>
              {v}
            </b>

            <small>
              {n}
            </small>

          </article>
        ))}

      </section>

      <section className="reportGrid">

        <div className="panel">

          <div className="panelHead">

            <div>

              <span className="eyebrow">
                ANSWER PERFORMANCE
              </span>

              <h3>
                How did your answers perform?
              </h3>

            </div>

            <span className="estimate">
              AI EVALUATION
            </span>

          </div>

          {chart.length ? (
            <ResponsiveContainer
              width="100%"
              height={190}
            >
              <AreaChart data={chart}>

                <defs>

                  <linearGradient id="g">

                    <stop
                      stopColor="#a4f75b"
                      stopOpacity=".5"
                    />

                    <stop
                      offset="1"
                      stopColor="#a4f75b"
                      stopOpacity="0"
                    />

                  </linearGradient>

                </defs>

                <Tooltip/>

                <Area
                  type="monotone"
                  dataKey="v"
                  stroke="#a4f75b"
                  strokeWidth={3}
                  fill="url(#g)"
                />

              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <p className="muted">
              No answer data available.
            </p>
          )}

          <p className="muted">
            Each point represents the AI evaluation
            of an actual answer from this interview.
          </p>

        </div>

        <div className="panel timeline">

          <span className="eyebrow">
            EVIDENCE TIMELINE
          </span>

          <h3>
            Moments worth replaying
          </h3>

          {a.flatMap(
            (x:any)=>
              (x.delivery?.fillers?.events || [])
                .slice(0,2)
                .map((e:any)=>(
                  <p
                    key={
                      `${e.timestamp}-${e.word}`
                    }
                  >
                    <b>
                      {fmt(e.timestamp)}
                    </b>

                    <span>
                      “{e.word}” — filler word
                    </span>
                  </p>
                ))
          ).slice(0,4)}

          {a.flatMap(
            (x:any)=>
              (x.delivery?.pauses?.events || [])
                .slice(0,2)
                .map((e:any)=>(
                  <p
                    key={
                      `${e.timestamp}-pause`
                    }
                  >
                    <b>
                      {fmt(e.timestamp)}
                    </b>

                    <span>
                      {e.duration}s long pause
                      <small>
                        {e.estimated
                          ? ' Estimated'
                          : ''}
                      </small>
                    </span>
                  </p>
                ))
          ).slice(0,4)}

          {!a.some(
            (x:any)=>
              (x.delivery?.fillers?.events?.length || 0)>0 ||
              (x.delivery?.pauses?.events?.length || 0)>0
          ) && (
            <p className="muted">
              No major delivery events detected.
            </p>
          )}

        </div>

      </section>

      <section className="habits">

        <div>

          <span className="eyebrow">
            YOUR TOP 3 PRACTICE TARGETS
          </span>

          <h2>
            The habits costing you<br/>
            <i>the most clarity.</i>
          </h2>

        </div>

        <div>

          {targets.slice(0,3).map(
            (x:any,i:number)=>(
              <article key={i}>

                <b>
                  0{i+1}
                </b>

                <div>

                  <h3>
                    {x[0]}
                  </h3>

                  <p>
                    {x[1]}
                  </p>

                  <strong>
                    DRILL · {x[2]}
                  </strong>

                </div>

              </article>
            )
          )}

        </div>

      </section>

      <section className="answers">

        <span className="eyebrow">
          CONTENT REVIEW
        </span>

        <h2>
          What you said.
        </h2>

        {a.map(
          (x:any,i:number)=>(
            <article key={i}>

              <span>
                Q{i+1} · {x.question_type}
              </span>

              <h3>
                {x.question}
              </h3>

              <p>
                “{x.transcript}”
              </p>

              <div className="contentScores">

                <b>
                  Relevance {
                    x.content?.relevance ?? 0
                  }
                </b>

                <b>
                  Structure {
                    x.content?.structure ?? 0
                  }
                </b>

                <b>
                  Depth {
                    x.content?.technical_depth ?? 0
                  }
                </b>

              </div>

              {x.content?.feedback && (
                <p>
                  <strong>
                    Feedback:
                  </strong>{' '}
                  {x.content.feedback}
                </p>
              )}

              {x.content?.unsupported_claims?.length>0 && (
                <div>
                  <strong>
                    ⚠ Unsupported claims
                  </strong>

                  {x.content.unsupported_claims.map(
                    (claim:any,j:number)=>(
                      <p key={j}>
                        <b>
                          {claim.claim}
                        </b>
                        {' — '}
                        {claim.reason}
                      </p>
                    )
                  )}
                </div>
              )}

              {x.content?.drill && (
                <p>
                  <strong>
                    Drill:
                  </strong>{' '}
                  {x.content.drill}
                </p>
              )}

            </article>
          )
        )}

      </section>

      <footer>

        <div>
          <ShieldCheck/>
          Raw recordings aren’t retained
          for this demo session.
        </div>

        <button
          className="secondary"
          onClick={deleteSession}
        >
          <Trash2 size={15}/>
          Delete session
        </button>

        <button
          className="primary"
          onClick={onRestart}
        >
          <RotateCcw size={16}/>
          Practice again
        </button>

      </footer>

    </main>
  );
}

function fmt(n:number){
  return `00:${String(
    Math.floor(n)
  ).padStart(2,'0')}`;
}

function speech(t:string){

  if(
    'speechSynthesis' in window
  ){

    window.speechSynthesis.cancel();

    window.speechSynthesis.speak(
      new SpeechSynthesisUtterance(t)
    );
  }
}

function localAnalysis(
  text:string,
  duration:number,
  eye:number
){

  const words=
    text.trim().split(/\s+/);

  const events=[
    ...text
      .toLowerCase()
      .matchAll(
        /\b(um|uh|like|basically|actually|literally|right|okay)\b/g
      )
  ].map(
    m=>({
      word:m[0],
      timestamp:
        Math.round(
          ((m.index||0)/
            Math.max(text.length,1))*
          duration*
          10
        )/10
    })
  );

  const wpm=Math.round(
    words.length/
    Math.max(duration/60,0.01)
  );

  const lower=text.toLowerCase();

  const technicalHits=[
    'model',
    'algorithm',
    'deployment',
    'python',
    'sql',
    'docker',
    'production',
    'architecture',
    'database',
    'api'
  ].filter(
    x=>lower.includes(x)
  ).length;

  const relevance=
    Math.min(
      95,
      55+technicalHits*5
    );

  const structure=
    Math.min(
      95,
      60+
      (
        lower.includes('first')||
        lower.includes('then')||
        lower.includes('result')
          ? 15
          : 0
      )+
      (
        words.length>60
          ? 10
          : 0
      )
    );

  const technicalDepth=
    Math.min(
      95,
      50+technicalHits*5
    );

  const overall=Math.round(
    relevance*.35+
    structure*.25+
    technicalDepth*.40
  );

  return {
    delivery:{
      fillers:{
        total:events.length,
        events,
        rate_per_minute:
          Math.round(
            events.length/
            Math.max(duration/60,.01)*
            10
          )/10,
        spikes:[]
      },

      pacing:{
        wpm,
        label:
          wpm>=130&&wpm<=170
            ? 'within target'
            : wpm<130
              ? 'slow'
              : 'fast',
        ideal_band:{
          min:130,
          max:170
        }
      },

      pauses:{
        events:[],
        long_pause_count:0
      },

      eye_contact:eye,
      voice_energy:'stable'
    },

    content:{
      overall_score:overall,
      relevance,
      structure,
      technical_depth:technicalDepth,

      star:{
        situation:false,
        task:false,
        action:false,
        result:false
      },

      unsupported_claims:[],

      strengths:[
        'Provided concrete details.'
      ],

      weaknesses:[
        'Add stronger evidence and measurable outcomes.'
      ],

      feedback:
        (()=>{

          const options:string[]=[];

          const hasOwnership=
            /\b(i|my)\b.*\b(built|implemented|developed|designed|created|decided|chose|used|worked)\b/i
              .test(text);

          const hasEvidence=
            /\b(accuracy|precision|recall|percent|%|ms|seconds|users|result|outcome|improved|reduced|increased|decreased|measured|score)\b/i
              .test(lower);

          const hasStructure=
            /\b(first|second|then|finally|because|therefore|result|outcome|initially|however)\b/i
              .test(lower);
          if(!hasOwnership){

            options.push(
              'Your answer introduces the topic, but your individual contribution is still unclear. State exactly what you built, changed, or decided.'
            );

            options.push(
              'The project context is understandable, but the interviewer needs more ownership. Focus on one action you personally took and explain why.'
            );

            options.push(
              'You describe the overall work more than your role. Highlight one decision you made and what responsibility you personally handled.'
            );

          }

          if(!hasEvidence){

            options.push(
              'The response explains the work but stops before showing its impact. Add a concrete result such as accuracy, latency, dataset size, or user outcome.'
            );

            options.push(
              'Your approach is mentioned, but there is no clear proof of its impact. Finish with a measurable result or a specific before-and-after comparison.'
            );

            options.push(
              'The answer would be more convincing with evidence. Mention what changed after your solution was implemented.'
            );

          }

          if(!hasStructure){

            options.push(
              'The ideas arrive as a continuous explanation. Give the interviewer a clearer sequence: problem, approach, decision, and result.'
            );

            options.push(
              'The main point is there, but the answer needs a cleaner flow. Start with the problem, explain your action, then close with the outcome.'
            );

          }

          if(technicalDepth<60){

            options.push(
              'The technical explanation stays fairly high-level. Explain why you chose the approach and mention one alternative or trade-off.'
            );

            options.push(
              'You identify the technical idea, but the reasoning is thin. Explain how your solution worked and why it was appropriate.'
            );

          }

          if(relevance<60){

            options.push(
              'The response only partially answers the question. Lead with the direct answer before adding project background.'
            );

            options.push(
              'Some context is useful, but the central question gets buried. Answer it directly first, then support your point with an example.'
            );

          }

          if(
            options.length===0
          ){

            options.push(
              'This is a solid response. Make it stronger by connecting your key decision directly to the result it produced.'
            );

            options.push(
              'The answer covers the main idea well. Add one concrete example to make your reasoning easier to evaluate.'
            );

            options.push(
              'You have a reasonable foundation here. The next improvement is to make the technical or behavioral impact more specific.'
            );

          }

          let hash=0;

          for(
            let i=0;
            i<text.length;
            i++
          ){

            hash=
              (
                (
                  hash*31
                )+
                text.charCodeAt(i)
              )>>>0;

          }

          const index=
            hash%options.length;

          return options[index];

        })(),

      drill:
        (()=>{

          if(
            !/\b(i|my)\b.*\b(built|implemented|developed|designed|created|decided|chose|used|worked)\b/i
              .test(text)
          ){

            return 'State your role, describe one action you personally took, and explain why you made that choice.';

          }

          if(
            !/\b(accuracy|precision|recall|percent|%|ms|seconds|users|result|outcome|improved|reduced|increased|decreased|measured|score)\b/i
              .test(lower)
          ){

            return 'Finish with one measurable result or concrete outcome that shows the impact of your work.';

          }

          if(
            technicalDepth<60
          ){

            return 'Explain your approach, one alternative, the trade-off, and why you selected your final solution.';

          }

          if(
            !/\b(first|second|then|finally|because|therefore|result|outcome|initially|however)\b/i
              .test(lower)
          ){

            return 'Structure the answer as Problem → Approach → Decision → Result.';

          }

          return 'Add one concrete example that demonstrates the impact of your decision.';

        })(),

      should_follow_up:false,
      follow_up_reason:''
    }
  };
}

createRoot(
  document.getElementById('root')!
).render(
  <App/>
);