import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type {
  EngineClient,
  SimulationResponseDTO,
  SimulatorMetaDTO,
} from "../../types/api";
import { readUrlState, updateUrlState } from "../../utils/urlState";
import { LogViewer } from "./LogViewer";
import { PlaybackBar } from "./PlaybackBar";
import { RaceTrackSVG } from "./RaceTrackSVG";
import { SimulatorConfigPanel } from "./SimulatorConfigPanel";
import { createLogHighlighter } from "./logFormat";
import {
  type SimConfig,
  defaultConfig,
  diceError,
  fromDecoded,
  toRequest,
} from "./simConfig";

interface SimulatorViewProps {
  client: EngineClient;
  simMeta: SimulatorMetaDTO;
  active: boolean;
}

const AUTO_RUN_DELAY_MS = 250;

function errorMessage(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}

export function SimulatorView({ client, simMeta, active }: SimulatorViewProps) {
  const [config, setConfig] = useState<SimConfig>(() => defaultConfig(simMeta));
  const [ready, setReady] = useState(false);
  const [result, setResult] = useState<SimulationResponseDTO | null>(null);
  const [stepIndex, setStepIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speedMs, setSpeedMs] = useState(450);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const latestRun = useRef(0);

  const highlighter = useMemo(() => createLogHighlighter(simMeta), [simMeta]);
  const configDiceError = diceError(config);

  const runSim = useCallback(
    async (next: SimConfig) => {
      const runId = ++latestRun.current;
      const isLatest = () => runId === latestRun.current;
      setRunning(true);
      setPlaying(false);
      try {
        const res = await client.runSimulation(toRequest(next));
        if (!isLatest()) return;
        setError(res.error);
        if (res.steps.length > 0) {
          setResult(res);
          setStepIndex(0);
          updateUrlState({ tab: "simulator", config: res.encoded_config });
        }
      } catch (err) {
        if (isLatest()) setError(errorMessage(err));
      } finally {
        if (isLatest()) setRunning(false);
      }
    },
    [client],
  );

  const importEncoded = useCallback(
    async (encoded: string) => {
      setConfig(fromDecoded(await client.decodeConfig(encoded)));
    },
    [client],
  );

  useEffect(() => {
    const encoded = readUrlState().config;
    if (!encoded) {
      setReady(true);
      return;
    }
    importEncoded(encoded)
      .catch((err: unknown) => setError(errorMessage(err)))
      .finally(() => setReady(true));
  }, [importEncoded]);

  useEffect(() => {
    if (!ready || configDiceError) return;
    const timer = window.setTimeout(() => void runSim(config), AUTO_RUN_DELAY_MS);
    return () => window.clearTimeout(timer);
  }, [config, ready, configDiceError, runSim]);

  const step = result?.steps[stepIndex] ?? null;
  const board = result && step ? result.board_states[step.board_state_idx] : null;

  return (
    <div className="flex flex-col gap-4 lg:flex-row lg:items-start">
      <SimulatorConfigPanel
        simMeta={simMeta}
        config={config}
        onChange={setConfig}
        encodedConfig={result?.encoded_config ?? ""}
        onImportEncoded={importEncoded}
        onReset={() => {
          setPlaying(false);
          setStepIndex(0);
        }}
        running={running}
        diceError={configDiceError}
      />

      <div className="min-w-0 flex-1 space-y-4">
        {error && (
          <div className="rounded-lg border border-rose-500/40 bg-rose-950/50 p-3 text-xs text-rose-200">
            {error}
          </div>
        )}

        {result && step && board ? (
          <>
            <RaceTrackSVG
              step={step}
              board={board}
              racerPalettes={result.racer_palettes}
            />

            <PlaybackBar
              steps={result.steps}
              turnMap={result.turn_map}
              stepIndex={stepIndex}
              onStepChange={setStepIndex}
              playing={playing}
              onPlayingChange={setPlaying}
              speedMs={speedMs}
              onSpeedChange={setSpeedMs}
              keyboardEnabled={active}
            />

            <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3 xl:grid-cols-6">
              {step.names.map((name, idx) => (
                <RacerCard
                  key={`${name}-${idx}`}
                  name={name}
                  color={result.racer_palettes[name]?.primary ?? "#818cf8"}
                  isCurrent={step.current_racer === idx}
                  place={step.finish_positions[idx]}
                  tile={step.positions[idx]}
                  vp={step.vp[idx]}
                  tripped={step.tripped[idx]}
                  eliminated={step.eliminated[idx]}
                  sidelined={step.sidelined[idx]}
                />
              ))}
            </div>

            <LogViewer
              logs={result.logs}
              steps={result.steps}
              activeStepIndex={stepIndex}
              racerNames={step.names}
              highlighter={highlighter}
              onJumpToStep={(index) => {
                setPlaying(false);
                setStepIndex(index);
              }}
            />
          </>
        ) : (
          <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-12 text-center text-xs text-slate-400">
            {running ? "Running race simulation..." : "Waiting for a valid configuration."}
          </div>
        )}
      </div>
    </div>
  );
}

interface RacerCardProps {
  name: string;
  color: string;
  isCurrent: boolean;
  place: number | null;
  tile: number | null;
  vp: number;
  tripped: boolean;
  eliminated: boolean;
  sidelined: boolean;
}

function RacerCard({
  name,
  color,
  isCurrent,
  place,
  tile,
  vp,
  tripped,
  eliminated,
  sidelined,
}: RacerCardProps) {
  return (
    <div
      className={`rounded-lg border p-2.5 text-xs ${
        isCurrent
          ? "border-amber-400/70 bg-amber-950/20"
          : "border-slate-800 bg-slate-900/70"
      }`}
    >
      <div className="flex items-center justify-between gap-1">
        <div className="flex min-w-0 items-center gap-1.5">
          <span
            className="h-2.5 w-2.5 shrink-0 rounded-full"
            style={{ backgroundColor: color }}
          />
          <span className="truncate font-semibold text-white">{name}</span>
        </div>
        {place !== null && (
          <span className="rounded bg-amber-500/20 px-1.5 py-0.5 text-[10px] font-bold text-amber-300">
            #{place}
          </span>
        )}
      </div>
      <div className="mt-1.5 flex items-center justify-between text-[11px] text-slate-400">
        <span>
          Tile: <strong className="text-slate-200">{tile ?? "—"}</strong>
        </span>
        <span>
          VP: <strong className="text-sky-300">{vp}</strong>
        </span>
      </div>
      {(tripped || eliminated || sidelined) && (
        <div className="mt-1 flex flex-wrap gap-1">
          {tripped && (
            <span className="rounded bg-rose-500/20 px-1.5 py-0.5 text-[9px] font-semibold text-rose-300">
              TRIPPED
            </span>
          )}
          {eliminated && (
            <span className="rounded bg-slate-700 px-1.5 py-0.5 text-[9px] font-semibold text-slate-300">
              ELIMINATED
            </span>
          )}
          {sidelined && (
            <span className="rounded bg-amber-500/20 px-1.5 py-0.5 text-[9px] font-semibold text-amber-300">
              SIDELINED
            </span>
          )}
        </div>
      )}
    </div>
  );
}
