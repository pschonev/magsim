import { useCallback, useEffect, useState } from "react";
import type {
  EngineClient,
  SimulationRequestDTO,
  SimulationResultDTO,
  SimulatorMetadataDTO,
} from "../../types/api";
import { setUrlState } from "../../utils/urlState";
import { LogViewer } from "./LogViewer";
import { PlaybackBar } from "./PlaybackBar";
import { RaceTrackSVG } from "./RaceTrackSVG";
import { SimulatorConfigPanel } from "./SimulatorConfigPanel";

interface SimulatorViewProps {
  client: EngineClient;
  simMeta: SimulatorMetadataDTO;
  incomingConfigStr: string | null;
  onConsumedIncomingConfig: () => void;
}

const DEFAULT_RACERS = [
  "Magician",
  "PartyAnimal",
  "Egg",
  "ThirdWheel",
  "Leaptoad",
  "Hypnotist",
];

export function SimulatorView({
  client,
  simMeta,
  incomingConfigStr,
  onConsumedIncomingConfig,
}: SimulatorViewProps) {
  const [config, setConfig] = useState<SimulationRequestDTO>(() => {
    const initialRacers = DEFAULT_RACERS.filter((r) =>
      simMeta.racers.includes(r),
    );
    const racers =
      initialRacers.length >= 2 ? initialRacers : simMeta.racers.slice(0, 4);
    return {
      board: simMeta.boards[0] ?? "Standard",
      racers,
      seed: 42,
      start_positions: racers.map(() => 0),
      dice: null,
      debug: false,
      forced_twists: [],
      exclude_twists: [],
    };
  });

  const [result, setResult] = useState<SimulationResultDTO | null>(null);
  const [stepIndex, setStepIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speedMs, setSpeedMs] = useState(450);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runSim = useCallback(
    async (req: SimulationRequestDTO) => {
      setRunning(true);
      setPlaying(false);
      setError(null);
      try {
        const res = await client.runSimulation(req);
        setResult(res);
        setStepIndex(0);
        setUrlState({ tab: "simulator", config: res.config_str });
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setRunning(false);
      }
    },
    [client],
  );

  const importAndRun = useCallback(
    async (raw: string) => {
      const decoded = await client.decodeSimConfig(raw);
      setConfig(decoded);
      await runSim(decoded);
    },
    [client, runSim],
  );

  // Consume incoming config from Raw Data click or URL query param
  useEffect(() => {
    if (incomingConfigStr) {
      importAndRun(incomingConfigStr).finally(() => {
        onConsumedIncomingConfig();
      });
    }
  }, [incomingConfigStr, importAndRun, onConsumedIncomingConfig]);

  // Auto-run once on initial mount if no incoming config
  useEffect(() => {
    if (!incomingConfigStr && !result && !running) {
      void runSim(config);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const currentStep = result?.steps[stepIndex] ?? null;
  const currentBoard =
    result && currentStep
      ? result.board_states[currentStep.board_state_idx] ??
        result.board_states[0]
      : null;

  return (
    <div className="flex flex-col gap-4 lg:flex-row lg:items-start">
      <SimulatorConfigPanel
        simMeta={simMeta}
        config={config}
        onChange={setConfig}
        configStr={result?.config_str ?? ""}
        onImportConfigStr={importAndRun}
        onRun={() => void runSim(config)}
        running={running}
      />

      <div className="min-w-0 flex-1 space-y-4">
        {error && (
          <div className="rounded-lg border border-rose-500/40 bg-rose-950/50 p-3 text-xs text-rose-200">
            {error}
          </div>
        )}

        {result && currentStep && currentBoard ? (
          <>
            <RaceTrackSVG
              step={currentStep}
              board={currentBoard}
              racerPalettes={simMeta.racer_palettes}
            />

            <PlaybackBar
              steps={result.steps}
              stepIndex={stepIndex}
              onStepChange={setStepIndex}
              playing={playing}
              onPlayingChange={setPlaying}
              speedMs={speedMs}
              onSpeedChange={setSpeedMs}
            />

            {/* Racer Status Cards */}
            <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3 xl:grid-cols-6">
              {currentStep.names.map((name, idx) => {
                const palette = simMeta.racer_palettes[name];
                const isCurrent = currentStep.current_racer === idx;
                const rank = currentStep.finish_order.indexOf(idx);
                return (
                  <div
                    key={`${name}-${idx}`}
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
                          style={{
                            backgroundColor: palette?.primary ?? "#818cf8",
                          }}
                        />
                        <span className="truncate font-semibold text-white">
                          {name}
                        </span>
                      </div>
                      {rank >= 0 && (
                        <span className="rounded bg-amber-500/20 px-1.5 py-0.5 text-[10px] font-bold text-amber-300">
                          #{rank + 1}
                        </span>
                      )}
                    </div>
                    <div className="mt-1.5 flex items-center justify-between text-[11px] text-slate-400">
                      <span>
                        Tile:{" "}
                        <strong className="text-slate-200">
                          {currentStep.positions[idx] ?? "—"}
                        </strong>
                      </span>
                      <span>
                        VP:{" "}
                        <strong className="text-sky-300">
                          {currentStep.vp[idx]}
                        </strong>
                      </span>
                    </div>
                    {(currentStep.tripped[idx] ||
                      currentStep.eliminated[idx] ||
                      currentStep.sidelined[idx]) && (
                      <div className="mt-1 flex flex-wrap gap-1">
                        {currentStep.tripped[idx] && (
                          <span className="rounded bg-rose-500/20 px-1.5 py-0.5 text-[9px] font-semibold text-rose-300">
                            TRIPPED
                          </span>
                        )}
                        {currentStep.eliminated[idx] && (
                          <span className="rounded bg-slate-700 px-1.5 py-0.5 text-[9px] font-semibold text-slate-300">
                            ELIMINATED
                          </span>
                        )}
                        {currentStep.sidelined[idx] && (
                          <span className="rounded bg-amber-500/20 px-1.5 py-0.5 text-[9px] font-semibold text-amber-300">
                            SIDELINED
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            <LogViewer
              logs={result.logs}
              steps={result.steps}
              activeStepIndex={stepIndex}
              racerNames={currentStep.names}
              onJumpToStep={(sIdx) => {
                setPlaying(false);
                setStepIndex(sIdx);
              }}
            />
          </>
        ) : (
          <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-12 text-center text-xs text-slate-400">
            {running
              ? "Running race simulation..."
              : "Configure racers and click Run Simulation."}
          </div>
        )}
      </div>
    </div>
  );
}
